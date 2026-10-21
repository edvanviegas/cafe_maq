-- =====================================================================
-- CafeMaq - FUNÇÕES, PROCEDIMENTOS E GATILHOS (TRIGGERS)
-- ---------------------------------------------------------------------
-- Executar como root (ou cafemaq_admin), depois do 01 e do 02:
--   mysql -u root -p < database/mysql/03_rotinas.sql
--
-- Conteúdo:
--   FUNÇÕES
--     fn_custo_maquina(maquina, inicio, fim)        custo de manutenção no período
--     fn_horas_desde_preventiva(maquina)            horas rodadas desde a última revisão
--     fn_horas_trabalhadas(funcionario, inicio, fim) horas de ponto no período
--   PROCEDIMENTOS
--     sp_resumo_custos(fazenda, inicio, fim)        ranking de custo por máquina (usado pelo site)
--     sp_registrar_manutencao(...)                  registra um serviço numa transação, validando tudo
--     sp_fechar_pontos_esquecidos(fazenda, horas)   fecha pontos que ficaram abertos
--   GATILHOS
--     trg_manutencoes_antes_inserir     valida custo/horímetro antes de gravar
--     trg_manutencoes_depois_inserir    atualiza horímetro, resolve o problema e audita
--     trg_ocorrencias_antes_atualizar   preenche/limpa a data de resolução
--     trg_maquinas_depois_atualizar     auditoria (antes x depois)
--     trg_maquinas_depois_excluir       auditoria
--     trg_funcionarios_depois_atualizar auditoria
--     trg_funcionarios_depois_excluir   auditoria
--     trg_fazendas_depois_excluir       auditoria
--     trg_usuarios_depois_atualizar     auditoria (sem expor o hash da senha)
--
-- Os gatilhos de auditoria gravam em log_auditoria quem fez a mudança:
--   usuario_bd  = CURRENT_USER()   (usuário do MySQL, ex.: cafemaq_app)
--   usuario_app = @app_usuario_id  (pessoa logada no site; o Flask define
--                                   essa variável a cada requisição, ver banco.py)
--
-- O "DELIMITER $$" troca o fim de comando de ; para $$, porque o corpo das
-- rotinas tem vários ; dentro dele. No MySQL Workbench funciona do mesmo jeito.
-- =====================================================================

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
