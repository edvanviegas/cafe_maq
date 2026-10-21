"""
CafeMaq - aplicação Flask

Rodar no computador:
    pip install -r requirements.txt
    copie .env.example para .env e preencha
    python app.py
e abrir http://localhost:5000
"""
from flask import Flask, jsonify, render_template, request
from werkzeug.middleware.proxy_fix import ProxyFix

import banco
import utils
from catalogo import TIPOS
from rotas import api, auth, dono, funcionario, publico

MENSAGENS_ERRO = {
    400: 'Requisição inválida.',
    401: 'Entre na sua conta para continuar.',
    403: 'Você não tem permissão para isso.',
    404: 'Página não encontrada.',
    405: 'Método não permitido para este endereço.',
    409: 'Conflito com os dados atuais.',
    413: 'Envio grande demais.',
    429: 'Muitas tentativas. Aguarde um pouco.',
    500: 'Erro interno. Tente novamente em instantes.',
}


def criar_app():
    app = Flask(__name__)
    app.config.from_object('config')

    if app.config['PRODUCAO']:
        # Atrás do proxy da hospedagem: confia no IP real enviado em X-Forwarded-For (usado nos logs)
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    utils.configurar_log(app)
    banco.criar_banco(app)
    app.teardown_appcontext(banco.fechar)

    # Ordem importa: primeiro confere a sessão (inatividade), depois o token CSRF
    app.before_request(utils.controlar_sessao)
    app.before_request(utils.verificar_csrf)
    app.after_request(utils.cabecalhos_seguranca)

    for bp in (publico.bp, auth.bp, dono.bp, funcionario.bp, api.bp):
        app.register_blueprint(bp)

    app.jinja_env.filters.update(utils.FILTROS)
    app.jinja_env.globals['ic'] = utils.ic

    @app.context_processor
    def variaveis_dos_templates():
        return {
            'usuario': utils.usuario(),
            'fazenda': utils.fazenda_atual(),
            'csrf_campo': utils.csrf_campo,
            'csrf_token': utils.csrf_token,
            'hoje': utils.hoje(),
            'ano_atual': utils.hoje()[:4],
            'TIPOS': TIPOS,
            'google_client_id': app.config['GOOGLE_CLIENT_ID'],
        }

    def tratar_erro(erro):
        """Páginas de erro amigáveis; na API devolve JSON {"erro": "..."}."""
        codigo = getattr(erro, 'code', 500) or 500
        mensagem = getattr(erro, 'description', None) if codigo != 500 else None
        if not mensagem or str(mensagem).startswith(('The ', 'You ')):  # textos padrão do Werkzeug em inglês
            mensagem = MENSAGENS_ERRO.get(codigo, 'Erro inesperado.')
        if codigo == 500:
            utils.log_seguranca.exception('Erro interno em %s %s', request.method, request.path)
        if request.path.startswith('/api/'):
            return jsonify(erro=mensagem), codigo
        return render_template('erro.html', mensagem=mensagem, voltar=request.referrer), codigo

    for codigo in MENSAGENS_ERRO:
        app.register_error_handler(codigo, tratar_erro)

    return app


app = criar_app()

if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'])
