BEGIN;
DROP INDEX IF EXISTS idx_feedback_stable_row_key;
ALTER TABLE hiveblot_feedback DROP COLUMN IF EXISTS stable_row_key;
DROP INDEX IF EXISTS idx_wbr_stable_row_key;
ALTER TABLE western_blot_records DROP COLUMN IF EXISTS stable_row_key;
COMMIT;
