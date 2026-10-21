-- =====================================================================
-- CafeMaq - USUÁRIOS DO BANCO E PERMISSÕES (princípio do menor privilégio)
-- ---------------------------------------------------------------------
-- Executar como root, depois do 01_estrutura.sql:
--   mysql -u root -p < database/mysql/02_usuarios.sql
--
-- Três usuários, cada um só com o que precisa:
--
--   cafemaq_admin  -> ADMINISTRADOR da base "cafemaq": pode tudo, mas SÓ
--                     nesta base (não mexe em outras bases do servidor).
--   cafemaq_app    -> usado pela APLICAÇÃO Flask (arquivo .env). Só lê e
--                     grava dados; não cria, altera nem apaga tabelas, e
--                     não pode apagar/alterar os logs de auditoria.
--   cafemaq_backup -> usado só pela rotina de backup (scripts/backup.py):
--                     apenas leitura.
--
-- IMPORTANTE: troque as senhas abaixo antes de usar em produção e coloque a
-- senha do cafemaq_app no arquivo .env (DB_SENHA). Nunca suba o .env pro GitHub.
-- 'localhost' = só aceita conexão da própria máquina. Se o MySQL ficar em
-- outro servidor, troque pelo IP/host da aplicação (evite usar '%').
-- =====================================================================

-- Remove versões antigas (permite rodar o script de novo sem erro)
DROP USER IF EXISTS 'cafemaq_admin'@'localhost';
DROP USER IF EXISTS 'cafemaq_app'@'localhost';
DROP USER IF EXISTS 'cafemaq_backup'@'localhost';

-- ---------------------------------------------------------------------
-- 1) ADMINISTRADOR da base
-- ---------------------------------------------------------------------
CREATE USER 'cafemaq_admin'@'localhost' IDENTIFIED BY 'Admin@CafeMaq2026';
-- Todos os privilégios, mas apenas na base cafemaq (cafemaq.*)
GRANT ALL PRIVILEGES ON cafemaq.* TO 'cafemaq_admin'@'localhost' WITH GRANT OPTION;

-- ---------------------------------------------------------------------
-- 2) APLICAÇÃO (permissões restritas, tabela por tabela)
-- ---------------------------------------------------------------------
CREATE USER 'cafemaq_app'@'localhost' IDENTIFIED BY 'App@CafeMaq2026';

-- Tabelas de negócio: ler, inserir, alterar e excluir (CRUD). Sem DDL.
GRANT SELECT, INSERT, UPDATE, DELETE ON cafemaq.usuarios        TO 'cafemaq_app'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON cafemaq.fazendas        TO 'cafemaq_app'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON cafemaq.funcionarios    TO 'cafemaq_app'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON cafemaq.maquinas        TO 'cafemaq_app'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON cafemaq.atividades      TO 'cafemaq_app'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON cafemaq.ponto           TO 'cafemaq_app'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON cafemaq.relatorios      TO 'cafemaq_app'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON cafemaq.relatorio_itens TO 'cafemaq_app'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON cafemaq.ocorrencias     TO 'cafemaq_app'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON cafemaq.manutencoes     TO 'cafemaq_app'@'localhost';

-- Logs: só INSERIR e LER. Sem UPDATE/DELETE, ninguém consegue apagar
-- rastros pela aplicação (integridade da auditoria).
GRANT SELECT, INSERT ON cafemaq.log_acesso    TO 'cafemaq_app'@'localhost';
GRANT SELECT, INSERT ON cafemaq.log_auditoria TO 'cafemaq_app'@'localhost';

-- Executar as funções e procedimentos da base (03_rotinas.sql)
GRANT EXECUTE ON cafemaq.* TO 'cafemaq_app'@'localhost';

-- ---------------------------------------------------------------------
-- 3) BACKUP (somente leitura + o necessário para o mysqldump)
-- ---------------------------------------------------------------------
CREATE USER 'cafemaq_backup'@'localhost' IDENTIFIED BY 'Backup@CafeMaq2026';
GRANT SELECT, SHOW VIEW, TRIGGER, LOCK TABLES, EVENT ON cafemaq.* TO 'cafemaq_backup'@'localhost';

FLUSH PRIVILEGES;

-- Ler o código das funções/procedimentos no dump (privilégio do MySQL 8.0.20+).
-- No MariaDB/XAMPP este privilégio não existe: se esta linha der erro, pode ignorar.
GRANT SHOW_ROUTINE ON *.* TO 'cafemaq_backup'@'localhost';

-- Para conferir as permissões:
--   SHOW GRANTS FOR 'cafemaq_admin'@'localhost';
--   SHOW GRANTS FOR 'cafemaq_app'@'localhost';
--   SHOW GRANTS FOR 'cafemaq_backup'@'localhost';
