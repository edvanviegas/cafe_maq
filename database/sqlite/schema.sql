-- CafeMaq - estrutura do banco SQLite (DB_TIPO=sqlite) - o banco do site publicado.
-- É criado/atualizado automaticamente ao iniciar o app (banco.py).
--
-- A entrega de Banco de Dados II é a versão MySQL (database/mysql), que além
-- das tabelas e gatilhos tem usuários com permissões, funções e procedimentos
-- (o SQLite não tem usuários nem procedimentos).

CREATE TABLE IF NOT EXISTS usuarios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  senha_hash TEXT NULL,
  google_id TEXT NULL UNIQUE,
  tipo TEXT NOT NULL CHECK (tipo IN ('dono','funcionario')),
  criado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fazendas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  dono_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  nome TEXT NOT NULL,
  municipio TEXT NULL,
  estado TEXT NULL,
  area_ha REAL NULL,
  producao_sacas INTEGER NULL,
  criado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS funcionarios (
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

CREATE TABLE IF NOT EXISTS maquinas (
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

CREATE TABLE IF NOT EXISTS atividades (
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

CREATE TABLE IF NOT EXISTS ponto (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fazenda_id INTEGER NOT NULL REFERENCES fazendas(id) ON DELETE CASCADE,
  funcionario_id INTEGER NOT NULL REFERENCES funcionarios(id) ON DELETE CASCADE,
  entrada TEXT NOT NULL,
  saida TEXT NULL
);

CREATE TABLE IF NOT EXISTS relatorios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fazenda_id INTEGER NOT NULL REFERENCES fazendas(id) ON DELETE CASCADE,
  funcionario_id INTEGER NOT NULL REFERENCES funcionarios(id) ON DELETE CASCADE,
  data TEXT NOT NULL,
  observacoes TEXT NULL,
  criado_em TEXT NOT NULL,
  UNIQUE (funcionario_id, data)
);

CREATE TABLE IF NOT EXISTS relatorio_itens (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  relatorio_id INTEGER NOT NULL REFERENCES relatorios(id) ON DELETE CASCADE,
  atividade_id INTEGER NULL REFERENCES atividades(id) ON DELETE SET NULL,
  atividade_titulo TEXT NOT NULL,
  status TEXT NOT NULL,
  horas REAL NOT NULL DEFAULT 0,
  maquina_id INTEGER NULL REFERENCES maquinas(id) ON DELETE SET NULL,
  horimetro REAL NULL
);

CREATE TABLE IF NOT EXISTS ocorrencias (
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

CREATE TABLE IF NOT EXISTS manutencoes (
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

-- Log de autenticação (login, falhas, bloqueios, saída) - usado contra força bruta
CREATE TABLE IF NOT EXISTS log_acesso (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  usuario_id INTEGER NULL REFERENCES usuarios(id) ON DELETE SET NULL,
  email TEXT NULL,
  evento TEXT NOT NULL,
  ip TEXT NULL,
  navegador TEXT NULL,
  criado_em TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_log_acesso_ip ON log_acesso (ip, evento, criado_em);
CREATE INDEX IF NOT EXISTS ix_log_acesso_email ON log_acesso (email, evento, criado_em);

-- Trilha de auditoria (no MySQL é preenchida pelos triggers)
CREATE TABLE IF NOT EXISTS log_auditoria (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tabela TEXT NOT NULL,
  registro_id INTEGER NOT NULL,
  acao TEXT NOT NULL,
  dados_antes TEXT NULL,
  dados_depois TEXT NULL,
  usuario_app INTEGER NULL,
  usuario_bd TEXT NOT NULL DEFAULT 'sqlite',
  criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================================
-- Quem está logado no site, para a auditoria.
-- O SQLite não tem variáveis de sessão (como o @app_usuario_id do MySQL):
-- a aplicação grava aqui o id da pessoa logada a cada requisição
-- (banco.definir_usuario_app) e os gatilhos leem daqui.
-- =====================================================================
CREATE TABLE IF NOT EXISTS sessao_app (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  usuario_id INTEGER NULL
);
INSERT OR IGNORE INTO sessao_app (id, usuario_id) VALUES (1, NULL);

-- =====================================================================
-- GATILHOS (TRIGGERS) - os mesmos do MySQL (database/mysql/03_rotinas.sql)
-- Horário: datetime('now', '-3 hours') = horário de Brasília.
-- =====================================================================

-- Antes de gravar uma manutenção: barra custo ou horímetro negativos,
-- mesmo que alguém insira direto no banco (sem passar pelo site).
CREATE TRIGGER IF NOT EXISTS trg_manutencoes_antes_inserir
BEFORE INSERT ON manutencoes
BEGIN
  SELECT RAISE(ABORT, 'O custo da manutenção não pode ser negativo.') WHERE NEW.custo < 0;
  SELECT RAISE(ABORT, 'O horímetro não pode ser negativo.') WHERE NEW.horimetro < 0;
END;

-- Depois de gravar uma manutenção: atualiza o horímetro da máquina,
-- resolve o problema ligado e registra na auditoria.
CREATE TRIGGER IF NOT EXISTS trg_manutencoes_depois_inserir
AFTER INSERT ON manutencoes
BEGIN
  UPDATE maquinas SET horimetro = NEW.horimetro
   WHERE id = NEW.maquina_id AND NEW.horimetro IS NOT NULL AND horimetro < NEW.horimetro;

  UPDATE ocorrencias SET status = 'resolvida'
   WHERE id = NEW.ocorrencia_id AND status = 'aberta';

  INSERT INTO log_auditoria (tabela, registro_id, acao, dados_antes, dados_depois, usuario_app, usuario_bd, criado_em)
  VALUES ('manutencoes', NEW.id, 'INSERT', NULL,
          json_object('maquina_id', NEW.maquina_id, 'data', NEW.data, 'tipo', NEW.tipo,
                      'custo', NEW.custo, 'horimetro', NEW.horimetro, 'descricao', NEW.descricao),
          (SELECT usuario_id FROM sessao_app WHERE id = 1), 'aplicacao', datetime('now', '-3 hours'));
END;

-- Ao resolver um problema, preenche a data de resolução; ao reabrir, limpa.
CREATE TRIGGER IF NOT EXISTS trg_ocorrencias_resolvida
AFTER UPDATE OF status ON ocorrencias
WHEN NEW.status = 'resolvida' AND NEW.resolvida_em IS NULL
BEGIN
  UPDATE ocorrencias SET resolvida_em = datetime('now', '-3 hours') WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_ocorrencias_reaberta
AFTER UPDATE OF status ON ocorrencias
WHEN NEW.status = 'aberta' AND NEW.resolvida_em IS NOT NULL
BEGIN
  UPDATE ocorrencias SET resolvida_em = NULL WHERE id = NEW.id;
END;

-- Auditoria de máquinas: antes e depois de cada alteração, e exclusões.
CREATE TRIGGER IF NOT EXISTS trg_maquinas_depois_atualizar
AFTER UPDATE ON maquinas
BEGIN
  INSERT INTO log_auditoria (tabela, registro_id, acao, dados_antes, dados_depois, usuario_app, usuario_bd, criado_em)
  VALUES ('maquinas', NEW.id, 'UPDATE',
          json_object('nome', OLD.nome, 'tipo', OLD.tipo, 'marca', OLD.marca, 'modelo', OLD.modelo,
                      'horimetro', OLD.horimetro, 'preco', OLD.preco, 'ativo', OLD.ativo),
          json_object('nome', NEW.nome, 'tipo', NEW.tipo, 'marca', NEW.marca, 'modelo', NEW.modelo,
                      'horimetro', NEW.horimetro, 'preco', NEW.preco, 'ativo', NEW.ativo),
          (SELECT usuario_id FROM sessao_app WHERE id = 1), 'aplicacao', datetime('now', '-3 hours'));
END;

CREATE TRIGGER IF NOT EXISTS trg_maquinas_depois_excluir
AFTER DELETE ON maquinas
BEGIN
  INSERT INTO log_auditoria (tabela, registro_id, acao, dados_antes, dados_depois, usuario_app, usuario_bd, criado_em)
  VALUES ('maquinas', OLD.id, 'DELETE',
          json_object('fazenda_id', OLD.fazenda_id, 'nome', OLD.nome, 'tipo', OLD.tipo, 'marca', OLD.marca,
                      'modelo', OLD.modelo, 'horimetro', OLD.horimetro, 'preco', OLD.preco),
          NULL, (SELECT usuario_id FROM sessao_app WHERE id = 1), 'aplicacao', datetime('now', '-3 hours'));
END;

-- Auditoria de funcionários.
CREATE TRIGGER IF NOT EXISTS trg_funcionarios_depois_atualizar
AFTER UPDATE ON funcionarios
BEGIN
  INSERT INTO log_auditoria (tabela, registro_id, acao, dados_antes, dados_depois, usuario_app, usuario_bd, criado_em)
  VALUES ('funcionarios', NEW.id, 'UPDATE',
          json_object('nome', OLD.nome, 'email', OLD.email, 'funcao', OLD.funcao,
                      'ativo', OLD.ativo, 'usuario_id', OLD.usuario_id),
          json_object('nome', NEW.nome, 'email', NEW.email, 'funcao', NEW.funcao,
                      'ativo', NEW.ativo, 'usuario_id', NEW.usuario_id),
          (SELECT usuario_id FROM sessao_app WHERE id = 1), 'aplicacao', datetime('now', '-3 hours'));
END;

CREATE TRIGGER IF NOT EXISTS trg_funcionarios_depois_excluir
AFTER DELETE ON funcionarios
BEGIN
  INSERT INTO log_auditoria (tabela, registro_id, acao, dados_antes, dados_depois, usuario_app, usuario_bd, criado_em)
  VALUES ('funcionarios', OLD.id, 'DELETE',
          json_object('fazenda_id', OLD.fazenda_id, 'nome', OLD.nome, 'email', OLD.email, 'funcao', OLD.funcao),
          NULL, (SELECT usuario_id FROM sessao_app WHERE id = 1), 'aplicacao', datetime('now', '-3 hours'));
END;

-- Auditoria de exclusão de fazenda (apaga tudo em cascata, então fica o registro).
CREATE TRIGGER IF NOT EXISTS trg_fazendas_depois_excluir
AFTER DELETE ON fazendas
BEGIN
  INSERT INTO log_auditoria (tabela, registro_id, acao, dados_antes, dados_depois, usuario_app, usuario_bd, criado_em)
  VALUES ('fazendas', OLD.id, 'DELETE',
          json_object('dono_id', OLD.dono_id, 'nome', OLD.nome, 'municipio', OLD.municipio, 'estado', OLD.estado),
          NULL, (SELECT usuario_id FROM sessao_app WHERE id = 1), 'aplicacao', datetime('now', '-3 hours'));
END;

-- Auditoria de contas: registra se a senha mudou, SEM copiar o hash da senha.
CREATE TRIGGER IF NOT EXISTS trg_usuarios_depois_atualizar
AFTER UPDATE ON usuarios
BEGIN
  INSERT INTO log_auditoria (tabela, registro_id, acao, dados_antes, dados_depois, usuario_app, usuario_bd, criado_em)
  VALUES ('usuarios', NEW.id, 'UPDATE',
          json_object('nome', OLD.nome, 'email', OLD.email, 'tipo', OLD.tipo,
                      'tem_google', OLD.google_id IS NOT NULL),
          json_object('nome', NEW.nome, 'email', NEW.email, 'tipo', NEW.tipo,
                      'tem_google', NEW.google_id IS NOT NULL,
                      'senha_alterada', OLD.senha_hash IS NOT NEW.senha_hash),
          (SELECT usuario_id FROM sessao_app WHERE id = 1), 'aplicacao', datetime('now', '-3 hours'));
END;
