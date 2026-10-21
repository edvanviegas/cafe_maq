"""Login, cadastro, login com Google e saída."""
import json
import re
import time
import urllib.parse
import urllib.request

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from banco import consulta, inserir, um
from utils import agora, campo, fazer_login, login_bloqueado, pagina_inicial, problemas_senha, registrar_evento, usuario

bp = Blueprint('auth', __name__)

EMAIL_VALIDO = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


@bp.route('/entrar', methods=['GET', 'POST'])
def entrar():
    if usuario():
        return redirect(pagina_inicial(usuario()))

    email = ''
    if request.method == 'POST':
        email = campo('email').lower()

        # Proteção contra força bruta: muitas senhas erradas seguidas bloqueiam por um tempo
        if login_bloqueado(email):
            registrar_evento('login_bloqueado', email)
            minutos = int(current_app.config['LOGIN_JANELA'].total_seconds() // 60)
            flash(f'Muitas tentativas erradas. Aguarde {minutos} minutos e tente de novo.', 'erro')
            return render_template('auth/entrar.html', email=email), 429

        conta = um('SELECT * FROM usuarios WHERE LOWER(email) = ?', (email,))

        if conta and conta['senha_hash'] and check_password_hash(conta['senha_hash'], campo('senha')):
            fazer_login(conta)
            return redirect(pagina_inicial(conta))

        registrar_evento('login_falha', email, conta['id'] if conta else None)
        if conta and not conta['senha_hash']:
            flash('Esta conta foi criada com o Google. Use o botão "Continuar com o Google".', 'erro')
        else:
            # Mesma mensagem para e-mail inexistente e senha errada: não revela quais e-mails têm conta
            flash('E-mail ou senha incorretos.', 'erro')

    return render_template('auth/entrar.html', email=email)


@bp.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if usuario():
        return redirect(pagina_inicial(usuario()))

    dados = {'nome': '', 'email': '', 'tipo': 'dono'}
    erros = []

    if request.method == 'POST':
        dados = {'nome': campo('nome'), 'email': campo('email').lower(), 'tipo': campo('tipo')}
        senha = campo('senha')

        if not 3 <= len(dados['nome']) <= 120:
            erros.append('Informe seu nome completo.')
        if not EMAIL_VALIDO.match(dados['email']) or len(dados['email']) > 255:
            erros.append('E-mail inválido.')
        erros.extend(problemas_senha(senha, dados['email']))  # política de senhas (utils.py)
        if senha != campo('senha2'):
            erros.append('As senhas não conferem.')
        if dados['tipo'] not in ('dono', 'funcionario'):
            erros.append('Escolha o tipo de conta.')
        if not erros and um('SELECT id FROM usuarios WHERE LOWER(email) = ?', (dados['email'],)):
            erros.append('Já existe uma conta com este e-mail.')

        if not erros:
            novo_id = inserir(
                'INSERT INTO usuarios (nome, email, senha_hash, tipo, criado_em) VALUES (?, ?, ?, ?, ?)',
                (dados['nome'], dados['email'], generate_password_hash(senha), dados['tipo'], agora()))
            novo = um('SELECT * FROM usuarios WHERE id = ?', (novo_id,))
            fazer_login(novo, evento='cadastro')
            flash('Conta criada! Bem-vindo(a) ao CafeMaq.', 'sucesso')
            return redirect(pagina_inicial(novo))

    return render_template('auth/cadastro.html', dados=dados, erros=erros)


@bp.route('/sair')
def sair():
    if usuario():
        registrar_evento('logout', usuario()['email'], usuario()['id'])
    session.clear()
    return redirect(url_for('publico.index'))


def validar_token_google(token):
    """Pergunta ao Google se o token é legítimo e devolve os dados da pessoa."""
    url = 'https://oauth2.googleapis.com/tokeninfo?id_token=' + urllib.parse.quote(token)
    try:
        with urllib.request.urlopen(url, timeout=10) as resposta:
            dados = json.load(resposta)
    except Exception:
        return None

    valido = (dados.get('aud') == current_app.config['GOOGLE_CLIENT_ID']
              and dados.get('iss') in ('accounts.google.com', 'https://accounts.google.com')
              and dados.get('email_verified') == 'true'
              and int(dados.get('exp', 0)) > time.time())
    return dados if valido else None


@bp.route('/google', methods=['POST'])
def google():
    """Recebe o token do "Continuar com o Google" e faz o login (ou pede o tipo de conta)."""
    if not current_app.config['GOOGLE_CLIENT_ID']:
        return redirect(url_for('auth.entrar'))

    dados = validar_token_google(campo('credential'))
    if not dados:
        registrar_evento('login_falha')  # token do Google inválido
        flash('Não foi possível validar o login com o Google. Tente novamente.', 'erro')
        return redirect(url_for('auth.entrar'))

    conta = (um('SELECT * FROM usuarios WHERE google_id = ?', (dados['sub'],))
             or um('SELECT * FROM usuarios WHERE LOWER(email) = LOWER(?)', (dados['email'],)))
    if conta:
        if not conta['google_id']:
            consulta('UPDATE usuarios SET google_id = ? WHERE id = ?', (dados['sub'], conta['id']))
        fazer_login(conta, evento='login_google')
        return redirect(pagina_inicial(conta))

    # Primeiro acesso: guarda os dados e pergunta se é dono ou funcionário
    session['google_pendente'] = {
        'sub': dados['sub'],
        'email': dados['email'].lower(),
        'nome': dados.get('name') or dados['email'],
    }
    return redirect(url_for('auth.escolher_tipo'))


@bp.route('/escolher-tipo', methods=['GET', 'POST'])
def escolher_tipo():
    """Primeiro acesso pelo Google: a pessoa escolhe se é dono ou funcionário."""
    google = session.get('google_pendente')
    if not google:
        return redirect(url_for('auth.entrar'))

    if request.method == 'POST':
        tipo = campo('tipo')
        if tipo in ('dono', 'funcionario'):
            novo_id = inserir(
                'INSERT INTO usuarios (nome, email, google_id, tipo, criado_em) VALUES (?, ?, ?, ?, ?)',
                (google['nome'], google['email'], google['sub'], tipo, agora()))
            novo = um('SELECT * FROM usuarios WHERE id = ?', (novo_id,))
            fazer_login(novo, evento='cadastro')
            flash('Conta criada! Bem-vindo(a) ao CafeMaq.', 'sucesso')
            return redirect(pagina_inicial(novo))
        flash('Escolha o tipo de conta.', 'erro')

    return render_template('auth/escolher_tipo.html', google=google)
