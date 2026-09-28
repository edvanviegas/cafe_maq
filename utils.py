"""Funções auxiliares: datas, formatação, segurança (CSRF) e login."""
import secrets
from datetime import datetime, timedelta

from flask import abort, current_app, flash, g, redirect, request, session, url_for
from markupsafe import Markup, escape

from banco import consulta, um
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


# ===================== Segurança (CSRF) =====================


def csrf_token():
    if 'csrf' not in session:
        session['csrf'] = secrets.token_hex(32)
    return session['csrf']


def csrf_campo():
    return Markup(f'<input type="hidden" name="csrf" value="{csrf_token()}">')


def verificar_csrf():
    """Roda antes de toda requisição POST (registrado em app.py)."""
    if request.method == 'POST' and not secrets.compare_digest(csrf_token(), request.form.get('csrf', '')):
        abort(400, 'Sessão expirada. Volte e tente novamente.')


# ===================== Login =====================


def usuario():
    if 'usuario' not in g:
        uid = session.get('uid')
        g.usuario = um('SELECT * FROM usuarios WHERE id = ?', (uid,)) if uid else None
    return g.usuario


def fazer_login(conta):
    csrf = session.get('csrf')
    session.clear()
    session['uid'] = conta['id']
    if csrf:
        session['csrf'] = csrf
    g.pop('usuario', None)
    if conta['tipo'] == 'funcionario':
        vincular_funcionario(conta)


def pagina_inicial(conta):
    return url_for('dono.index') if conta['tipo'] == 'dono' else url_for('funcionario.index')


def exigir_login(tipo):
    """Usado no before_request dos painéis. Devolve um redirect se não puder entrar."""
    u = usuario()
    if not u:
        flash('Entre na sua conta para continuar.', 'info')
        return redirect(url_for('auth.entrar'))
    if u['tipo'] != tipo:
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
