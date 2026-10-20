"""
CafeMaq - Configurações

Nada sensível fica escrito no código: senhas e chaves vêm do arquivo .env
(copie o .env.example para .env e preencha). O .env está no .gitignore e
nunca deve ir para o GitHub.
"""
import os
import secrets
import warnings
from datetime import timedelta

from dotenv import load_dotenv

PASTA = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(PASTA, '.env'))


def _env(nome, padrao=''):
    return os.environ.get(nome, padrao).strip()


# ===================== Ambiente =====================

AMBIENTE = _env('AMBIENTE', 'desenvolvimento')  # desenvolvimento | producao
PRODUCAO = AMBIENTE == 'producao'
DEBUG = not PRODUCAO and _env('FLASK_DEBUG', '1') == '1'

# ===================== Chave secreta =====================
# Assina o cookie de sessão. Gere uma com:
#   python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY = _env('SECRET_KEY') or _env('CAFEMAQ_SECRET')
if not SECRET_KEY:
    if PRODUCAO:
        raise RuntimeError('Defina SECRET_KEY no arquivo .env antes de rodar em produção.')
    SECRET_KEY = secrets.token_hex(32)
    warnings.warn('SECRET_KEY não definida no .env: usando uma chave temporária (as sessões caem ao reiniciar).')

# ===================== Banco de dados =====================

DB_TIPO = _env('DB_TIPO', 'sqlite').lower()  # mysql | sqlite

# MySQL: use o usuário da APLICAÇÃO (cafemaq_app), nunca o root
DB_HOST = _env('DB_HOST', 'localhost')
DB_PORTA = int(_env('DB_PORTA', '3306'))
DB_NOME = _env('DB_NOME', 'cafemaq')
DB_USUARIO = _env('DB_USUARIO', 'cafemaq_app')
DB_SENHA = _env('DB_SENHA')

# SQLite: arquivo criado sozinho na primeira execução
BANCO = _env('CAFEMAQ_BANCO') or os.path.join(PASTA, 'database', 'cafemaq.db')

# ===================== Login com Google =====================
# Crie um "ID do cliente OAuth" (Aplicativo da Web) em
# https://console.cloud.google.com/apis/credentials (vazio = esconde o botão)
GOOGLE_CLIENT_ID = _env('GOOGLE_CLIENT_ID')

FUSO_HORARIO = 'America/Sao_Paulo'

# ===================== Sessão =====================

SESSION_COOKIE_NAME = 'cafemaq'
SESSION_COOKIE_HTTPONLY = True        # JavaScript não lê o cookie (protege contra roubo por XSS)
SESSION_COOKIE_SAMESITE = 'Lax'       # cookie não vai em requisições de outros sites (CSRF)
SESSION_COOKIE_SECURE = PRODUCAO      # em produção o cookie só trafega por HTTPS
PERMANENT_SESSION_LIFETIME = timedelta(hours=8)                        # tempo máximo de uma sessão
SESSAO_INATIVIDADE = timedelta(minutes=int(_env('SESSAO_INATIVIDADE_MIN', '30')))  # sai sozinho se ficar parado

# ===================== Proteção contra força bruta =====================

LOGIN_MAX_TENTATIVAS = int(_env('LOGIN_MAX_TENTATIVAS', '5'))  # erros permitidos...
LOGIN_JANELA = timedelta(minutes=int(_env('LOGIN_JANELA_MIN', '15')))  # ...dentro desta janela

# ===================== Limites =====================

MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # recusa requisições maiores que 2 MB
LOG_ARQUIVO = os.path.join(PASTA, 'logs', 'seguranca.log')
