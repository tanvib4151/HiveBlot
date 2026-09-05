# Supabase CLI layout

`supabase/migrations/*.sql` are TIMESTAMPED COPIES of the canonical SQL:

| CLI migration                          | canonical source                  |
|----------------------------------------|-----------------------------------|
| 20260701000001_base_schema.sql         | api/db/schema.sql                 |
| 20260701000002_evidence_record.sql     | migrations/001_evidence_record.sql|
| 20260701000003_feedback.sql            | migrations/002_feedback.sql       |

Edit the CANONICAL files, then run `scripts/sync_supabase_migrations.py`.
`api/tests/test_supabase_migrations_sync.py` fails the suite on any drift.
Fresh-project flow: see DEPLOYMENT.md §1.
