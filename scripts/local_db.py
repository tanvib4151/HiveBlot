"""Local beta database for HiveBlot development — embedded Postgres, no cloud.

Runs a real Postgres (via the `pgserver` wheel — no system install, no Docker)
with its data dir inside the repo at `.localdb/` (gitignored), then applies the
SAME SQL a Supabase project would get, in the same order:

    1. api/db/schema.sql                  (table + pg_trgm + hive_readonly role)
    2. migrations/001_evidence_record.sql (additive Evidence Record columns)

and loads demo Evidence Record rows. The API's /search path talks to Postgres
via asyncpg (DB_READONLY_URL) and never touches PostgREST, so against this
database the search loop is the REAL production path. Cloud Supabase is still
required for the hosted beta — this exists so the loop runs end-to-end locally.

Usage (from repo root):
    .venv/bin/python scripts/local_db.py up            # init + start + migrate
    .venv/bin/python scripts/local_db.py load <rows.json> [...]   # load demo rows
    .venv/bin/python scripts/local_db.py status        # row counts + DSNs
    .venv/bin/python scripts/local_db.py stop

Idempotent: `up` re-applies (everything is IF NOT EXISTS); `load` replaces any
existing rows with the same paper_id (safe re-runs, no duplicate records).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA_DIR = REPO / ".localdb"
DB_NAME = "hiveblot"

# JSONB columns in western_blot_records (migration 001): serialized on insert.
JSONB_COLS = {"aliases_used_in_paper", "experiment_flags", "antibody_source_evidence",
              "provenance", "validation", "anomaly_flags", "experiment_type_evidence"}


def get_server(cleanup_mode: str | None = None):
    """cleanup_mode=None leaves Postgres RUNNING after this script exits, so
    the API server (a separate process) can keep connecting. `stop` shuts it
    down explicitly."""
    import pgserver
    DATA_DIR.mkdir(exist_ok=True)
    return pgserver.get_server(DATA_DIR, cleanup_mode=cleanup_mode)


def superuser_uri(server) -> str:
    return server.get_uri(DB_NAME)


def readonly_uri(server) -> str:
    # pgserver uses trust auth on its unix socket, so no password is needed
    # locally; the role still exercises the same scoped-SELECT grants as prod.
    return superuser_uri(server).replace("postgres:@", "hive_readonly:@").replace(
        "user=postgres", "user=hive_readonly")


def _connect(uri: str):
    import psycopg2  # optional path; asyncpg used otherwise
    return psycopg2.connect(uri)


def run_sql(uri: str, sql: str) -> None:
    import asyncio

    import asyncpg

    async def _run():
        conn = await asyncpg.connect(uri)
        try:
            await conn.execute(sql)
        finally:
            await conn.close()
    asyncio.run(_run())


def fetch(uri: str, sql: str):
    import asyncio

    import asyncpg

    async def _run():
        conn = await asyncpg.connect(uri)
        try:
            return [dict(r) for r in await conn.fetch(sql)]
        finally:
            await conn.close()
    return asyncio.run(_run())


def cmd_up() -> None:
    server = get_server()
    # Create the app database if missing (pgserver initializes with `postgres`).
    base = server.get_uri()  # default db
    names = [r["datname"] for r in fetch(base, "SELECT datname FROM pg_database")]
    if DB_NAME not in names:
        run_sql(base, f'CREATE DATABASE "{DB_NAME}"')
    uri = superuser_uri(server)

    schema_sql = (REPO / "api/db/schema.sql").read_text()
    # schema.sql grants CONNECT on "postgres" (the Supabase default DB); grant
    # on the local DB name instead so the same file applies unmodified.
    try:
        run_sql(uri, schema_sql)
    except Exception as e:
        if "pg_trgm" not in str(e):
            raise
        # pgserver does not bundle the pg_trgm contrib extension. The trigram
        # index is a search-latency optimization, not correctness — strip the
        # extension + its index locally; Supabase applies the file unmodified.
        import re
        local_sql = re.sub(r"create extension if not exists pg_trgm;", "", schema_sql)
        local_sql = re.sub(
            r"create index if not exists idx_western_blot_records_target[^;]+;",
            "", local_sql)
        run_sql(uri, local_sql)
        print("NOTE: pg_trgm unavailable locally — trigram index skipped "
              "(cloud Supabase still gets it from schema.sql).")
    run_sql(uri, f'GRANT CONNECT ON DATABASE "{DB_NAME}" TO hive_readonly')
    migrations = sorted((REPO / "migrations").glob("[0-9]*.sql"))
    for mig in migrations:
        if mig.name.endswith(".down.sql"):
            continue
        run_sql(uri, mig.read_text())
        print(f"applied {mig.name}")
    run_sql(uri, f'GRANT CONNECT ON DATABASE "{DB_NAME}" TO hive_feedback')
    print("schema + migrations applied (idempotent).")
    cmd_status()


def cmd_load(paths: list[str]) -> None:
    import asyncio

    import asyncpg

    server = get_server()
    uri = superuser_uri(server)

    async def _load():
        conn = await asyncpg.connect(uri)
        try:
            cols = {r["column_name"] for r in await conn.fetch(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='western_blot_records'")}
            total = 0
            for path in paths:
                rows = json.loads(Path(path).read_text())
                papers = sorted({r.get("paper_id") for r in rows if r.get("paper_id")})
                # Replace (idempotent re-load), never duplicate.
                for pid in papers:
                    await conn.execute(
                        "DELETE FROM western_blot_records WHERE paper_id=$1", pid)
                for row in rows:
                    data = {k: v for k, v in row.items() if k in cols and k != "id"}
                    keys = list(data)
                    vals, casts = [], []
                    for i, k in enumerate(keys, 1):
                        v = data[k]
                        if k in JSONB_COLS and v is not None:
                            vals.append(json.dumps(v))
                            casts.append(f"${i}::jsonb")
                        else:
                            vals.append(v)
                            casts.append(f"${i}")
                    await conn.execute(
                        f'INSERT INTO western_blot_records ({", ".join(keys)}) '
                        f'VALUES ({", ".join(casts)})', *vals)
                total += len(rows)
                print(f"loaded {len(rows)} rows from {path} (papers: {', '.join(papers)})")
            n = await conn.fetchval("SELECT count(*) FROM western_blot_records")
            print(f"inserted {total}; table now holds {n} rows total")
        finally:
            await conn.close()
    asyncio.run(_load())


def cmd_status() -> None:
    server = get_server()
    uri = superuser_uri(server)
    try:
        n = fetch(uri, "SELECT count(*) AS n FROM western_blot_records")[0]["n"]
    except Exception:
        n = "(table missing — run `up`)"
    print(f"db: {DB_NAME} at {DATA_DIR}")
    print(f"western_blot_records rows: {n}")
    print(f"DB_READONLY_URL={readonly_uri(server)}")


def cmd_stop() -> None:
    server = get_server(cleanup_mode="stop")
    server.cleanup()
    print("stopped.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "up":
        cmd_up()
    elif cmd == "load":
        cmd_load(sys.argv[2:])
    elif cmd == "status":
        cmd_status()
    elif cmd == "stop":
        cmd_stop()
    else:
        print(__doc__)
        sys.exit(1)
