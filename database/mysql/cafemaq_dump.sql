-- =====================================================================
-- CafeMaq - CÓPIA DE SEGURANÇA (DUMP) DA BASE DE DADOS "cafemaq"
-- ---------------------------------------------------------------------
-- Contém: estrutura (tabelas, chaves, índices), dados de demonstração,
-- funções, procedimentos e gatilhos.
-- NÃO contém os usuários do MySQL (eles ficam no servidor, não na base):
-- rode o 02_usuarios.sql depois de restaurar.
--
-- Restaurar:
--   mysql -u root -p < database/mysql/cafemaq_dump.sql
--   mysql -u root -p < database/mysql/02_usuarios.sql
-- ou no MySQL Workbench: Server > Data Import > Import from Self-Contained File.
--
-- Para gerar um dump novo do seu banco: python scripts/backup.py
-- (ou: mysqldump -u cafemaq_backup -p --routines --triggers --databases cafemaq > dump.sql)
-- Contas de teste: dono@cafemaq.com.br / joao@cafemaq.com.br  (senha Cafe@2026)
-- =====================================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
SET @OLD_SQL_MODE = @@SQL_MODE, SQL_MODE = 'NO_AUTO_VALUE_ON_ZERO';

DROP DATABASE IF EXISTS cafemaq;

-- ---------------------------------------------------------------------
-- ESTRUTURA
-- ---------------------------------------------------------------------

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


-- ---------------------------------------------------------------------
-- DADOS
-- ---------------------------------------------------------------------

-- usuarios: 3 registro(s)
INSERT INTO `usuarios` (`id`, `nome`, `email`, `senha_hash`, `google_id`, `tipo`, `criado_em`) VALUES
  (1, 'Carlos Mendes', 'dono@cafemaq.com.br', 'scrypt:32768:8:1$QNi7LTtEwCbK7gYP$6bcd45ef9130d8049d8c94bfa25ed2c71f3761828c3ad06be80b6dc71b56bb98a748fa387bcbca388e2fcaf209c0cabee27e48acfaf17bbfb49e48b2bbd7f2f3', NULL, 'dono', '2026-08-01 08:00:00'),
  (2, 'João Pereira', 'joao@cafemaq.com.br', 'scrypt:32768:8:1$QNi7LTtEwCbK7gYP$6bcd45ef9130d8049d8c94bfa25ed2c71f3761828c3ad06be80b6dc71b56bb98a748fa387bcbca388e2fcaf209c0cabee27e48acfaf17bbfb49e48b2bbd7f2f3', NULL, 'funcionario', '2026-08-02 07:30:00'),
  (3, 'Maria Oliveira', 'maria@cafemaq.com.br', 'scrypt:32768:8:1$QNi7LTtEwCbK7gYP$6bcd45ef9130d8049d8c94bfa25ed2c71f3761828c3ad06be80b6dc71b56bb98a748fa387bcbca388e2fcaf209c0cabee27e48acfaf17bbfb49e48b2bbd7f2f3', NULL, 'funcionario', '2026-08-02 07:40:00');

-- fazendas: 1 registro(s)
INSERT INTO `fazendas` (`id`, `dono_id`, `nome`, `municipio`, `estado`, `area_ha`, `producao_sacas`, `criado_em`) VALUES
  (1, 1, 'Sítio Boa Esperança', 'Ariquemes', 'RO', 42.50, 1800, '2026-08-01 08:10:00');

-- funcionarios: 3 registro(s)
INSERT INTO `funcionarios` (`id`, `fazenda_id`, `usuario_id`, `nome`, `email`, `funcao`, `ativo`, `criado_em`) VALUES
  (1, 1, 2, 'João Pereira', 'joao@cafemaq.com.br', 'Operador de máquinas', 1, '2026-08-01 08:20:00'),
  (2, 1, 3, 'Maria Oliveira', 'maria@cafemaq.com.br', 'Tratorista', 1, '2026-08-01 08:21:00'),
  (3, 1, NULL, 'Pedro Santos', 'pedro@cafemaq.com.br', 'Mecânico', 1, '2026-08-01 08:22:00');

-- maquinas: 5 registro(s)
INSERT INTO `maquinas` (`id`, `fazenda_id`, `nome`, `tipo`, `marca`, `modelo`, `ano`, `revisao_horas`, `horimetro`, `preco`, `ativo`, `criado_em`) VALUES
  (1, 1, 'Trator 01', 'trator', 'Massey Ferguson', 'MF 4275', 2018, NULL, 4994.0, 210000.00, 1, '2026-08-01 08:30:00'),
  (2, 1, 'Colhedora K3', 'colhedora', 'Jacto', 'K3 Millennium', 2020, NULL, 1440.0, 1250000.00, 1, '2026-08-01 08:31:00'),
  (3, 1, 'Pulverizador Arbus', 'pulverizador', 'Jacto', 'Arbus 2000', 2021, NULL, 696.5, 92000.00, 1, '2026-08-01 08:32:00'),
  (4, 1, 'Roçadeira 01', 'rocadeira', 'Kamaq', NULL, 2019, NULL, 805.0, 35000.00, 1, '2026-08-01 08:33:00'),
  (5, 1, 'Derriçadeira 02', 'derricadeira', 'Stihl', 'SP 481', 2022, NULL, 210.0, 4300.00, 1, '2026-08-01 08:34:00');

-- atividades: 4 registro(s)
INSERT INTO `atividades` (`id`, `fazenda_id`, `titulo`, `descricao`, `tipo`, `maquina_id`, `funcionario_id`, `data_prevista`, `recorrente`, `status`, `criado_em`) VALUES
  (1, 1, 'Checklist diário do trator', 'Conferir óleo, água do radiador e pneus antes de sair.', 'operacao', 1, 2, '2026-08-05', 1, 'pendente', '2026-08-04 18:00:00'),
  (2, 1, 'Roçar entre linhas do talhão 3', NULL, 'operacao', 4, 1, '2026-10-21', 0, 'pendente', '2026-10-19 17:00:00'),
  (3, 1, 'Pulverização foliar talhão 1', 'Calda conforme receituário do agrônomo.', 'operacao', 3, 1, '2026-10-15', 0, 'concluida', '2026-10-13 17:00:00'),
  (4, 1, 'Revisão preventiva - Colhedora K3', 'Revisão de 150 h antes da safra.', 'manutencao', 2, 3, '2026-10-24', 0, 'pendente', '2026-10-18 10:00:00');

-- ponto: 4 registro(s)
INSERT INTO `ponto` (`id`, `fazenda_id`, `funcionario_id`, `entrada`, `saida`) VALUES
  (1, 1, 1, '2026-10-15 07:02:00', '2026-10-15 16:10:00'),
  (2, 1, 2, '2026-10-15 07:10:00', '2026-10-15 16:30:00'),
  (3, 1, 1, '2026-10-16 07:00:00', '2026-10-16 15:55:00'),
  (4, 1, 2, '2026-10-16 07:05:00', '2026-10-16 16:20:00');

-- relatorios: 3 registro(s)
INSERT INTO `relatorios` (`id`, `fazenda_id`, `funcionario_id`, `data`, `observacoes`, `criado_em`) VALUES
  (1, 1, 1, '2026-10-15', 'Pulverização concluída sem problemas.', '2026-10-15 16:05:00'),
  (2, 1, 2, '2026-10-15', NULL, '2026-10-15 16:25:00'),
  (3, 1, 1, '2026-10-16', 'Barulho estranho no trator ao subir o morro.', '2026-10-16 15:50:00');

-- relatorio_itens: 3 registro(s)
INSERT INTO `relatorio_itens` (`id`, `relatorio_id`, `atividade_id`, `atividade_titulo`, `status`, `horas`, `maquina_id`, `horimetro`) VALUES
  (1, 1, 3, 'Pulverização foliar talhão 1', 'feita', 6.50, 3, 696.5),
  (2, 2, 1, 'Checklist diário do trator', 'feita', 0.50, 1, 4986.0),
  (3, 3, 1, 'Checklist diário do trator', 'parcial', 0.50, 1, 4994.0);

-- ocorrencias: 2 registro(s)
INSERT INTO `ocorrencias` (`id`, `fazenda_id`, `maquina_id`, `funcionario_id`, `relatorio_id`, `descricao`, `gravidade`, `status`, `criado_em`, `resolvida_em`) VALUES
  (1, 1, 1, 1, 3, 'Barulho na caixa de câmbio ao subir terreno inclinado.', 'alta', 'aberta', '2026-10-16 15:50:00', NULL),
  (2, 1, 4, 2, 2, 'Correia da roçadeira patinando.', 'media', 'resolvida', '2026-10-10 16:00:00', '2026-10-12 09:00:00');

-- manutencoes: 5 registro(s)
INSERT INTO `manutencoes` (`id`, `fazenda_id`, `maquina_id`, `data`, `tipo`, `descricao`, `custo`, `horimetro`, `ocorrencia_id`, `criado_em`) VALUES
  (1, 1, 1, '2026-08-20', 'preventiva', 'Revisão de 250 h: óleo do motor, filtros e graxa.', 1250.00, 4750.0, NULL, '2026-08-20 11:00:00'),
  (2, 1, 2, '2026-09-02', 'preventiva', 'Revisão pré-safra: hastes, correias e lubrificação.', 3800.00, 1300.0, NULL, '2026-09-02 15:00:00'),
  (3, 1, 3, '2026-09-18', 'corretiva', 'Troca de bicos e mangueira do pulverizador.', 640.00, 680.0, NULL, '2026-09-18 10:30:00'),
  (4, 1, 4, '2026-10-12', 'corretiva', 'Troca da correia.', 280.00, 805.0, 2, '2026-10-12 09:00:00'),
  (5, 1, 5, '2026-10-05', 'preventiva', 'Limpeza do filtro de ar e troca da vela.', 95.00, 200.0, NULL, '2026-10-05 08:00:00');

-- log_acesso: 3 registro(s)
INSERT INTO `log_acesso` (`id`, `usuario_id`, `email`, `evento`, `ip`, `navegador`, `criado_em`) VALUES
  (1, 1, 'dono@cafemaq.com.br', 'login_ok', '127.0.0.1', 'Demonstração', '2026-10-19 08:00:00'),
  (2, NULL, 'dono@cafemaq.com.br', 'login_falha', '127.0.0.1', 'Demonstração', '2026-10-19 07:59:00'),
  (3, 2, 'joao@cafemaq.com.br', 'login_ok', '127.0.0.1', 'Demonstração', '2026-10-16 07:00:00');


-- ---------------------------------------------------------------------
-- FUNÇÕES, PROCEDIMENTOS E GATILHOS
-- (criados depois dos dados, como o mysqldump faz, para não disparar
--  os gatilhos durante a restauração)
-- ---------------------------------------------------------------------

USE cafemaq;

DROP FUNCTION  IF EXISTS fn_custo_maquina;
DROP FUNCTION  IF EXISTS fn_horas_desde_preventiva;
DROP FUNCTION  IF EXISTS fn_horas_trabalhadas;
DROP PROCEDURE IF EXISTS sp_resumo_custos;
DROP PROCEDURE IF EXISTS sp_registrar_manutencao;
DROP PROCEDURE IF EXISTS sp_fechar_pontos_esquecidos;
DROP TRIGGER   IF EXISTS trg_manutencoes_antes_inserir;
DROP TRIGGER   IF EXISTS trg_manutencoes_depois_inserir;
DROP TRIGGER   IF EXISTS trg_ocorrencias_antes_atualizar;
DROP TRIGGER   IF EXISTS trg_maquinas_depois_atualizar;
DROP TRIGGER   IF EXISTS trg_maquinas_depois_excluir;
DROP TRIGGER   IF EXISTS trg_funcionarios_depois_atualizar;
DROP TRIGGER   IF EXISTS trg_funcionarios_depois_excluir;
DROP TRIGGER   IF EXISTS trg_fazendas_depois_excluir;
DROP TRIGGER   IF EXISTS trg_usuarios_depois_atualizar;

DELIMITER $$

-- =====================================================================
-- FUNÇÕES
-- =====================================================================

-- ---------------------------------------------------------------------
-- fn_custo_maquina: soma o custo das manutenções de uma máquina entre duas
-- datas (inclusive). Devolve 0 quando não houve gasto.
-- Exemplo: SELECT fn_custo_maquina(1, '2026-01-01', '2026-12-31');
-- ---------------------------------------------------------------------
CREATE FUNCTION fn_custo_maquina(p_maquina_id INT UNSIGNED, p_inicio DATE, p_fim DATE)
RETURNS DECIMAL(12,2)
READS SQL DATA
BEGIN
  DECLARE v_total DECIMAL(12,2);

  SELECT COALESCE(SUM(custo), 0) INTO v_total
    FROM manutencoes
   WHERE maquina_id = p_maquina_id
     AND data BETWEEN p_inicio AND p_fim;

  RETURN v_total;
END$$

-- ---------------------------------------------------------------------
-- fn_horas_desde_preventiva: quantas horas a máquina rodou desde a última
-- revisão preventiva (horímetro atual - horímetro da última preventiva).
-- Devolve NULL se a máquina nunca teve preventiva registrada.
-- Exemplo: SELECT nome, fn_horas_desde_preventiva(id) FROM maquinas;
-- ---------------------------------------------------------------------
CREATE FUNCTION fn_horas_desde_preventiva(p_maquina_id INT UNSIGNED)
RETURNS DECIMAL(10,1)
READS SQL DATA
BEGIN
  DECLARE v_atual DECIMAL(10,1);
  DECLARE v_ultima DECIMAL(10,1);

  SELECT horimetro INTO v_atual FROM maquinas WHERE id = p_maquina_id;

  SELECT MAX(horimetro) INTO v_ultima
    FROM manutencoes
   WHERE maquina_id = p_maquina_id AND tipo = 'preventiva' AND horimetro IS NOT NULL;

  IF v_ultima IS NULL THEN
    RETURN NULL;
  END IF;
  RETURN GREATEST(v_atual - v_ultima, 0);
END$$

-- ---------------------------------------------------------------------
-- fn_horas_trabalhadas: horas registradas no ponto por um funcionário entre
-- duas datas. Pontos ainda abertos contam até o momento atual.
-- Exemplo: SELECT nome, fn_horas_trabalhadas(id, '2026-10-01', '2026-10-31') FROM funcionarios;
-- ---------------------------------------------------------------------
CREATE FUNCTION fn_horas_trabalhadas(p_funcionario_id INT UNSIGNED, p_inicio DATE, p_fim DATE)
RETURNS DECIMAL(8,2)
READS SQL DATA
BEGIN
  DECLARE v_minutos BIGINT;

  SELECT COALESCE(SUM(TIMESTAMPDIFF(MINUTE, entrada, COALESCE(saida, NOW()))), 0) INTO v_minutos
    FROM ponto
   WHERE funcionario_id = p_funcionario_id
     AND DATE(entrada) BETWEEN p_inicio AND p_fim;

  RETURN ROUND(v_minutos / 60, 2);
END$$

-- =====================================================================
-- PROCEDIMENTOS
-- =====================================================================

-- ---------------------------------------------------------------------
-- sp_resumo_custos: ranking das máquinas de uma fazenda pelo custo de
-- manutenção no período. Usado pela rota GET /api/fazenda/custos do site.
-- Usa as funções fn_custo_maquina e fn_horas_desde_preventiva.
-- Exemplo: CALL sp_resumo_custos(1, '2026-01-01', '2026-12-31');
-- ---------------------------------------------------------------------
CREATE PROCEDURE sp_resumo_custos(IN p_fazenda_id INT UNSIGNED, IN p_inicio DATE, IN p_fim DATE)
READS SQL DATA
BEGIN
  SELECT m.id,
         m.nome,
         m.tipo,
         m.horimetro,
         (SELECT COUNT(*) FROM manutencoes mn
           WHERE mn.maquina_id = m.id AND mn.data BETWEEN p_inicio AND p_fim)                         AS qtd_servicos,
         (SELECT COUNT(*) FROM manutencoes mn
           WHERE mn.maquina_id = m.id AND mn.tipo = 'corretiva' AND mn.data BETWEEN p_inicio AND p_fim) AS qtd_corretivas,
         fn_custo_maquina(m.id, p_inicio, p_fim)                                                     AS custo_total,
         fn_horas_desde_preventiva(m.id)                                                             AS horas_desde_preventiva,
         (SELECT COUNT(*) FROM ocorrencias o WHERE o.maquina_id = m.id AND o.status = 'aberta')       AS problemas_abertos
    FROM maquinas m
   WHERE m.fazenda_id = p_fazenda_id
   ORDER BY custo_total DESC, m.nome;
END$$

-- ---------------------------------------------------------------------
-- sp_registrar_manutencao: registra um serviço numa máquina dentro de uma
-- TRANSAÇÃO. Confere se a máquina é da fazenda informada; se algo der
-- errado, desfaz tudo (ROLLBACK) e devolve o erro.
-- O gatilho trg_manutencoes_depois_inserir cuida do horímetro e do problema.
-- Exemplo:
--   CALL sp_registrar_manutencao(1, 2, '2026-10-20', 'preventiva',
--                                'Troca de óleo e filtros', 850.00, 1250.0, NULL, @novo_id);
--   SELECT @novo_id;
-- ---------------------------------------------------------------------
CREATE PROCEDURE sp_registrar_manutencao(
  IN  p_fazenda_id    INT UNSIGNED,
  IN  p_maquina_id    INT UNSIGNED,
  IN  p_data          DATE,
  IN  p_tipo          VARCHAR(20),
  IN  p_descricao     TEXT,
  IN  p_custo         DECIMAL(12,2),
  IN  p_horimetro     DECIMAL(10,1),
  IN  p_ocorrencia_id INT UNSIGNED,
  OUT p_novo_id       INT UNSIGNED
)
MODIFIES SQL DATA
BEGIN
  DECLARE v_existe INT DEFAULT 0;

  -- Qualquer erro dentro do bloco: desfaz a transação e repassa o erro
  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  START TRANSACTION;

  SELECT COUNT(*) INTO v_existe FROM maquinas WHERE id = p_maquina_id AND fazenda_id = p_fazenda_id;
  IF v_existe = 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Máquina não pertence a esta fazenda.';
  END IF;

  IF p_tipo NOT IN ('preventiva', 'corretiva') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Tipo de manutenção inválido (use preventiva ou corretiva).';
  END IF;

  INSERT INTO manutencoes (fazenda_id, maquina_id, data, tipo, descricao, custo, horimetro, ocorrencia_id, criado_em)
  VALUES (p_fazenda_id, p_maquina_id, COALESCE(p_data, CURDATE()), p_tipo, p_descricao,
          COALESCE(p_custo, 0), p_horimetro, p_ocorrencia_id, NOW());

  SET p_novo_id = LAST_INSERT_ID();
  COMMIT;
END$$

-- ---------------------------------------------------------------------
-- sp_fechar_pontos_esquecidos: fecha os pontos que ficaram abertos por mais
-- de p_horas_max horas (funcionário esqueceu de bater a saída). A saída é
-- registrada como entrada + p_horas_max. Devolve quantos foram fechados.
-- Exemplo: CALL sp_fechar_pontos_esquecidos(1, 12);
-- ---------------------------------------------------------------------
CREATE PROCEDURE sp_fechar_pontos_esquecidos(IN p_fazenda_id INT UNSIGNED, IN p_horas_max INT)
MODIFIES SQL DATA
BEGIN
  UPDATE ponto
     SET saida = DATE_ADD(entrada, INTERVAL p_horas_max HOUR)
   WHERE fazenda_id = p_fazenda_id
     AND saida IS NULL
     AND entrada < DATE_SUB(NOW(), INTERVAL p_horas_max HOUR);

  SELECT ROW_COUNT() AS pontos_fechados;
END$$

-- =====================================================================
-- GATILHOS (TRIGGERS)
-- =====================================================================

-- ---------------------------------------------------------------------
-- Antes de gravar uma manutenção: impede custo ou horímetro negativos,
-- mesmo que alguém insira direto no banco (sem passar pelo site).
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_manutencoes_antes_inserir
BEFORE INSERT ON manutencoes
FOR EACH ROW
BEGIN
  IF NEW.custo < 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'O custo da manutenção não pode ser negativo.';
  END IF;
  IF NEW.horimetro IS NOT NULL AND NEW.horimetro < 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'O horímetro não pode ser negativo.';
  END IF;
  IF NEW.criado_em IS NULL THEN
    SET NEW.criado_em = NOW();
  END IF;
END$$

-- ---------------------------------------------------------------------
-- Depois de gravar uma manutenção:
--   1) se o horímetro informado for maior que o da máquina, atualiza a máquina;
--   2) se o serviço resolveu um problema (ocorrencia_id), marca como resolvido;
--   3) registra na auditoria.
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_manutencoes_depois_inserir
AFTER INSERT ON manutencoes
FOR EACH ROW
BEGIN
  IF NEW.horimetro IS NOT NULL THEN
    UPDATE maquinas SET horimetro = NEW.horimetro
     WHERE id = NEW.maquina_id AND horimetro < NEW.horimetro;
  END IF;

  IF NEW.ocorrencia_id IS NOT NULL THEN
    UPDATE ocorrencias SET status = 'resolvida'
     WHERE id = NEW.ocorrencia_id AND status = 'aberta';
  END IF;

  INSERT INTO log_auditoria (tabela, registro_id, acao, dados_antes, dados_depois, usuario_app, usuario_bd)
  VALUES ('manutencoes', NEW.id, 'INSERT', NULL,
          JSON_OBJECT('maquina_id', NEW.maquina_id, 'data', NEW.data, 'tipo', NEW.tipo,
                      'custo', NEW.custo, 'horimetro', NEW.horimetro, 'descricao', NEW.descricao),
          @app_usuario_id, CURRENT_USER());
END$$

-- ---------------------------------------------------------------------
-- Ao mudar o status de um problema: preenche resolvida_em quando vira
-- "resolvida" e limpa se for reaberto. Assim a data nunca fica errada.
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_ocorrencias_antes_atualizar
BEFORE UPDATE ON ocorrencias
FOR EACH ROW
BEGIN
  IF NEW.status = 'resolvida' AND OLD.status <> 'resolvida' AND NEW.resolvida_em IS NULL THEN
    SET NEW.resolvida_em = NOW();
  ELSEIF NEW.status = 'aberta' THEN
    SET NEW.resolvida_em = NULL;
  END IF;
END$$

-- ---------------------------------------------------------------------
-- Auditoria de máquinas: guarda o antes e o depois de cada alteração.
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_maquinas_depois_atualizar
AFTER UPDATE ON maquinas
FOR EACH ROW
BEGIN
  INSERT INTO log_auditoria (tabela, registro_id, acao, dados_antes, dados_depois, usuario_app, usuario_bd)
  VALUES ('maquinas', NEW.id, 'UPDATE',
          JSON_OBJECT('nome', OLD.nome, 'tipo', OLD.tipo, 'marca', OLD.marca, 'modelo', OLD.modelo,
                      'horimetro', OLD.horimetro, 'preco', OLD.preco, 'ativo', OLD.ativo),
          JSON_OBJECT('nome', NEW.nome, 'tipo', NEW.tipo, 'marca', NEW.marca, 'modelo', NEW.modelo,
                      'horimetro', NEW.horimetro, 'preco', NEW.preco, 'ativo', NEW.ativo),
          @app_usuario_id, CURRENT_USER());
END$$

CREATE TRIGGER trg_maquinas_depois_excluir
AFTER DELETE ON maquinas
FOR EACH ROW
BEGIN
  INSERT INTO log_auditoria (tabela, registro_id, acao, dados_antes, dados_depois, usuario_app, usuario_bd)
  VALUES ('maquinas', OLD.id, 'DELETE',
          JSON_OBJECT('fazenda_id', OLD.fazenda_id, 'nome', OLD.nome, 'tipo', OLD.tipo, 'marca', OLD.marca,
                      'modelo', OLD.modelo, 'horimetro', OLD.horimetro, 'preco', OLD.preco),
          NULL, @app_usuario_id, CURRENT_USER());
END$$

-- ---------------------------------------------------------------------
-- Auditoria de funcionários.
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_funcionarios_depois_atualizar
AFTER UPDATE ON funcionarios
FOR EACH ROW
BEGIN
  INSERT INTO log_auditoria (tabela, registro_id, acao, dados_antes, dados_depois, usuario_app, usuario_bd)
  VALUES ('funcionarios', NEW.id, 'UPDATE',
          JSON_OBJECT('nome', OLD.nome, 'email', OLD.email, 'funcao', OLD.funcao,
                      'ativo', OLD.ativo, 'usuario_id', OLD.usuario_id),
          JSON_OBJECT('nome', NEW.nome, 'email', NEW.email, 'funcao', NEW.funcao,
                      'ativo', NEW.ativo, 'usuario_id', NEW.usuario_id),
          @app_usuario_id, CURRENT_USER());
END$$

CREATE TRIGGER trg_funcionarios_depois_excluir
AFTER DELETE ON funcionarios
FOR EACH ROW
BEGIN
  INSERT INTO log_auditoria (tabela, registro_id, acao, dados_antes, dados_depois, usuario_app, usuario_bd)
  VALUES ('funcionarios', OLD.id, 'DELETE',
          JSON_OBJECT('fazenda_id', OLD.fazenda_id, 'nome', OLD.nome, 'email', OLD.email, 'funcao', OLD.funcao),
          NULL, @app_usuario_id, CURRENT_USER());
END$$

-- ---------------------------------------------------------------------
-- Auditoria de exclusão de fazenda (apaga tudo em cascata, então fica o registro).
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_fazendas_depois_excluir
AFTER DELETE ON fazendas
FOR EACH ROW
BEGIN
  INSERT INTO log_auditoria (tabela, registro_id, acao, dados_antes, dados_depois, usuario_app, usuario_bd)
  VALUES ('fazendas', OLD.id, 'DELETE',
          JSON_OBJECT('dono_id', OLD.dono_id, 'nome', OLD.nome, 'municipio', OLD.municipio, 'estado', OLD.estado),
          NULL, @app_usuario_id, CURRENT_USER());
END$$

-- ---------------------------------------------------------------------
-- Auditoria de contas: registra mudanças de nome/e-mail/tipo e se a senha
-- foi trocada, SEM copiar o hash da senha para o log (confidencialidade).
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_usuarios_depois_atualizar
AFTER UPDATE ON usuarios
FOR EACH ROW
BEGIN
  INSERT INTO log_auditoria (tabela, registro_id, acao, dados_antes, dados_depois, usuario_app, usuario_bd)
  VALUES ('usuarios', NEW.id, 'UPDATE',
          JSON_OBJECT('nome', OLD.nome, 'email', OLD.email, 'tipo', OLD.tipo,
                      'tem_google', OLD.google_id IS NOT NULL),
          JSON_OBJECT('nome', NEW.nome, 'email', NEW.email, 'tipo', NEW.tipo,
                      'tem_google', NEW.google_id IS NOT NULL,
                      'senha_alterada', NOT (OLD.senha_hash <=> NEW.senha_hash)),
          @app_usuario_id, CURRENT_USER());
END$$

DELIMITER ;


SET SQL_MODE = @OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS = 1;
-- Fim do dump
