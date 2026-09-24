"""
CafeMaq - Configurações

Os valores podem ser trocados por variáveis de ambiente (útil ao publicar):
    CAFEMAQ_SECRET      chave usada para assinar a sessão (obrigatório trocar em produção)
    CAFEMAQ_BANCO       caminho do arquivo SQLite
    GOOGLE_CLIENT_ID    ID do cliente OAuth do Google (vazio = esconde o botão do Google)
"""
import os

PASTA = os.path.dirname(os.path.abspath(__file__))

SECRET_KEY = os.environ.get('CAFEMAQ_SECRET', 'troque-esta-chave-em-producao')

# O banco é criado sozinho na primeira execução
BANCO = os.environ.get('CAFEMAQ_BANCO', os.path.join(PASTA, 'database', 'cafemaq.db'))

# Login com Google: crie um "ID do cliente OAuth" (Aplicativo da Web) em
# https://console.cloud.google.com/apis/credentials e adicione em "Origens JavaScript autorizadas":
#   http://localhost:5000          (teste local)
#   https://seudominio.com.br      (site publicado)
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')

FUSO_HORARIO = 'America/Sao_Paulo'

SESSION_COOKIE_NAME = 'cafemaq'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
