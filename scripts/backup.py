"""
Rotina de BACKUP e RECUPERAÇÃO do banco do CafeMaq (disponibilidade - CID).

    python scripts/backup.py                      # cria um backup em backups/
    python scripts/backup.py verificar ARQUIVO    # confere a integridade (SHA-256)
    python scripts/backup.py restaurar ARQUIVO    # restaura um backup

Como funciona:
  * MySQL: usa o mysqldump (com funções, procedimentos e triggers) logado com o
    usuário cafemaq_backup, que só tem permissão de leitura. Se o mysqldump não
    estiver instalado, gera o dump pelo próprio Python.
  * SQLite: copia o arquivo do banco com a API de backup do SQLite.
  * Cada backup ganha um arquivo .sha256 ao lado: se o backup for alterado ou
    corromper, a verificação acusa.
  * Mantém só os BACKUP_MANTER mais recentes (padrão 7) e apaga os antigos.

Agendar todo dia às 23h:
  Linux (crontab -e):   0 23 * * * cd /caminho/cafe_maq && python3 scripts/backup.py
  Windows:              Agendador de Tarefas > Criar tarefa básica > python scripts\\backup.py
  PythonAnywhere:       aba Tasks > Scheduled tasks > python3 /home/USUARIO/cafe_maq/scripts/backup.py

Variáveis do .env usadas: DB_TIPO, DB_HOST, DB_PORTA, DB_NOME, BACKUP_USUARIO,
BACKUP_SENHA (usuário cafemaq_backup), BACKUP_PASTA e BACKUP_MANTER.
"""
import datetime
import getpass
import glob
import hashlib
import os
import shutil
import sqlite3
import subprocess
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, RAIZ)

import config  # noqa: E402  (precisa do sys.path acima)


def env(nome, padrao=''):
    return os.environ.get(nome, padrao).strip()


PASTA = env('BACKUP_PASTA') or os.path.join(RAIZ, 'backups')
MANTER = int(env('BACKUP_MANTER', '7'))


# ===================== Integridade =====================


def sha256(caminho):
    h = hashlib.sha256()
    with open(caminho, 'rb') as f:
        for bloco in iter(lambda: f.read(65536), b''):
            h.update(bloco)
    return h.hexdigest()


def gravar_hash(caminho):
    with open(caminho + '.sha256', 'w', encoding='utf-8') as f:
        f.write(f'{sha256(caminho)}  {os.path.basename(caminho)}\n')


def verificar(caminho):
    arquivo_hash = caminho + '.sha256'
    if not os.path.exists(arquivo_hash):
        print('Sem arquivo .sha256 para comparar.')
        return False
    esperado = open(arquivo_hash, encoding='utf-8').read().split()[0]
    ok = sha256(caminho) == esperado
    print('Backup íntegro.' if ok else 'ATENÇÃO: o backup foi alterado ou está corrompido!')
    return ok


def limpar_antigos(padrao):
    arquivos = sorted(glob.glob(os.path.join(PASTA, padrao)))
    for velho in arquivos[:-MANTER]:
        os.remove(velho)
        if os.path.exists(velho + '.sha256'):
            os.remove(velho + '.sha256')
        print(f'   removido backup antigo: {os.path.basename(velho)}')


# ===================== MySQL =====================


def credenciais_backup():
    usuario = env('BACKUP_USUARIO', 'cafemaq_backup')
    senha = env('BACKUP_SENHA')
    if not senha:
        senha = getpass.getpass(f'Senha do MySQL para {usuario}: ')
    return usuario, senha


def dump_mysqldump(destino, usuario, senha):
    comando = ['mysqldump', '-h', config.DB_HOST, '-P', str(config.DB_PORTA), '-u', usuario,
               '--single-transaction', '--routines', '--triggers', '--events', '--no-tablespaces',
               '--default-character-set=utf8mb4', '--databases', config.DB_NOME, f'--result-file={destino}']
    # A senha vai pela variável de ambiente, para não aparecer na lista de processos
    subprocess.run(comando, check=True, env={**os.environ, 'MYSQL_PWD': senha})


def dump_python(destino, usuario, senha):
    """Dump sem o mysqldump: estrutura, dados e depois rotinas e triggers."""
    import pymysql

    con = pymysql.connect(host=config.DB_HOST, port=config.DB_PORTA, user=usuario, password=senha,
                          database=config.DB_NOME, charset='utf8mb4')
    cur = con.cursor()
    linhas = [f'-- Backup do CafeMaq gerado em {datetime.datetime.now():%d/%m/%Y %H:%M:%S}',
              'SET NAMES utf8mb4;', 'SET FOREIGN_KEY_CHECKS = 0;',
              f'CREATE DATABASE IF NOT EXISTS `{config.DB_NOME}` DEFAULT CHARACTER SET utf8mb4;',
              f'USE `{config.DB_NOME}`;', '']
    cur.execute("SHOW FULL TABLES WHERE Table_type = 'BASE TABLE'")
    tabelas = [t[0] for t in cur.fetchall()]
    for tabela in tabelas:
        cur.execute(f'SHOW CREATE TABLE `{tabela}`')
        linhas += [f'DROP TABLE IF EXISTS `{tabela}`;', cur.fetchone()[1] + ';', '']
    for tabela in tabelas:
        cur.execute(f'SELECT * FROM `{tabela}`')
        registros = cur.fetchall()
        if registros:
            colunas = ', '.join(f'`{c[0]}`' for c in cur.description)
            valores = ',\n  '.join('(' + ', '.join(con.escape(v) for v in r) + ')' for r in registros)
            linhas += [f'INSERT INTO `{tabela}` ({colunas}) VALUES\n  {valores};', '']
    linhas += ['DELIMITER ;;']
    for tipo in ('FUNCTION', 'PROCEDURE'):
        cur.execute(f'SHOW {tipo} STATUS WHERE Db = %s', (config.DB_NOME,))
        for rotina in [r[1] for r in cur.fetchall()]:
            cur.execute(f'SHOW CREATE {tipo} `{rotina}`')
            linhas += [f'DROP {tipo} IF EXISTS `{rotina}`;;', cur.fetchone()[2] + ';;', '']
    cur.execute('SHOW TRIGGERS')
    for gatilho in [r[0] for r in cur.fetchall()]:
        cur.execute(f'SHOW CREATE TRIGGER `{gatilho}`')
        linhas += [f'DROP TRIGGER IF EXISTS `{gatilho}`;;', cur.fetchone()[2] + ';;', '']
    linhas += ['DELIMITER ;', 'SET FOREIGN_KEY_CHECKS = 1;', '']
    with open(destino, 'w', encoding='utf-8') as f:
        f.write('\n'.join(linhas))
    con.close()


def backup_mysql(carimbo):
    destino = os.path.join(PASTA, f'cafemaq_{carimbo}.sql')
    usuario, senha = credenciais_backup()
    if shutil.which('mysqldump'):
        dump_mysqldump(destino, usuario, senha)
    else:
        print('   mysqldump não encontrado: gerando o dump pelo Python.')
        dump_python(destino, usuario, senha)
    return destino, 'cafemaq_*.sql'


def restaurar_mysql(caminho):
    import pymysql
    from instalar_banco import comandos

    usuario = env('RESTAURAR_USUARIO', 'cafemaq_admin')  # precisa poder criar tabelas
    senha = getpass.getpass(f'Senha do MySQL para {usuario}: ')
    con = pymysql.connect(host=config.DB_HOST, port=config.DB_PORTA, user=usuario, password=senha,
                          charset='utf8mb4', autocommit=True)
    with open(caminho, encoding='utf-8') as f, con.cursor() as cur:
        for comando in comandos(f.read()):
            cur.execute(comando)


# ===================== SQLite =====================


def backup_sqlite(carimbo):
    destino = os.path.join(PASTA, f'cafemaq_{carimbo}.db')
    origem = sqlite3.connect(config.BANCO)
    copia = sqlite3.connect(destino)
    with copia:
        origem.backup(copia)  # cópia consistente mesmo com o site rodando
    copia.close()
    origem.close()
    return destino, 'cafemaq_*.db'


def restaurar_sqlite(caminho):
    seguranca = config.BANCO + '.antes-da-restauracao'
    if os.path.exists(config.BANCO):
        shutil.copy2(config.BANCO, seguranca)
        print(f'   banco atual guardado em {seguranca}')
    shutil.copy2(caminho, config.BANCO)


# ===================== Principal =====================


def criar():
    os.makedirs(PASTA, exist_ok=True)
    carimbo = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    destino, padrao = backup_mysql(carimbo) if config.DB_TIPO == 'mysql' else backup_sqlite(carimbo)
    gravar_hash(destino)
    tamanho = os.path.getsize(destino) / 1024
    print(f'Backup criado: {destino} ({tamanho:.1f} KB)')
    limpar_antigos(padrao)


def restaurar(caminho):
    if not verificar(caminho):
        print('Restauração cancelada: o arquivo não passou na verificação.')
        sys.exit(1)
    if input('Isto substitui os dados atuais. Digite RESTAURAR para continuar: ') != 'RESTAURAR':
        print('Cancelado.')
        return
    if caminho.endswith('.sql'):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        restaurar_mysql(caminho)
    else:
        restaurar_sqlite(caminho)
    print('Banco restaurado.')


if __name__ == '__main__':
    acao = sys.argv[1] if len(sys.argv) > 1 else 'criar'
    if acao == 'criar':
        criar()
    elif acao in ('verificar', 'restaurar') and len(sys.argv) > 2:
        (verificar if acao == 'verificar' else restaurar)(sys.argv[2])
    else:
        print(__doc__)
