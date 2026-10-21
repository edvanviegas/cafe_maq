# Publicar o CafeMaq (deploy)

Hospedagem comum de PHP (como a HostGator básica) não roda Flask. O **PythonAnywhere** tem plano
gratuito **com MySQL incluso**, então é a opção mais simples para este projeto.

## PythonAnywhere (gratuito)

1. Crie a conta em <https://www.pythonanywhere.com> (plano *Beginner*). O site fica em
   `https://SEUUSUARIO.pythonanywhere.com`.
2. **Banco:** aba *Databases* → defina a senha do MySQL → em *Create database* digite `cafemaq`.
   A base criada se chama `SEUUSUARIO$cafemaq`.
3. **Código:** aba *Consoles* → *Bash*:
   ```bash
   git clone https://github.com/edvanviegas/cafe_maq.git
   cd cafe_maq
   pip3 install --user -r requirements.txt
   cp .env.example .env && nano .env
   ```
   No `.env`:
   ```ini
   AMBIENTE=producao
   SECRET_KEY=<resultado de: python3 -c "import secrets; print(secrets.token_hex(32))">
   DB_TIPO=mysql
   DB_HOST=SEUUSUARIO.mysql.pythonanywhere-services.com
   DB_NOME=SEUUSUARIO$cafemaq
   DB_USUARIO=SEUUSUARIO
   DB_SENHA=<senha do MySQL do passo 2>
   ```
4. **Tabelas, rotinas e dados de exemplo** (a hospedagem não deixa criar usuários do MySQL, então o
   `02_usuarios.sql` fica para a demonstração local):
   ```bash
   python3 scripts/instalar_banco.py --host SEUUSUARIO.mysql.pythonanywhere-services.com \
       --usuario SEUUSUARIO --base 'SEUUSUARIO$cafemaq' --sem-usuarios --exemplo
   ```
5. **Web app:** aba *Web* → *Add a new web app* → *Manual configuration* → Python 3.10+.
   - *Source code* e *Working directory*: `/home/SEUUSUARIO/cafe_maq`
   - Abra o *WSGI configuration file*, apague tudo e deixe:
     ```python
     import sys
     sys.path.insert(0, '/home/SEUUSUARIO/cafe_maq')
     from app import app as application
     ```
   - Em *Security*, ligue **Force HTTPS**.
   - Clique em **Reload**.
6. **Backup diário:** aba *Tasks* → `python3 /home/SEUUSUARIO/cafe_maq/scripts/backup.py`
   (coloque `BACKUP_USUARIO=SEUUSUARIO` e `BACKUP_SENHA=` no `.env`).
7. **Login com Google (opcional):** adicione `https://SEUUSUARIO.pythonanywhere.com` nas origens
   autorizadas do ID do cliente OAuth e preencha `GOOGLE_CLIENT_ID` no `.env`.

Para atualizar depois: `cd ~/cafe_maq && git pull` e **Reload** na aba *Web*.

> Se a hospedagem recusar criar as funções (erro 1419 de *binary logging*), peça ao suporte para
> liberar `log_bin_trust_function_creators`. Enquanto isso, só a tabela de custos da página Desempenho
> (que chama o `sp_resumo_custos`, dependente das funções) fica fora; o resto do sistema funciona.

## Depois de publicar

Coloque o link no **About** do repositório (engrenagem ao lado de *About* → *Website*) e no relatório do AVA.

## Login com Google (opcional)

1. Acesse <https://console.cloud.google.com> → crie um projeto.
2. *APIs e serviços → Tela de permissão OAuth*: configure como **Externo** e preencha nome e e-mail.
3. *Credenciais → Criar credenciais → ID do cliente OAuth → Aplicativo da Web*.
4. Em **Origens JavaScript autorizadas** adicione `http://localhost:5000` e o endereço publicado.
5. Copie o **ID do cliente** para `GOOGLE_CLIENT_ID` no `.env`.
