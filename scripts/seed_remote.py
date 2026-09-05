"""Seed a REMOTE Postgres (e.g. the cloud Supabase beta) with the reviewed
demo Evidence Record rows — closes the DEPLOYMENT.md TODO.

Usage:
    export SEED_DATABASE_URL='postgresql://…'   # an OWNER/service connection
                                                # string, NOT hive_readonly
    .venv/bin/python scripts/seed_remote.py eval/demo/*/supabase_rows.json
    .venv/bin/python scripts/seed_remote.py --check      # row counts only

Behavior mirrors scripts/local_db.py load:
  * idempotent per paper: existing rows for each paper_id are replaced,
    never duplicated (safe to re-run after re-reviewing a paper)
  * JSONB columns serialized; unknown keys dropped against the live schema,
    so an older remote schema degrades gracefully (and prints what it dropped)
  * refuses to run against a URL containing 'hive_readonly' or 'hive_feedback'
    (those roles must not own data loads)

The connection string is read from SEED_DATABASE_URL only — never a CLI arg,
so it cannot leak into shell history/process lists. No secrets are printed.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
JSONB_COLS = {"aliases_used_in_paper", "experiment_flags", "antibody_source_evidence",
              "provenance", "validation", "anomaly_flags", "experiment_type_evidence"}


async def _main(paths: list[str], check_only: bool) -> int:
    import asyncpg

    url = os.environ.get("SEED_DATABASE_URL", "")
    if not url:
        print("SEED_DATABASE_URL is not set. Export the target's OWNER connection "
              "string (Supabase: Settings → Database → connection string).")
        return 1
    if "hive_readonly" in url or "hive_feedback" in url:
        print("Refusing: SEED_DATABASE_URL must not use the restricted roles.")
        return 1

    conn = await asyncpg.connect(url)
    try:
        cols = {r["column_name"] for r in await conn.fetch(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='western_blot_records'")}
        if not cols:
            print("Table western_blot_records not found — run api/db/schema.sql "
                  "and migrations/001, 002 first (see DEPLOYMENT.md).")
            return 1
        n = await conn.fetchval("SELECT count(*) FROM western_blot_records")
        print(f"remote western_blot_records: {n} rows, {len(cols)} columns")
        if check_only:
            return 0

        total = 0
        dropped_keys: set[str] = set()
        for path in paths:
            rows = json.loads(Path(path).read_text())
            papers = sorted({r.get("paper_id") for r in rows if r.get("paper_id")})
            for pid in papers:
                await conn.execute(
                    "DELETE FROM western_blot_records WHERE paper_id=$1", pid)
            for row in rows:
                data = {k: v for k, v in row.items() if k in cols and k != "id"}
                dropped_keys |= set(row) - set(data) - {"id"}
                keys = list(data)
                vals, casts = [], []
                for i, k in enumerate(keys, 1):
                    v = data[k]
                    if k in JSONB_COLS and v is not None:
                        vals.append(json.dumps(v)); casts.append(f"${i}::jsonb")
                    else:
                        vals.append(v); casts.append(f"${i}")
                await conn.execute(
                    f'INSERT INTO western_blot_records ({", ".join(keys)}) '
                    f'VALUES ({", ".join(casts)})', *vals)
            total += len(rows)
            print(f"seeded {len(rows):4} rows from {path} (papers: {', '.join(papers)})")
        if dropped_keys:
            print(f"NOTE: keys absent from the remote schema were dropped: "
                  f"{sorted(dropped_keys)} — apply the latest migrations to keep them.")
        n = await conn.fetchval("SELECT count(*) FROM western_blot_records")
        print(f"done: inserted {total}; table now holds {n} rows")
        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    args = sys.argv[1:]
    check = "--check" in args
    paths = [a for a in args if a != "--check"]
    if not check and not paths:
        print(__doc__)
        raise SystemExit(1)
    raise SystemExit(asyncio.run(_main(paths, check)))
