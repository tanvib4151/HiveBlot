# Beta-table plan — `western_blot_records_beta` / `blot_results_beta` in `QIB`

**Date:** 2026-08-17 · **Auditor:** Claude Code (Opus 5) · **Mode:** READ-ONLY
**Project:** `QIB` (`belalrbfrndxvdwvjxte`), org SuhasKM's-Org, us-west-2, PG 17.6
**Branch of record:** `feature/bio-context-beta`
**Companion doc:** [`research/supabase_legacy_audit.md`](supabase_legacy_audit.md)

**Scope honoured.** Inspection and planning only. Nothing was altered: no DDL,
no migration, no seed, no write of any kind — against the beta tables or
anything else. `public.western_blot_records` and `public.blot_results` were
re-verified untouched at 616 and 2 rows.

> **Recommendation, stated plainly: do not use the beta tables. Wait for
> Srushti's separate HiveBlot project.** The blocker is not effort — it is that
> `western_blot_records_beta` **cannot be made to work without modifying
> production-level objects you have been told not to touch.** HiveBlot's
> `/search` path requires the `hive_readonly` role and `/feedback` requires
> `hive_feedback`; roles are **cluster-wide**, not per-table, and neither
> exists in `QIB`. The trigram index needs `CREATE EXTENSION pg_trgm`, which is
> **database-wide**. Both land outside the two beta tables, in the production
> database, against an explicit "do not modify production roles" constraint.
> Everything below is the evidence for that conclusion.

---

## 1. Current beta-table state

### 1.1 They exist, they are empty, and they are exact structural copies

`public` now holds **four** tables. Both beta tables are visible through
PostgREST and return HTTP 200 with an empty array.

| Table | Rows | Table size | Index size |
|---|---:|---:|---:|
| `western_blot_records` (production) | **616** | 128 kB | 32 kB |
| `blot_results` (production) | **2** | 16 kB | 32 kB |
| `western_blot_records_beta` | **0** | 8 kB | 8 kB |
| `blot_results_beta` | **0** | 16 kB *(idx)* / 8 kB *(table)* | 16 kB |

**Neither beta table contains any data.** Exact counts taken with
`Prefer: count=exact`; both returned `Content-Range: */0` for both the `anon`
and `service_role` keys.

Minor observation, not load-bearing: each beta table has **8 kB allocated
despite 0 live rows**. A never-written PostgreSQL table occupies 0 pages, so a
page was allocated at some point — consistent with rows having been inserted
and deleted, or with an aborted insert. Harmless either way, and irrelevant
under the recommendation below.

### 1.2 Exact schema — `western_blot_records_beta`

| # | Column | Type | Null? | Default |
|---|--------|------|-------|---------|
| 1 | `id` | `bigint` | not null | **PK** — see the sequence caveat in §1.5 |
| 2 | `paper_id` | `text` | **not null** | — |
| 3 | `page` | `integer` | null | — |
| 4 | `western_blot_type` | `text` | null | — |
| 5 | `sample` | `text` | null | — |
| 6 | `organism` | `text` | null | — |
| 7 | `treatment_context` | `text` | null | — |
| 8 | `figure_label` | `text` | null | — |
| 9 | `target` | `text` | null | — |
| 10 | `condition` | `text` | null | — |
| 11 | `band_detected` | `boolean` | null | — |
| 12 | `confidence` | **`text`** | null | — |

**Indexes:** `western_blot_records_beta_pkey (id)` — and nothing else.
**Constraints:** primary key on `id`, `NOT NULL` on `paper_id`. No CHECK
constraints, no unique constraints, **no foreign keys**.

### 1.3 Exact schema — `blot_results_beta`

| # | Column | Type | Null? | Default |
|---|--------|------|-------|---------|
| 1 | `id` | `bigint` | not null | **PK** |
| 2 | `protein_target_name` | `text` | **not null** | — |
| 3 | `cell_line_tissue` | `text` | null | — |
| 4 | `treatment_condition` | `text` | null | — |
| 5 | `antibody_source_catalog` | `text` | null | — |
| 6 | `loading_amount` | `text` | null | — |
| 7 | `normalization_method` | `text` | null | — |
| 8 | `is_loading_control` | `boolean` | null | **`false`** |
| 9 | `molecular_weight` | `text` | null | — |
| 10 | `image_confidence` | `text` | null | — |
| 11 | `bands` | `jsonb` | null | — |
| 12 | `figure_label` | `text` | null | — |
| 13 | `figure_caption` | `text` | null | — |
| 14 | `pmid_doi` | `text` | null | — |
| 15 | `source_paper` | `text` | null | — |
| 16 | `created_at` | `timestamptz` | null | **`now()`** |

**Indexes:** `blot_results_beta_pkey (id)` and
`blot_results_beta_lower_idx` on `lower(protein_target_name)`.
**Constraints:** PK on `id`, `NOT NULL` on `protein_target_name`, no FKs.

### 1.4 Are they copies of the legacy production tables? — **Yes, exactly**

Diffed field-by-field against the production tables audited yesterday:

| Comparison | Result |
|---|---|
| `western_blot_records` vs `..._beta` — column names **and order** | **identical** |
| — types | **identical** (including `confidence text`) |
| — defaults | identical |
| — nullability / `required` set | identical |
| `blot_results` vs `..._beta` — names, order, types, defaults, nullability | **identical** |

Only the index *names* differ: production's hand-named `idx_protein` appears on
the copy as the auto-generated `blot_results_beta_lower_idx`. That naming
pattern is what `CREATE TABLE … (LIKE … INCLUDING ALL)` produces, which is the
most likely way these were made (a plain `CREATE TABLE AS SELECT` would have
copied neither the primary key nor the functional index).

**Consequence that matters:** `western_blot_records_beta` inherits **every**
gap catalogued in the legacy audit. It is not a HiveBlot table with no rows —
it is a copy of a 2026-06-28 hackathon table with no rows, carrying the same
`confidence text` divergence and missing all 61 Evidence Record columns.

### 1.5 Two things inspection could not settle (verify before any use)

Neither can be answered read-only through PostgREST, and both would need a SQL
console. Listed for completeness; neither changes the recommendation.

1. **Does `id` have its own sequence?** PostgREST reports `id` as a
   not-null primary key but does not expose whether a default exists. If the
   tables were made with `LIKE … INCLUDING ALL`, a `bigserial` column's copied
   default may still reference the **original table's sequence**
   (`western_blot_records_id_seq`). If so, every insert into the beta table
   **advances production's id counter** — a real, if minor, mutation of a
   production object, and exactly the kind of leak the beta tables were meant
   to prevent. Read-only check:
   ```sql
   SELECT table_name, column_name, column_default, is_identity
   FROM information_schema.columns
   WHERE table_name IN ('western_blot_records_beta','blot_results_beta')
     AND column_name = 'id';
   ```
2. **RLS and policies.** Both beta tables answer `anon` reads with HTTP 200 and
   an empty array, which proves `anon` holds a **SELECT grant** but cannot
   distinguish "RLS disabled" from "RLS enabled with no policy" — on an empty
   table both return `[]`. `LIKE` does not copy RLS enablement, and the parent
   tables are anon-readable (legacy audit §6), so RLS is *probably* off on
   both; treat that as an inference, not a finding. Read-only check:
   ```sql
   SELECT relname, relrowsecurity, relforcerowsecurity
   FROM pg_class WHERE relname LIKE '%_beta';
   SELECT * FROM pg_policies WHERE tablename LIKE '%_beta';
   ```
   Write privileges for `anon` were **not** probed, on either the beta or the
   production tables — any probe would have been a write.

### 1.6 What is still absent from the project entirely

- **No `hiveblot_feedback` table, and no `hiveblot_feedback_beta`.** `public`
  contains exactly the four tables above.
- **No `hive_readonly` role. No `hive_feedback` role.** Re-verified against the
  full server role list: `QIB` carries only stock Supabase roles (`postgres`,
  `anon`, `authenticated`, `service_role`, `authenticator`, `supabase_*`,
  `pg_*`, `dashboard_user`, `pgbouncer`) plus `cli_login_postgres`, the
  temporary login role the CLI provisioned during yesterday's audit.
- **Migration history is still empty** — all four local migrations unapplied.
- **`pg_trgm` extension state is unverified**; the trigram index it exists to
  support is definitively absent from every table.

---

## 2. Differences from current canonical HiveBlot

Canonical set as of `b4e1ade`. Note the numbering: the repo's canonical files
are `api/db/schema.sql` + `migrations/001` + `002` + `003`, and the CLI copies
in `supabase/migrations/` are timestamped `…0001`–`…0004`. **"Migration 004"
(`20260701000004_stable_row_key.sql`) is the CLI copy of canonical `003`** —
there is no fifth migration. A pytest drift guard
(`api/tests/test_supabase_migrations_sync.py`) asserts the four pairs are
**byte-identical**.

### 2.1 Missing columns — 61 of them

`western_blot_records_beta` has **12** columns. Canonical has **73**
(12 base + 60 from migration 001 + `stable_row_key` from 003).

**Missing, from migration 001 (60):** `pmid`, `pmcid`, `doi`, `title`,
`authors`, `source_url`, `panel_label`, `figure_caption`, `image_crop_ref`,
`raw_target_name`, `canonical_target`, `uniprot_id`, `aliases_used_in_paper`,
`protein_status`, `modification_type`, `residue`, `residue_position`,
`modification_label`, `modification_status`, `phospho_specific_antibody`,
`experiment_type`, `experiment_flags`, `experiment_type_confidence`,
`experiment_type_evidence`, `cell_line`, `tissue`, `genotype`,
`treatment_name`, `dose`, `dose_unit`, `duration`, `duration_unit`,
`antibody_target`, `antibody_vendor`, `antibody_catalog_number`,
`antibody_clone`, `antibody_dilution`, `antibody_source_evidence`,
`band_state`, `lane_condition`, `loading_control`,
`reported_molecular_weight_kda`, `expected_molecular_weight_kda`,
`molecular_weight_source`, `provenance`, `validation`, `anomaly_flags`,
`needs_review`, `extraction_stage`, `extraction_model`, `extraction_version`,
`raw_intensity`, `background_corrected_intensity`, `normalized_intensity`,
`band_width_px`, `band_height_px`, `band_area_px`, `smearing_score`,
`saturation_flag`, `densitometry_source`.

**Missing, from migration 003 (1):** `stable_row_key`.

**Extra columns in beta:** none.

### 2.2 Type mismatch — `confidence text` vs `real`

**One mismatch, and it is required to fix.** `api/db/schema.sql` declares
`confidence real`; the beta copy inherits production's `text`. The reviewed
seed carries `confidence` as a Python **float** (`0.9`), and
`scripts/seed_remote.py` inserts through asyncpg, which is strictly typed and
will reject a float bound to a `text` parameter. **Answer to Phase-2 question
2: yes, `confidence text → real` is required.** The fix itself is one line:

```sql
ALTER TABLE western_blot_records_beta
    ALTER COLUMN confidence TYPE real USING confidence::real;
```

Safe here precisely because the table is empty — the `USING` cast has nothing
to fail on. (Running the equivalent on production is out of the question and
is not proposed anywhere in this document.)

### 2.3 Missing indexes — 10

| Source | Index | On |
|---|---|---|
| `api/db/schema.sql` | `idx_western_blot_records_target` | GIN trigram on `target` — also needs `CREATE EXTENSION pg_trgm` |
| migration 001 | `idx_wbr_canonical_target` | `canonical_target` |
| migration 001 | `idx_wbr_modification` | `modification_type` |
| migration 001 | `idx_wbr_residue` | `(residue, residue_position)` |
| migration 001 | `idx_wbr_experiment_type` | `experiment_type` |
| migration 001 | `idx_wbr_vendor` | `antibody_vendor` |
| migration 001 | `idx_wbr_catalog` | `antibody_catalog_number` |
| migration 001 | `idx_wbr_cell_line` | `cell_line` |
| migration 001 | `idx_wbr_needs_review` | `needs_review` |
| migration 003 | `idx_wbr_stable_row_key` | `stable_row_key` |

Every one would need a renamed twin, since index names are database-unique and
`idx_wbr_*` would eventually collide if production is ever migrated properly.

### 2.4 Feedback support — absent entirely

Migration 002 creates `hiveblot_feedback` (16 columns, `BIGSERIAL` PK, a CHECK
constraint on `feedback_scope ∈ {field, record, missing_field, search, ui}`,
4 indexes), migration 003 adds `stable_row_key` + a 5th index. **None of it
exists in `QIB`, in beta form or otherwise.**

One helpful property: `hiveblot_feedback.record_id` deliberately carries **no
foreign key** to `western_blot_records` ("feedback must survive record
re-ingestion/deletes"). So a feedback table pointed at beta records creates no
cross-table dependency on production.

### 2.5 `stable_row_key` support — absent, but would work cleanly

`stable_row_key` is `<record-hash>:<lane_index>`, computed from the reviewed
observation data itself, and is what makes researcher feedback survive a
reseed (session 9 proved rehydration across a full reseed: feedback submitted
on id 4019 came back on id 4494). It is a plain `TEXT` column plus a b-tree
index on each of the two tables, with **no dependency on the table's name**.

**Answer to Phase-2 question 5: yes, `stable_row_key` works cleanly with a beta
table** — add the column to `western_blot_records_beta` and to whatever
feedback table is used, and rehydration behaves identically. It is the one
piece of this that ports with zero friction.

### 2.6 Role and security differences

| Requirement | Canonical | `QIB` today |
|---|---|---|
| `hive_readonly` (SELECT-only; the DSN `/search` runs LLM-generated SQL as) | required | **does not exist** |
| `hive_feedback` (INSERT+SELECT on the feedback table only, zero grants on records) | required | **does not exist** |
| `ALTER DEFAULT PRIVILEGES … GRANT SELECT` for `hive_readonly` | in base schema | not applied |
| RLS posture | not relied on — security is grant-based | anon holds SELECT on all four tables |

This is the crux. **Postgres roles are cluster-level objects, not table-level
ones.** `CREATE ROLE hive_readonly` in `QIB` is a change to the production
cluster's role set, and the base schema also issues
`GRANT CONNECT ON DATABASE postgres` and
`ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES` — the latter
silently making **every future table in `public`**, including production ones,
readable by the new role. Likewise `CREATE EXTENSION pg_trgm` is
database-scoped. None of these can be confined to two tables.

The task constraints say: do not modify *"any other existing production
table/schema"*, *"production roles/policies"*. Standing up HiveBlot against the
beta tables requires violating that. **There is no scoped-to-beta version of
these three objects.**

---

## 3. Safe migration plan **if** the beta tables were used anyway

Documented because it was asked for, and because it is the concrete basis for
the cost side of §4. **It is not recommended, and it requires an explicit new
exception from Suhas for the role and extension steps.**

### 3.1 The CLI migration path is unusable here — SQL editor only

`supabase db push` **cannot be used against `QIB` at all**, and this is not a
matter of care:

- Remote migration history is **empty**, so `db push` applies **every** file in
  `supabase/migrations/` — all four, which target `western_blot_records` and
  `hiveblot_feedback` by name. The base migration is
  `create table if not exists`, so it would not error on the existing
  production table; it would sail past and then `ALTER` it.
- The only way to stop that is `supabase migration repair --status applied`,
  which **writes production migration history** — explicitly forbidden.

So the beta route means abandoning the CLI flow this repo just built,
drift-guarded, and documented in `DEPLOYMENT.md` §1, and reverting to
hand-pasting SQL into the dashboard editor. Every future schema change to the
beta then has to be applied by hand, twice (once for beta, once eventually for
real), with no history and no drift guard.

### 3.2 Exact scoped changes required

A `_beta` fork of all four migrations — roughly 700 lines of SQL with every
identifier renamed:

1. **61 `ALTER TABLE western_blot_records_beta ADD COLUMN IF NOT EXISTS …`** —
   the 60 from migration 001 plus `stable_row_key` from 003.
2. **1 type change** — `confidence` → `real` (§2.2).
3. **`CREATE EXTENSION IF NOT EXISTS pg_trgm`** — ⚠️ **database-wide, not
   scopeable to beta.**
4. **10 renamed indexes** — `idx_wbr_*_beta`, plus the GIN trigram index on
   `target`.
5. **A beta feedback table** — see §3.4.
6. **`CREATE ROLE hive_readonly` and `CREATE ROLE hive_feedback`** —
   ⚠️ **cluster-wide, not scopeable to beta.** Passwords set separately.
7. **Grants, hand-narrowed to beta only** — and here the canonical SQL must be
   *edited*, not just renamed:
   - `GRANT SELECT ON western_blot_records_beta TO hive_readonly;`
   - `GRANT INSERT, SELECT ON hiveblot_feedback_beta TO hive_feedback;` plus
     its sequence
   - **omit** `ALTER DEFAULT PRIVILEGES … GRANT SELECT ON TABLES`, which would
     otherwise grant `hive_readonly` read access to future production tables
   - explicitly `REVOKE` anything the new roles inherit on the production
     tables, and verify with `information_schema.role_table_grants`

### 3.3 How to guarantee the production tables stay untouched

If this route were taken anyway, these are the non-negotiable guards:

- **Never run `supabase db push` / `db pull` / `db reset` / `migration repair`
  against `belalrbfrndxvdwvjxte`.** Keep the `_beta` SQL **out of**
  `supabase/migrations/` so it cannot be swept up by a push.
- **Every statement names a `_beta` table.** Review the fork with
  `grep -n 'western_blot_records\b\|blot_results\b\|hiveblot_feedback\b'` and
  require **zero** non-`_beta` hits before running anything.
- **Wrap each script in `BEGIN; … COMMIT;`** and run `SELECT count(*)` against
  both production tables immediately before and after — expect 616 and 2.
- **Verify the id sequence** (§1.5 check 1) before the first insert; if the
  beta default points at production's sequence, give the beta table its own
  before writing anything.
- **Verify grants after roles exist:** query
  `information_schema.role_table_grants` for `hive_readonly` / `hive_feedback`
  and require **zero** rows naming `western_blot_records` or `blot_results`.
- **Seed with a `_beta`-only DSN** and never with the production owner string
  in a shell that also has the canonical seed command in history.

Note that guards 1–6 are process discipline, not enforcement. The physical
isolation a separate database gives you for free has to be reconstructed here
out of review checklists.

### 3.4 Is a separate feedback-beta table required? — **Yes**

**Answer to Phase-2 question 4: yes, and it is not optional.** `hiveblot_feedback`
does not exist in `QIB`, so something must be created regardless; creating it
under the canonical name would plant a permanent, production-named HiveBlot
table inside the QIB production schema — the opposite of the isolation the beta
tables exist to provide. It must be `hiveblot_feedback_beta`, with its own
`BIGSERIAL` sequence, its own CHECK constraint, and 5 renamed indexes.

`record_id` still needs no FK, so beta feedback points at beta records with no
structural link to production.

### 3.5 API / config / code changes required

**Answer to Phase-2 question 6: partly config, but not entirely — code changes
are required.**

| What | Mechanism | Change needed |
|---|---|---|
| Records table name in the API | `Settings.table_name` (`api/app/config.py:51`), a pydantic-settings field ⇒ env `TABLE_NAME` | **Config only.** Set `TABLE_NAME=western_blot_records_beta`. `db.py`, `nlp.py`, `sql_guard.py`, `bio_query.py`, `routers/internal.py` all read `settings.table_name`, so `sql_guard`'s allow-list follows automatically. |
| Feedback table name | **hardcoded** in `api/app/db.py` (the `SELECT … FROM hiveblot_feedback` at :107 and the `INSERT INTO hiveblot_feedback` at :123) | **Code change.** No config knob exists; either add one or edit two SQL strings. |
| Seeding | **hardcoded** ×4 in `scripts/seed_remote.py` (:50 information_schema lookup, :55/:87 counts, :67 DELETE, :80 INSERT) | **Code change** — add a `--table` flag or fork the script. |
| Local dev | **hardcoded** in `scripts/local_db.py` | Change only if local is mirrored to beta names; otherwise local and remote diverge in table name, which is its own footgun. |
| Ingestion loader | `SUPABASE_TABLE` env (`western_blot_miner/supabase_loader.py`) | Config only. |
| Frontend (`web/`) | no table names anywhere | **None.** |

So: one env var, plus edits to `api/app/db.py` and `scripts/seed_remote.py`,
plus a `_beta` SQL fork living outside the drift guard.

### 3.6 Are these changes temporary-only? — **Yes, all of them**

**Answer to Phase-2 question 7: yes, and that is the strongest argument against
doing them.** Every item in §3.2 and §3.5 exists solely to accommodate two
table names in a database we intend to leave. When Srushti's project lands,
all of it is reverted: the `_beta` SQL fork is deleted, `TABLE_NAME` goes back
to the default, `db.py` and `seed_remote.py` are reverted, and the canonical
migrations run unchanged. Net durable value: **zero**. Net durable risk:
whatever slips through the revert — a stray `TABLE_NAME` in a deployed env, a
`_beta` string left in `db.py`, feedback rows stranded in a table nobody
migrates.

---

## 4. Option A vs Option B

**A** — temporarily adapt HiveBlot to `western_blot_records_beta` /
`blot_results_beta` inside `QIB`.
**B** — wait for Srushti's separate free HiveBlot Supabase project and deploy
the canonical migrations there unchanged.

| Dimension | A — beta tables in QIB | B — separate project |
|---|---|---|
| **Engineering work** | `_beta` fork of ~700 lines of SQL; 61 ALTERs; 1 type change; 10 renamed indexes; a beta feedback table + 5 indexes; 2 roles + hand-narrowed grants; code edits in `db.py` and `seed_remote.py`; a `TABLE_NAME` override — then **all of it reverted later** | `supabase link` → `db push` → 2 role passwords → `seed_remote.py`. **Four commands, zero code change, zero SQL written.** |
| **Risk** | Every operation runs in the **same database** as 616 production rows. One un-suffixed identifier in a hand-written script alters production. `db push` is a loaded gun that must never be fired. | Production is in a **different database**. A mistake cannot reach it. `db push` is safe because it is the only thing there. |
| **Schema drift** | **Guaranteed.** The `_beta` fork sits outside `test_supabase_migrations_sync.py`, which byte-compares only the four canonical pairs. Two schema definitions, hand-synced. | **None.** The drift guard keeps the CLI copies byte-identical to canonical, and that is what gets pushed. |
| **Code churn** | `api/app/db.py`, `scripts/seed_remote.py`, possibly `scripts/local_db.py`, env config, plus 4+ new SQL files — then a revert commit touching all of it | **Zero.** Not one source file changes. |
| **Deployment simplicity** | CLI migration path **unusable** (§3.1); dashboard SQL-editor pasting only; `DEPLOYMENT.md` §1 must be rewritten for beta and rewritten back afterwards | `DEPLOYMENT.md` §1 already describes it exactly. It was written for this. |
| **Feedback integrity** | Researcher corrections accumulate in `hiveblot_feedback_beta` inside a database owned by someone else's project, and must later be migrated by hand into the real table. **The feedback IS the beta's deliverable** — putting it somewhere temporary is the worst possible place for it. | Feedback lands in `hiveblot_feedback` in HiveBlot's own project on day one and never moves. |
| **Future maintenance** | Two schema variants to keep in step for the life of the workaround; every fix applied twice | One schema, one path |
| **Scientific-data safety** | 475 reviewed rows and the whole `stable_row_key` rehydration chain live one identifier-typo away from a table holding legacy rows with the **banned p-prefix classification** (62 `p53` rows typed `phospho_signaling`). A `_beta`-suffix slip mixes reviewed evidence with data the project has formally rejected. | Reviewed corpus is alone in a clean database. No legacy rows exist to mix with. |

### The disqualifier

Options A and B are not close on effort, and A is not merely worse — **A cannot
be executed within the constraints of this task.** Making
`western_blot_records_beta` serve HiveBlot requires three objects that have no
table-scoped form:

1. `CREATE ROLE hive_readonly` — cluster-wide. `/search` cannot run without it;
   it is the second layer of defence behind `sql_guard.py`.
2. `CREATE ROLE hive_feedback` — cluster-wide. `POST /feedback` cannot run
   without it.
3. `CREATE EXTENSION pg_trgm` — database-wide. Required by the trigram index on
   `target`.

The brief says do not modify production roles/policies or any other production
schema. Creating two cluster roles and a database extension in `QIB` is exactly
that. **Option A therefore needs a fresh, explicit exception from Suhas before
it could even begin** — and it would buy a temporary setup that is reverted the
moment Srushti's project appears.

The beta tables are a thoughtful gesture and they do solve the *table*-level
isolation problem cleanly. They just cannot solve the *role* and *extension*
problem, because those aren't table-level.

---

## 5. Recommendation

**Wait for Srushti's separate HiveBlot Supabase project. Do not adapt HiveBlot
to `western_blot_records_beta` / `blot_results_beta`.**

Reasons, in order of weight:

1. **Option A requires production-level changes the brief forbids** — two
   cluster roles and a database extension, none of which can be scoped to two
   tables.
2. **The CLI migration path dies** — remote history is empty, so `db push`
   would apply production-targeted migrations; the only fix writes production
   migration history, which is also forbidden.
3. **The beta tables are copies of the *legacy* schema, not the current one** —
   they start 61 columns and one type behind, so "use the beta tables" is not a
   shortcut past yesterday's findings; it inherits every one of them.
4. **All the work is throwaway** and every line of it is reverted later.
5. **Feedback integrity** — researcher corrections are the beta's actual
   deliverable and should not be born in a temporary table inside someone
   else's project.
6. **Option B is already built** — `DEPLOYMENT.md` §1, the four drift-guarded
   migrations, and `seed_remote.py` were written for exactly this and need no
   modification.

**How this supersedes yesterday's recommendation.** The legacy audit
recommended a persistent `hive-beta` branch off `QIB`, with a standalone
project as the fallback. Srushti's separate project **is** that standalone
option, and it is now the better of the two: it needs no plan upgrade, costs
nothing, carries no per-hour branch compute, is owned by HiveBlot rather than
scoped inside SuhasKM's-Org, and leaves `QIB` completely alone. **Prefer
Srushti's project over the branch.** Keep the branch as the fallback if her
project stalls.

**What to do with the beta tables meanwhile:** leave them exactly as they are —
empty and unused. They cost nothing at 0 rows, and Suhas can drop them whenever
he wants. Thank him for making them; the blocker is roles, not tables.

**If Srushti's project is delayed and the beta is genuinely urgent,** the next
best move is *not* Option A — it is asking Suhas to create a second free
Supabase project (a HiveBlot-owned one takes minutes) or falling back to the
persistent `hive-beta` branch. Both keep the canonical migrations unmodified.

---

## 6. Verification commands used (all read-only)

```bash
supabase inspect db table-stats        # 4 tables, sizes, beta tables present
supabase inspect db index-stats        # index inventory incl. both beta pkeys
supabase inspect db role-stats         # no hive_readonly, no hive_feedback
supabase migration list                # remote history still empty
# PostgREST, read-only over HTTPS:
GET /rest/v1/                          # OpenAPI: beta columns/types/defaults/PK
GET /rest/v1/<table>?select=*&limit=1  (Prefer: count=exact)   # exact counts
```

Post-check, production unchanged: `western_blot_records` **616**,
`blot_results` **2**.

Not run, deliberately: any DDL, any `INSERT`/`UPDATE`/`DELETE`, any migration,
any seed, any `db push` / `db pull` / `db reset` / `migration repair` — against
the beta tables or production.
