-- Rollback for 002_feedback.sql. Drops ONLY what 002 created.
BEGIN;
DROP TABLE IF EXISTS hiveblot_feedback;
-- The hive_feedback role is left in place (dropping roles can break other
-- grants); revoke instead if needed:
--   REVOKE ALL ON ALL TABLES IN SCHEMA public FROM hive_feedback;
COMMIT;
