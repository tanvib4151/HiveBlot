# HiveBlot beta — deployment guide (no secrets in this file)

The beta is three pieces: **Postgres** (Supabase in prod, embedded pgserver
locally), **FastAPI** (`api/`), **Next.js** (`web/`). Everything below is
config + commands; all secret VALUES live in env vars / `.env` files only.

**The canonical beta stack is zero-cost and must stay that way:**

| Piece | Host | Plan |
|---|---|---|
| Postgres | Supabase `zafombwswztvnjikcsdm` | **Free** |
| FastAPI (`api/`) | **Render Web Service** (Docker, `render.yaml`) | **Free** |
| Next.js (`web/`) | **Vercel** | **Free (Hobby)** |

Never select Render Starter/Standard/Pro or a paid Vercel plan. `render.yaml`
pins `plan: free`; changing that line starts billing.

**Live URLs**

| | |
|---|---|
| Web | **https://hiveblot-beta.vercel.app** |
| API | **https://hiveblot-api.onrender.com** (Render free Web Service `hiveblot-api`, `srv-da1rbvs9v7es738635ug`) |

## 0. Which Supabase project

| | |
|---|---|
| **Beta project ref** | `zafombwswztvnjikcsdm` |
| **Project URL** | `https://zafombwswztvnjikcsdm.supabase.co` |
| Region / engine | us-east-1 · Postgres 17.6 |
| Status | **schema applied + seeded (475 rows)** — see `HANDOFF.md` |

> **The old hackathon project `QIB` (`belalrbfrndxvdwvjxte`) is NOT a
> deployment target and never will be.** Never point `supabase link`,
> `db push`, `seed_remote.py`, or any DSN at it. Its migration history is
> empty, so a `db push` there would alter Suhas's production tables. Background:
> `research/supabase_legacy_audit.md`, `research/supabase_beta_table_plan.md`.

**Connect through the pooler, not the direct host.** `db.<ref>.supabase.co`
resolves **IPv6-only**, which many container hosts cannot reach. Use Supavisor
**session mode** (port 5432 — transaction mode on 6543 breaks asyncpg's
prepared statements), with the `role.projectref` username form:

```
postgresql://<role>.zafombwswztvnjikcsdm:<password>@aws-0-us-east-1.pooler.supabase.com:5432/postgres
```

## 1. Database — first-time setup on a fresh project
Canonical flow: the Supabase CLI against `supabase/migrations/` (timestamped
copies of the canonical SQL; a pytest drift guard keeps them byte-identical —
edit the canonical files and run `scripts/sync_supabase_migrations.py`, never
edit the copies).

```bash
supabase login                                # once per machine
supabase link --project-ref zafombwswztvnjikcsdm
supabase db push --dry-run                    # review: 4 migrations, additive
supabase db push                              # base schema + 001 + 002 + 003
```
Both restricted roles are created **by the migrations themselves** (there is no
`supabase/roles.sql`): `hive_readonly` in the base schema, `hive_feedback` in
`002`. Give them passwords afterwards — generated values, never reused. Keep the
statement out of shell history by putting it in a `chmod 600` file:

```bash
supabase db query --linked -f /path/to/roles.sql   # then delete the file
```
```sql
ALTER ROLE hive_readonly WITH PASSWORD '<generated>';
ALTER ROLE hive_feedback WITH PASSWORD '<generated>';
```
Verify with `SELECT rolname, rolpassword LIKE 'SCRAM-SHA-256%' FROM pg_authid
WHERE rolname LIKE 'hive%';` — `pg_roles.rolpassword` always reads non-null and
proves nothing; `pg_authid` is the authoritative source.

Then seed the reviewed corpus (idempotent per paper). `seed_remote.py` needs
INSERT/DELETE, which neither restricted role has by design, so use the project
owner's connection string — or a temporary role you drop immediately after:

```bash
export SEED_DATABASE_URL='<owner connection string>'   # NOT a restricted role
.venv/bin/python scripts/seed_remote.py eval/demo/*/supabase_rows.json
.venv/bin/python scripts/seed_remote.py --check                 # expect 475 rows
```
Fallback (no CLI): run the four canonical files in the SQL editor in order —
`api/db/schema.sql`, `migrations/001_evidence_record.sql`,
`migrations/002_feedback.sql`, `migrations/003_stable_row_key.sql` — then
passwords + seed as above. Do NOT run both the CLI flow and the SQL-editor
flow; everything is idempotent, but pick one.

**Security invariants (encoded in the SQL; verified on the beta project):**
`hive_readonly` = SELECT-only on evidence + feedback. `hive_feedback` =
INSERT+SELECT on `hiveblot_feedback` ONLY (+ its id sequence) — it holds **no
grant of any kind on `western_blot_records`** and cannot UPDATE or DELETE
anything. Neither restricted DSN ever reaches browser JavaScript: both live in
API-server env vars; the web app talks only to the API through the Next.js
server-side proxy with `INTERNAL_API_KEY`.

## 2. API (`api/`, FastAPI) — Render free Web Service
`render.yaml` is a committed Blueprint; it is the canonical deployment path.

**Routine deploy (CLI, service already exists).** `autoDeploy` is off, so a
push does not ship. Deploy an explicit commit and confirm it went live:

```bash
render deploys create srv-da1rbvs9v7es738635ug --commit <sha> --confirm -o json
render deploys list srv-da1rbvs9v7es738635ug --confirm -o json   # status must read "live"
curl -s https://hiveblot-api.onrender.com/health                 # {"status":"ok"}
```
`render deploys list` takes no `--limit`; the newest deploy is the first entry.

**First-time deploy (Render dashboard, ~2 minutes):**
1. **New → Blueprint**, authorize GitHub if asked, pick **`nikhilesh-s/hive`**,
   branch **`feature/bio-context-beta`**.
2. Render reads `render.yaml` and proposes one web service, `hiveblot-api`,
   already on the **Free** plan. Do not change the plan.
3. It then prompts for the four `sync: false` secrets — paste them from the
   untracked `api/.env.cloud`: `DB_READONLY_URL`, `DB_FEEDBACK_URL`,
   `SUPABASE_KEY`, `INTERNAL_API_KEY`. Everything else is already in the file.
4. **Apply**. First build takes a few minutes (Docker image, ~6 MB of crops).

Health check is `/health`; `autoDeploy: false`, so later pushes deploy only
when you click **Manual Deploy**.

The image is host-agnostic — Fly.io, Cloud Run, EC2 or a local `docker run`
work with the same file. Railway also works and was the earlier plan; it is no
longer the recommended path because Render's free Web Service costs nothing.

```bash
docker build -f api/Dockerfile -t hiveblot-api .   # context = REPO ROOT
```
- Run: `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (the image's default
  CMD, falling back to 8000 locally, so the same image runs in both places;
  Render injects `PORT`). Deps `api/requirements.txt`, Python 3.13 in the image.
- Health check: `GET /health` (no auth)
- Env NAMES (exact, from `api/app/config.py` — never commit values):
  required: `SUPABASE_URL`, `SUPABASE_KEY` (may stay empty → only `/proteins`
  and `/` degrade), `OPENAI_KEY` (empty ⇒ deterministic bio_query search),
  `DB_READONLY_URL` (hive_readonly pooler DSN), `DB_FEEDBACK_URL`
  (hive_feedback pooler DSN), `INTERNAL_API_KEY`, `AGENT_API_KEYS`,
  `ALLOWED_ORIGINS` (the deployed web origin);
  optional with defaults: `SEARCH_RATE_LIMIT`, `AGENT_RATE_LIMIT`,
  `TABLE_NAME`, `MAX_SEARCH_LIMIT`, `CROP_BASE_DIR` (set by the image),
  `OPENAI_MODEL`. Model-provider vars (`WBM_LLM_BACKEND`, `AWS_*`,
  `ANTHROPIC_API_KEY`) belong to the INGESTION engine later, not to this API.

### Render free-tier behaviour — accepted, not worked around
- **The service spins down after ~15 minutes idle.** The next request pays a
  cold start, typically 30–60 s. Expect the first search of a session to hang
  briefly; it is not a bug and it is not a reason to change the architecture.
  Warn testers rather than adding a keep-alive pinger.
- **The filesystem is ephemeral** — anything written at runtime is lost on
  redeploy or spin-down. This is safe here because **the API never writes to
  disk at runtime** (audited: no `open(...,'w')`, no `mkdir`, no temp files in
  `api/app/`). **Supabase is the only persistence layer**, including all
  researcher feedback. Figure crops are read-only and baked into the image.
- **No shell/disk add-on on free.** Anything you would want to persist has to
  go in Postgres.
- Rate limiting is in-process (slowapi), so it is per-instance.

**Figure crops in the container.** Records store an ABSOLUTE `image_crop_ref`,
and `/records/{id}/crop` requires the path to resolve inside `CROP_BASE_DIR`, so
the image reproduces the authoring path verbatim — crops serve with zero code
change and, more importantly, **zero change to the reviewed corpus**.
`api/crops/` (21 files, ~6 MB) is **tracked in git on purpose**: Render builds
from the GitHub clone, so an untracked directory would mean no figure evidence
in the hosted beta. Refresh it with `python scripts/stage_crops.py`. Storing
crop refs *relative* to `CROP_BASE_DIR` is the cleaner long-term fix and is
tracked in `HANDOFF.md`.

## 3. Web (`web/`, Next.js) — Vercel free
Already deployed: project `hiveblot-beta`, production alias
**https://hiveblot-beta.vercel.app**. The Vercel project root is `web/`.

```bash
cd web
vercel link --yes --project hiveblot-beta     # once per machine
vercel deploy --prod --yes
```
- Vercel marks these **Sensitive**, which makes them write-only: `vercel env
  pull` returns the literal `[SENSITIVE]`, not the value. The readable source
  of truth is the untracked `api/.env.cloud`. Changing a value means
  `vercel env rm` then `vercel env add`, then a redeploy.
- Env (Production + Preview + Development), set with `vercel env add`:
  `API_BASE_URL` = the Render API origin, `INTERNAL_API_KEY` = the same value
  the API has. Both are read only in server-side route handlers; nothing
  secret ships to the browser. **Never prefix either with `NEXT_PUBLIC_`** —
  that publishes it to every visitor.
- After changing an env var you must **redeploy** (`vercel deploy --prod
  --yes`); Vercel does not hot-swap env values into an existing build.
- Keep `ALLOWED_ORIGINS` on the API in sync with this origin.

## 4. Smoke test after deploy
1. `GET <api>/health` → `{"status":"ok"}`
2. Web UI: type `phospho STAT3 Tyr705`, press Enter/SEARCH → 3 grouped
   experiment cards (18 lane records), STAT3 · phospho-Tyr705, Hep3B,
   CST #9145, expected 88.1 kDa. Corpus-wide the reviewed set is **475 rows /
   93 experiments** — cards are grouped by the experiment identity hash
   (`stable_row_key` before the `:`), which is the same identity researcher
   feedback keys to.
3. Search `co-IP PIK3CA` → co-IP cards with IP bait = PIK3CA
4. Search `GAPDH mouse` → 5 experiments, Loading Control, DEVELOPMENTAL SERIES
   on the E14.5/P0/P28 panels and **no** design tag on the ligation panels
5. Search `P-ERK` → `MAPK1/MAPK3` + **Conflicting**; the modification must stay
   unsettled with both competing claims shown and no winner
6. Search `BRCA1 MCF7 olaparib` → 0 results with the scoped "current HiveBlot
   beta dataset (3 reviewed papers)" copy
7. Expand a card → evidence panel loads (`GET /records/{id}` via web proxy)
8. Crop endpoint: `GET /records/{id}/crop` → PNG where the crop archive is
   deployed; clean 404 + text-only evidence panel where it is not
9. Click 👍 on a field → row appears in `hiveblot_feedback` (feedback role);
   reload the page → the feedback rehydrates beside the field
10. Typing must fire **no** request — only Enter/SEARCH submits
11. CORS: browser devtools show no blocked API calls (`ALLOWED_ORIGINS` = web
    origin; the browser only ever talks to the Next.js proxy)
12. No secrets client-side: view-source/devtools network — no DSNs, no
    `INTERNAL_API_KEY`, no Supabase key in any browser-delivered asset

## Local development (no cloud at all)
```bash
.venv/bin/python scripts/local_db.py up
.venv/bin/python scripts/local_db.py load eval/demo/*/supabase_rows.json
cd api && .venv/bin/python -m uvicorn app.main:app --port 8000
cd web && npm run dev
```

## Local API against the CLOUD database
Keep cloud config in `api/.env.cloud` (untracked — `api/.gitignore` has
`.env.*`) and let real env vars override the committed `.env` defaults:
```bash
cd api && set -a && . ./.env.cloud && set +a && .venv/bin/python -m uvicorn app.main:app --port 8010
```
Point the web app at it with `web/.env.local` (also untracked):
`API_BASE_URL=http://127.0.0.1:8010` + the matching `INTERNAL_API_KEY`.

## Known deployment gaps (deliberate, documented)
- Crop refs are absolute paths; the container reproduces the authoring path.
  Relative refs + a join against `CROP_BASE_DIR` is the tracked follow-up.
- `/proteins` and `/` require real Supabase (PostgREST); `/search`,
  `/records/{id}`, `/feedback` run on plain Postgres.
- Rate limiting is in-process (slowapi); it is per-instance, so it weakens if
  the API is scaled to multiple instances.
- Render free spins down when idle; the first request after that is slow. This
  is documented for testers rather than engineered around.
