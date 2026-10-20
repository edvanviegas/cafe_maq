"""
API de máquinas (JSON), usada pelo cadastro de máquinas do painel do dono.

    GET /api/catalogo                 tipos de máquina com dados de referência
    GET /api/catalogo/<tipo>          um tipo, com marcas, modelos e checklist preventivo
    GET /api/catalogo/busca?q=arbus   procura marca/modelo em todos os tipos
    GET /api/maquinas                 máquinas cadastradas na fazenda atual (dono logado)
    GET /api/maquinas/<id>            uma máquina com situação da revisão e histórico
"""
from flask import Blueprint, abort, jsonify, request

from banco import todos, um
from catalogo import TIPOS, buscar_modelos, ficha_tipo, nome_tipo
from utils import fazenda_atual, situacao_revisao

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/catalogo')
def catalogo():
    return jsonify([ficha_tipo(tipo) for tipo in TIPOS])


@bp.route('/catalogo/busca')
def busca():
    return jsonify(buscar_modelos(request.args.get('q', '')))


@bp.route('/catalogo/<tipo>')
def catalogo_tipo(tipo):
    if tipo not in TIPOS:
        abort(404)
    return jsonify(ficha_tipo(tipo))


def fazenda_ou_401():
    fazenda = fazenda_atual()
    if not fazenda:
        abort(401)
    return fazenda


SQL_MAQUINA = '''SELECT m.*,
                        (SELECT MAX(horimetro) FROM manutencoes WHERE maquina_id = m.id AND tipo = 'preventiva') AS ultima_preventiva,
                        (SELECT COUNT(*) FROM ocorrencias WHERE maquina_id = m.id AND status = 'aberta') AS problemas_abertos
                 FROM maquinas m WHERE m.fazenda_id = ?'''


def maquina_json(m):
    return {
        'id': m['id'],
        'nome': m['nome'],
        'tipo': m['tipo'],
        'tipo_nome': nome_tipo(m['tipo']),
        'marca': m['marca'],
        'modelo': m['modelo'],
        'ano': m['ano'],
        'horimetro': m['horimetro'],
        'ativo': bool(m['ativo']),
        'problemas_abertos': m['problemas_abertos'],
        'revisao': situacao_revisao(m),
    }


@bp.route('/maquinas')
def maquinas():
    fazenda = fazenda_ou_401()
    return jsonify([maquina_json(m) for m in todos(SQL_MAQUINA + ' ORDER BY m.nome', (fazenda['id'],))])


@bp.route('/maquinas/<int:maquina_id>')
def maquina(maquina_id):
    fazenda = fazenda_ou_401()
    m = um(SQL_MAQUINA + ' AND m.id = ?', (fazenda['id'], maquina_id))
    if not m:
        abort(404)
    dados = maquina_json(m)
    dados['itens_preventivos'] = TIPOS.get(m['tipo'], TIPOS['outra'])['itens_preventivos']
    dados['manutencoes'] = todos('SELECT data, tipo, descricao, custo, horimetro FROM manutencoes '
                                 'WHERE maquina_id = ? ORDER BY data DESC, id DESC', (m['id'],))
    return jsonify(dados)
