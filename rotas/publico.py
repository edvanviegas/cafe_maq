"""Site institucional: catálogo, calculadora, dicas e sobre."""
from flask import Blueprint, render_template

bp = Blueprint('publico', __name__)


@bp.route('/')
def index():
    return render_template('publico/index.html')


@bp.route('/maquinas')
def maquinas():
    return render_template('publico/maquinas.html')


@bp.route('/calculadora')
def calculadora():
    return render_template('publico/calculadora.html')


@bp.route('/manutencao')
def manutencao():
    return render_template('publico/manutencao.html')


@bp.route('/sobre')
def sobre():
    return render_template('publico/sobre.html')
