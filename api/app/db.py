import asyncpg
from supabase import Client, create_client

from .config import settings

# Used only for simple, already-parameterized queries (.ilike(), .limit(), ...)
# via the Supabase query builder - never for the LLM-generated SQL.
# Created lazily: only /proteins and the index page need PostgREST, and the
# /search path must be able to boot and run against DB_READONLY_URL alone
# (e.g. the local dev database from scripts/local_db.py) with no Supabase
# project configured. create_client("") raises at import time otherwise.
_supabase: Client | None = None


def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        _supabase = create_client(settings.supabase_url, settings.supabase_key)
    return _supabase

_pool: asyncpg.Pool | None = None


async def _decode_json(conn: asyncpg.Connection) -> None:
    # asyncpg returns json/jsonb as raw strings by default; the response
    # models type these columns as lists/dicts (e.g. anomaly_flags,
    # experiment_flags), so decode them at the driver boundary.
    import json

    for typename in ("json", "jsonb"):
        await conn.set_type_codec(
            typename, encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
        )


async def get_readonly_pool() -> asyncpg.Pool:
    """
    Lazily-created pool for db_readonly_url, which must point at a Postgres
    role granted SELECT on settings.table_name only. This is what actually
    executes the validated, LLM-generated SQL from /search.
    """
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.db_readonly_url, min_size=1, max_size=5, init=_decode_json
        )
    return _pool


async def close_readonly_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def run_readonly_query(sql: str) -> list[dict]:
    pool = await get_readonly_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql)
        return [dict(row) for row in rows]


async def fetch_record_by_id(record_id: int) -> dict | None:
    """One full row (including the provenance/validation JSONB envelopes) for
    the record-detail endpoint. Parameterized; runs on the read-only role."""
    pool = await get_readonly_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT * FROM {settings.table_name} WHERE id = $1", record_id
        )
        return dict(row) if row else None


# --- feedback write path (hive_feedback role; migration 002) ---------------
_feedback_pool: asyncpg.Pool | None = None


async def get_feedback_pool() -> asyncpg.Pool:
    global _feedback_pool
    if _feedback_pool is None:
        _feedback_pool = await asyncpg.create_pool(
            settings.db_feedback_url, min_size=1, max_size=3, init=_decode_json
        )
    return _feedback_pool


async def close_feedback_pool() -> None:
    global _feedback_pool
    if _feedback_pool is not None:
        await _feedback_pool.close()
        _feedback_pool = None


async def fetch_feedback_for_record(record_id: int,
                                    stable_row_key: str | None = None) -> list[dict]:
    """All researcher feedback rows for one record (rehydration). Matches the
    volatile serial id OR the reseed-proof stable_row_key (migration 003) —
    a DB reload replaces serial ids, and feedback keyed only to them orphaned
    (manual-beta P0 finding). Read via the feedback role's own SELECT grant;
    the Evidence Record itself is never touched."""
    pool = await get_feedback_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT feedback_id, created_at, feedback_scope, stable_row_key, "
            "field_name, model_value, feedback_type, suggested_value, comment, "
            "session_id FROM hiveblot_feedback "
            "WHERE record_id = $1 OR (stable_row_key IS NOT NULL AND stable_row_key = $2) "
            "ORDER BY feedback_id",
            record_id, stable_row_key,
        )
        return [dict(r) for r in rows]


async def insert_feedback(fields: dict) -> int:
    """Insert one feedback row; returns feedback_id. Human feedback lives in
    hiveblot_feedback ONLY — the hive_feedback role has no grants on
    western_blot_records, so the AI extraction cannot be overwritten here."""
    pool = await get_feedback_pool()
    cols = list(fields)
    placeholders = ", ".join(f"${i}" for i in range(1, len(cols) + 1))
    sql = (
        f'INSERT INTO hiveblot_feedback ({", ".join(cols)}) '
        f"VALUES ({placeholders}) RETURNING feedback_id"
    )
    async with pool.acquire() as conn:
        return await conn.fetchval(sql, *[fields[c] for c in cols])
