# CafeMaq

Site sobre custos de manutenção de maquinário em fazendas de café, com sistema de gestão
para donos de lavoura e funcionários.

Desenvolvido por **Hiago Amaral** e **Edvan Henrique**.

## Estrutura

Feito em **Python + Flask**, com banco **SQLite**.

| Pasta / arquivo | Conteúdo |
|---|---|
| `app.py` | Cria o app Flask e registra as rotas (é o arquivo que se executa) |
| `config.py` | Configurações: chave secreta, caminho do banco, login com Google |
| `banco.py` | Conexão com o SQLite e funções de consulta (`um`, `todos`, `valor`, `inserir`) |
| `utils.py` | Datas, formatação, proteção CSRF, login e situação da revisão das máquinas |
| `catalogo.py` | Catálogo de tipos, marcas e modelos de máquinas (usado pela API) |
| `rotas/` | Rotas separadas por área: `publico`, `auth`, `dono`, `funcionario`, `api` |
| `templates/` | Páginas HTML (Jinja2) |
| `static/` | CSS, JavaScript e imagens |
| `database/schema.sql` | Estrutura do banco (criado sozinho na primeira execução) |

## Rodar no computador

Precisa do Python 3.10 ou mais novo. Na pasta do projeto:

```
pip install -r requirements.txt
python app.py
```

Abra http://localhost:5000. O banco é criado sozinho em `database/cafemaq.db`.

## API de máquinas

Usada no cadastro de máquinas: ao escolher o tipo, o formulário sugere marcas, modelos, intervalo
de revisão e valor de referência; a busca (ex.: "arbus", "K3") preenche tipo, marca e modelo de uma vez.

| Rota | Retorna |
|---|---|
| `GET /api/catalogo` | Todos os tipos de máquina com dados de referência |
| `GET /api/catalogo/<tipo>` | Um tipo com marcas, modelos e checklist preventivo |
| `GET /api/catalogo/busca?q=texto` | Modelos que combinam com o texto |
| `GET /api/maquinas` | Máquinas cadastradas na fazenda (dono logado) |
| `GET /api/maquinas/<id>` | Uma máquina com situação da revisão e histórico de manutenções |

Para acrescentar marcas e modelos, edite `MODELOS` em `catalogo.py`.

## Publicar

Hospedagem compartilhada comum de PHP (como a HostGator básica) não roda Flask. Opções simples com
plano gratuito: **PythonAnywhere** ou **Render**. Em produção, defina a variável de ambiente
`CAFEMAQ_SECRET` com um texto aleatório longo e rode com um servidor WSGI (ex.: `gunicorn app:app`).

## Login com Google

1. Acesse https://console.cloud.google.com → crie um projeto.
2. *APIs e serviços → Tela de permissão OAuth*: configure como **Externo** e preencha nome e e-mail.
3. *Credenciais → Criar credenciais → ID do cliente OAuth → Aplicativo da Web*.
4. Em **Origens JavaScript autorizadas** adicione `http://localhost:5000` e `https://seudominio.com.br`.
5. Copie o **ID do cliente** para `GOOGLE_CLIENT_ID` em `config.py` (ou na variável de ambiente de mesmo nome).

## Como funciona

1. O **dono** cria a conta, cadastra a fazenda, as máquinas e os funcionários (pelo e-mail).
2. O **funcionário** cria a conta (ou entra com Google) usando o mesmo e-mail e é vinculado automaticamente.
3. O dono cria **atividades** (únicas ou diárias), que podem ter responsável e máquina.
4. O funcionário **bate o ponto** e, no fim do dia, envia o **relatório**: o que foi feito, horas,
   horímetro e problemas nas máquinas. O envio pode registrar a saída automaticamente.
5. Problemas relatados viram **alertas** na aba **Manutenção**. Lá o dono escolhe uma das máquinas
   cadastradas, vê a situação da revisão pelo horímetro, marca o checklist preventivo, registra o
   serviço e o custo, e pode agendar a manutenção para um funcionário.
6. A aba **Desempenho** resume horas, atividades, taxa de conclusão, relatórios, problemas e custos
   por dia, semana ou mês.
