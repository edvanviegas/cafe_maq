-- =====================================================================
-- CafeMaq - DADOS DE DEMONSTRAÇÃO (opcional)
-- ---------------------------------------------------------------------
-- Uma fazenda de café em Rondônia com máquinas, equipe, atividades,
-- relatórios, problemas e manutenções - bom para apresentar o sistema.
--
--   mysql -u root -p < database/mysql/04_dados_exemplo.sql
--
-- Contas de teste (senha das duas: Cafe@2026)
--   Dono:        dono@cafemaq.com.br
--   Funcionário: joao@cafemaq.com.br
--
-- Repare que, ao inserir as manutenções, os GATILHOS atualizam o horímetro
-- das máquinas, resolvem os problemas ligados e gravam a auditoria sozinhos.
-- =====================================================================

USE cafemaq;

SET @hash = 'scrypt:32768:8:1$QNi7LTtEwCbK7gYP$6bcd45ef9130d8049d8c94bfa25ed2c71f3761828c3ad06be80b6dc71b56bb98a748fa387bcbca388e2fcaf209c0cabee27e48acfaf17bbfb49e48b2bbd7f2f3';

INSERT INTO usuarios (id, nome, email, senha_hash, tipo, criado_em) VALUES
  (1, 'Carlos Mendes',  'dono@cafemaq.com.br',  @hash, 'dono',        '2026-08-01 08:00:00'),
  (2, 'João Pereira',   'joao@cafemaq.com.br',  @hash, 'funcionario', '2026-08-02 07:30:00'),
  (3, 'Maria Oliveira', 'maria@cafemaq.com.br', @hash, 'funcionario', '2026-08-02 07:40:00');

INSERT INTO fazendas (id, dono_id, nome, municipio, estado, area_ha, producao_sacas, criado_em) VALUES
  (1, 1, 'Sítio Boa Esperança', 'Ariquemes', 'RO', 42.50, 1800, '2026-08-01 08:10:00');

INSERT INTO funcionarios (id, fazenda_id, usuario_id, nome, email, funcao, ativo, criado_em) VALUES
  (1, 1, 2,    'João Pereira',   'joao@cafemaq.com.br',   'Operador de máquinas', 1, '2026-08-01 08:20:00'),
  (2, 1, 3,    'Maria Oliveira', 'maria@cafemaq.com.br',  'Tratorista',           1, '2026-08-01 08:21:00'),
  (3, 1, NULL, 'Pedro Santos',   'pedro@cafemaq.com.br',  'Mecânico',             1, '2026-08-01 08:22:00');

INSERT INTO maquinas (id, fazenda_id, nome, tipo, marca, modelo, ano, revisao_horas, horimetro, preco, ativo, criado_em) VALUES
  (1, 1, 'Trator 01',          'trator',       'Massey Ferguson', 'MF 4275',    2018, NULL, 4980.0, 210000.00, 1, '2026-08-01 08:30:00'),
  (2, 1, 'Colhedora K3',       'colhedora',    'Jacto',           'K3 Millennium', 2020, NULL, 1440.0, 1250000.00, 1, '2026-08-01 08:31:00'),
  (3, 1, 'Pulverizador Arbus', 'pulverizador', 'Jacto',           'Arbus 2000', 2021, NULL, 690.0, 92000.00, 1, '2026-08-01 08:32:00'),
  (4, 1, 'Roçadeira 01',       'rocadeira',    'Kamaq',           NULL,         2019, NULL, 805.0, 35000.00, 1, '2026-08-01 08:33:00'),
  (5, 1, 'Derriçadeira 02',    'derricadeira', 'Stihl',           'SP 481',     2022, NULL, 210.0, 4300.00, 1, '2026-08-01 08:34:00');

INSERT INTO atividades (id, fazenda_id, titulo, descricao, tipo, maquina_id, funcionario_id, data_prevista, recorrente, status, criado_em) VALUES
  (1, 1, 'Checklist diário do trator', 'Conferir óleo, água do radiador e pneus antes de sair.', 'operacao', 1, 2, '2026-08-05', 1, 'pendente', '2026-08-04 18:00:00'),
  (2, 1, 'Roçar entre linhas do talhão 3', NULL, 'operacao', 4, 1, '2026-10-21', 0, 'pendente', '2026-10-19 17:00:00'),
  (3, 1, 'Pulverização foliar talhão 1', 'Calda conforme receituário do agrônomo.', 'operacao', 3, 1, '2026-10-15', 0, 'concluida', '2026-10-13 17:00:00'),
  (4, 1, 'Revisão preventiva - Colhedora K3', 'Revisão de 150 h antes da safra.', 'manutencao', 2, 3, '2026-10-24', 0, 'pendente', '2026-10-18 10:00:00');

INSERT INTO ponto (id, fazenda_id, funcionario_id, entrada, saida) VALUES
  (1, 1, 1, '2026-10-15 07:02:00', '2026-10-15 16:10:00'),
  (2, 1, 2, '2026-10-15 07:10:00', '2026-10-15 16:30:00'),
  (3, 1, 1, '2026-10-16 07:00:00', '2026-10-16 15:55:00'),
  (4, 1, 2, '2026-10-16 07:05:00', '2026-10-16 16:20:00');

INSERT INTO relatorios (id, fazenda_id, funcionario_id, data, observacoes, criado_em) VALUES
  (1, 1, 1, '2026-10-15', 'Pulverização concluída sem problemas.', '2026-10-15 16:05:00'),
  (2, 1, 2, '2026-10-15', NULL, '2026-10-15 16:25:00'),
  (3, 1, 1, '2026-10-16', 'Barulho estranho no trator ao subir o morro.', '2026-10-16 15:50:00');

INSERT INTO relatorio_itens (id, relatorio_id, atividade_id, atividade_titulo, status, horas, maquina_id, horimetro) VALUES
  (1, 1, 3, 'Pulverização foliar talhão 1', 'feita',   6.5, 3, 696.5),
  (2, 2, 1, 'Checklist diário do trator',   'feita',   0.5, 1, 4986.0),
  (3, 3, 1, 'Checklist diário do trator',   'parcial', 0.5, 1, 4994.0);

UPDATE maquinas SET horimetro = 696.5  WHERE id = 3;
UPDATE maquinas SET horimetro = 4994.0 WHERE id = 1;

INSERT INTO ocorrencias (id, fazenda_id, maquina_id, funcionario_id, relatorio_id, descricao, gravidade, status, criado_em) VALUES
  (1, 1, 1, 1, 3, 'Barulho na caixa de câmbio ao subir terreno inclinado.', 'alta', 'aberta', '2026-10-16 15:50:00'),
  (2, 1, 4, 2, 2, 'Correia da roçadeira patinando.', 'media', 'aberta', '2026-10-10 16:00:00');

-- As manutenções disparam os gatilhos (horímetro, resolução do problema e auditoria)
INSERT INTO manutencoes (id, fazenda_id, maquina_id, data, tipo, descricao, custo, horimetro, ocorrencia_id, criado_em) VALUES
  (1, 1, 1, '2026-08-20', 'preventiva', 'Revisão de 250 h: óleo do motor, filtros e graxa.', 1250.00, 4750.0, NULL, '2026-08-20 11:00:00'),
  (2, 1, 2, '2026-09-02', 'preventiva', 'Revisão pré-safra: hastes, correias e lubrificação.', 3800.00, 1300.0, NULL, '2026-09-02 15:00:00'),
  (3, 1, 3, '2026-09-18', 'corretiva',  'Troca de bicos e mangueira do pulverizador.', 640.00, 680.0, NULL, '2026-09-18 10:30:00'),
  (4, 1, 4, '2026-10-12', 'corretiva',  'Troca da correia.', 280.00, 805.0, 2, '2026-10-12 09:00:00'),
  (5, 1, 5, '2026-10-05', 'preventiva', 'Limpeza do filtro de ar e troca da vela.', 95.00, 200.0, NULL, '2026-10-05 08:00:00');

-- Alguns acessos para o log de autenticação
INSERT INTO log_acesso (usuario_id, email, evento, ip, navegador, criado_em) VALUES
  (1, 'dono@cafemaq.com.br', 'login_ok',    '127.0.0.1', 'Demonstração', '2026-10-19 08:00:00'),
  (NULL, 'dono@cafemaq.com.br', 'login_falha', '127.0.0.1', 'Demonstração', '2026-10-19 07:59:00'),
  (2, 'joao@cafemaq.com.br', 'login_ok',    '127.0.0.1', 'Demonstração', '2026-10-16 07:00:00');
