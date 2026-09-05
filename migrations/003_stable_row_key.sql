-- =====================================================================
-- Migration 003: stable per-lane row identity (additive, idempotent)
-- =====================================================================
-- The serial `id` changes on every reseed (loaders replace a paper's rows),
-- which orphaned researcher feedback keyed to it (manual-beta P0 finding).
-- `stable_row_key` = <record-hash>:<lane_index>, computed deterministically
-- from the reviewed observation data by to_supabase_rows(), so feedback
-- keyed to it survives reloads. Feedback also gains the column; the two are
-- OR-matched at read time. Strictly additive; rollback in the .down file.
BEGIN;

ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS stable_row_key TEXT;
CREATE INDEX IF NOT EXISTS idx_wbr_stable_row_key
    ON western_blot_records (stable_row_key);

ALTER TABLE hiveblot_feedback ADD COLUMN IF NOT EXISTS stable_row_key TEXT;
CREATE INDEX IF NOT EXISTS idx_feedback_stable_row_key
    ON hiveblot_feedback (stable_row_key);

COMMIT;
