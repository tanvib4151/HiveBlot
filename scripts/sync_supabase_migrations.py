"""Copy the canonical SQL files into the Supabase CLI migration layout.
Run after editing api/db/schema.sql or migrations/*.sql. The pytest drift
guard (api/tests/test_supabase_migrations_sync.py) enforces equality."""
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PAIRS = [
    ("api/db/schema.sql", "supabase/migrations/20260701000001_base_schema.sql"),
    ("migrations/001_evidence_record.sql", "supabase/migrations/20260701000002_evidence_record.sql"),
    ("migrations/002_feedback.sql", "supabase/migrations/20260701000003_feedback.sql"),
    ("migrations/003_stable_row_key.sql", "supabase/migrations/20260701000004_stable_row_key.sql"),
]

if __name__ == "__main__":
    for src, dst in PAIRS:
        shutil.copyfile(REPO / src, REPO / dst)
        print(f"synced {src} -> {dst}")
