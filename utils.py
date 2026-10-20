"""Funções auxiliares: datas, formatação, segurança (CSRF, sessão, logs, senhas) e login."""
import logging
import os
import re
import secrets
from datetime import datetime, timedelta

from flask import abort, current_app, flash, g, jsonify, redirect, request, session, url_for
from markupsafe import Markup, escape

from banco import consulta, definir_usuario_app, inserir, um, valor
from catalogo import intervalo_revisao

FORMATO = '%Y-%m-%d %H:%M:%S'

# ===================== Datas =====================


def _fuso():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(current_app.config['FUSO_HORARIO'])
    except Exception:
        return None  # sem base de fusos (Windows sem o pacote tzdata): usa a hora do computador


def agora_dt():
    return datetime.now(_fuso()).replace(tzinfo=None, microsecond=0)


def agora():
    return agora_dt().strftime(FORMATO)


def hoje():
    return agora_dt().strftime('%Y-%m-%d')


def data_iso(dt):
    return dt.strftime('%Y-%m-%d')


def para_data(texto):
    """Converte 'AAAA-MM-DD' (ou com hora) em datetime; None se inválido."""
    if not texto:
        return None
    for formato in (FORMATO, '%Y-%m-%d'):
        try:
            return datetime.strptime(str(texto)[:19], formato)
        except ValueError:
            pass
    return None


def duracao_ponto(entrada, saida):
    """Horas entre entrada e saída; registros ainda abertos contam até agora."""
    fim = para_data(saida) if saida else agora_dt()
    return max(0.0, (fim - para_data(entrada)).total_seconds() / 3600)


def dias_atras(n):
    return data_iso(agora_dt() - timedelta(days=n))


# ===================== Formatação (filtros do Jinja) =====================


def data_br(texto):
    d = para_data(texto)
    return d.strftime('%d/%m/%Y') if d else '—'


def hora_br(texto):
    d = para_data(texto)
    return d.strftime('%H:%M') if d else '—'


def num_br(valor, casas=1):
    texto = f'{float(valor or 0):,.{casas}f}'
    return texto.replace(',', '_').replace('.', ',').replace('_', '.')


def reais(valor):
    return 'R$ ' + num_br(valor, 2)


def horas_br(horas):
    horas = float(horas or 0)
    h = int(horas)
    m = round((horas - h) * 60)
    if m == 60:
        h, m = h + 1, 0
    return f'{h}h{m:02d}'


def nl2br(texto):
    return Markup('<br>'.join(escape(texto or '').split('\n')))


def primeiro_nome(nome):
    return (nome or '').split(' ')[0]


def ic(nome, classe=''):
    """Ícone de traço sem cor (desenhos em templates/_icones.html)."""
    extra = ' ' + classe if classe else ''
    return Markup('<svg class="ic%s" aria-hidden="true"><use href="#ic-%s"></use></svg>' % (extra, escape(nome)))


FILTROS = {
    'data_br': data_br,
    'hora_br': hora_br,
    'num_br': num_br,
    'reais': reais,
    'horas_br': horas_br,
    'nl2br': nl2br,
    'primeiro_nome': primeiro_nome,
}

# ===================== Formulários =====================


def campo(nome, padrao=''):
    return (request.form.get(nome) or padrao).strip()


def numero_ou_nulo(texto):
    texto = str(texto or '').replace(',', '.').strip()
    try:
        return float(texto)
    except ValueError:
        return None


def inteiro(texto, padrao=0):
    try:
        return int(texto)
    except (TypeError, ValueError):
        return padrao


# ===================== Segurança: CSRF =====================

METODOS_QUE_ALTERAM = ('POST', 'PUT', 'PATCH', 'DELETE')


def csrf_token():
    if 'csrf' not in session:
        session['csrf'] = secrets.token_hex(32)
    return session['csrf']


def csrf_campo():
    return Markup(f'<input type="hidden" name="csrf" value="{csrf_token()}">')


def verificar_csrf():
    """Roda antes de toda requisição que altera dados (registrado em app.py).

    Formulários mandam o token no campo "csrf"; o JavaScript (fetch) manda no
    cabeçalho X-CSRF-Token. Sem o token certo, a requisição é recusada.
    """
    if request.method not in METODOS_QUE_ALTERAM:
        return
    enviado = request.form.get('csrf') or request.headers.get('X-CSRF-Token', '')
    if not secrets.compare_digest(csrf_token(), enviado):
        abort(400, 'Sessão expirada. Volte e tente novamente.')


# ===================== Segurança: cabeçalhos HTTP =====================


def cabecalhos_seguranca(resposta):
    """Cabeçalhos que dificultam ataques comuns no navegador (registrado em app.py)."""
    resposta.headers.setdefault('X-Content-Type-Options', 'nosniff')          # não "adivinha" o tipo do arquivo
    resposta.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')              # impede o site dentro de iframe alheio
    resposta.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    resposta.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
    if current_app.config['PRODUCAO']:
        resposta.headers.setdefault('Strict-Transport-Security', 'max-age=31536000')  # força HTTPS
    if session.get('uid'):
        resposta.headers.setdefault('Cache-Control', 'no-store')              # páginas logadas não ficam em cache
    return resposta


# ===================== Segurança: logs =====================

log_seguranca = logging.getLogger('cafemaq.seguranca')


def configurar_log(app):
    """Grava os eventos de segurança também em logs/seguranca.log (além da tabela log_acesso)."""
    caminho = app.config['LOG_ARQUIVO']
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    if not log_seguranca.handlers:
        arquivo = logging.FileHandler(caminho, encoding='utf-8')
        arquivo.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        log_seguranca.addHandler(arquivo)
        log_seguranca.setLevel(logging.INFO)


def ip_cliente():
    return (request.remote_addr or '')[:45]


def registrar_evento(evento, email=None, usuario_id=None):
    """Registra um evento de segurança (login, falha, bloqueio, saída...) no banco e no arquivo de log."""
    navegador = (request.headers.get('User-Agent') or '')[:255]
    try:
        inserir('INSERT INTO log_acesso (usuario_id, email, evento, ip, navegador, criado_em) VALUES (?, ?, ?, ?, ?, ?)',
                (usuario_id, (email or '').lower()[:255] or None, evento, ip_cliente(), navegador, agora()))
    except Exception:  # o log nunca pode derrubar o login
        log_seguranca.exception('Falha ao gravar log_acesso')
    nivel = logging.WARNING if evento in ('login_falha', 'login_bloqueado', 'acesso_negado') else logging.INFO
    log_seguranca.log(nivel, 'evento=%s email=%s usuario=%s ip=%s', evento, email, usuario_id, ip_cliente())


# ===================== Segurança: força bruta =====================

SQL_FALHAS_RECENTES = '''SELECT COUNT(*) FROM log_acesso
                         WHERE evento = 'login_falha' AND criado_em >= ? AND (ip = ? OR email = ?)'''


def login_bloqueado(email):
    """True se este e-mail ou este IP erraram a senha demais dentro da janela de tempo (config.py)."""
    cfg = current_app.config
    desde = (agora_dt() - cfg['LOGIN_JANELA']).strftime(FORMATO)
    falhas = valor(SQL_FALHAS_RECENTES, (desde, ip_cliente(), (email or '').lower()))
    return (falhas or 0) >= cfg['LOGIN_MAX_TENTATIVAS']


# ===================== Segurança: política de senha =====================


def problemas_senha(senha, email=''):
    """Política de senhas: devolve a lista do que falta (lista vazia = senha aceita)."""
    erros = []
    if len(senha) < 8:
        erros.append('A senha precisa ter pelo menos 8 caracteres.')
    if not re.search(r'[A-Za-zÀ-ÿ]', senha) or not re.search(r'\d', senha):
        erros.append('A senha precisa ter letras e números.')
    if email and senha.lower() in (email.lower(), email.lower().split('@')[0]):
        erros.append('A senha não pode ser igual ao seu e-mail.')
    return erros


# ===================== Segurança: sessão =====================


def controlar_sessao():
    """Encerra a sessão parada há mais tempo que SESSAO_INATIVIDADE e avisa o banco quem está logado."""
    uid = session.get('uid')
    if uid:
        ultimo = session.get('ultimo_acesso')
        limite = current_app.config['SESSAO_INATIVIDADE'].total_seconds()
        agora_ts = datetime.now().timestamp()
        if ultimo and agora_ts - ultimo > limite:
            registrar_evento('sessao_expirada', usuario_id=uid)
            session.clear()
            g.pop('usuario', None)
            flash('Sua sessão expirou por inatividade. Entre novamente.', 'info')
            uid = None
        else:
            session['ultimo_acesso'] = agora_ts
    definir_usuario_app(uid)


# ===================== Login =====================


def usuario():
    if 'usuario' not in g:
        uid = session.get('uid')
        g.usuario = um('SELECT * FROM usuarios WHERE id = ?', (uid,)) if uid else None
    return g.usuario


def fazer_login(conta, evento='login_ok'):
    """Começa uma sessão nova (evita fixação de sessão), com token CSRF novo, e registra o login."""
    session.clear()
    session.permanent = True  # respeita PERMANENT_SESSION_LIFETIME (config.py)
    session['uid'] = conta['id']
    session['ultimo_acesso'] = datetime.now().timestamp()
    session['csrf'] = secrets.token_hex(32)
    g.pop('usuario', None)
    definir_usuario_app(conta['id'])
    registrar_evento(evento, conta['email'], conta['id'])
    if conta['tipo'] == 'funcionario':
        vincular_funcionario(conta)


def pagina_inicial(conta):
    return url_for('dono.index') if conta['tipo'] == 'dono' else url_for('funcionario.index')


def exigir_login(tipo):
    """Controle de acesso: usado no before_request dos painéis e da API.

    Devolve uma resposta (redirect ou JSON 401/403) se a pessoa não puder entrar.
    """
    u = usuario()
    quer_json = request.path.startswith('/api/')
    if not u:
        if quer_json:
            return jsonify(erro='Entre na sua conta para continuar.'), 401
        flash('Entre na sua conta para continuar.', 'info')
        return redirect(url_for('auth.entrar'))
    if u['tipo'] != tipo:
        registrar_evento('acesso_negado', u['email'], u['id'])
        if quer_json:
            return jsonify(erro='Você não tem permissão para isso.'), 403
        return redirect(pagina_inicial(u))
    return None


def vincular_funcionario(conta):
    """Liga a conta do funcionário aos cadastros feitos pelo dono com o mesmo e-mail."""
    consulta('UPDATE funcionarios SET usuario_id = ? WHERE usuario_id IS NULL AND LOWER(email) = LOWER(?)',
             (conta['id'], conta['email']))


# ===================== Fazenda / vínculo =====================


def fazenda_atual():
    """Fazenda selecionada pelo dono (ou a primeira dele)."""
    u = usuario()
    if not u or u['tipo'] != 'dono':
        return None
    f = um('SELECT * FROM fazendas WHERE id = ? AND dono_id = ?', (session.get('fazenda_id', 0), u['id']))
    if not f:
        f = um('SELECT * FROM fazendas WHERE dono_id = ? ORDER BY id LIMIT 1', (u['id'],))
        if f:
            session['fazenda_id'] = f['id']
    return f


def vinculo_atual():
    """Cadastro de funcionário (vínculo com a fazenda) do usuário logado."""
    return um(
        '''SELECT f.*, fz.nome AS fazenda_nome FROM funcionarios f
           JOIN fazendas fz ON fz.id = f.fazenda_id
           WHERE f.usuario_id = ? AND f.ativo = 1 ORDER BY f.id LIMIT 1''',
        (usuario()['id'],))


def ponto_aberto(funcionario_id):
    return um('SELECT * FROM ponto WHERE funcionario_id = ? AND saida IS NULL ORDER BY entrada DESC LIMIT 1',
              (funcionario_id,))


# ===================== Máquinas =====================


def situacao_revisao(maquina):
    """Situação da revisão preventiva pelo horímetro.

    A máquina precisa trazer 'ultima_preventiva' (horímetro da última preventiva ou None).
    """
    intervalo = intervalo_revisao(maquina)
    if maquina.get('ultima_preventiva') is None:
        return {'estado': 'sem', 'intervalo': intervalo, 'desde': None, 'faltam': None}
    desde = float(maquina['horimetro']) - float(maquina['ultima_preventiva'])
    faltam = intervalo - desde
    if faltam <= 0:
        estado = 'vencida'
    elif faltam <= intervalo * 0.1:
        estado = 'proxima'
    else:
        estado = 'ok'
    return {'estado': estado, 'intervalo': intervalo, 'desde': desde, 'faltam': faltam}
