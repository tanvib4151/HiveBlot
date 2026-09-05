# Hive — execution plan

Read this whole file before touching anything. It's written to be self-contained
for a fresh session with no prior context.

## Why this repo exists

The previous implementation was two repos:
- **`Ananya-Jha-code/QBI`** ("HiveBlot" frontend, Next.js) — had a real, working
  search flow, but it was fused with a dead leftover product ("VOC Triage":
  `/molecules`, `/receptors`, `/diseases`, `/oracle`, `lib/data.ts`, a 1.8MB mock
  JSON — none of it linked from nav), plus repo hygiene problems: `.next` build
  output committed (62MB `.git`), duplicate screenshots/videos, stray AI-prompt
  drafts, a hardcoded backend URL, and an always-on uncapped canvas animation.
- **`SuhasKM2001/blot_backend`** (FastAPI, 219 lines total) — its `/search`
  endpoint had GPT write **raw PostgreSQL from user text**, checked it with a
  **substring blocklist** (`if "drop" in sql.lower()`), and executed it via a
  Supabase RPC using what's almost certainly the service-role key. Unauthenticated,
  `CORS allow_origins=["*"]`, no rate limiting, no enforced `LIMIT`, no error
  handling on `/search`. This was the single most urgent finding of the whole
  audit — a live, internet-facing, unauthenticated endpoint executing
  LLM-generated SQL with no real sandboxing.

`nikhilesh-s/hive` is the clean rebuild. **Decisions locked in with the user:**
1. Monorepo: `web/` (frontend) + `api/` (backend), rebuilt together so the
   security fix isn't deferred.
2. Search stays natural-language-to-SQL (not switched to a filter-builder),
   but properly sandboxed: AST-level validation + a dedicated low-privilege
   DB role + a server-enforced `LIMIT`, replacing the substring blocklist.
3. The dead "VOC Triage" app is dropped entirely — only the real flow got rebuilt.
4. **This is a from-scratch deploy** — new Supabase project, new Render service,
   new Vercel project. Nothing is migrated from the old `.env`s; there is no
   existing production data to preserve.
5. **Preserve the frontend as much as possible.** Beyond dropping the dead
   VOC Triage pages and the specific fixes listed below (debounce, paused
   canvas animation, env-configurable backend URL, rebrand text), **do not
   redesign, restyle, or restructure the UI.** The look, copy, layout, and
   component structure of the real HiveBlot flow (`page.tsx`, `search/page.tsx`,
   `about`, `learn`, and all the carried-over components) should stay as close
   to the original as possible. If you think something in the UI should
   change beyond what's listed here, ask first rather than assuming the
   rebuild is a redesign opportunity.
6. **Two API surfaces, not one** — see below. This was added after the
   initial scaffold, so it's already reflected in the code in this repo, not
   something still to build.

## Architecture: internal APIs + one external, agent-facing API

The backend has two distinct surfaces sharing one search pipeline:

- **Internal** (`api/app/routers/internal.py`): `/health`, `/`, `/proteins`,
  `/search`. Called only by `web/`'s server-side `/api/search` route handler
  (Next.js BFF), authenticated with `INTERNAL_API_KEY`. This is a private
  contract between the frontend and its own backend — free to change shape
  as the frontend's needs change.
- **External** (`api/app/routers/external.py`): `POST /v1/search`. The one
  stable, documented endpoint meant for **agents/third-party integrations**
  to call directly, not through the frontend. Versioned (`/v1`) so its
  contract can stay stable independent of internal changes. Authenticated
  against a *set* of keys (`AGENT_API_KEYS`, comma-separated) rather than one
  shared secret, so an individual agent's access can be issued or revoked
  without affecting the frontend or any other agent. It has its own,
  separately-tunable rate limit (`AGENT_RATE_LIMIT`) and a rich OpenAPI
  `summary`/`description` (visible at `/docs`) written for an agent/LLM
  consumer, not a human reading source code.
- Both routers call **the same** `api/app/search_service.py:execute_search`,
  which runs the full `generate_sql → sql_guard.guard_and_limit_sql →
  run_readonly_query` pipeline. There is exactly one implementation of the
  security-critical path — the internal/external split is only about auth,
  rate limits, and API contract stability, never about having two different
  (and therefore two potentially-inconsistent) sandboxing implementations.

If you need to give an agent framework a tool spec, point it at
`GET /openapi.json` (or `/docs` for a human) — `/v1/search`'s description is
already written to double as that tool's description.

## What's already built in this repo (do not redo — verify, don't rewrite)

### `api/` — FastAPI backend
- `app/config.py` — `pydantic-settings` `Settings`, fails fast with a clear
  error if any required env var is missing. Holds `internal_api_key` and
  `agent_api_keys` (comma-separated, exposed as `.agent_api_keys_set`)
  separately — don't collapse these back into one key.
- `app/db.py` — `supabase` client (for the already-safe, parameterized
  `/proteins` and `/` queries) **and** a separate `asyncpg` pool
  (`get_readonly_pool`/`run_readonly_query`) used only to execute the
  validated, LLM-generated SQL from search.
- `app/sql_guard.py` — **the core security fix.** Parses generated SQL with
  `sqlglot`, rejects anything that isn't a single plain `SELECT` against
  `western_blot_records` (no unions, no writes/DDL, no disallowed functions),
  and rewrites in a server-enforced `LIMIT` regardless of what the model
  produced. This is defense layer 1.
- `db/schema.sql` — creates `western_blot_records` and a `hive_readonly`
  Postgres role that only has `SELECT` on that one table. `DB_READONLY_URL`
  (used by `db.py`) must point at this role, not the Supabase service key.
  This is defense layer 2 — even a bug in `sql_guard.py` can't escalate past
  what this role is physically allowed to do.
- `app/auth.py` — `require_internal_key` (checked against `INTERNAL_API_KEY`)
  and `require_agent_key` (checked against the `AGENT_API_KEYS` set, returns
  the matched key so callers can log which agent made the request).
- `app/search_service.py` — the one shared `execute_search()` pipeline, see
  architecture section above.
- `app/routers/internal.py` / `app/routers/external.py` — the two routers.
- `app/limiter.py` — the single shared `slowapi` `Limiter` instance both
  routers and `main.py` reference.
- `app/main.py` — just wires the app together now: CORS locked to
  `ALLOWED_ORIGINS` (not `*`, and only meaningful for the internal router —
  `/v1/search` is guarded by `require_agent_key`, not CORS), registers both
  routers, registers the rate-limit exception handler.
- `app/nlp.py` — the NL→SQL prompt (`generate_sql`), moved over as-is. The old
  repo's unused `parse_query`/Qwen code path was **deliberately dropped** —
  it was dead code contradicting the README (README claimed Qwen, live code
  path used GPT-4.1-mini). Don't resurrect it without a real decision to use it.
- `app/schemas.py` — `confidence` is typed `float | None` (0–1) to match the
  frontend's real `DatabaseResult` type. **Open decision, see step 3 below.**

### `web/` — Next.js frontend (preserved, not redesigned — see decision 5 above)
- Carried over as-is, with only the fixes listed: `app/page.tsx` (home +
  inline results), `app/search/page.tsx`, `app/about/page.tsx`,
  `app/learn/page.tsx`,
  `components/{SearchInput,ResultsTable,ResultsCard,DatabaseResultCard,Navigation,OrbitCanvas}.tsx`.
- Dropped entirely: `/molecules`, `/receptors`, `/diseases`, `/oracle`,
  `lib/data.ts`, the 1.8MB mock JSON dataset — none of it was linked from nav
  in the old repo; it was dead weight, not a feature to preserve.
- `app/api/search/route.ts` — calls the backend's *internal* `/search`
  endpoint. No longer hardcodes `blot-backend.onrender.com`; reads
  `API_BASE_URL` and attaches `Authorization: Bearer ${INTERNAL_API_KEY}`.
  This must never be pointed at an agent key or at `/v1/search`.
- `components/SearchInput.tsx` — now debounces `onSearch` (400ms, Enter key
  bypasses the debounce) since every search now costs a real OpenAI call —
  firing on every keystroke was fine when it was free (client-side JSON
  filtering); it isn't anymore.
- `components/OrbitCanvas.tsx` — now uses an `IntersectionObserver` to pause
  its `requestAnimationFrame` loop when off-screen, instead of running forever.
- Kept only the one background video actually referenced (`hive-background-v3.mp4`
  → renamed `hive-background.mp4`), dropped the 3 unused near-duplicates.
- `.gitignore` (both root-level configs) explicitly excludes `.next/`,
  `*.tsbuildinfo`, `node_modules/`, `.env*` from day one.
- Rebrand cleanup done: `package.json` name, and the "voc triage" label baked
  into `OrbitCanvas`'s canvas text, both fixed — this is copy/label
  correction, not a design change, and is in scope per decision 5.

**None of this has been run yet** (`npm install`/`npm run dev`,
`pip install`/`uvicorn`). That's step 1 below.

## Status (last updated 2026-07-29)

Steps 1, 2 and 7 are **done**. Steps 3, 4, 5, 6 are **done except for the parts
that need a live Supabase project and OpenAI key**; step 8 (deploy) and step 9
(retire the old services) are untouched and need account access.

What a fresh session should pick up:
1. Create the Supabase project and fill the four blank values in `api/.env`
   (`SUPABASE_URL`, `SUPABASE_KEY`, `OPENAI_KEY`, `DB_READONLY_URL`). Both
   `.env` files already exist with generated, matching API keys.
2. Then finish the live half of steps 5 and 6 — marked ⏳ below.
3. Then deploy (step 8).

Two things changed in the code while verifying, both noted in place below: a
real hole in `sql_guard.py`'s function allowlist (step 2), and the `confidence`
type drift being resolved in favour of numeric 0-1 (step 3).

## Remaining steps — do these in order

### 1. ✅ Verify both apps actually run
- `api/`: create a venv, `pip install -r requirements.txt` (or `pip install -e .`),
  confirm `python -c "import app.main"` doesn't blow up on missing env vars in
  a sane way (it should raise a clear pydantic validation error, not a random
  crash) — you'll need dummy env vars for this, real ones come in step 3.
- `web/`: `npm install`, `npm run build` (not just `dev` — catches type errors
  the old repo probably had, `next.config.ts` should be checked for
  `ignoreBuildErrors`/`ignoreDuringBuilds` flags that would hide problems).
  If `npm run build` surfaces issues, fix them without changing the visual
  design (decision 5) — these should be type/config fixes, not rewrites.

**Outcome:** both run. `api/.venv` created, `pip install -r requirements.txt`
clean on Python 3.14; missing env vars raise the intended pydantic
`ValidationError` naming all 6 required fields. `web/` builds with no type
errors and no `ignoreBuildErrors`/`ignoreDuringBuilds` in `next.config.ts`;
the only routes emitted are `/`, `/about`, `/learn`, `/search`, `/api/search`.
`next` was bumped 16.2.9 → 16.2.12 to clear 9 advisories (middleware/proxy
bypass, two SSRFs, Server Action DoS, cache confusion). `npm audit` still
reports Next's *bundled* `postcss` and `sharp` — build-time only, pinned by
Next itself, and npm's only offered "fix" is a downgrade to next@9. Recheck on
the next Next release rather than forcing an override. The remaining eslint
advisories are dev-only and need an eslint 10 major bump.

### 2. ✅ Write and run tests for `sql_guard.py` — the highest-value test in the whole repo
No tests exist yet. Write `api/tests/test_sql_guard.py` covering at minimum:
- A normal generated query (`SELECT * FROM western_blot_records WHERE target ILIKE '%p53%'`)
  passes through and gets a `LIMIT` appended.
- `SELECT * FROM auth.users` → rejected (wrong table).
- `SELECT * FROM western_blot_records; DROP TABLE western_blot_records;` →
  rejected (multiple statements).
- A query with a huge or missing `LIMIT` → clamped to `min(requested, 500)`.
- `SELECT pg_sleep(10) FROM western_blot_records` → rejected (disallowed function).
- A `UNION`-based query trying to reach another table → rejected.
- Confirm these with **real invocations of `guard_and_limit_sql`**, not just
  reasoning about the code — `sqlglot`'s exact AST shapes are easy to get
  subtly wrong (e.g. whether `LIMIT` shows up as `stmt.args["limit"]` in every
  case). Run `pytest` and actually look at the output.
- Add one test for `auth.require_agent_key`: a key not in `AGENT_API_KEYS`
  is rejected, and removing a key from the set immediately invalidates it
  (no caching bug where an old key keeps working).

**Outcome: 81 tests, all passing** (`cd api && .venv/bin/python -m pytest`).
`api/conftest.py` sets dummy env vars before `app` is imported (config.Settings
is instantiated at import time) and puts `api/` on `sys.path`.
- `tests/test_sql_guard.py` (43) — every case listed above plus subquery/CTE/
  JOIN attempts at another table, `SELECT INTO`, tableless `SELECT 1`,
  unparseable input, and `min(model_limit, requested, max)` limit semantics.
- `tests/test_auth.py` (19) — the agent-key cases above, plus the property
  that matters most: the internal key and the agent keys are **disjoint sets**,
  asserted in both directions.
- `tests/test_api_security.py` (19) — endpoint-level, via `TestClient` with the
  search pipeline stubbed: 401s on both surfaces, neither key working against
  the other's endpoint, independent rate-limit budgets, and CORS refusing an
  arbitrary origin. This is most of step 6, kept as permanent tests.

**A real bug was found and fixed doing this.** The function allowlist only
inspected `exp.Anonymous` nodes, so every function sqlglot has a dedicated
class for — `version()`, `current_user`, `session_user`, `current_database()`,
`md5()`, `encode()`, `string_agg()` — bypassed the allowlist completely. The
genuinely dangerous ones (`pg_read_file`, `dblink`, `pg_sleep`, `query_to_xml`)
*are* `Anonymous` and were correctly blocked, so the exposure was DB/session
metadata rather than table data — but "deny by default" wasn't actually true,
and sqlglot adds typed nodes every release. `sql_guard.py` now resolves a name
for *all* `exp.Func` nodes; `test_functions_sqlglot_has_a_node_type_for_are_still_rejected`
locks it in. `cast` was added to `ALLOWED_FUNCTIONS` since `::` casts are pure
and plausible in generated SQL.

### 3. ⏳ Provision the new Supabase project — needs your account
- Create the project.
- Run `api/db/schema.sql` in the SQL editor. Read its inline comments — it
  creates `hive_readonly` without a password; set the password as a separate
  `ALTER ROLE` statement (commented example is in the file) so a real secret
  never sits in a checked-in file.
- ~~Decide the `confidence` column's real type now~~ — **decided: numeric
  0–1.** It was already `real` in `db/schema.sql`, `float | None` in
  `schemas.py`, and `number` in the frontend (which renders `confidence * 100`
  as a percentage); only `nlp.py`'s prompt schema still declared it `TEXT`,
  which would have had GPT emit `confidence ILIKE '%high%'` against a numeric
  column. `nlp.py` now says `REAL` and has a rule telling the model to compare
  it numerically. If your extraction pipeline produces `"high"/"medium"/"low"`,
  map to a score before insert — don't reintroduce a text column on one side.

### 4. ✅ Fill in both `.env` files — except the four credential values
- `api/.env` from `api/.env.example`: `SUPABASE_URL`/`SUPABASE_KEY` (new
  project), `OPENAI_KEY`, `DB_READONLY_URL` (the `hive_readonly` connection
  string from step 3), `INTERNAL_API_KEY` and at least one entry in
  `AGENT_API_KEYS` (generate each with
  `python -c "import secrets; print(secrets.token_urlsafe(32))"` — different
  values, don't reuse one key for both), `ALLOWED_ORIGINS` (your Vercel URL
  once you have it, plus `localhost:3000` for now).
- `web/.env` from `web/.env.example`: `API_BASE_URL` (local:
  `http://localhost:8000`), `INTERNAL_API_KEY` (must match the backend's
  `INTERNAL_API_KEY` — never one of the `AGENT_API_KEYS` values).

**Outcome:** both `.env` files exist and are gitignored (verified with
`git check-ignore`). `INTERNAL_API_KEY` and one `AGENT_API_KEYS` entry were
generated as distinct `secrets.token_urlsafe(32)` values, and the web key
matches the api key. These are **dev-only** — generate fresh ones for
production and set them in the platform dashboards.

**Still blank, pending step 3:** `SUPABASE_URL`, `SUPABASE_KEY`, `OPENAI_KEY`,
`DB_READONLY_URL`. The API won't boot until they're set, by design.

### 5. ⏳ Local end-to-end test — done except the search results themselves
- Start `api/` (`uvicorn app.main:app --reload`), start `web/` (`npm run dev`).
- Do a real search from the browser, confirm results render in `ResultsTable`,
  and confirm the UI looks like the original (decision 5) — this is a
  regression check, not just a functionality check.
- Separately, call `POST /v1/search` directly (e.g. via `curl` or `httpx`)
  with an `AGENT_API_KEYS` value, confirm it works standalone without the
  frontend involved at all — that's the point of it being an external API.
- Confirm `/molecules`, `/receptors`, `/diseases`, `/oracle` 404 rather than
  serving stale content (they shouldn't exist at all in this build).

**Outcome:** both apps were booted together (the API with placeholder values
for the four blanks) and driven from a real browser.
- ✅ `/`, `/search`, `/about`, `/learn` all render, no console errors, UI
  matches the original HiveBlot design (nav, hero, hex background, search box).
- ✅ `/molecules`, `/receptors`, `/diseases`, `/oracle` all 404.
- ✅ Typing a query and pressing Enter fires **exactly one** `POST
  /api/search` (debounce holding), which reaches the backend's internal
  `/search` authenticated — the backend logged a 502 from the placeholder
  OpenAI key, not a 401. The full browser → BFF → backend chain is wired
  correctly, and the UI degrades to "Error: Search failed" rather than
  crashing.
- ⏳ **Not yet done:** results actually rendering in `ResultsTable`, and the
  standalone `POST /v1/search` call returning real rows. Both need a live
  Supabase project and OpenAI key. The auth/rate-limit half of the `/v1/search`
  standalone check is already covered — see step 6.

### 6. ⏳ Security verification (don't skip this — it's the whole point of the rebuild)
- Call `/search` with no `Authorization` header → expect 401. Same for
  `/v1/search`.
- Call `/search` (or `/v1/search`) with a query engineered to make GPT emit
  SQL touching another table (e.g. ask something like "show me all users and
  their emails") → confirm `sql_guard` rejects it (400), not that it
  silently returns empty.
- Confirm an `INTERNAL_API_KEY` does **not** work against `/v1/search`, and
  an `AGENT_API_KEYS` value does **not** work against `/search` — the two
  auth sets must not accidentally overlap in practice.
- Hammer `/search` past `SEARCH_RATE_LIMIT`, and `/v1/search` past
  `AGENT_RATE_LIMIT` independently → expect 429s from each without one
  affecting the other's budget.
- Confirm the DB connection used for search really is `hive_readonly` (not
  the Supabase service key) by checking `DB_READONLY_URL` in `.env` and
  trying (from `psql`, as that role) to `SELECT` from a different table or
  `INSERT` into `western_blot_records` — both should fail with a permission error.

**Outcome — verified live against a running server, and locked in as tests:**
- ✅ `/search` and `/v1/search` both 401 with no header, a junk key, or a
  malformed header. `/proteins` 401s too. `/health` stays public.
- ✅ The key sets don't overlap in practice: `INTERNAL_API_KEY` → 401 against
  `/v1/search`, and an `AGENT_API_KEYS` value → 401 against `/search`.
- ✅ Independent rate limits: the agent budget (`10/minute`) returned 429 once
  spent, while `/search` kept serving on its own `20/minute` budget.
- ✅ CORS returns no `access-control-allow-origin` for an arbitrary origin and
  the exact origin for a configured one — not `*`.
- ✅ Error bodies don't leak upstream detail (a failed OpenAI call surfaces as
  `{"detail":"Failed to generate search query"}`, not the provider's error).
- ✅ The SQL-injection-via-prompt case is covered at the unit level instead:
  `test_sql_guard.py` proves a query touching `auth.users` — directly, via
  JOIN, via subquery, or via CTE — is rejected with a 400-mapped
  `SQLGuardError`, never silently emptied.
- ⏳ **Not yet done, needs live infra:** driving that same rejection through a
  real GPT call ("show me all users and their emails"), and the `psql` check
  that `hive_readonly` genuinely can't read another table or insert. That
  second one is defense layer 2 and can't be inferred from the code — **do it
  by hand once the Supabase project exists.**

### 7. ✅ Repo hygiene check before/after first push
- Confirm `.git` doesn't contain `.next/`, `node_modules/`, or any `.env` file
  (`git ls-files | grep -E '\.env$|\.next/|node_modules/'` should be empty).
- Confirm no stray debug/prompt files got copied over from the old repos.

**Outcome:** clean. `git ls-files | grep -E '\.env$|\.next/|node_modules/'` is
empty, `.git` is 2.1MB (the old repo was 62MB), and the only committed binaries
are `hive.png` and `hive-background.mp4` — both actually referenced by
`app/page.tsx`. No stray prompt/debug files. Removed the five unreferenced
`create-next-app` placeholder SVGs (`next`, `vercel`, `file`, `globe`,
`window`) that were still tracked in `web/public/`.

### 8. ⏳ Deploy — needs your Render/Vercel accounts
- `api/` → new Render (or equivalent) web service, root `api/`, start command
  `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, all env vars from step 4
  set in the platform's dashboard (never committed).
- `web/` → new Vercel project, root `web/`, `API_BASE_URL` set to the deployed
  API's URL, `INTERNAL_API_KEY` matching, `ALLOWED_ORIGINS` on the API updated
  to the real Vercel URL once you have it (not `*`).
- Smoke test the production URLs the same way as step 5, including a direct
  `/v1/search` call from outside the frontend.
- Whatever agent/integration is meant to call `/v1/search` in production
  should get its own dedicated entry in `AGENT_API_KEYS`, not share one
  generic key with everything else that might call it later.

### 9. ⏳ Once verified, decide what happens to the old repos/services
`QBI` and `blot_backend` (and their Vercel/Render deployments) still exist and
are still live with the unauthenticated raw-SQL endpoint until you take them
down or repoint DNS/domains. Flag this to whoever owns those deployments —
rebuilding `hive` doesn't retire the old vulnerable one automatically.
