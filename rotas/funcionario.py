"""Painel do funcionário: bater ponto, relatório do dia e histórico."""
from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from banco import consulta, inserir, todos, transacao, um
from utils import (agora, agora_dt, campo, dias_atras, duracao_ponto, exigir_login, hoje, inteiro, numero_ou_nulo,
                   ponto_aberto, usuario, vincular_funcionario, vinculo_atual)

bp = Blueprint('funcionario', __name__, url_prefix='/funcionario')


@bp.before_request
def proteger():
    bloqueio = exigir_login('funcionario')
    if bloqueio:
        return bloqueio
    vincular_funcionario(usuario())
    g.vinculo = vinculo_atual()
    return None


def salvar_relatorio(vinculo, aberto):
    fid = vinculo['id']
    fazenda_id = vinculo['fazenda_id']

    with transacao():
        relatorio_id = inserir(
            'INSERT INTO relatorios (fazenda_id, funcionario_id, data, observacoes, criado_em) VALUES (?, ?, ?, ?, ?)',
            (fazenda_id, fid, hoje(), campo('observacoes') or None, agora()))

        def inserir_item(atividade_id, titulo, status, horas, maquina_id, horimetro):
            inserir('''INSERT INTO relatorio_itens (relatorio_id, atividade_id, atividade_titulo, status, horas,
                                                    maquina_id, horimetro) VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (relatorio_id, atividade_id, titulo, status, horas, maquina_id, horimetro))
            if maquina_id and horimetro is not None:
                consulta('UPDATE maquinas SET horimetro = ? WHERE id = ? AND horimetro < ?',
                         (horimetro, maquina_id, horimetro))

        # Atividades do formulário (só as que realmente pertencem a este funcionário/fazenda)
        for chave in request.form:
            if not (chave.startswith('itens[') and chave.endswith('][status]')):
                continue
            atividade_id = inteiro(chave[len('itens['):-len('][status]')])
            status = request.form[chave]
            a = um('''SELECT * FROM atividades WHERE id = ? AND fazenda_id = ? AND status = 'pendente'
                      AND (funcionario_id IS NULL OR funcionario_id = ?)''', (atividade_id, fazenda_id, fid))
            if not a or status not in ('feita', 'parcial', 'nao_feita'):
                continue
            inserir_item(a['id'], a['titulo'], status, numero_ou_nulo(campo(f'itens[{atividade_id}][horas]')) or 0,
                         a['maquina_id'], numero_ou_nulo(campo(f'itens[{atividade_id}][horimetro]')))
            if status == 'feita' and not a['recorrente']:
                consulta("UPDATE atividades SET status = 'concluida' WHERE id = ?", (a['id'],))

        # Atividade extra, fora da lista
        if campo('extra_titulo'):
            maq = um('SELECT id FROM maquinas WHERE id = ? AND fazenda_id = ?', (inteiro(campo('extra_maquina')), fazenda_id))
            inserir_item(None, campo('extra_titulo'), 'feita', numero_ou_nulo(campo('extra_horas')) or 0,
                         maq['id'] if maq else None, numero_ou_nulo(campo('extra_horimetro')))

        # Problema em máquina vira um alerta para o dono (aba Manutenção)
        maq_problema = um('SELECT id FROM maquinas WHERE id = ? AND fazenda_id = ?',
                          (inteiro(campo('problema_maquina')), fazenda_id))
        if maq_problema and campo('problema_descricao'):
            gravidade = campo('problema_gravidade') if campo('problema_gravidade') in ('baixa', 'media', 'alta') else 'media'
            inserir('''INSERT INTO ocorrencias (fazenda_id, maquina_id, funcionario_id, relatorio_id, descricao,
                                                gravidade, criado_em) VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (fazenda_id, maq_problema['id'], fid, relatorio_id, campo('problema_descricao'), gravidade, agora()))

        registrou_saida = 'registrar_saida' in request.form and aberto
        if registrou_saida:
            consulta('UPDATE ponto SET saida = ? WHERE id = ?', (agora(), aberto['id']))

    flash('Relatório enviado!' + (f' Saída registrada às {agora_dt():%H:%M}.' if registrou_saida else ''), 'sucesso')


@bp.route('/', methods=['GET', 'POST'])
def index():
    vinculo = g.vinculo
    if not vinculo:
        return render_template('funcionario/sem_vinculo.html', aba='dia')

    fid = vinculo['id']
    aberto = ponto_aberto(fid)

    if request.method == 'POST':
        acao = campo('acao')
        if acao == 'entrada' and not aberto:
            inserir('INSERT INTO ponto (fazenda_id, funcionario_id, entrada) VALUES (?, ?, ?)',
                    (vinculo['fazenda_id'], fid, agora()))
            flash(f'Entrada registrada às {agora_dt():%H:%M}. Bom trabalho!', 'sucesso')

        if acao == 'saida' and aberto:
            consulta('UPDATE ponto SET saida = ? WHERE id = ?', (agora(), aberto['id']))
            flash(f'Saída registrada às {agora_dt():%H:%M}.', 'sucesso')

        if acao == 'relatorio':
            if um('SELECT id FROM relatorios WHERE funcionario_id = ? AND data = ?', (fid, hoje())):
                flash('Você já enviou o relatório de hoje.', 'erro')
            else:
                salvar_relatorio(vinculo, aberto)
        return redirect(url_for('funcionario.index'))

    pontos_hoje = todos('SELECT * FROM ponto WHERE funcionario_id = ? AND entrada >= ? ORDER BY entrada',
                        (fid, hoje() + ' 00:00:00'))
    relatorio_hoje = um('SELECT * FROM relatorios WHERE funcionario_id = ? AND data = ?', (fid, hoje()))
    itens_hoje = todos('SELECT * FROM relatorio_itens WHERE relatorio_id = ?', (relatorio_hoje['id'],)) if relatorio_hoje else []

    atividades = todos(
        '''SELECT a.*, m.nome AS maquina, m.horimetro AS maquina_horimetro FROM atividades a
           LEFT JOIN maquinas m ON m.id = a.maquina_id
           WHERE a.fazenda_id = ? AND a.status = 'pendente' AND (a.funcionario_id IS NULL OR a.funcionario_id = ?)
             AND (a.data_prevista IS NULL OR a.data_prevista <= ?)
           ORDER BY a.recorrente DESC, a.data_prevista, a.id''', (vinculo['fazenda_id'], fid, hoje()))

    proximas = todos(
        '''SELECT titulo, data_prevista FROM atividades WHERE fazenda_id = ? AND status = 'pendente'
             AND (funcionario_id IS NULL OR funcionario_id = ?) AND data_prevista > ? AND recorrente = 0
           ORDER BY data_prevista LIMIT 5''', (vinculo['fazenda_id'], fid, hoje()))

    return render_template(
        'funcionario/index.html', aba='dia', vinculo=vinculo, aberto=aberto, pontos_hoje=pontos_hoje,
        horas_hoje=sum(duracao_ponto(p['entrada'], p['saida']) for p in pontos_hoje),
        relatorio_hoje=relatorio_hoje, itens_hoje=itens_hoje, atividades=atividades, proximas=proximas,
        maquinas=todos('SELECT id, nome, horimetro FROM maquinas WHERE fazenda_id = ? AND ativo = 1 ORDER BY nome',
                       (vinculo['fazenda_id'],)))


@bp.route('/historico')
def historico():
    vinculo = g.vinculo
    if not vinculo:
        return redirect(url_for('funcionario.index'))

    inicio = dias_atras(30)
    pontos = todos('SELECT * FROM ponto WHERE funcionario_id = ? AND entrada >= ? ORDER BY entrada DESC',
                   (vinculo['id'], inicio + ' 00:00:00'))
    relatorios = todos(
        '''SELECT r.*, COUNT(i.id) AS total, SUM(CASE WHEN i.status = 'feita' THEN 1 ELSE 0 END) AS feitas,
                  COALESCE(SUM(i.horas), 0) AS horas
           FROM relatorios r LEFT JOIN relatorio_itens i ON i.relatorio_id = r.id
           WHERE r.funcionario_id = ? AND r.data >= ? GROUP BY r.id ORDER BY r.data DESC''', (vinculo['id'], inicio))

    # Agrupa as marcações de ponto por dia
    dias = {}
    for p in pontos:
        dia = dias.setdefault(p['entrada'][:10], {'marcacoes': [], 'horas': 0.0})
        dia['marcacoes'].insert(0, p)
        dia['horas'] += duracao_ponto(p['entrada'], p['saida'])

    return render_template('funcionario/historico.html', aba='historico', dias=dias, relatorios=relatorios,
                           total_horas=sum(d['horas'] for d in dias.values()))
