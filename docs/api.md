# API REST — CafeMaq

Documentação da disciplina **Programação Web**. O CRUD das quatro entidades principais é feito pela API
em [`rotas/api.py`](../rotas/api.py), cada operação com o seu **método HTTP**. As telas do painel do dono
chamam essa API pelo JavaScript ([`static/js/crud.js`](../static/js/crud.js)).

| Operação | Método | Resposta de sucesso |
|---|---|---|
| Ler (lista ou um item) | `GET` | `200 OK` |
| Criar | `POST` | `201 Created` + cabeçalho `Location` |
| Alterar o registro inteiro | `PUT` | `200 OK` |
| Alterar um campo (ativar/desativar, status) | `PATCH` | `200 OK` |
| Excluir | `DELETE` | `200 OK` |

Erros sempre em JSON `{"erro": "..."}`:
`401` sem login · `403` sem permissão · `404` não existe ou é de outra fazenda ·
`409` conflito (ex.: excluir máquina com histórico) · `422` dados inválidos (com a lista em `"erros"`) ·
`429` muitas tentativas de login.

Toda requisição que altera dados precisa do token CSRF no cabeçalho `X-CSRF-Token`
(o valor está na `<meta name="csrf-token">` de qualquer página).

## Recursos

| Recurso | Coleção | Item |
|---|---|---|
| Máquinas | `GET` `POST` `/api/maquinas` | `GET` `PUT` `PATCH` `DELETE` `/api/maquinas/<id>` |
| Funcionários | `GET` `POST` `/api/funcionarios` | `GET` `PUT` `PATCH` `DELETE` `/api/funcionarios/<id>` |
| Atividades | `GET` `POST` `/api/atividades` (`?status=pendente`) | `GET` `PUT` `PATCH` `DELETE` `/api/atividades/<id>` |
| Fazendas | `GET` `POST` `/api/fazendas` | `GET` `PUT` `DELETE` `/api/fazendas/<id>` |
| Custos (procedimento `sp_resumo_custos`) | `GET /api/fazenda/custos?inicio=AAAA-MM-DD&fim=AAAA-MM-DD` | |
| Catálogo de máquinas (público) | `GET /api/catalogo` · `GET /api/catalogo/<tipo>` · `GET /api/catalogo/busca?q=arbus` | |

Só o **dono logado** usa os recursos da fazenda, e só enxerga os registros da **própria** fazenda.

## Exemplos

```http
POST /api/maquinas
Content-Type: application/json
X-CSRF-Token: 3f9a...

{"tipo": "trator", "nome": "Trator 02", "marca": "Valtra", "modelo": "A950", "ano": 2021, "horimetro": 830}
```
```http
HTTP/1.1 201 Created
Location: /api/maquinas/7

{"mensagem": "Máquina cadastrada...", "maquina": {"id": 7, "nome": "Trator 02", "revisao": {"estado": "sem", ...}}}
```

```http
PUT /api/maquinas/7          {"tipo": "trator", "nome": "Trator 02", "marca": "Valtra", "horimetro": 900}
PATCH /api/maquinas/7        {"ativo": 0}
DELETE /api/maquinas/7
PATCH /api/atividades/3      {"status": "concluida"}
```

```http
POST /api/maquinas   {"tipo": "trator", "ano": 1800}

HTTP/1.1 422 Unprocessable Entity
{"erro": "Ano deve estar entre 1950 e 2027.", "erros": ["Ano deve estar entre 1950 e 2027."]}
```

```http
DELETE /api/maquinas/1

HTTP/1.1 409 Conflict
{"erro": "\"Trator 01\" tem histórico de uso ou manutenção. Desative em vez de excluir, para não perder os custos registrados."}
```

## Onde cada operação aparece na tela

| Tela | Criar (POST) | Editar (PUT) | Desativar / status (PATCH) | Excluir (DELETE) |
|---|---|---|---|---|
| Máquinas | formulário “Cadastrar máquina” | botão **Editar** | **Desativar / Reativar** | **Excluir** |
| Funcionários | formulário “Cadastrar funcionário” | botão **Editar** | **Desativar / Reativar** | **Excluir** |
| Atividades | formulário “Nova atividade” | botão **Editar** | **Concluir / Arquivar / Reabrir** | **Excluir** |
| Fazendas | formulário “Cadastrar fazenda” | botão **Editar** | — | **Excluir** |

Depois de cada operação a tela mostra um aviso de sucesso; se der erro, a mensagem aparece em cima do
formulário sem apagar o que foi digitado.

## Estrutura do projeto Flask

```
app.py            fábrica do app: config, blueprints, segurança, páginas de erro
config.py         configurações lidas do .env
banco.py          conexão MySQL/SQLite e funções de consulta parametrizada
utils.py          datas, formatação, CSRF, sessão, logs, política de senha, login
catalogo.py       catálogo de tipos/marcas/modelos de máquinas
rotas/
  publico.py      site institucional
  auth.py         login, cadastro, Google, sair
  dono.py         painel do dono (páginas)
  funcionario.py  painel do funcionário (ponto e relatório)
  api.py          API REST (CRUD)
templates/        páginas Jinja2 (herdam de base.html / painel.html)
static/           CSS, JavaScript e imagens
```
