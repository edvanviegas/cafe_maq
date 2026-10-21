-- =====================================================================
-- CafeMaq - MODELO FÍSICO (MySQL 8)
-- ---------------------------------------------------------------------
-- Cria a base de dados "cafemaq" e todas as tabelas do sistema.
--
-- Ordem de execução dos scripts:
--   01_estrutura.sql      -> base, tabelas, chaves e índices   (este arquivo)
--   02_usuarios.sql       -> usuários do banco e permissões
--   03_rotinas.sql        -> funções, procedimentos e gatilhos (triggers)
--   04_dados_exemplo.sql  -> dados de demonstração (opcional)
--
-- Executar como root (ou outro usuário com permissão de CREATE):
--   mysql -u root -p < database/mysql/01_estrutura.sql
--
-- Convenções:
--   * Motor InnoDB (transações e chaves estrangeiras) e utf8mb4 (acentos e emojis).
--   * Toda tabela tem "id" inteiro autoincremento como chave primária.
--   * "criado_em" guarda quando o registro foi criado.
--   * Campos booleanos usam TINYINT(1): 1 = sim / 0 = não.
-- =====================================================================

CREATE DATABASE IF NOT EXISTS cafemaq
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE cafemaq;

-- ---------------------------------------------------------------------
-- usuarios: contas de acesso ao sistema (donos de fazenda e funcionários).
-- A senha nunca é salva em texto: guardamos só o hash (PBKDF2/scrypt do Werkzeug).
-- Contas criadas pelo "Continuar com o Google" não têm senha (senha_hash NULL).
-- ---------------------------------------------------------------------
CREATE TABLE usuarios (
  id          INT UNSIGNED NOT NULL AUTO_INCREMENT,
  nome        VARCHAR(120) NOT NULL,
  email       VARCHAR(255) NOT NULL,
  senha_hash  VARCHAR(255) NULL COMMENT 'Hash da senha; NULL quando a conta usa só o Google',
  google_id   VARCHAR(64)  NULL COMMENT 'Identificador "sub" devolvido pelo Google',
  tipo        ENUM('dono','funcionario') NOT NULL,
  criado_em   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_usuarios_email (email),
  UNIQUE KEY uq_usuarios_google (google_id)
) ENGINE=InnoDB COMMENT='Contas de acesso (dono ou funcionário)';

-- ---------------------------------------------------------------------
-- fazendas: propriedades de café. Um dono pode ter várias.
-- ---------------------------------------------------------------------
CREATE TABLE fazendas (
  id              INT UNSIGNED NOT NULL AUTO_INCREMENT,
  dono_id         INT UNSIGNED NOT NULL,
  nome            VARCHAR(120) NOT NULL,
  municipio       VARCHAR(120) NULL,
  estado          CHAR(2)      NULL COMMENT 'UF, ex.: RO, MG',
  area_ha         DECIMAL(10,2) NULL COMMENT 'Área plantada em hectares',
  producao_sacas  INT UNSIGNED NULL COMMENT 'Produção anual em sacas de 60 kg',
  criado_em       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_fazendas_dono (dono_id),
  CONSTRAINT fk_fazendas_dono FOREIGN KEY (dono_id) REFERENCES usuarios (id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='Fazendas cadastradas pelos donos';

-- ---------------------------------------------------------------------
-- funcionarios: vínculo de uma pessoa com uma fazenda.
-- O dono cadastra pelo e-mail; quando a pessoa cria a conta com o mesmo
-- e-mail, usuario_id é preenchido (vínculo automático).
-- ---------------------------------------------------------------------
CREATE TABLE funcionarios (
  id          INT UNSIGNED NOT NULL AUTO_INCREMENT,
  fazenda_id  INT UNSIGNED NOT NULL,
  usuario_id  INT UNSIGNED NULL COMMENT 'Conta do funcionário (NULL até ele se cadastrar)',
  nome        VARCHAR(120) NOT NULL,
  email       VARCHAR(255) NOT NULL,
  funcao      VARCHAR(80)  NULL,
  ativo       TINYINT(1)   NOT NULL DEFAULT 1,
  criado_em   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_funcionarios_fazenda_email (fazenda_id, email),
  KEY ix_funcionarios_usuario (usuario_id),
  CONSTRAINT fk_funcionarios_fazenda FOREIGN KEY (fazenda_id) REFERENCES fazendas (id) ON DELETE CASCADE,
  CONSTRAINT fk_funcionarios_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='Equipe de cada fazenda';

-- ---------------------------------------------------------------------
-- maquinas: maquinário da fazenda (tratores, colhedoras, pulverizadores...).
-- "tipo" usa as chaves do catálogo (catalogo.py), por isso é VARCHAR.
-- "horimetro" é atualizado pelos relatórios e pelas manutenções.
-- ---------------------------------------------------------------------
CREATE TABLE maquinas (
  id             INT UNSIGNED NOT NULL AUTO_INCREMENT,
  fazenda_id     INT UNSIGNED NOT NULL,
  nome           VARCHAR(120) NOT NULL COMMENT 'Apelido, ex.: Trator 02',
  tipo           VARCHAR(40)  NOT NULL COMMENT 'Chave do catálogo, ex.: trator, colhedora',
  marca          VARCHAR(80)  NULL,
  modelo         VARCHAR(80)  NULL,
  ano            SMALLINT UNSIGNED NULL,
  revisao_horas  DECIMAL(8,1) NULL COMMENT 'Intervalo da revisão preventiva; NULL = padrão do tipo',
  horimetro      DECIMAL(10,1) NOT NULL DEFAULT 0 COMMENT 'Horas de uso acumuladas',
  preco          DECIMAL(12,2) NULL,
  ativo          TINYINT(1) NOT NULL DEFAULT 1,
  criado_em      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_maquinas_fazenda (fazenda_id, ativo),
  CONSTRAINT fk_maquinas_fazenda FOREIGN KEY (fazenda_id) REFERENCES fazendas (id) ON DELETE CASCADE,
  CONSTRAINT ck_maquinas_horimetro CHECK (horimetro >= 0)
) ENGINE=InnoDB COMMENT='Máquinas de cada fazenda';

-- ---------------------------------------------------------------------
-- atividades: tarefas criadas pelo dono (operação ou manutenção agendada).
-- recorrente = 1: aparece todo dia no relatório do funcionário.
-- ---------------------------------------------------------------------
CREATE TABLE atividades (
  id              INT UNSIGNED NOT NULL AUTO_INCREMENT,
  fazenda_id      INT UNSIGNED NOT NULL,
  titulo          VARCHAR(150) NOT NULL,
  descricao       TEXT NULL,
  tipo            ENUM('operacao','manutencao') NOT NULL DEFAULT 'operacao',
  maquina_id      INT UNSIGNED NULL,
  funcionario_id  INT UNSIGNED NULL COMMENT 'Responsável; NULL = qualquer funcionário',
  data_prevista   DATE NULL,
  recorrente      TINYINT(1) NOT NULL DEFAULT 0,
  status          ENUM('pendente','concluida','arquivada') NOT NULL DEFAULT 'pendente',
  criado_em       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_atividades_fazenda_status (fazenda_id, status),
  CONSTRAINT fk_atividades_fazenda FOREIGN KEY (fazenda_id) REFERENCES fazendas (id) ON DELETE CASCADE,
  CONSTRAINT fk_atividades_maquina FOREIGN KEY (maquina_id) REFERENCES maquinas (id) ON DELETE SET NULL,
  CONSTRAINT fk_atividades_funcionario FOREIGN KEY (funcionario_id) REFERENCES funcionarios (id) ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='Tarefas do dia a dia e manutenções agendadas';

-- ---------------------------------------------------------------------
-- ponto: registro de entrada e saída do funcionário. saida NULL = trabalhando.
-- ---------------------------------------------------------------------
CREATE TABLE ponto (
  id              INT UNSIGNED NOT NULL AUTO_INCREMENT,
  fazenda_id      INT UNSIGNED NOT NULL,
  funcionario_id  INT UNSIGNED NOT NULL,
  entrada         DATETIME NOT NULL,
  saida           DATETIME NULL,
  PRIMARY KEY (id),
  KEY ix_ponto_funcionario (funcionario_id, saida),
  KEY ix_ponto_fazenda (fazenda_id, entrada),
  CONSTRAINT fk_ponto_fazenda FOREIGN KEY (fazenda_id) REFERENCES fazendas (id) ON DELETE CASCADE,
  CONSTRAINT fk_ponto_funcionario FOREIGN KEY (funcionario_id) REFERENCES funcionarios (id) ON DELETE CASCADE,
  CONSTRAINT ck_ponto_saida CHECK (saida IS NULL OR saida >= entrada)
) ENGINE=InnoDB COMMENT='Controle de ponto (entrada/saída)';

-- ---------------------------------------------------------------------
-- relatorios: relatório diário do funcionário (um por dia).
-- ---------------------------------------------------------------------
CREATE TABLE relatorios (
  id              INT UNSIGNED NOT NULL AUTO_INCREMENT,
  fazenda_id      INT UNSIGNED NOT NULL,
  funcionario_id  INT UNSIGNED NOT NULL,
  data            DATE NOT NULL,
  observacoes     TEXT NULL,
  criado_em       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_relatorios_funcionario_data (funcionario_id, data),
  KEY ix_relatorios_fazenda (fazenda_id, data),
  CONSTRAINT fk_relatorios_fazenda FOREIGN KEY (fazenda_id) REFERENCES fazendas (id) ON DELETE CASCADE,
  CONSTRAINT fk_relatorios_funcionario FOREIGN KEY (funcionario_id) REFERENCES funcionarios (id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='Relatório de fim de dia';

-- ---------------------------------------------------------------------
-- relatorio_itens: o que foi feito em cada relatório (uma linha por atividade).
-- atividade_titulo é copiado para o histórico continuar legível mesmo se a
-- atividade for excluída depois.
-- ---------------------------------------------------------------------
CREATE TABLE relatorio_itens (
  id                INT UNSIGNED NOT NULL AUTO_INCREMENT,
  relatorio_id      INT UNSIGNED NOT NULL,
  atividade_id      INT UNSIGNED NULL,
  atividade_titulo  VARCHAR(150) NOT NULL,
  status            ENUM('feita','parcial','nao_feita') NOT NULL,
  horas             DECIMAL(5,2) NOT NULL DEFAULT 0,
  maquina_id        INT UNSIGNED NULL,
  horimetro         DECIMAL(10,1) NULL COMMENT 'Leitura do horímetro no fim do serviço',
  PRIMARY KEY (id),
  KEY ix_itens_relatorio (relatorio_id),
  KEY ix_itens_atividade (atividade_id),
  CONSTRAINT fk_itens_relatorio FOREIGN KEY (relatorio_id) REFERENCES relatorios (id) ON DELETE CASCADE,
  CONSTRAINT fk_itens_atividade FOREIGN KEY (atividade_id) REFERENCES atividades (id) ON DELETE SET NULL,
  CONSTRAINT fk_itens_maquina FOREIGN KEY (maquina_id) REFERENCES maquinas (id) ON DELETE SET NULL,
  CONSTRAINT ck_itens_horas CHECK (horas >= 0 AND horas <= 24)
) ENGINE=InnoDB COMMENT='Itens (atividades) de cada relatório';

-- ---------------------------------------------------------------------
-- ocorrencias: problemas em máquinas relatados pelos funcionários.
-- Viram alertas na aba Manutenção do dono.
-- ---------------------------------------------------------------------
CREATE TABLE ocorrencias (
  id              INT UNSIGNED NOT NULL AUTO_INCREMENT,
  fazenda_id      INT UNSIGNED NOT NULL,
  maquina_id      INT UNSIGNED NOT NULL,
  funcionario_id  INT UNSIGNED NULL,
  relatorio_id    INT UNSIGNED NULL,
  descricao       TEXT NOT NULL,
  gravidade       ENUM('baixa','media','alta') NOT NULL DEFAULT 'media',
  status          ENUM('aberta','resolvida') NOT NULL DEFAULT 'aberta',
  criado_em       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  resolvida_em    DATETIME NULL,
  PRIMARY KEY (id),
  KEY ix_ocorrencias_fazenda_status (fazenda_id, status),
  KEY ix_ocorrencias_maquina (maquina_id, status),
  CONSTRAINT fk_ocorrencias_fazenda FOREIGN KEY (fazenda_id) REFERENCES fazendas (id) ON DELETE CASCADE,
  CONSTRAINT fk_ocorrencias_maquina FOREIGN KEY (maquina_id) REFERENCES maquinas (id) ON DELETE CASCADE,
  CONSTRAINT fk_ocorrencias_funcionario FOREIGN KEY (funcionario_id) REFERENCES funcionarios (id) ON DELETE SET NULL,
  CONSTRAINT fk_ocorrencias_relatorio FOREIGN KEY (relatorio_id) REFERENCES relatorios (id) ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='Problemas relatados nas máquinas';

-- ---------------------------------------------------------------------
-- manutencoes: serviços feitos nas máquinas (preventiva = revisão,
-- corretiva = conserto), com custo e horímetro no momento do serviço.
-- ---------------------------------------------------------------------
CREATE TABLE manutencoes (
  id             INT UNSIGNED NOT NULL AUTO_INCREMENT,
  fazenda_id     INT UNSIGNED NOT NULL,
  maquina_id     INT UNSIGNED NOT NULL,
  data           DATE NOT NULL,
  tipo           ENUM('preventiva','corretiva') NOT NULL,
  descricao      TEXT NOT NULL,
  custo          DECIMAL(12,2) NOT NULL DEFAULT 0,
  horimetro      DECIMAL(10,1) NULL,
  ocorrencia_id  INT UNSIGNED NULL COMMENT 'Problema que este serviço resolveu',
  criado_em      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_manutencoes_maquina (maquina_id, tipo, data),
  KEY ix_manutencoes_fazenda (fazenda_id, data),
  CONSTRAINT fk_manutencoes_fazenda FOREIGN KEY (fazenda_id) REFERENCES fazendas (id) ON DELETE CASCADE,
  CONSTRAINT fk_manutencoes_maquina FOREIGN KEY (maquina_id) REFERENCES maquinas (id) ON DELETE CASCADE,
  CONSTRAINT fk_manutencoes_ocorrencia FOREIGN KEY (ocorrencia_id) REFERENCES ocorrencias (id) ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='Histórico de manutenções e custos';

-- ---------------------------------------------------------------------
-- log_acesso: eventos de segurança gravados pela aplicação
-- (login certo, login errado, bloqueio por excesso de tentativas, saída...).
-- Usado também para limitar tentativas de login (força bruta).
-- ---------------------------------------------------------------------
CREATE TABLE log_acesso (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  usuario_id  INT UNSIGNED NULL,
  email       VARCHAR(255) NULL,
  evento      VARCHAR(30)  NOT NULL COMMENT 'login_ok, login_falha, login_bloqueado, logout, cadastro, login_google, acesso_negado',
  ip          VARCHAR(45)  NULL COMMENT 'IPv4 ou IPv6',
  navegador   VARCHAR(255) NULL,
  criado_em   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_log_acesso_ip (ip, evento, criado_em),
  KEY ix_log_acesso_email (email, evento, criado_em),
  CONSTRAINT fk_log_acesso_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='Log de autenticação (auditoria de acesso)';

-- ---------------------------------------------------------------------
-- log_auditoria: alterações nos dados, gravadas AUTOMATICAMENTE pelos
-- gatilhos (03_rotinas.sql). Guarda o antes e o depois em JSON.
-- O usuário da aplicação só pode INSERIR e LER aqui (não pode apagar
-- nem alterar o histórico) - ver 02_usuarios.sql.
-- ---------------------------------------------------------------------
CREATE TABLE log_auditoria (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  tabela        VARCHAR(40)  NOT NULL,
  registro_id   INT UNSIGNED NOT NULL,
  acao          ENUM('INSERT','UPDATE','DELETE') NOT NULL,
  dados_antes   JSON NULL,
  dados_depois  JSON NULL,
  usuario_app   INT UNSIGNED NULL COMMENT 'Usuário logado no site (variável @app_usuario_id)',
  usuario_bd    VARCHAR(100) NOT NULL COMMENT 'Usuário do MySQL que executou o comando',
  criado_em     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_auditoria_tabela (tabela, registro_id),
  KEY ix_auditoria_data (criado_em)
) ENGINE=InnoDB COMMENT='Trilha de auditoria preenchida pelos triggers';
