"""
Conexão com o banco de dados e funções curtas para consultas.

Funciona com dois bancos, escolhidos pela variável DB_TIPO do arquivo .env:
    sqlite  -> um arquivo, sem instalar nada (padrão; usado no site publicado)
    mysql   -> versão da disciplina de Banco de Dados II (usuários, funções,
               procedimentos e triggers)

As rotas escrevem o SQL sempre com "?" nos parâmetros (consulta parametrizada,
que impede SQL Injection). Para o MySQL, o "?" é trocado por "%s" aqui.
"""
import datetime
import os
import sqlite3
from decimal import Decimal

from flask import current_app, g

PASTA = os.path.dirname(os.path.abspath(__file__))


def eh_mysql():
    return current_app.config['DB_TIPO'] == 'mysql'


# ===================== Conexão =====================


def _conectar_mysql(cfg):
    import pymysql  # só é necessário quando DB_TIPO=mysql

    db = pymysql.connect(
        host=cfg['DB_HOST'], port=cfg['DB_PORTA'], user=cfg['DB_USUARIO'], password=cfg['DB_SENHA'],
        database=cfg['DB_NOME'], charset='utf8mb4', autocommit=True,
    )
    with db.cursor() as cur:
        cur.execute("SET time_zone = '-03:00'")  # NOW() nos triggers no horário de Brasília
    return db


def conexao():
    """Uma conexão por requisição, fechada automaticamente no fim (ver fechar)."""
    if 'db' not in g:
        cfg = current_app.config
        if cfg['DB_TIPO'] == 'mysql':
            g.db = _conectar_mysql(cfg)
        else:
            # isolation_level=None: cada comando é salvo na hora (use transacao() para agrupar)
            g.db = sqlite3.connect(cfg['BANCO'], isolation_level=None)
            g.db.execute('PRAGMA foreign_keys = ON')
    return g.db


def fechar(_erro=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def criar_banco(app):
    """SQLite: cria o arquivo e as tabelas que faltarem (CREATE TABLE IF NOT EXISTS).

    MySQL: a estrutura é criada pelos scripts de database/mysql (ver README),
    porque eles também criam usuários, funções, procedimentos e triggers.
    """
    if app.config['DB_TIPO'] == 'mysql':
        return
    caminho = app.config['BANCO']
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    db = sqlite3.connect(caminho)
    try:
        with open(os.path.join(PASTA, 'database', 'sqlite', 'schema.sql'), encoding='utf-8') as arquivo:
            db.executescript(arquivo.read())
    finally:
        db.close()


# ===================== Conversão de valores =====================


def _normalizar(valor):
    """Deixa os valores iguais nos dois bancos (o MySQL devolve Decimal e datetime)."""
    if isinstance(valor, Decimal):
        # SUM/COUNT de inteiros vem como Decimal sem casas (ex.: 3) -> int; o resto -> float
        return int(valor) if valor.as_tuple().exponent >= 0 else float(valor)
    if isinstance(valor, datetime.datetime):
        return valor.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(valor, datetime.date):
        return valor.strftime('%Y-%m-%d')
    return valor


def _linha_dict(cursor, linha):
    nomes = [coluna[0] for coluna in cursor.description]
    return {nome: _normalizar(v) for nome, v in zip(nomes, linha)}


# ===================== Consultas =====================


def consulta(sql, params=()):
    """Executa um comando parametrizado e devolve o cursor."""
    db = conexao()
    if eh_mysql():
        cursor = db.cursor()
        cursor.execute(sql.replace('?', '%s'), tuple(params) or None)
        return cursor
    return db.execute(sql, params)


def um(sql, params=()):
    cursor = consulta(sql, params)
    linha = cursor.fetchone()
    return _linha_dict(cursor, linha) if linha else None


def todos(sql, params=()):
    cursor = consulta(sql, params)
    return [_linha_dict(cursor, linha) for linha in cursor.fetchall()]


def valor(sql, params=()):
    linha = consulta(sql, params).fetchone()
    return _normalizar(linha[0]) if linha else None


def inserir(sql, params=()):
    """Executa um INSERT e devolve o id criado."""
    return consulta(sql, params).lastrowid


def alterados(sql, params=()):
    """Executa UPDATE/DELETE e devolve quantas linhas foram afetadas."""
    return consulta(sql, params).rowcount


def chamar_procedimento(nome, params=()):
    """CALL de um procedimento do MySQL (ex.: sp_resumo_custos) e devolve as linhas."""
    cursor = conexao().cursor()
    cursor.callproc(nome, tuple(params))
    linhas = [_linha_dict(cursor, linha) for linha in cursor.fetchall()]
    while cursor.nextset():  # descarta o resultado extra que todo CALL devolve
        pass
    return linhas


def definir_usuario_app(usuario_id):
    """Informa ao banco quem está logado, para os triggers de auditoria.

    MySQL: variável de sessão @app_usuario_id. SQLite: tabela sessao_app (schema.sql).
    """
    if eh_mysql():
        consulta('SET @app_usuario_id = ?', (usuario_id,))
    else:
        consulta('UPDATE sessao_app SET usuario_id = ? WHERE id = 1', (usuario_id,))


class transacao:
    """Agrupa vários comandos: ou salva todos, ou nenhum.

        with transacao():
            consulta(...)
            consulta(...)
    """

    def __enter__(self):
        consulta('START TRANSACTION' if eh_mysql() else 'BEGIN')

    def __exit__(self, tipo_erro, *_):
        consulta('ROLLBACK' if tipo_erro else 'COMMIT')
        return False
