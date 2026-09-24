"""
CafeMaq - aplicação Flask

Rodar no computador:
    pip install -r requirements.txt
    python app.py
e abrir http://localhost:5000
"""
from flask import Flask, render_template, request

import banco
import utils
from catalogo import TIPOS
from rotas import api, auth, dono, funcionario, publico


def criar_app():
    app = Flask(__name__)
    app.config.from_object('config')

    banco.criar_banco(app)
    app.teardown_appcontext(banco.fechar)
    app.before_request(utils.verificar_csrf)

    for bp in (publico.bp, auth.bp, dono.bp, funcionario.bp, api.bp):
        app.register_blueprint(bp)

    app.jinja_env.filters.update(utils.FILTROS)

    @app.context_processor
    def variaveis_dos_templates():
        return {
            'usuario': utils.usuario(),
            'fazenda': utils.fazenda_atual(),
            'csrf_campo': utils.csrf_campo,
            'hoje': utils.hoje(),
            'ano_atual': utils.hoje()[:4],
            'TIPOS': TIPOS,
            'google_client_id': app.config['GOOGLE_CLIENT_ID'],
        }

    @app.errorhandler(400)
    def requisicao_invalida(erro):
        return render_template('erro.html', mensagem=erro.description, voltar=request.referrer), 400

    @app.errorhandler(404)
    def nao_encontrado(_erro):
        return render_template('erro.html', mensagem='Página não encontrada.', voltar=None), 404

    return app


app = criar_app()

if __name__ == '__main__':
    app.run(debug=True)
