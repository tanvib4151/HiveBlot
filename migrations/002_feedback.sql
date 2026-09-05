-- =====================================================================
-- HiveBlot beta -- Migration 002: Researcher feedback (additive)
-- =====================================================================
-- SAFETY / AUDITABILITY:
--   * Strictly ADDITIVE: creates one new table + role; touches nothing else.
--   * Human feedback NEVER mutates western_blot_records. The AI extraction
--     and the human correction are separate rows in separate tables, so the
--     system can always render "AI claim -> human correction" and future
--     model evaluation can use corrections as labels.
--   * model_value snapshots the AI value AT FEEDBACK TIME, so the pair stays
--     meaningful even if the record is later re-extracted.
--   * A dedicated role (hive_feedback) can ONLY insert/select this table --
--     the API's feedback path physically cannot write anywhere else.
--
-- Run AFTER 001. Idempotent. Rollback: 002_feedback.down.sql.
-- =====================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS hiveblot_feedback (
    feedback_id     BIGSERIAL PRIMARY KEY,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    app_version     TEXT,

    -- What kind of feedback this is.
    --   field         : judgment on one biological field of one record
    --   record        : result-level flag (wrong interpretation, wrong figure, ...)
    --   missing_field : "I wish HiveBlot also showed <X>"
    --   search        : did HiveBlot understand the query (yes/partially/no)
    --   ui            : general interface feedback
    feedback_scope  TEXT NOT NULL CHECK (feedback_scope IN
                        ('field', 'record', 'missing_field', 'search', 'ui')),

    -- Optional anchors (nullable by design; scope determines which apply).
    record_id       BIGINT,            -- western_blot_records.id (no FK: feedback
                                       -- must survive record re-ingestion/deletes)
    paper_id        TEXT,
    figure_label    TEXT,
    search_query    TEXT,
    field_name      TEXT,              -- e.g. cell_line, experiment_type, antibody_catalog_number
    model_value     TEXT,              -- AI value snapshot at feedback time (audit)
    feedback_type   TEXT,              -- field: correct|incorrect|not_useful|missing_context
                                       -- record: wrong_interpretation|wrong_experiment_type|
                                       --         wrong_target_modification|wrong_phosphosite|
                                       --         wrong_antibody_association|wrong_figure_association|
                                       --         missing_methods_context|irrelevant_result|other
                                       -- search: understood_yes|understood_partially|understood_no
                                       -- missing_field / ui: free-form via field_name/comment
    suggested_value TEXT,              -- researcher's correction; NEVER auto-applied
    comment         TEXT,
    ui_location     TEXT,              -- page/component identifier
    session_id      TEXT               -- anonymous browser-session id (no PII)
);

CREATE INDEX IF NOT EXISTS idx_feedback_scope   ON hiveblot_feedback (feedback_scope);
CREATE INDEX IF NOT EXISTS idx_feedback_record  ON hiveblot_feedback (record_id);
CREATE INDEX IF NOT EXISTS idx_feedback_created ON hiveblot_feedback (created_at);
CREATE INDEX IF NOT EXISTS idx_feedback_field   ON hiveblot_feedback (field_name);

-- --- Insert-only role for the API's feedback path --------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'hive_feedback') THEN
        CREATE ROLE hive_feedback WITH LOGIN;
    END IF;
END
$$;

-- Password is set out-of-band (same policy as hive_readonly in schema.sql):
-- alter role hive_feedback with password 'REPLACE_WITH_A_GENERATED_SECRET';

GRANT USAGE ON SCHEMA public TO hive_feedback;
GRANT INSERT, SELECT ON hiveblot_feedback TO hive_feedback;
GRANT USAGE ON SEQUENCE hiveblot_feedback_feedback_id_seq TO hive_feedback;
-- The read-only search role may read feedback (for future "community notes"
-- style display) but cannot write it.
GRANT SELECT ON hiveblot_feedback TO hive_readonly;

COMMIT;
