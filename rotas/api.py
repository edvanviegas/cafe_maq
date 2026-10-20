"""
API REST do CafeMaq (JSON).

Cada operação do CRUD usa o método HTTP correspondente:

    GET     ler (lista ou um item)          200 OK
    POST    criar                           201 Created
    PUT     alterar o registro inteiro      200 OK
    PATCH   alterar só um campo (ativo/status)  200 OK
    DELETE  excluir                         200 OK

Erros: 401 (sem login), 403 (sem permissão), 404 (não existe ou é de outra
fazenda), 409 (conflito, ex.: excluir máquina com histórico) e 422 (dados
inválidos, com a lista em "erros").

Catálogo (público):
    GET  /api/catalogo                    tipos de máquina com dados de referência
    GET  /api/catalogo/<tipo>             um tipo, com marcas, modelos e checklist preventivo
    GET  /api/catalogo/busca?q=arbus      procura marca/modelo em todos os tipos

Dados da fazenda (só o dono logado, e só os registros da fazenda dele):
    /api/maquinas        GET, POST       /api/maquinas/<id>      GET, PUT, PATCH, DELETE
    /api/funcionarios    GET, POST       /api/funcionarios/<id>  GET, PUT, PATCH, DELETE
    /api/atividades      GET, POST       /api/atividades/<id>    GET, PUT, PATCH, DELETE
    /api/fazendas        GET, POST       /api/fazendas/<id>      GET, PUT, DELETE
    GET /api/fazenda/custos?inicio=AAAA-MM-DD&fim=AAAA-MM-DD   (procedimento sp_resumo_custos no MySQL)

Toda requisição que altera dados precisa do cabeçalho X-CSRF-Token (ver utils.verificar_csrf).
"""
from datetime import datetime

from flask import Blueprint, abort, flash, g, jsonify, request, session, url_for

from banco import alterados, chamar_procedimento, consulta, eh_mysql, inserir, todos, um, valor
from catalogo import TIPOS, buscar_modelos, ficha_tipo, nome_tipo
from rotas.auth import EMAIL_VALIDO
from utils import agora, dias_atras, exigir_login, fazenda_atual, hoje, situacao_revisao, usuario

bp = Blueprint('api', __name__, url_prefix='/api')


# ===================== Ajudantes =====================


def dados_recebidos():
    """Aceita JSON (fetch) ou formulário comum."""
    return request.get_json(silent=True) or request.form.to_dict()


def texto(dados, chave, limite):
    return str(dados.get(chave) or '').strip()[:limite]


def numero(dados, chave):
    bruto = str(dados.get(chave) if dados.get(chave) is not None else '').replace(',', '.').strip()
    if not bruto:
        return None
    try:
        return float(bruto)
    except ValueError:
        return 'invalido'


def inteiro_ou_none(dados, chave):
    try:
        return int(dados.get(chave))
    except (TypeError, ValueError):
        return None


def verdadeiro(dados, chave):
    return str(dados.get(chave, '')).lower() in ('1', 'true', 'on', 'sim')


def data_valida(textodata):
    if not textodata:
        return None
    try:
        return datetime.strptime(textodata, '%Y-%m-%d').strftime('%Y-%m-%d')
    except ValueError:
        return 'invalida'


def erro_validacao(erros):
    return jsonify(erros=erros, erro=erros[0]), 422


def sucesso(mensagem, codigo=200, **extra):
    """Resposta de sucesso. A mensagem também vira um aviso na próxima página (flash)."""
    flash(mensagem, 'sucesso')
    return jsonify(mensagem=mensagem, **extra), codigo


@bp.before_request
def proteger():
    """O catálogo é público; o resto da API é só para o dono logado, com fazenda cadastrada."""
    if request.endpoint and request.endpoint.startswith('api.catalogo'):
        return None
    bloqueio = exigir_login('dono')
    if bloqueio:
        return bloqueio
    g.fazenda = fazenda_atual()
    if not g.fazenda and not request.path.startswith('/api/fazendas'):
        return jsonify(erro='Cadastre sua fazenda primeiro.'), 409
    return None


# ===================== Catálogo (público) =====================


@bp.get('/catalogo')
def catalogo():
    return jsonify([ficha_tipo(tipo) for tipo in TIPOS])


@bp.get('/catalogo/busca')
def catalogo_busca():
    return jsonify(buscar_modelos(request.args.get('q', '')[:60]))


@bp.get('/catalogo/<tipo>')
def catalogo_tipo(tipo):
    if tipo not in TIPOS:
        abort(404)
    return jsonify(ficha_tipo(tipo))


# ===================== Máquinas =====================

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
        'revisao_horas': m['revisao_horas'],
        'preco': m['preco'],
        'ativo': bool(m['ativo']),
        'problemas_abertos': m['problemas_abertos'],
        'revisao': situacao_revisao(m),
    }


def buscar_maquina(maquina_id):
    """Só encontra máquinas da fazenda do dono logado (outra fazenda = 404)."""
    m = um(SQL_MAQUINA + ' AND m.id = ?', (g.fazenda['id'], maquina_id))
    if not m:
        abort(404, 'Máquina não encontrada.')
    return m


def validar_maquina(dados):
    """Valida os dados de uma máquina. Devolve (valores, erros)."""
    erros = []
    tipo = dados.get('tipo') if dados.get('tipo') in TIPOS else 'outra'
    ano, horimetro, revisao, preco = (numero(dados, c) for c in ('ano', 'horimetro', 'revisao_horas', 'preco'))
    ano_max = int(hoje()[:4]) + 1

    if ano == 'invalido' or (ano is not None and not 1950 <= ano <= ano_max):
        erros.append(f'Ano deve estar entre 1950 e {ano_max}.')
    if horimetro == 'invalido' or (horimetro is not None and not 0 <= horimetro <= 1_000_000):
        erros.append('Horímetro inválido.')
    if revisao == 'invalido' or (revisao is not None and not 1 <= revisao <= 100_000):
        erros.append('Intervalo de revisão inválido.')
    if preco == 'invalido' or (preco is not None and not 0 <= preco <= 100_000_000):
        erros.append('Valor inválido.')

    valores = {
        'nome': texto(dados, 'nome', 120) or TIPOS[tipo]['nome'],
        'tipo': tipo,
        'marca': texto(dados, 'marca', 80) or None,
        'modelo': texto(dados, 'modelo', 80) or None,
        'ano': int(ano) if isinstance(ano, float) else None,
        'horimetro': horimetro if isinstance(horimetro, float) else 0,
        'revisao_horas': revisao if isinstance(revisao, float) else None,
        'preco': preco if isinstance(preco, float) else None,
    }
    return valores, erros


@bp.get('/maquinas')
def listar_maquinas():
    return jsonify([maquina_json(m) for m in todos(SQL_MAQUINA + ' ORDER BY m.nome', (g.fazenda['id'],))])


@bp.get('/maquinas/<int:maquina_id>')
def ver_maquina(maquina_id):
    m = buscar_maquina(maquina_id)
    dados = maquina_json(m)
    dados['itens_preventivos'] = TIPOS.get(m['tipo'], TIPOS['outra'])['itens_preventivos']
    dados['manutencoes'] = todos('SELECT data, tipo, descricao, custo, horimetro FROM manutencoes '
                                 'WHERE maquina_id = ? ORDER BY data DESC, id DESC', (m['id'],))
    return jsonify(dados)


@bp.post('/maquinas')
def criar_maquina():
    v, erros = validar_maquina(dados_recebidos())
    if erros:
        return erro_validacao(erros)
    novo_id = inserir('''INSERT INTO maquinas (nome, tipo, marca, modelo, ano, horimetro, revisao_horas, preco,
                                               fazenda_id, criado_em) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (v['nome'], v['tipo'], v['marca'], v['modelo'], v['ano'], v['horimetro'], v['revisao_horas'],
                       v['preco'], g.fazenda['id'], agora()))
    resposta = sucesso('Máquina cadastrada. Os registros de manutenção ficam na aba Manutenção.', 201,
                       maquina=maquina_json(buscar_maquina(novo_id)))
    resposta[0].headers['Location'] = url_for('api.ver_maquina', maquina_id=novo_id)
    return resposta


@bp.put('/maquinas/<int:maquina_id>')
def atualizar_maquina(maquina_id):
    buscar_maquina(maquina_id)
    v, erros = validar_maquina(dados_recebidos())
    if erros:
        return erro_validacao(erros)
    consulta('''UPDATE maquinas SET nome = ?, tipo = ?, marca = ?, modelo = ?, ano = ?, horimetro = ?,
                       revisao_horas = ?, preco = ? WHERE id = ? AND fazenda_id = ?''',
             (v['nome'], v['tipo'], v['marca'], v['modelo'], v['ano'], v['horimetro'], v['revisao_horas'],
              v['preco'], maquina_id, g.fazenda['id']))
    return sucesso('Máquina atualizada.', redirecionar=url_for('dono.maquinas'),
                   maquina=maquina_json(buscar_maquina(maquina_id)))


@bp.patch('/maquinas/<int:maquina_id>')
def ativar_maquina(maquina_id):
    """Ativa ou desativa (a máquina some das listas, mas o histórico fica)."""
    buscar_maquina(maquina_id)
    ativo = 1 if verdadeiro(dados_recebidos(), 'ativo') else 0
    consulta('UPDATE maquinas SET ativo = ? WHERE id = ? AND fazenda_id = ?', (ativo, maquina_id, g.fazenda['id']))
    return sucesso('Máquina reativada.' if ativo else 'Máquina desativada.')


@bp.delete('/maquinas/<int:maquina_id>')
def excluir_maquina(maquina_id):
    m = buscar_maquina(maquina_id)
    historico = valor('''SELECT (SELECT COUNT(*) FROM manutencoes WHERE maquina_id = ?)
                              + (SELECT COUNT(*) FROM ocorrencias WHERE maquina_id = ?)
                              + (SELECT COUNT(*) FROM relatorio_itens WHERE maquina_id = ?)''',
                      (maquina_id, maquina_id, maquina_id))
    if historico:
        # Integridade: apagar a máquina apagaria custos e manutenções dos relatórios
        return jsonify(erro=f'"{m["nome"]}" tem histórico de uso ou manutenção. Desative em vez de excluir, '
                            'para não perder os custos registrados.'), 409
    consulta('DELETE FROM maquinas WHERE id = ? AND fazenda_id = ?', (maquina_id, g.fazenda['id']))
    return sucesso(f'Máquina "{m["nome"]}" excluída.')


# ===================== Funcionários =====================


def buscar_funcionario(funcionario_id):
    f = um('SELECT * FROM funcionarios WHERE id = ? AND fazenda_id = ?', (funcionario_id, g.fazenda['id']))
    if not f:
        abort(404, 'Funcionário não encontrado.')
    return f


def funcionario_json(f):
    return {k: f[k] for k in ('id', 'nome', 'email', 'funcao', 'usuario_id')} | {'ativo': bool(f['ativo'])}


def validar_funcionario(dados, funcionario_id=None):
    """Valida nome/e-mail e procura a conta de funcionário com aquele e-mail. Devolve (valores, erros)."""
    erros = []
    nome = texto(dados, 'nome', 120)
    email = texto(dados, 'email', 255).lower()
    if len(nome) < 2:
        erros.append('Informe o nome do funcionário.')
    if not EMAIL_VALIDO.match(email):
        erros.append('Informe um e-mail válido.')
    conta = None
    if not erros:
        repetido = um('SELECT id FROM funcionarios WHERE fazenda_id = ? AND LOWER(email) = ? AND id <> ?',
                      (g.fazenda['id'], email, funcionario_id or 0))
        if repetido:
            erros.append('Este e-mail já está cadastrado nesta fazenda.')
        conta = um('SELECT id, tipo FROM usuarios WHERE LOWER(email) = ?', (email,))
        if conta and conta['tipo'] != 'funcionario':
            erros.append('Este e-mail pertence a uma conta de dono. O funcionário precisa de uma conta do tipo '
                         '"Funcionário".')
    return {'nome': nome, 'email': email, 'funcao': texto(dados, 'funcao', 80) or None,
            'usuario_id': conta['id'] if conta else None}, erros


@bp.get('/funcionarios')
def listar_funcionarios():
    lista = todos('SELECT * FROM funcionarios WHERE fazenda_id = ? ORDER BY ativo DESC, nome', (g.fazenda['id'],))
    return jsonify([funcionario_json(f) for f in lista])


@bp.get('/funcionarios/<int:funcionario_id>')
def ver_funcionario(funcionario_id):
    return jsonify(funcionario_json(buscar_funcionario(funcionario_id)))


@bp.post('/funcionarios')
def criar_funcionario():
    v, erros = validar_funcionario(dados_recebidos())
    if erros:
        return erro_validacao(erros)
    novo_id = inserir('''INSERT INTO funcionarios (fazenda_id, usuario_id, nome, email, funcao, criado_em)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (g.fazenda['id'], v['usuario_id'], v['nome'], v['email'], v['funcao'], agora()))
    mensagem = (f'{v["nome"]} já tinha conta e foi vinculado(a) à fazenda.' if v['usuario_id'] else
                f'{v["nome"]} cadastrado(a). Peça para criar uma conta de funcionário com o e-mail {v["email"]}.')
    resposta = sucesso(mensagem, 201, funcionario=funcionario_json(buscar_funcionario(novo_id)))
    resposta[0].headers['Location'] = url_for('api.ver_funcionario', funcionario_id=novo_id)
    return resposta


@bp.put('/funcionarios/<int:funcionario_id>')
def atualizar_funcionario(funcionario_id):
    buscar_funcionario(funcionario_id)
    v, erros = validar_funcionario(dados_recebidos(), funcionario_id)
    if erros:
        return erro_validacao(erros)
    # Se o e-mail mudou, o vínculo passa para a conta do novo e-mail (ou fica pendente)
    consulta('UPDATE funcionarios SET nome = ?, email = ?, funcao = ?, usuario_id = ? WHERE id = ? AND fazenda_id = ?',
             (v['nome'], v['email'], v['funcao'], v['usuario_id'], funcionario_id, g.fazenda['id']))
    return sucesso('Funcionário atualizado.', redirecionar=url_for('dono.funcionarios'),
                   funcionario=funcionario_json(buscar_funcionario(funcionario_id)))


@bp.patch('/funcionarios/<int:funcionario_id>')
def ativar_funcionario(funcionario_id):
    buscar_funcionario(funcionario_id)
    ativo = 1 if verdadeiro(dados_recebidos(), 'ativo') else 0
    consulta('UPDATE funcionarios SET ativo = ? WHERE id = ? AND fazenda_id = ?', (ativo, funcionario_id, g.fazenda['id']))
    if not ativo:
        # Quem é desativado não fica com o ponto aberto
        consulta('UPDATE ponto SET saida = ? WHERE funcionario_id = ? AND saida IS NULL', (agora(), funcionario_id))
    return sucesso('Funcionário reativado.' if ativo else 'Funcionário desativado. Ele não acessa mais esta fazenda.')


@bp.delete('/funcionarios/<int:funcionario_id>')
def excluir_funcionario(funcionario_id):
    f = buscar_funcionario(funcionario_id)
    historico = valor('''SELECT (SELECT COUNT(*) FROM ponto WHERE funcionario_id = ?)
                              + (SELECT COUNT(*) FROM relatorios WHERE funcionario_id = ?)''',
                      (funcionario_id, funcionario_id))
    if historico:
        return jsonify(erro=f'{f["nome"]} tem ponto ou relatórios registrados. Desative em vez de excluir, '
                            'para não perder o histórico de horas.'), 409
    consulta('DELETE FROM funcionarios WHERE id = ? AND fazenda_id = ?', (funcionario_id, g.fazenda['id']))
    return sucesso(f'{f["nome"]} foi removido(a) da equipe.')


# ===================== Atividades =====================

STATUS_ATIVIDADE = ('pendente', 'concluida', 'arquivada')


def buscar_atividade(atividade_id):
    a = um('SELECT * FROM atividades WHERE id = ? AND fazenda_id = ?', (atividade_id, g.fazenda['id']))
    if not a:
        abort(404, 'Atividade não encontrada.')
    return a


def validar_atividade(dados):
    erros = []
    fid = g.fazenda['id']
    titulo = texto(dados, 'titulo', 150)
    data_prevista = data_valida(texto(dados, 'data_prevista', 10))
    if not titulo:
        erros.append('Informe o título da atividade.')
    if data_prevista == 'invalida':
        erros.append('Data prevista inválida.')
    # Só aceita máquina e funcionário desta fazenda (não dá para "apontar" para dados de outra)
    maquina_id = inteiro_ou_none(dados, 'maquina_id')
    funcionario_id = inteiro_ou_none(dados, 'funcionario_id')
    if maquina_id and not um('SELECT id FROM maquinas WHERE id = ? AND fazenda_id = ?', (maquina_id, fid)):
        erros.append('Máquina inválida.')
    if funcionario_id and not um('SELECT id FROM funcionarios WHERE id = ? AND fazenda_id = ?', (funcionario_id, fid)):
        erros.append('Responsável inválido.')
    return {
        'titulo': titulo,
        'descricao': texto(dados, 'descricao', 2000) or None,
        'tipo': 'manutencao' if dados.get('tipo') == 'manutencao' else 'operacao',
        'maquina_id': maquina_id or None,
        'funcionario_id': funcionario_id or None,
        'data_prevista': data_prevista if data_prevista != 'invalida' else None,
        'recorrente': 1 if verdadeiro(dados, 'recorrente') else 0,
    }, erros


@bp.get('/atividades')
def listar_atividades():
    status = request.args.get('status')
    if status in STATUS_ATIVIDADE:
        lista = todos('SELECT * FROM atividades WHERE fazenda_id = ? AND status = ? ORDER BY id DESC',
                      (g.fazenda['id'], status))
    else:
        lista = todos('SELECT * FROM atividades WHERE fazenda_id = ? ORDER BY id DESC', (g.fazenda['id'],))
    return jsonify(lista)


@bp.get('/atividades/<int:atividade_id>')
def ver_atividade(atividade_id):
    return jsonify(buscar_atividade(atividade_id))


@bp.post('/atividades')
def criar_atividade():
    v, erros = validar_atividade(dados_recebidos())
    if erros:
        return erro_validacao(erros)
    novo_id = inserir('''INSERT INTO atividades (fazenda_id, titulo, descricao, tipo, maquina_id, funcionario_id,
                                                 data_prevista, recorrente, criado_em)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (g.fazenda['id'], v['titulo'], v['descricao'], v['tipo'], v['maquina_id'], v['funcionario_id'],
                       v['data_prevista'], v['recorrente'], agora()))
    resposta = sucesso('Atividade criada. Ela já aparece no formulário dos funcionários.', 201,
                       atividade=buscar_atividade(novo_id))
    resposta[0].headers['Location'] = url_for('api.ver_atividade', atividade_id=novo_id)
    return resposta


@bp.put('/atividades/<int:atividade_id>')
def atualizar_atividade(atividade_id):
    buscar_atividade(atividade_id)
    v, erros = validar_atividade(dados_recebidos())
    if erros:
        return erro_validacao(erros)
    consulta('''UPDATE atividades SET titulo = ?, descricao = ?, tipo = ?, maquina_id = ?, funcionario_id = ?,
                       data_prevista = ?, recorrente = ? WHERE id = ? AND fazenda_id = ?''',
             (v['titulo'], v['descricao'], v['tipo'], v['maquina_id'], v['funcionario_id'], v['data_prevista'],
              v['recorrente'], atividade_id, g.fazenda['id']))
    return sucesso('Atividade atualizada.', redirecionar=url_for('dono.atividades'),
                   atividade=buscar_atividade(atividade_id))


@bp.patch('/atividades/<int:atividade_id>')
def mudar_status_atividade(atividade_id):
    buscar_atividade(atividade_id)
    status = dados_recebidos().get('status')
    if status not in STATUS_ATIVIDADE:
        return erro_validacao(['Status inválido.'])
    consulta('UPDATE atividades SET status = ? WHERE id = ? AND fazenda_id = ?', (status, atividade_id, g.fazenda['id']))
    rotulo = {'pendente': 'reaberta', 'concluida': 'concluída', 'arquivada': 'arquivada'}[status]
    return sucesso(f'Atividade {rotulo}.')


@bp.delete('/atividades/<int:atividade_id>')
def excluir_atividade(atividade_id):
    a = buscar_atividade(atividade_id)
    # Os relatórios antigos continuam com o título (relatorio_itens.atividade_titulo)
    consulta('DELETE FROM atividades WHERE id = ? AND fazenda_id = ?', (atividade_id, g.fazenda['id']))
    return sucesso(f'Atividade "{a["titulo"]}" excluída.')


# ===================== Fazendas =====================


def buscar_fazenda(fazenda_id):
    f = um('SELECT * FROM fazendas WHERE id = ? AND dono_id = ?', (fazenda_id, usuario()['id']))
    if not f:
        abort(404, 'Fazenda não encontrada.')
    return f


def validar_fazenda(dados):
    erros = []
    nome = texto(dados, 'nome', 120)
    estado = texto(dados, 'estado', 2).upper()
    area, producao = numero(dados, 'area_ha'), numero(dados, 'producao_sacas')
    if not nome:
        erros.append('Informe o nome da fazenda.')
    if estado and not estado.isalpha():
        erros.append('UF inválida.')
    if area == 'invalido' or (area is not None and not 0 <= area <= 10_000_000):
        erros.append('Área inválida.')
    if producao == 'invalido' or (producao is not None and not 0 <= producao <= 100_000_000):
        erros.append('Produção inválida.')
    return {
        'nome': nome,
        'municipio': texto(dados, 'municipio', 120) or None,
        'estado': estado or None,
        'area_ha': area if isinstance(area, float) else None,
        'producao_sacas': int(producao) if isinstance(producao, float) else None,
    }, erros


@bp.get('/fazendas')
def listar_fazendas():
    return jsonify(todos('SELECT * FROM fazendas WHERE dono_id = ? ORDER BY nome', (usuario()['id'],)))


@bp.get('/fazendas/<int:fazenda_id>')
def ver_fazenda(fazenda_id):
    return jsonify(buscar_fazenda(fazenda_id))


@bp.post('/fazendas')
def criar_fazenda():
    v, erros = validar_fazenda(dados_recebidos())
    if erros:
        return erro_validacao(erros)
    novo_id = inserir('''INSERT INTO fazendas (nome, municipio, estado, area_ha, producao_sacas, dono_id, criado_em)
                         VALUES (?, ?, ?, ?, ?, ?, ?)''',
                      (v['nome'], v['municipio'], v['estado'], v['area_ha'], v['producao_sacas'], usuario()['id'], agora()))
    session['fazenda_id'] = novo_id
    resposta = sucesso('Fazenda cadastrada! Agora cadastre seus funcionários e máquinas.', 201,
                       fazenda=buscar_fazenda(novo_id), redirecionar=url_for('dono.index'))
    resposta[0].headers['Location'] = url_for('api.ver_fazenda', fazenda_id=novo_id)
    return resposta


@bp.put('/fazendas/<int:fazenda_id>')
def atualizar_fazenda(fazenda_id):
    buscar_fazenda(fazenda_id)
    v, erros = validar_fazenda(dados_recebidos())
    if erros:
        return erro_validacao(erros)
    consulta('''UPDATE fazendas SET nome = ?, municipio = ?, estado = ?, area_ha = ?, producao_sacas = ?
                WHERE id = ? AND dono_id = ?''',
             (v['nome'], v['municipio'], v['estado'], v['area_ha'], v['producao_sacas'], fazenda_id, usuario()['id']))
    return sucesso('Fazenda atualizada.', redirecionar=url_for('dono.fazendas'), fazenda=buscar_fazenda(fazenda_id))


@bp.delete('/fazendas/<int:fazenda_id>')
def excluir_fazenda(fazenda_id):
    f = buscar_fazenda(fazenda_id)
    em_uso = valor('''SELECT (SELECT COUNT(*) FROM maquinas WHERE fazenda_id = ?)
                           + (SELECT COUNT(*) FROM funcionarios WHERE fazenda_id = ?)''', (fazenda_id, fazenda_id))
    if em_uso:
        return jsonify(erro=f'A fazenda "{f["nome"]}" ainda tem máquinas ou funcionários. '
                            'Exclua ou transfira esses cadastros antes.'), 409
    alterados('DELETE FROM fazendas WHERE id = ? AND dono_id = ?', (fazenda_id, usuario()['id']))
    if session.get('fazenda_id') == fazenda_id:
        session.pop('fazenda_id')
    return sucesso(f'Fazenda "{f["nome"]}" excluída.', redirecionar=url_for('dono.fazendas'))


# ===================== Relatório de custos (procedimento do banco) =====================


def resumo_custos(fazenda_id, inicio, fim):
    """Ranking de custo por máquina. No MySQL chama o procedimento sp_resumo_custos (03_rotinas.sql)."""
    if eh_mysql():
        return chamar_procedimento('sp_resumo_custos', (fazenda_id, inicio, fim))
    # SQLite não tem procedimentos: mesma consulta escrita aqui
    return todos('''SELECT m.id, m.nome, m.tipo, m.horimetro,
                         (SELECT COUNT(*) FROM manutencoes mn WHERE mn.maquina_id = m.id AND mn.data BETWEEN ? AND ?) AS qtd_servicos,
                         (SELECT COUNT(*) FROM manutencoes mn WHERE mn.maquina_id = m.id AND mn.tipo = 'corretiva'
                             AND mn.data BETWEEN ? AND ?) AS qtd_corretivas,
                         (SELECT COALESCE(SUM(custo), 0) FROM manutencoes mn WHERE mn.maquina_id = m.id
                             AND mn.data BETWEEN ? AND ?) AS custo_total,
                         (SELECT COUNT(*) FROM ocorrencias o WHERE o.maquina_id = m.id AND o.status = 'aberta') AS problemas_abertos
                  FROM maquinas m WHERE m.fazenda_id = ? ORDER BY custo_total DESC, m.nome''',
                 (inicio, fim, inicio, fim, inicio, fim, fazenda_id))


@bp.get('/fazenda/custos')
def custos_fazenda():
    """Ranking de custo por máquina no período (padrão: últimos 12 meses)."""
    inicio = data_valida(request.args.get('inicio', '')) or dias_atras(365)
    fim = data_valida(request.args.get('fim', '')) or hoje()
    if 'invalida' in (inicio, fim):
        return erro_validacao(['Use datas no formato AAAA-MM-DD.'])
    linhas = resumo_custos(g.fazenda['id'], inicio, fim)
    return jsonify(inicio=inicio, fim=fim, total=sum(float(l['custo_total'] or 0) for l in linhas), maquinas=linhas)
