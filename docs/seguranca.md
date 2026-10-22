# Segurança da Informação — CafeMaq

Documentação da disciplina **Segurança da Informação**. O critério pede no mínimo **2 mecanismos**
funcionais que protejam a **Confidencialidade, Integridade e Disponibilidade (CID)**, cobrindo
**autenticação, autorização e auditoria**. O CafeMaq implementa **7**:

| # | Mecanismo | C | I | D | Onde está |
|---|---|:-:|:-:|:-:|---|
| 1 | Controle de acesso e menor privilégio | ✔ | ✔ | | `utils.exigir_login`, `rotas/api.py`, `02_usuarios.sql` |
| 2 | Registro e monitoramento de logs (auditoria) | | ✔ | | `log_acesso`, `log_auditoria`, gatilhos, `logs/seguranca.log` |
| 3 | Proteção contra força bruta no login | ✔ | | ✔ | `utils.login_bloqueado`, `rotas/auth.py` |
| 4 | Gerenciamento e controle de sessão | ✔ | | | `config.py`, `utils.controlar_sessao`, `utils.fazer_login` |
| 5 | Políticas de segurança (senha e dados sensíveis) | ✔ | ✔ | | `utils.problemas_senha`, `.env`, `config.py` |
| 6 | Rotina de backup e recuperação | | ✔ | ✔ | `scripts/backup.py` |
| 7 | Proteções da aplicação web (CSRF, SQL Injection, XSS, cabeçalhos) | ✔ | ✔ | | `utils.py`, `banco.py`, templates |

---

## 1. Controle de acesso e menor privilégio

**Autorização na aplicação**
- Dois perfis: **dono** e **funcionário**. Cada área tem um `before_request` que barra quem não é do
  perfil (`exigir_login('dono')` / `exigir_login('funcionario')`). Na API a resposta é `401` (sem login)
  ou `403` (perfil errado), e a tentativa é registrada como `acesso_negado`.
- **Isolamento entre fazendas:** toda consulta filtra por `fazenda_id` da fazenda do dono logado
  (`... WHERE id = ? AND fazenda_id = ?`). Um dono que tenta abrir/alterar a máquina de outra fazenda
  recebe `404` — nem fica sabendo que ela existe (evita IDOR).
- O funcionário só vê as atividades da fazenda dele e só envia relatório com máquinas dessa fazenda.

**Menor privilégio no banco** (`database/mysql/02_usuarios.sql`)
- O site conecta com `cafemaq_app`, que só lê/grava dados. Não cria nem apaga tabelas, não lê outras
  bases e **não pode apagar nem alterar os logs** (só `SELECT, INSERT` neles).
- `cafemaq_admin` administra só a base `cafemaq`; `cafemaq_backup` é somente leitura.

**Como demonstrar:** entrar como funcionário e abrir `/dono/` (volta para o painel dele) ou `/api/maquinas`
(`403`). No MySQL, logado como `cafemaq_app`, rodar `DELETE FROM log_auditoria;` → *command denied*.

## 2. Registro e monitoramento de logs (auditoria)

- **`log_acesso`** (gravado pela aplicação): `login_ok`, `login_falha`, `login_bloqueado`, `login_google`,
  `cadastro`, `logout`, `sessao_expirada`, `acesso_negado` — com data, IP, navegador e e-mail.
- **`log_auditoria`** (gravado pelos **gatilhos** do banco, no MySQL e no SQLite do site publicado): toda alteração/exclusão de máquinas,
  funcionários, fazendas e contas, e toda manutenção nova, com os dados **antes e depois** em JSON, o
  usuário do banco e a pessoa logada no site. Como é o banco que grava, nem um bug no site deixa de auditar.
- **`logs/seguranca.log`**: os mesmos eventos de autenticação em arquivo, para monitorar no servidor
  (falhas e bloqueios aparecem como `WARNING`).
- Os logs são **imutáveis para a aplicação** (sem `UPDATE`/`DELETE`) e o hash da senha **nunca** vai para o log.

```sql
-- Tentativas de login com falha nas últimas 24 h, por IP
SELECT ip, COUNT(*) AS falhas FROM log_acesso
WHERE evento = 'login_falha' AND criado_em >= NOW() - INTERVAL 1 DAY GROUP BY ip ORDER BY falhas DESC;

-- Quem mexeu na máquina 1
SELECT criado_em, acao, usuario_app, dados_antes, dados_depois FROM log_auditoria
WHERE tabela = 'maquinas' AND registro_id = 1 ORDER BY id DESC;
```

## 3. Proteção contra força bruta

- Cada senha errada vira um `login_falha` no `log_acesso`.
- Antes de conferir a senha, o sistema conta as falhas recentes **do mesmo IP ou do mesmo e-mail**.
  Passou de `LOGIN_MAX_TENTATIVAS` (5) dentro de `LOGIN_JANELA_MIN` (15 min) → responde **HTTP 429** e
  nem testa a senha, mesmo que esteja certa.
- A mensagem de erro é a mesma para e-mail inexistente e senha errada (não revela quem tem conta).

**Como demonstrar:** errar a senha 5 vezes → na 6ª aparece “Muitas tentativas erradas. Aguarde 15 minutos”.

## 4. Gerenciamento e controle de sessão

- **Sessão nova a cada login** (`session.clear()` + token CSRF novo): evita fixação de sessão.
- **Expiração por inatividade:** 30 min parado (`SESSAO_INATIVIDADE_MIN`) e a sessão é encerrada e registrada
  como `sessao_expirada`. **Tempo máximo** de 8 h (`PERMANENT_SESSION_LIFETIME`).
- **Cookie protegido:** `HttpOnly` (JavaScript não lê), `SameSite=Lax` (não vai em requisições de outros
  sites) e `Secure` em produção (só HTTPS). O cookie é assinado com a `SECRET_KEY`.
- Páginas logadas são enviadas com `Cache-Control: no-store` (não ficam no cache do navegador).
- **Sair** limpa a sessão e registra `logout`.

## 5. Políticas de segurança

**Senhas**
- Mínimo de **8 caracteres, com letras e números**, diferente do e-mail (validado no servidor e no formulário).
- Guardadas só como **hash scrypt com salt** (`werkzeug.security`), nunca em texto.
- Login com Google valida o token direto no Google (emissor, destinatário, e-mail verificado e validade).

**Dados sensíveis e configuração**
- Senhas do banco e `SECRET_KEY` ficam no **`.env`**, fora do código e fora do GitHub (`.gitignore`).
  O repositório traz só o modelo `.env.example`.
- Em produção (`AMBIENTE=producao`) o sistema **não inicia sem `SECRET_KEY`**, desliga o modo debug e
  liga cookie seguro + HSTS.
- Requisições acima de 2 MB são recusadas (`MAX_CONTENT_LENGTH`).

## 6. Backup e recuperação

`scripts/backup.py` cuida da **disponibilidade**:

```bash
python scripts/backup.py                                   # cria backups/cafemaq_AAAAMMDD_HHMMSS.sql
python scripts/backup.py verificar backups/ARQUIVO.sql     # confere o SHA-256
python scripts/backup.py restaurar backups/ARQUIVO.sql     # verifica, pede confirmação e restaura
```

- MySQL: `mysqldump --single-transaction --routines --triggers` (cópia consistente com o site no ar),
  logado com o usuário **somente leitura** `cafemaq_backup`; a senha vai por variável de ambiente, não
  aparece na lista de processos. Sem `mysqldump`, o próprio Python gera o dump.
- SQLite: cópia pela API de backup do SQLite.
- Cada backup ganha um **`.sha256`**; a restauração **recusa** arquivo alterado/corrompido e pede para
  digitar `RESTAURAR` antes de substituir os dados.
- **Retenção:** guarda os 7 mais recentes (`BACKUP_MANTER`) e apaga os antigos.
- **Agendamento diário:** `0 23 * * * cd /caminho/cafe_maq && python3 scripts/backup.py` (cron),
  Agendador de Tarefas do Windows ou *Scheduled tasks* do PythonAnywhere.

## 7. Proteções da aplicação web

| Ameaça | Proteção |
|---|---|
| **SQL Injection** | 100% das consultas parametrizadas (`?` → `%s`), nunca concatenando texto do usuário (`banco.py`) |
| **CSRF** | Token aleatório por sessão em todo `POST/PUT/PATCH/DELETE`: campo `csrf` nos formulários e cabeçalho `X-CSRF-Token` no `fetch`; comparação em tempo constante |
| **XSS** | Jinja2 escapa tudo automaticamente; no JavaScript, texto vindo do usuário ou da API entra com `textContent` (o `innerHTML` só monta marcação fixa e números) |
| **Clickjacking / sniffing** | `X-Frame-Options: SAMEORIGIN`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy`, HSTS em produção |
| **Validação de entrada** | Tamanhos máximos, números e datas conferidos no servidor (`rotas/api.py`); `ENUM` e `CHECK` no banco; gatilho barra custo negativo |
| **Integridade dos dados** | Não deixa excluir máquina/funcionário/fazenda com histórico (`409 Conflict`) — oferece desativar |
| **Vazamento em erros** | Páginas de erro amigáveis; detalhes técnicos só no log do servidor |
