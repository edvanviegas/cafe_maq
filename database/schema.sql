-- CafeMaq - estrutura do banco SQLite.
-- É criado automaticamente na primeira execução do app (banco.py).

CREATE TABLE usuarios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  senha_hash TEXT NULL,
  google_id TEXT NULL UNIQUE,
  tipo TEXT NOT NULL CHECK (tipo IN ('dono','funcionario')),
  criado_em TEXT NOT NULL
);

CREATE TABLE fazendas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  dono_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  nome TEXT NOT NULL,
  municipio TEXT NULL,
  estado TEXT NULL,
  area_ha REAL NULL,
  producao_sacas INTEGER NULL,
  criado_em TEXT NOT NULL
);

CREATE TABLE funcionarios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fazenda_id INTEGER NOT NULL REFERENCES fazendas(id) ON DELETE CASCADE,
  usuario_id INTEGER NULL REFERENCES usuarios(id) ON DELETE SET NULL,
  nome TEXT NOT NULL,
  email TEXT NOT NULL,
  funcao TEXT NULL,
  ativo INTEGER NOT NULL DEFAULT 1,
  criado_em TEXT NOT NULL,
  UNIQUE (fazenda_id, email)
);

CREATE TABLE maquinas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fazenda_id INTEGER NOT NULL REFERENCES fazendas(id) ON DELETE CASCADE,
  nome TEXT NOT NULL,
  tipo TEXT NOT NULL,
  marca TEXT NULL,
  modelo TEXT NULL,
  ano INTEGER NULL,
  revisao_horas REAL NULL,
  horimetro REAL NOT NULL DEFAULT 0,
  preco REAL NULL,
  ativo INTEGER NOT NULL DEFAULT 1,
  criado_em TEXT NOT NULL
);

CREATE TABLE atividades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fazenda_id INTEGER NOT NULL REFERENCES fazendas(id) ON DELETE CASCADE,
  titulo TEXT NOT NULL,
  descricao TEXT NULL,
  tipo TEXT NOT NULL DEFAULT 'operacao',
  maquina_id INTEGER NULL REFERENCES maquinas(id) ON DELETE SET NULL,
  funcionario_id INTEGER NULL REFERENCES funcionarios(id) ON DELETE SET NULL,
  data_prevista TEXT NULL,
  recorrente INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'pendente',
  criado_em TEXT NOT NULL
);

CREATE TABLE ponto (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fazenda_id INTEGER NOT NULL REFERENCES fazendas(id) ON DELETE CASCADE,
  funcionario_id INTEGER NOT NULL REFERENCES funcionarios(id) ON DELETE CASCADE,
  entrada TEXT NOT NULL,
  saida TEXT NULL
);

CREATE TABLE relatorios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fazenda_id INTEGER NOT NULL REFERENCES fazendas(id) ON DELETE CASCADE,
  funcionario_id INTEGER NOT NULL REFERENCES funcionarios(id) ON DELETE CASCADE,
  data TEXT NOT NULL,
  observacoes TEXT NULL,
  criado_em TEXT NOT NULL,
  UNIQUE (funcionario_id, data)
);

CREATE TABLE relatorio_itens (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  relatorio_id INTEGER NOT NULL REFERENCES relatorios(id) ON DELETE CASCADE,
  atividade_id INTEGER NULL REFERENCES atividades(id) ON DELETE SET NULL,
  atividade_titulo TEXT NOT NULL,
  status TEXT NOT NULL,
  horas REAL NOT NULL DEFAULT 0,
  maquina_id INTEGER NULL REFERENCES maquinas(id) ON DELETE SET NULL,
  horimetro REAL NULL
);

CREATE TABLE ocorrencias (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fazenda_id INTEGER NOT NULL REFERENCES fazendas(id) ON DELETE CASCADE,
  maquina_id INTEGER NOT NULL REFERENCES maquinas(id) ON DELETE CASCADE,
  funcionario_id INTEGER NULL REFERENCES funcionarios(id) ON DELETE SET NULL,
  relatorio_id INTEGER NULL REFERENCES relatorios(id) ON DELETE SET NULL,
  descricao TEXT NOT NULL,
  gravidade TEXT NOT NULL DEFAULT 'media',
  status TEXT NOT NULL DEFAULT 'aberta',
  criado_em TEXT NOT NULL,
  resolvida_em TEXT NULL
);

CREATE TABLE manutencoes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fazenda_id INTEGER NOT NULL REFERENCES fazendas(id) ON DELETE CASCADE,
  maquina_id INTEGER NOT NULL REFERENCES maquinas(id) ON DELETE CASCADE,
  data TEXT NOT NULL,
  tipo TEXT NOT NULL,
  descricao TEXT NOT NULL,
  custo REAL NOT NULL DEFAULT 0,
  horimetro REAL NULL,
  ocorrencia_id INTEGER NULL REFERENCES ocorrencias(id) ON DELETE SET NULL,
  criado_em TEXT NOT NULL
);
