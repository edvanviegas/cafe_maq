"""Conexão com o banco SQLite e funções curtas para consultas."""
import os
import sqlite3

from flask import current_app, g

PASTA = os.path.dirname(os.path.abspath(__file__))


def conexao():
    """Uma conexão por requisição, fechada automaticamente no fim (ver fechar)."""
    if 'db' not in g:
        # isolation_level=None: cada comando é salvo na hora (use transacao() para agrupar)
        g.db = sqlite3.connect(current_app.config['BANCO'], isolation_level=None)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db


def fechar(_erro=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def criar_banco(app):
    """Cria o arquivo do banco e as tabelas na primeira execução."""
    caminho = app.config['BANCO']
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    db = sqlite3.connect(caminho)
    try:
        existe = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios'").fetchone()
        if not existe:
            with open(os.path.join(PASTA, 'database', 'schema.sql'), encoding='utf-8') as arquivo:
                db.executescript(arquivo.read())
    finally:
        db.close()


def consulta(sql, params=()):
    return conexao().execute(sql, params)


def um(sql, params=()):
    linha = consulta(sql, params).fetchone()
    return dict(linha) if linha else None


def todos(sql, params=()):
    return [dict(linha) for linha in consulta(sql, params).fetchall()]


def valor(sql, params=()):
    linha = consulta(sql, params).fetchone()
    return linha[0] if linha else None


def inserir(sql, params=()):
    """Executa um INSERT e devolve o id criado."""
    return consulta(sql, params).lastrowid


class transacao:
    """Agrupa vários comandos: ou salva todos, ou nenhum.

        with transacao():
            consulta(...)
            consulta(...)
    """

    def __enter__(self):
        consulta('BEGIN')

    def __exit__(self, tipo_erro, *_):
        consulta('ROLLBACK' if tipo_erro else 'COMMIT')
        return False
