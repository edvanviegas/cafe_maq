# Publicar o CafeMaq (deploy)

O site publicado usa o **SQLite**: o banco é um arquivo dentro da pasta do projeto, sem servidor de banco
e sem senha. O **PythonAnywhere** tem plano gratuito que roda Flask, e é o caminho mais simples.
(Hospedagem comum de PHP, como a HostGator básica, não roda Flask.)

## PythonAnywhere (gratuito)

Onde estiver escrito **SEUUSUARIO**, troque pelo seu usuário do PythonAnywhere.

1. Crie a conta em <https://www.pythonanywhere.com> (*Pricing & signup* → *Create a Beginner account*).
   O site fica em `https://SEUUSUARIO.pythonanywhere.com`.
2. **Código:** aba *Consoles* → *Bash*:
   ```bash
   git clone https://github.com/edvanviegas/cafe_maq.git
   cd cafe_maq
   pip3 install --user -r requirements.txt
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```
   O último comando mostra um código grande: copie, é a sua `SECRET_KEY`.
3. **Configuração:**
   ```bash
   cp .env.example .env
   nano .env
   ```
   Mude só estas duas linhas e deixe o resto como está:
   ```ini
   AMBIENTE=producao
   SECRET_KEY=<o código grande que você copiou>
   ```
   Para salvar: **Ctrl+O**, **Enter**, **Ctrl+X**.
4. **Banco com dados de exemplo:**
   ```bash
   python3 scripts/instalar_banco.py --sqlite --exemplo
   ```
   Tem que aparecer **OK** duas vezes.
5. **Web app:** aba *Web* → *Add a new web app* → *Next* → *Manual configuration* → Python mais novo → *Next*.
   - *Source code* e *Working directory*: `/home/SEUUSUARIO/cafe_maq`
   - *Static files*: URL `/static/` → Directory `/home/SEUUSUARIO/cafe_maq/static`
   - *Security*: ligue **Force HTTPS**.
6. Clique no link do *WSGI configuration file*, apague tudo, deixe só isto e clique em *Save*:
   ```python
   import sys
   sys.path.insert(0, '/home/SEUUSUARIO/cafe_maq')
   from app import app as application
   ```
7. Volte na aba *Web* e clique em **Reload**. Abra `https://SEUUSUARIO.pythonanywhere.com` e entre com
   `dono@cafemaq.com.br` (senha `Cafe@2026`).
8. **Backup diário (opcional):** aba *Tasks* → `python3 /home/SEUUSUARIO/cafe_maq/scripts/backup.py`.

Para atualizar depois: `cd ~/cafe_maq && git pull` e **Reload** na aba *Web*. O banco
(`database/cafemaq.db`) fica fora do Git, então o `git pull` não apaga os dados.

> No plano grátis o site fica no ar por 3 meses. Antes de vencer, clique em
> **Run until 3 months from today** na aba *Web*.
>
> Deu erro? Na aba *Web*, o link **Error log** mostra o motivo.

## Depois de publicar

Coloque o link no **About** do repositório (engrenagem ao lado de *About* → *Website*) e no relatório do AVA.

## Usar o MySQL em vez do SQLite (opcional)

A versão MySQL é a entrega de Banco de Dados II e roda no computador (MySQL Workbench / XAMPP):
`DB_TIPO=mysql` no `.env` e `python scripts/instalar_banco.py --exemplo` (ver
[`banco-de-dados.md`](banco-de-dados.md)). Para publicar com MySQL no PythonAnywhere, crie o banco na
aba *Databases* e rode `python3 scripts/instalar_banco.py --host SEUUSUARIO.mysql.pythonanywhere-services.com
--usuario SEUUSUARIO --base 'SEUUSUARIO$cafemaq' --sem-usuarios --exemplo`.

## Login com Google (opcional)

1. Acesse <https://console.cloud.google.com> → crie um projeto.
2. *APIs e serviços → Tela de permissão OAuth*: configure como **Externo** e preencha nome e e-mail.
3. *Credenciais → Criar credenciais → ID do cliente OAuth → Aplicativo da Web*.
4. Em **Origens JavaScript autorizadas** adicione `http://localhost:5000` e o endereço publicado.
5. Copie o **ID do cliente** para `GOOGLE_CLIENT_ID` no `.env`.
