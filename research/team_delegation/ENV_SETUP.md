# Team Local Development — ENV Setup

**Rule zero: this file, and the repo, contain variable NAMES only. Values live
in your local `.env` files (gitignored) or come from Nik through a secure
channel. Never commit a `.env`, never paste a value into chat/Slack/WhatsApp,
never screenshot one.**

Work happens on the **`feature/bio-context-beta`** branch. `main` predates the
beta — clone the repo and `git checkout feature/bio-context-beta` first.

---

## 1. Do you need ENV at all?

| Teammate | Workstream | Needs ENV? | What |
|---|---|---|---|
| **Suhas** | Search / data integrity / API / infra (D) | **Yes** | Full local stack (self-generated values) + ONE cloud read-only credential from Nik |
| **Ananya** | Biology QA (A) + search/CS support (D) | **Only if running the local stack** | Biology QA is done on the live site in a browser — zero ENV. For CS support: full local stack, self-generated values, no secrets from Nik |
| **Srushti** | Product / UX (C) | **Only if running the local stack** | Mockups + live-site review need zero ENV. To see UI changes locally: local stack, self-generated values, no secrets from Nik |
| **Tanvi** | Scientific communication (B) + biology support (A) | **Mostly no** | Copy drafting for `/about` and `/learn` can use the local stack too (the pages are in `web/app/`); self-generated values, no secrets from Nik |
| **Yashvi** | Coordination | **No** | Live site in a browser only |
| **Nik** | Owner / integration / deploy | Already has everything | Sole holder of all production credentials |

**Key point: the local stack requires ZERO production secrets.** The repo
ships an embedded local Postgres (`scripts/local_db.py`) seeded with the same
475 reviewed rows the hosted beta serves. Every value in a local `.env` is
either non-secret or generated on your own machine.

---

## 2. Variable classification

| Variable | Class | Who gets it |
|---|---|---|
| `API_BASE_URL`, `ALLOWED_ORIGINS`, `SEARCH_RATE_LIMIT`, `AGENT_RATE_LIMIT`, `SUPABASE_TABLE`, `WBM_PDF_DPI`, `WBM_MIN_*`, `NCBI_EMAIL` | safe / non-secret | anyone; defaults are fine |
| `INTERNAL_API_KEY` (local), `AGENT_API_KEYS` (local) | locally generated secret | each teammate generates their OWN on their machine; never shared, never production's |
| Local `DB_READONLY_URL` / `DB_FEEDBACK_URL` (from `scripts/local_db.py status`) | local, passwordless (trust auth on a local socket) | anyone running the local stack |
| **Cloud `DB_READONLY_URL`** (`hive_readonly` role on the beta Supabase) | project read-only credential | **Suhas only**, from Nik, secure channel |
| Cloud `SUPABASE_URL`, `SUPABASE_KEY` | production sensitive | nobody (not needed locally — leave empty) |
| Production `INTERNAL_API_KEY`, `AGENT_API_KEYS`, `VERCEL_OIDC_TOKEN` | production sensitive | nobody |
| Cloud `DB_FEEDBACK_URL` (`hive_feedback`, INSERT-capable) | **write-capable sensitive** | **nobody, ever** — a leak lets anyone write rows into the production feedback table, which is the beta's primary metric |
| `ANTHROPIC_API_KEY`, `OPENAI_KEY`, `WBM_VLM_API_KEY`, `NCBI_API_KEY`, AWS credentials | personal / model credential | nobody — Nik's personal keys are never distributed. Model automation is NOT part of any current task; if it becomes one, use your own key or ask Nik for a separate project-scoped key with its own budget and revocation |

---

## 3. Local stack setup (everyone who runs code)

From repo root, on `feature/bio-context-beta`:

```bash
# 1. Python env + local database (real Postgres, no Docker, no cloud)
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-local.txt
.venv/bin/python scripts/local_db.py up
.venv/bin/python scripts/local_db.py load eval/demo/*/supabase_rows.json
.venv/bin/python scripts/local_db.py status   # prints row counts + the local DSNs
```

`requirements-local.txt` includes the production API dependencies plus
`pgserver`, the local-only package that starts the embedded Postgres database.
Render still installs `api/requirements.txt`; production does not need
`pgserver`.

```bash
# 2. api/.env — copy the example, then fill as below
cp api/.env.example api/.env
```

In `api/.env`:

- `SUPABASE_URL=`, `SUPABASE_KEY=`, `OPENAI_KEY=` — **leave empty.** The
  search path runs on the deterministic parser + asyncpg; PostgREST-only
  endpoints are not needed for any current task.
- `DB_READONLY_URL=` — the read-only DSN printed by `local_db.py status`.
- `DB_FEEDBACK_URL=` — the feedback DSN from `status` if you need the feedback
  endpoints locally; empty is fine (they return 503, everything else works).
- `INTERNAL_API_KEY=` — generate your own:
  `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`
- `AGENT_API_KEYS=` — generate a second throwaway the same way (required to be
  non-empty; you will likely never use it).
- Everything else: keep the example defaults.

```bash
# 3. web/.env — copy the example
cp web/.env.example web/.env
```

In `web/.env`:

- `API_BASE_URL=http://localhost:8000`
- `INTERNAL_API_KEY=` — the SAME value you generated for `api/.env`. This pair
  only authenticates your local web process to your local API; it has no
  relationship to production's key.

```bash
# 4. Run
cd api && ../.venv/bin/uvicorn app.main:app --reload    # terminal 1
cd web && npm install && npm run dev                     # terminal 2
# open http://localhost:3000, search: phospho STAT3 Tyr705
```

Expected: the seven flagship searches return the same shapes as the hosted
beta (18/3, 14/4, 18/3, 10/2, 31/5, 20/4, 0).

---

## 4. Suhas only — cloud read-only access

For data-integrity work that must be verified against the **production** rows
(e.g. the `image_crop_ref` audit), Nik provides the cloud `DB_READONLY_URL`
through a secure channel (see §6). What it is:

- The `hive_readonly` Postgres role on the beta Supabase project, connecting
  through the session pooler.
- Permissions, verified in the session-12 audit: `SELECT` on
  `western_blot_records` only. No INSERT/UPDATE/DELETE anywhere, no grants on
  `hiveblot_feedback`, not superuser, no createrole/createdb/bypassrls.
  Worst case if leaked: someone reads the 475 reviewed rows — data the public
  site already serves — or burns free-tier connection quota. Nik rotates one
  password to revoke.
- Use it **read-only by construction and by convention**: put it in
  `DB_READONLY_URL`, or query it directly with `psql`. Do not broaden its
  grants, do not use it in scripts that attempt writes.
- Default to the local DB anyway; reach for the cloud DSN only when the
  question is specifically about production state.

Nobody else needs this. Ananya's CS-support work runs against the local DB
(same rows).

---

## 5. What must never be committed

Already enforced by `.gitignore` (`api/.env*`, `web/.env*`,
`western_blot_miner/.env*` — examples excepted). Still, the rules:

- No `.env` file, ever, under any name (`.env.cloud`, `.env.local`,
  `.env.backup`…).
- No connection strings, keys, or tokens in code, tests, docs, HANDOFF,
  commit messages, or PR bodies. **Names only** — this is an existing HANDOFF
  rule.
- No secrets in screenshots attached to findings.
- If a secret ever lands in a commit — even unpushed — tell Nik immediately;
  the fix is rotation + history rewrite, not a follow-up commit deleting it.

---

## 6. How Nik delivers the one real credential

Preferred, in order:

1. **Password manager secure share** (1Password/Bitwarden shared vault or a
   one-time secret link) — auditable, revocable, no plaintext residue.
2. **AirDrop of a minimal file, in person** — then the recipient moves the
   value into `api/.env` and deletes the file.

Never WhatsApp/iMessage/email/Slack plaintext. The prepared per-teammate
bundles live OUTSIDE this repo on Nik's machine (see
`~/hiveblot-env-handoff/`), mode 0600, delete after delivery.
