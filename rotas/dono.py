"""Painel do dono: visão geral, desempenho, relatórios, atividades, máquinas, manutenção, funcionários e fazendas."""
import calendar
from datetime import timedelta

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from banco import consulta, inserir, todos, um, valor
from catalogo import TIPOS, nome_tipo
from rotas.auth import EMAIL_VALIDO
from utils import (agora, campo, data_iso, dias_atras, duracao_ponto, exigir_login, fazenda_atual, hoje, inteiro,
                   numero_ou_nulo, para_data, situacao_revisao, usuario)

bp = Blueprint('dono', __name__, url_prefix='/dono')


@bp.before_request
def proteger():
    """Só donos entram aqui, e quase todas as páginas precisam de uma fazenda cadastrada."""
    bloqueio = exigir_login('dono')
    if bloqueio:
        return bloqueio
    g.fazenda = fazenda_atual()
    if not g.fazenda and request.endpoint != 'dono.fazendas':
        flash('Cadastre sua fazenda para começar.', 'info')
        return redirect(url_for('dono.fazendas'))
    return None


def maquina_da_fazenda(maquina_id):
    """Confere se a máquina é da fazenda atual."""
    return um('SELECT * FROM maquinas WHERE id = ? AND fazenda_id = ?', (inteiro(maquina_id), g.fazenda['id']))


# ===================== Visão geral =====================


@bp.route('/')
def index():
    fid = g.fazenda['id']
    trabalhando = todos(
        '''SELECT f.nome, f.funcao, p.entrada FROM ponto p JOIN funcionarios f ON f.id = p.funcionario_id
           WHERE p.fazenda_id = ? AND p.saida IS NULL ORDER BY p.entrada''', (fid,))
    for t in trabalhando:
        t['horas'] = duracao_ponto(t['entrada'], None)

    total_func = valor('SELECT COUNT(*) FROM funcionarios WHERE fazenda_id = ? AND ativo = 1', (fid,))
    total_maq = valor('SELECT COUNT(*) FROM maquinas WHERE fazenda_id = ? AND ativo = 1', (fid,))
    total_ativ = valor('SELECT COUNT(*) FROM atividades WHERE fazenda_id = ?', (fid,))

    ultimos = todos(
        '''SELECT r.data, r.criado_em, f.nome, COUNT(i.id) AS total,
                  SUM(CASE WHEN i.status = 'feita' THEN 1 ELSE 0 END) AS feitas
           FROM relatorios r JOIN funcionarios f ON f.id = r.funcionario_id
           LEFT JOIN relatorio_itens i ON i.relatorio_id = r.id
           WHERE r.fazenda_id = ? GROUP BY r.id ORDER BY r.criado_em DESC LIMIT 6''', (fid,))

    primeiros_passos = [
        ('Cadastrar a fazenda', True, url_for('dono.fazendas')),
        ('Cadastrar as máquinas', total_maq > 0, url_for('dono.maquinas')),
        ('Cadastrar funcionários', total_func > 0, url_for('dono.funcionarios')),
        ('Criar a primeira atividade', total_ativ > 0, url_for('dono.atividades')),
    ]

    return render_template(
        'dono/index.html', aba='geral',
        trabalhando=trabalhando, total_func=total_func, total_maq=total_maq, ultimos=ultimos,
        primeiros_passos=primeiros_passos,
        falta_passo=not all(p[1] for p in primeiros_passos),
        relatorios_hoje=valor('SELECT COUNT(*) FROM relatorios WHERE fazenda_id = ? AND data = ?', (fid, hoje())),
        pendentes=valor("SELECT COUNT(*) FROM atividades WHERE fazenda_id = ? AND status = 'pendente'", (fid,)),
        problemas=valor("SELECT COUNT(*) FROM ocorrencias WHERE fazenda_id = ? AND status = 'aberta'", (fid,)),
        gasto_mes=valor('SELECT COALESCE(SUM(custo), 0) FROM manutencoes WHERE fazenda_id = ? AND data >= ?',
                        (fid, hoje()[:8] + '01')),
    )


# ===================== Desempenho =====================

DIAS_SEMANA = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo']
MESES = ['', 'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro',
         'outubro', 'novembro', 'dezembro']


def calcular_periodo(periodo, ref):
    """Devolve (início, fim, anterior, próximo, rótulo) do período que contém a data ref."""
    if periodo == 'dia':
        ini = fim = ref
        anterior, proximo = ref - timedelta(days=1), ref + timedelta(days=1)
        rotulo = f'{DIAS_SEMANA[ref.weekday()].capitalize()}, {ref:%d/%m/%Y}'
    elif periodo == 'semana':
        ini = ref - timedelta(days=ref.weekday())  # segunda-feira
        fim = ini + timedelta(days=6)
        anterior, proximo = ini - timedelta(days=7), ini + timedelta(days=7)
        rotulo = f'Semana de {ini:%d/%m} a {fim:%d/%m/%Y}'
    else:
        ini = ref.replace(day=1)
        fim = ref.replace(day=calendar.monthrange(ref.year, ref.month)[1])
        anterior = (ini - timedelta(days=1)).replace(day=1)
        proximo = fim + timedelta(days=1)
        rotulo = f'{MESES[ref.month].capitalize()} de {ref.year}'
    return ini, fim, anterior, proximo, rotulo


@bp.route('/desempenho')
def desempenho():
    fid = g.fazenda['id']
    periodo = request.args.get('p') if request.args.get('p') in ('dia', 'semana', 'mes') else 'dia'
    ref = para_data(request.args.get('d')) or para_data(hoje())
    ini_dt, fim_dt, anterior, proximo, rotulo = calcular_periodo(periodo, ref)
    ini, fim = data_iso(ini_dt), data_iso(fim_dt)

    funcionarios = todos('SELECT id, nome, funcao, ativo FROM funcionarios WHERE fazenda_id = ? ORDER BY nome', (fid,))
    pontos = todos('SELECT funcionario_id, entrada, saida FROM ponto WHERE fazenda_id = ? AND entrada BETWEEN ? AND ?',
                   (fid, f'{ini} 00:00:00', f'{fim} 23:59:59'))
    itens = todos(
        '''SELECT r.id AS relatorio_id, r.funcionario_id, r.data, i.status, i.horas, i.maquina_id
           FROM relatorios r LEFT JOIN relatorio_itens i ON i.relatorio_id = r.id
           WHERE r.fazenda_id = ? AND r.data BETWEEN ? AND ?''', (fid, ini, fim))
    ocorrencias = todos('SELECT funcionario_id FROM ocorrencias WHERE fazenda_id = ? AND criado_em BETWEEN ? AND ?',
                        (fid, f'{ini} 00:00:00', f'{fim} 23:59:59'))
    manut = um(
        '''SELECT COUNT(*) AS qtd, COALESCE(SUM(custo), 0) AS custo,
                  COALESCE(SUM(CASE WHEN tipo = 'preventiva' THEN 1 ELSE 0 END), 0) AS preventivas
           FROM manutencoes WHERE fazenda_id = ? AND data BETWEEN ? AND ?''', (fid, ini, fim))
    uso_maquinas = todos(
        '''SELECT m.nome, SUM(i.horas) AS horas, COUNT(DISTINCT r.id) AS dias
           FROM relatorio_itens i JOIN relatorios r ON r.id = i.relatorio_id JOIN maquinas m ON m.id = i.maquina_id
           WHERE r.fazenda_id = ? AND r.data BETWEEN ? AND ? GROUP BY m.id, m.nome ORDER BY horas DESC''',
        (fid, ini, fim))

    # Consolida por funcionário
    por_func = {f['id']: {**f, 'horas': 0.0, 'dias': set(), 'relatorios': set(), 'feita': 0, 'parcial': 0,
                          'nao_feita': 0, 'problemas': 0} for f in funcionarios}
    horas_por_dia = {}
    for p in pontos:
        h = duracao_ponto(p['entrada'], p['saida'])
        dia = p['entrada'][:10]
        por_func[p['funcionario_id']]['horas'] += h
        por_func[p['funcionario_id']]['dias'].add(dia)
        horas_por_dia[dia] = horas_por_dia.get(dia, 0) + h
    for i in itens:
        f = por_func[i['funcionario_id']]
        f['relatorios'].add(i['relatorio_id'])
        if i['status']:
            f[i['status']] += 1
    for o in ocorrencias:
        if o['funcionario_id'] in por_func:
            por_func[o['funcionario_id']]['problemas'] += 1

    # Mostra só quem está ativo ou teve movimento no período
    lista = [f for f in por_func.values() if f['ativo'] or f['horas'] > 0 or f['relatorios']]
    lista.sort(key=lambda f: f['horas'], reverse=True)
    for f in lista:
        total = f['feita'] + f['parcial'] + f['nao_feita']
        f['conclusao'] = f['feita'] / total * 100 if total else None
        f['sem_relatorio'] = len(f['dias']) - len(f['relatorios'])

    tot = {
        'horas': sum(f['horas'] for f in lista),
        'feita': sum(f['feita'] for f in lista),
        'parcial': sum(f['parcial'] for f in lista),
        'nao_feita': sum(f['nao_feita'] for f in lista),
        'relatorios': sum(len(f['relatorios']) for f in lista),
        'dias_trab': sum(len(f['dias']) for f in lista),
    }
    tot_itens = tot['feita'] + tot['parcial'] + tot['nao_feita']
    taxa = tot['feita'] / tot_itens * 100 if tot_itens else None

    # Gráfico: horas por funcionário (dia) ou por dia (semana/mês)
    if periodo == 'dia':
        grafico = [(f['nome'].split(' ')[0], f['horas']) for f in lista]
    else:
        grafico = []
        d = ini_dt
        while d <= fim_dt:
            nome = f'{DIAS_SEMANA[d.weekday()][:3].capitalize()} {d:%d}' if periodo == 'semana' else f'{d:%d}'
            grafico.append((nome, horas_por_dia.get(data_iso(d), 0)))
            d += timedelta(days=1)

    return render_template(
        'dono/desempenho.html', aba='desempenho',
        periodo=periodo, ref=data_iso(ref), anterior=data_iso(anterior), proximo=data_iso(proximo), rotulo=rotulo,
        tot=tot, taxa=taxa, ocorrencias=ocorrencias, manut=manut, uso_maquinas=uso_maquinas, por_func=lista,
        grafico=grafico,
        max_grafico=max([1] + [h for _, h in grafico]),
        max_horas_func=max([1] + [f['horas'] for f in lista]),
    )


# ===================== Relatórios =====================


@bp.route('/relatorios')
def relatorios():
    fid = g.fazenda['id']
    de = request.args.get('de') if para_data(request.args.get('de')) else dias_atras(6)
    ate = request.args.get('ate') if para_data(request.args.get('ate')) else hoje()
    func_filtro = inteiro(request.args.get('funcionario'))

    sql = '''SELECT r.*, f.nome, f.funcao FROM relatorios r JOIN funcionarios f ON f.id = r.funcionario_id
             WHERE r.fazenda_id = ? AND r.data BETWEEN ? AND ?'''
    params = [fid, de, ate]
    if func_filtro:
        sql += ' AND r.funcionario_id = ?'
        params.append(func_filtro)
    lista = todos(sql + ' ORDER BY r.data DESC, r.criado_em DESC', params)

    for r in lista:
        r['itens'] = todos('''SELECT i.*, m.nome AS maquina FROM relatorio_itens i
                              LEFT JOIN maquinas m ON m.id = i.maquina_id WHERE i.relatorio_id = ?''', (r['id'],))
        r['pontos'] = todos('SELECT * FROM ponto WHERE funcionario_id = ? AND entrada BETWEEN ? AND ? ORDER BY entrada',
                            (r['funcionario_id'], r['data'] + ' 00:00:00', r['data'] + ' 23:59:59'))
        r['problemas'] = todos('''SELECT o.*, m.nome AS maquina FROM ocorrencias o
                                  JOIN maquinas m ON m.id = o.maquina_id WHERE o.relatorio_id = ?''', (r['id'],))
        r['horas_ponto'] = sum(duracao_ponto(p['entrada'], p['saida']) for p in r['pontos'])

    return render_template(
        'dono/relatorios.html', aba='relatorios', relatorios=lista, de=de, ate=ate, func_filtro=func_filtro,
        funcionarios=todos('SELECT id, nome FROM funcionarios WHERE fazenda_id = ? ORDER BY nome', (fid,)))


# ===================== Atividades =====================


@bp.route('/atividades', methods=['GET', 'POST'])
def atividades():
    fid = g.fazenda['id']

    if request.method == 'POST':
        acao = campo('acao')
        if acao == 'criar':
            titulo = campo('titulo')
            if not titulo:
                flash('Informe o título da atividade.', 'erro')
                return redirect(url_for('dono.atividades'))
            # Só aceita máquina e funcionário que sejam desta fazenda
            maquina = maquina_da_fazenda(campo('maquina_id'))
            func = um('SELECT id FROM funcionarios WHERE id = ? AND fazenda_id = ?', (inteiro(campo('funcionario_id')), fid))
            inserir(
                '''INSERT INTO atividades (fazenda_id, titulo, descricao, tipo, maquina_id, funcionario_id,
                                           data_prevista, recorrente, criado_em)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (fid, titulo, campo('descricao') or None, 'manutencao' if campo('tipo') == 'manutencao' else 'operacao',
                 maquina['id'] if maquina else None, func['id'] if func else None, campo('data_prevista') or None,
                 1 if 'recorrente' in request.form else 0, agora()))
            flash('Atividade criada. Ela já aparece no formulário dos funcionários.', 'sucesso')

        if acao == 'status' and campo('valor') in ('pendente', 'concluida', 'arquivada'):
            consulta('UPDATE atividades SET status = ? WHERE id = ? AND fazenda_id = ?',
                     (campo('valor'), inteiro(campo('id')), fid))
        return redirect(url_for('dono.atividades'))

    sql_base = '''SELECT a.*, m.nome AS maquina, f.nome AS funcionario,
                         (SELECT MAX(r.data) FROM relatorio_itens i JOIN relatorios r ON r.id = i.relatorio_id
                           WHERE i.atividade_id = a.id AND i.status <> 'nao_feita') AS ultima_execucao
                  FROM atividades a
                  LEFT JOIN maquinas m ON m.id = a.maquina_id
                  LEFT JOIN funcionarios f ON f.id = a.funcionario_id
                  WHERE a.fazenda_id = ? AND a.status = ?'''
    return render_template(
        'dono/atividades.html', aba='atividades',
        pendentes=todos(sql_base + ' ORDER BY a.recorrente DESC, a.data_prevista IS NULL, a.data_prevista, a.id',
                        (fid, 'pendente')),
        concluidas=todos(sql_base + ' ORDER BY a.id DESC LIMIT 20', (fid, 'concluida')),
        maquinas=todos('SELECT id, nome FROM maquinas WHERE fazenda_id = ? AND ativo = 1 ORDER BY nome', (fid,)),
        funcionarios=todos('SELECT id, nome FROM funcionarios WHERE fazenda_id = ? AND ativo = 1 ORDER BY nome', (fid,)),
    )


# ===================== Máquinas (cadastro) =====================


def maquinas_com_resumo(fid, so_ativas=False):
    """Máquinas da fazenda com última preventiva, gasto em 12 meses, problemas abertos e situação da revisão."""
    lista = todos(
        f'''SELECT m.*,
                  (SELECT MAX(horimetro) FROM manutencoes WHERE maquina_id = m.id AND tipo = 'preventiva') AS ultima_preventiva,
                  (SELECT MAX(data) FROM manutencoes WHERE maquina_id = m.id) AS ultima_manutencao,
                  (SELECT COALESCE(SUM(custo), 0) FROM manutencoes WHERE maquina_id = m.id AND data >= ?) AS gasto_ano,
                  (SELECT COUNT(*) FROM ocorrencias WHERE maquina_id = m.id AND status = 'aberta') AS abertas
            FROM maquinas m WHERE fazenda_id = ? {'AND ativo = 1' if so_ativas else ''}
            ORDER BY ativo DESC, nome''', (dias_atras(365), fid))
    for m in lista:
        m['revisao'] = situacao_revisao(m)
        m['tipo_nome'] = nome_tipo(m['tipo'])
    return lista


@bp.route('/maquinas', methods=['GET', 'POST'])
def maquinas():
    fid = g.fazenda['id']

    if request.method == 'POST':
        acao = campo('acao')
        if acao == 'salvar_maquina':
            tipo = campo('tipo') if campo('tipo') in TIPOS else 'outra'
            ano = numero_ou_nulo(campo('ano'))
            dados = (
                campo('nome') or TIPOS[tipo]['nome'],
                tipo,
                campo('marca') or None,
                campo('modelo') or None,
                int(ano) if ano else None,
                numero_ou_nulo(campo('horimetro')) or 0,
                numero_ou_nulo(campo('revisao_horas')),
                numero_ou_nulo(campo('preco')),
            )
            existente = maquina_da_fazenda(campo('id'))
            if existente:
                consulta('''UPDATE maquinas SET nome = ?, tipo = ?, marca = ?, modelo = ?, ano = ?, horimetro = ?,
                                   revisao_horas = ?, preco = ? WHERE id = ?''', dados + (existente['id'],))
                flash('Máquina atualizada.', 'sucesso')
            else:
                inserir('''INSERT INTO maquinas (nome, tipo, marca, modelo, ano, horimetro, revisao_horas, preco,
                                                 fazenda_id, criado_em) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        dados + (fid, agora()))
                flash('Máquina cadastrada. Os registros de manutenção ficam na aba Manutenção.', 'sucesso')

        if acao == 'ativo':
            consulta('UPDATE maquinas SET ativo = ? WHERE id = ? AND fazenda_id = ?',
                     (inteiro(campo('valor')), inteiro(campo('id')), fid))
        return redirect(url_for('dono.maquinas'))

    lista = maquinas_com_resumo(fid)
    # Quantas máquinas de cada tipo já existem, para sugerir o apelido (ex.: "Trator cafeeiro 02")
    por_tipo = {}
    for m in lista:
        por_tipo[m['tipo']] = por_tipo.get(m['tipo'], 0) + 1

    return render_template(
        'dono/maquinas.html', aba='maquinas', maquinas=lista, por_tipo=por_tipo,
        editar=maquina_da_fazenda(request.args['editar']) if 'editar' in request.args else None)


# ===================== Manutenção =====================


@bp.route('/manutencao', methods=['GET', 'POST'])
def manutencao():
    fid = g.fazenda['id']

    if request.method == 'POST':
        acao = campo('acao')
        maq = maquina_da_fazenda(campo('maquina_id'))

        if acao == 'registrar':
            if not maq or not campo('descricao'):
                flash('Escolha a máquina e descreva o serviço.', 'erro')
                return redirect(url_for('dono.manutencao', maquina=maq['id'] if maq else None))
            horimetro = numero_ou_nulo(campo('horimetro'))
            ocorrencia = um('SELECT id FROM ocorrencias WHERE id = ? AND fazenda_id = ? AND maquina_id = ?',
                            (inteiro(campo('ocorrencia_id')), fid, maq['id']))
            inserir(
                '''INSERT INTO manutencoes (fazenda_id, maquina_id, data, tipo, descricao, custo, horimetro,
                                            ocorrencia_id, criado_em) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (fid, maq['id'], campo('data') or hoje(), 'corretiva' if campo('tipo') == 'corretiva' else 'preventiva',
                 campo('descricao'), numero_ou_nulo(campo('custo')) or 0, horimetro,
                 ocorrencia['id'] if ocorrencia else None, agora()))
            if horimetro is not None and horimetro > float(maq['horimetro']):
                consulta('UPDATE maquinas SET horimetro = ? WHERE id = ?', (horimetro, maq['id']))
            if ocorrencia:
                consulta("UPDATE ocorrencias SET status = 'resolvida', resolvida_em = ? WHERE id = ?",
                         (agora(), ocorrencia['id']))
            # Conclui a atividade agendada que originou este serviço, se houver
            consulta("UPDATE atividades SET status = 'concluida' WHERE id = ? AND fazenda_id = ? AND tipo = 'manutencao'",
                     (inteiro(campo('atividade_id')), fid))
            flash('Manutenção registrada.', 'sucesso')

        if acao == 'agendar':
            if not maq:
                flash('Escolha a máquina.', 'erro')
                return redirect(url_for('dono.manutencao'))
            func = um('SELECT id FROM funcionarios WHERE id = ? AND fazenda_id = ?', (inteiro(campo('funcionario_id')), fid))
            inserir(
                '''INSERT INTO atividades (fazenda_id, titulo, descricao, tipo, maquina_id, funcionario_id,
                                           data_prevista, recorrente, criado_em)
                   VALUES (?, ?, ?, 'manutencao', ?, ?, ?, 0, ?)''',
                (fid, campo('titulo') or f'Revisão preventiva - {maq["nome"]}', campo('descricao') or None, maq['id'],
                 func['id'] if func else None, campo('data_prevista') or hoje(), agora()))
            flash('Manutenção agendada. Ela aparece no relatório do dia do funcionário.', 'sucesso')

        if acao == 'resolver':
            consulta("UPDATE ocorrencias SET status = 'resolvida', resolvida_em = ? WHERE id = ? AND fazenda_id = ?",
                     (agora(), inteiro(campo('id')), fid))
            flash('Ocorrência marcada como resolvida.', 'sucesso')

        return redirect(url_for('dono.manutencao', maquina=maq['id'] if maq else None))

    maquinas_ativas = maquinas_com_resumo(fid, so_ativas=True)

    ocorrencias = todos(
        '''SELECT o.*, m.nome AS maquina, f.nome AS funcionario FROM ocorrencias o
           JOIN maquinas m ON m.id = o.maquina_id LEFT JOIN funcionarios f ON f.id = o.funcionario_id
           WHERE o.fazenda_id = ? AND o.status = 'aberta'
           ORDER BY CASE o.gravidade WHEN 'alta' THEN 1 WHEN 'media' THEN 2 ELSE 3 END, o.criado_em DESC''', (fid,))

    ocorrencia_sel = None
    if 'ocorrencia' in request.args:
        ocorrencia_sel = um('SELECT * FROM ocorrencias WHERE id = ? AND fazenda_id = ?',
                            (inteiro(request.args['ocorrencia']), fid))
    atividade_sel = None
    if 'atividade' in request.args:
        atividade_sel = um("SELECT * FROM atividades WHERE id = ? AND fazenda_id = ? AND tipo = 'manutencao'",
                           (inteiro(request.args['atividade']), fid))

    # Máquina escolhida: pelo link direto, pelo problema ou pela atividade agendada
    maquina_id = inteiro(request.args.get('maquina')) or (ocorrencia_sel or atividade_sel or {}).get('maquina_id')
    sel = next((m for m in maquinas_ativas if m['id'] == maquina_id), None)

    if sel:
        historico = todos('SELECT * FROM manutencoes WHERE maquina_id = ? ORDER BY data DESC, id DESC', (sel['id'],))
        for h in historico:
            h['maquina'] = sel['nome']
    else:
        historico = todos('''SELECT mn.*, m.nome AS maquina FROM manutencoes mn JOIN maquinas m ON m.id = mn.maquina_id
                             WHERE mn.fazenda_id = ? ORDER BY mn.data DESC, mn.id DESC LIMIT 30''', (fid,))

    agendadas = todos(
        f'''SELECT a.*, m.nome AS maquina, f.nome AS funcionario FROM atividades a
            JOIN maquinas m ON m.id = a.maquina_id LEFT JOIN funcionarios f ON f.id = a.funcionario_id
            WHERE a.fazenda_id = ? AND a.status = 'pendente' AND a.tipo = 'manutencao'
            {'AND a.maquina_id = ?' if sel else ''}
            ORDER BY a.data_prevista IS NULL, a.data_prevista''', (fid, sel['id']) if sel else (fid,))

    return render_template(
        'dono/manutencao.html', aba='manutencao',
        maquinas=maquinas_ativas, sel=sel, ocorrencias=ocorrencias, ocorrencia_sel=ocorrencia_sel,
        atividade_sel=atividade_sel, historico=historico, agendadas=agendadas,
        vencidas=sum(1 for m in maquinas_ativas if m['revisao']['estado'] == 'vencida'),
        proximas=sum(1 for m in maquinas_ativas if m['revisao']['estado'] == 'proxima'),
        gasto_mes=valor('SELECT COALESCE(SUM(custo), 0) FROM manutencoes WHERE fazenda_id = ? AND data >= ?',
                        (fid, hoje()[:8] + '01')),
        funcionarios=todos('SELECT id, nome FROM funcionarios WHERE fazenda_id = ? AND ativo = 1 ORDER BY nome', (fid,)),
    )


# ===================== Funcionários =====================


@bp.route('/funcionarios', methods=['GET', 'POST'])
def funcionarios():
    fid = g.fazenda['id']

    if request.method == 'POST':
        acao = campo('acao')
        if acao == 'adicionar':
            nome = campo('nome')
            email = campo('email').lower()
            if not nome or not EMAIL_VALIDO.match(email):
                flash('Informe nome e um e-mail válido.', 'erro')
            elif um('SELECT id FROM funcionarios WHERE fazenda_id = ? AND LOWER(email) = ?', (fid, email)):
                flash('Este e-mail já está cadastrado nesta fazenda.', 'erro')
            else:
                conta = um('SELECT * FROM usuarios WHERE LOWER(email) = ?', (email,))
                if conta and conta['tipo'] != 'funcionario':
                    flash('Este e-mail pertence a uma conta de dono. O funcionário precisa de uma conta do tipo '
                          '"Funcionário".', 'erro')
                    return redirect(url_for('dono.funcionarios'))
                inserir('''INSERT INTO funcionarios (fazenda_id, usuario_id, nome, email, funcao, criado_em)
                           VALUES (?, ?, ?, ?, ?, ?)''',
                        (fid, conta['id'] if conta else None, nome, email, campo('funcao') or None, agora()))
                flash(f'{nome} já tinha conta e foi vinculado(a) à fazenda.' if conta else
                      f'{nome} cadastrado(a). Peça para criar uma conta de funcionário com o e-mail {email}.', 'sucesso')

        if acao == 'ativo':
            consulta('UPDATE funcionarios SET ativo = ? WHERE id = ? AND fazenda_id = ?',
                     (inteiro(campo('valor')), inteiro(campo('id')), fid))
            flash('Cadastro atualizado.', 'sucesso')
        return redirect(url_for('dono.funcionarios'))

    lista = todos(
        '''SELECT f.*,
                  (SELECT entrada FROM ponto WHERE funcionario_id = f.id AND saida IS NULL ORDER BY entrada DESC LIMIT 1) AS em_servico,
                  (SELECT MAX(data) FROM relatorios WHERE funcionario_id = f.id) AS ultimo_relatorio
           FROM funcionarios f WHERE fazenda_id = ? ORDER BY ativo DESC, nome''', (fid,))
    return render_template('dono/funcionarios.html', aba='funcionarios', funcionarios=lista)


# ===================== Fazendas =====================


@bp.route('/fazendas', methods=['GET', 'POST'])
def fazendas():
    u = usuario()

    if request.method == 'POST':
        acao = campo('acao')
        if acao == 'salvar':
            nome = campo('nome')
            if not nome:
                flash('Informe o nome da fazenda.', 'erro')
                return redirect(url_for('dono.fazendas'))
            producao = numero_ou_nulo(campo('producao_sacas'))
            dados = (nome, campo('municipio') or None, campo('estado')[:2].upper() or None,
                     numero_ou_nulo(campo('area_ha')), int(producao) if producao is not None else None)
            fazenda_id = inteiro(campo('id'))
            if fazenda_id:
                consulta('''UPDATE fazendas SET nome = ?, municipio = ?, estado = ?, area_ha = ?, producao_sacas = ?
                            WHERE id = ? AND dono_id = ?''', dados + (fazenda_id, u['id']))
                flash('Fazenda atualizada.', 'sucesso')
            else:
                session['fazenda_id'] = inserir(
                    '''INSERT INTO fazendas (nome, municipio, estado, area_ha, producao_sacas, dono_id, criado_em)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''', dados + (u['id'], agora()))
                flash('Fazenda cadastrada! Agora cadastre seus funcionários e máquinas.', 'sucesso')
                return redirect(url_for('dono.index'))

        if acao == 'selecionar':
            session['fazenda_id'] = inteiro(campo('id'))
            return redirect(url_for('dono.index'))
        return redirect(url_for('dono.fazendas'))

    lista = todos(
        '''SELECT f.*, (SELECT COUNT(*) FROM funcionarios WHERE fazenda_id = f.id AND ativo = 1) AS total_func,
                  (SELECT COUNT(*) FROM maquinas WHERE fazenda_id = f.id AND ativo = 1) AS total_maq
           FROM fazendas f WHERE dono_id = ? ORDER BY nome''', (u['id'],))
    editar = None
    if 'editar' in request.args:
        editar = um('SELECT * FROM fazendas WHERE id = ? AND dono_id = ?', (inteiro(request.args['editar']), u['id']))
    return render_template('dono/fazendas.html', aba='fazendas', fazendas=lista, editar=editar, atual=g.fazenda)
