"""
Instala o banco MySQL do CafeMaq executando os scripts de database/mysql em ordem.

Uso (na pasta do projeto):
    python scripts/instalar_banco.py                 # estrutura, usuários e rotinas
    python scripts/instalar_banco.py --exemplo       # ... e também os dados de demonstração
    python scripts/instalar_banco.py --host 127.0.0.1 --usuario root

Hospedagem com banco já criado e sem permissão de CREATE USER (ex.: PythonAnywhere):
    python scripts/instalar_banco.py --host USUARIO.mysql.pythonanywhere-services.com \
           --usuario USUARIO --base 'USUARIO$cafemaq' --sem-usuarios --exemplo

A senha do root é perguntada no terminal (não fica salva em lugar nenhum).
Também dá para rodar cada .sql pelo MySQL Workbench ou pelo terminal:
    mysql -u root -p < database/mysql/01_estrutura.sql
"""
import argparse
import getpass
import os
import re
import sys

import pymysql

PASTA_SQL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'database', 'mysql')
SCRIPTS = ['01_estrutura.sql', '02_usuarios.sql', '03_rotinas.sql']


def comandos(texto):
    """Divide um script .sql em comandos, entendendo o "DELIMITER $$" usado nas rotinas."""
    delimitador = ';'
    atual = []
    for linha in texto.splitlines():
        limpa = linha.strip()
        if limpa.upper().startswith('DELIMITER '):
            delimitador = limpa.split()[1]
            continue
        if not atual and (not limpa or limpa.startswith('--')):
            continue  # linha em branco ou comentário entre comandos
        atual.append(linha)
        if limpa.endswith(delimitador):
            comando = '\n'.join(atual).strip()
            comando = comando[: -len(delimitador)].strip()
            if comando:
                yield comando
            atual = []
    sobra = '\n'.join(atual).strip()
    if sobra:
        yield sobra


def trocar_base(comando, base):
    """Troca o nome da base "cafemaq" (sem mexer em cafemaq_app nem em e-mails @cafemaq.com.br)."""
    if base == 'cafemaq':
        return comando
    return re.sub(r'(?<![@\w])cafemaq(?![\w])(?!\.com)', f'`{base}`', comando)


def executar(conexao, arquivo, ignorar_erros=(), base='cafemaq'):
    caminho = os.path.join(PASTA_SQL, arquivo)
    with open(caminho, encoding='utf-8') as f:
        lista = [trocar_base(c, base) for c in comandos(f.read())]
    with conexao.cursor() as cur:
        for comando in lista:
            try:
                cur.execute(comando)
            except pymysql.MySQLError as erro:
                if any(trecho in comando for trecho in ignorar_erros):
                    print(f'   aviso (ignorado): {erro.args[-1]}')
                    continue
                print(f'\nErro em {arquivo}:\n{comando[:300]}\n-> {erro}')
                sys.exit(1)
    print(f'OK  {arquivo} ({len(lista)} comandos)')


def main():
    p = argparse.ArgumentParser(description='Instala o banco MySQL do CafeMaq')
    p.add_argument('--host', default='localhost')
    p.add_argument('--porta', type=int, default=3306)
    p.add_argument('--usuario', default='root')
    p.add_argument('--senha', default=None, help='se omitida, é perguntada no terminal')
    p.add_argument('--exemplo', action='store_true', help='carrega também 04_dados_exemplo.sql')
    p.add_argument('--base', default='cafemaq', help='nome da base (padrão: cafemaq)')
    p.add_argument('--sem-usuarios', action='store_true',
                   help='não roda o 02_usuarios.sql (hospedagens que não deixam criar usuários)')
    args = p.parse_args()

    senha = args.senha if args.senha is not None else getpass.getpass(f'Senha do MySQL para {args.usuario}: ')
    conexao = pymysql.connect(host=args.host, port=args.porta, user=args.usuario, password=senha,
                              charset='utf8mb4', autocommit=True)

    for arquivo in SCRIPTS:
        if args.sem_usuarios and arquivo == '02_usuarios.sql':
            continue
        # SHOW_ROUTINE não existe no MariaDB/XAMPP, e hospedagens já entregam a base criada
        # (sem permissão de CREATE DATABASE): esses dois erros não impedem a instalação
        executar(conexao, arquivo, ignorar_erros=('SHOW_ROUTINE', 'CREATE DATABASE'), base=args.base)
    if args.exemplo:
        executar(conexao, '04_dados_exemplo.sql', base=args.base)

    print('\nBanco "cafemaq" pronto. Agora preencha o .env com DB_TIPO=mysql e a senha do usuário cafemaq_app.')


if __name__ == '__main__':
    main()
