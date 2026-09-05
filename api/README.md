# Hive API

FastAPI backend for Hive. Serves Western Blot records extracted from
scientific papers, stored in Supabase.

## Two API surfaces, one search pipeline

- **Internal** (`app/routers/internal.py`): `/health`, `/`, `/proteins`,
  `/search`. Called only by `web/`'s server-side `/api/search` route
  (Next.js BFF) using `INTERNAL_API_KEY`. Free to change shape as the
  frontend's needs change - not a contract anyone else depends on.
- **External** (`app/routers/external.py`): `POST /v1/search`. The one
  stable, documented endpoint meant for third-party agents/integrations to
  call directly. Auth is a *set* of keys (`AGENT_API_KEYS`), so an
  individual agent can be issued or revoked its own key independently of
  the frontend or other agents. See the endpoint's OpenAPI description
  (`/docs`) for the contract agents should rely on.

Both routers call the same `app/search_service.py:execute_search`, so there's
exactly one implementation of the security-critical pipeline below - no risk
of the internal and external paths drifting apart.

## How search works

1. GPT (`OPENAI_MODEL`, default `gpt-4.1-mini`) turns the question into a
   PostgreSQL `SELECT` (`app/nlp.py`).
2. `app/sql_guard.py` parses that SQL into an AST (via `sqlglot`) and rejects
   anything that isn't a single `SELECT` against `western_blot_records`,
   rejects disallowed functions, and rewrites in a server-enforced `LIMIT`
   regardless of what the model produced.
3. The validated query runs through a **dedicated Postgres role that only has
   SELECT on `western_blot_records`** (`DB_READONLY_URL`, see `db/schema.sql`)
   - not the Supabase service-role key. A bug in step 2 still can't turn into
   a full-database read/write.

Both `/search` and `/v1/search` are rate-limited (`SEARCH_RATE_LIMIT` /
`AGENT_RATE_LIMIT`) since each call costs an OpenAI request.

## Setup

1. Create a new Supabase project.
2. Run `db/schema.sql` in the Supabase SQL editor (creates the table and the
   `hive_readonly` role - read the comments inline, set that role's password
   as a separate step before copying it into `.env`).
3. `cp .env.example .env` and fill in the values. Generate `INTERNAL_API_KEY`
   and each entry in `AGENT_API_KEYS` with
   `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
4. `pip install -r requirements.txt` (or `pip install -e .` / `uv sync`)
5. `uvicorn app.main:app --reload`

## Tests

```bash
pip install pytest
python -m pytest
```

No credentials needed - `conftest.py` supplies dummy env vars and nothing here
talks to Supabase, OpenAI, or Postgres. The suite covers the SQL guard
(`tests/test_sql_guard.py`), the two auth dependencies and their disjointness
(`tests/test_auth.py`), and endpoint-level auth/rate-limit/CORS behaviour
(`tests/test_api_security.py`).

If you add a function to `sql_guard.ALLOWED_FUNCTIONS`, add a test for it. The
allowlist is deny-by-default and has to stay that way: it resolves a name for
every `exp.Func` node, not just `exp.Anonymous`, because sqlglot parses
functions it recognises into dedicated classes that would otherwise skip the
check entirely.

## Endpoints

| Method | Path         | Auth | Consumer |
|--------|--------------|------|----------|
| GET    | `/health`    | none | uptime pings |
| GET    | `/`          | none | Supabase connectivity check, returns 5 sample rows |
| GET    | `/proteins`  | `INTERNAL_API_KEY` | web/ frontend only |
| POST   | `/search`    | `INTERNAL_API_KEY`, rate-limited | web/ frontend only |
| POST   | `/v1/search` | one of `AGENT_API_KEYS`, rate-limited | external agents/integrations |
