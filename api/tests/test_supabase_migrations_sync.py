"""Drift guard: the Supabase CLI migration copies must stay byte-identical to
the canonical SQL files, so `supabase db push` and the local/psql flow can
never apply different schemas. Fix drift with scripts/sync_supabase_migrations.py."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PAIRS = [
    ("api/db/schema.sql", "supabase/migrations/20260701000001_base_schema.sql"),
    ("migrations/001_evidence_record.sql", "supabase/migrations/20260701000002_evidence_record.sql"),
    ("migrations/002_feedback.sql", "supabase/migrations/20260701000003_feedback.sql"),
    ("migrations/003_stable_row_key.sql", "supabase/migrations/20260701000004_stable_row_key.sql"),
]


def test_supabase_migrations_match_canonical_sql():
    for src, dst in PAIRS:
        a, b = (REPO / src), (REPO / dst)
        assert b.exists(), f"missing CLI copy {dst} — run scripts/sync_supabase_migrations.py"
        assert a.read_bytes() == b.read_bytes(), (
            f"{dst} drifted from {src} — run scripts/sync_supabase_migrations.py")
