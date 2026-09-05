# Legacy Supabase production audit — project `QIB` (`belalrbfrndxvdwvjxte`)

**Date:** 2026-08-17 · **Auditor:** Claude Code (Opus 5) · **Mode:** READ-ONLY
**Branch of record:** `feature/bio-context-beta`
**Owner constraint honoured:** production schema was **not** changed. No
`db push`, no migration run, no CREATE/ALTER/DROP on `public`, no seed, no
reset, no `migration repair`, no `db pull`.

> **Bottom line:** production is a 616-row, 12-column *ancestor* of the current
> HiveBlot base table, built by hand (no CLI migration history), holding
> pre-Evidence-Record extractions from an older pipeline whose target
> classification is demonstrably wrong. It is **not** a migration source and
> **not** a data source for the beta. Nothing in this repository reads it.
> Recommendation: build the beta in a **persistent Supabase branch named
> `hive-beta`** and leave production frozen.

---

## 0. Phase 1 — CLI, authentication, linking

| Step | Result |
|------|--------|
| Supabase CLI installed | **Yes** — `/opt/homebrew/bin/supabase`, **v2.113.0** |
| Authenticated | **Yes** — already logged in; `supabase projects list` succeeded, no re-login needed |
| Linked to `belalrbfrndxvdwvjxte` | **Yes** — `supabase link --project-ref belalrbfrndxvdwvjxte` returned `{"project_ref":"belalrbfrndxvdwvjxte"}` |
| Local files mutated by linking | **None** — `git status` clean afterwards; `supabase/config.toml` unchanged |

Project facts read back from the API:

- Name `QIB`, org `SuhasKM's-Org` (`skpdsrhsbwhdeavtwhzv`), region **us-west-2**
- Status `ACTIVE_HEALTHY`, Postgres **17.6.1.127**
- Created **2026-06-28** (hackathon)
- Database size **10 MB**; total table size **104 kB**; total index size **64 kB**

### Two remote side effects, disclosed in full

Neither touches the `public` schema, but both are honest deltas caused by the
audit itself:

1. **`cli_login_postgres` login role.** Every read-only CLI command printed
   `Initialising login role...`. The CLI provisions this temporary role through
   the Management API so it can connect without a database password. It is a
   role, not schema, and it owns nothing.
2. **`supabase_migrations` bookkeeping schema.** `supabase migration list`
   creates `supabase_migrations.schema_migrations` if it is absent. The table
   came back **empty**, so either it already existed empty or the command
   created it empty. Either way it is Supabase's own bookkeeping schema,
   outside `public`, and it contains **zero rows** — production's application
   schema is untouched.

### Tooling constraint worth recording

`supabase db dump` and `supabase db diff` require **Docker Desktop**, which is
not installed on this machine (`docker: not found`). The audit therefore used:

- `supabase migration list`, `supabase inspect db {table-stats, index-stats, role-stats, db-stats}` — native Go, no Docker, read-only
- PostgREST read-only introspection over HTTPS: the project's OpenAPI schema
  document (`GET /rest/v1/`) for columns/types/defaults/PK/FK, and
  `Prefer: count=exact` `SELECT`s for exact row counts and full data export

No write of any kind (`POST`/`PATCH`/`DELETE`/`RPC`) was issued against
production, including probes — testing write privileges would have mutated the
database, so §6 marks write privileges as *deliberately unverified*.

---

## 1. Production table inventory

`public` contains **exactly two** tables. There are **no** views, and **no**
foreign keys anywhere.

### 1.1 `western_blot_records` — 616 rows

128 kB table + 32 kB index. Twelve columns:

| # | Column | Type | Null? | Notes |
|---|--------|------|-------|-------|
| 1 | `id` | `bigint` | not null | **PK**, `bigserial`, values 1–616 contiguous |
| 2 | `paper_id` | `text` | **not null** | |
| 3 | `page` | `integer` | null | |
| 4 | `western_blot_type` | `text` | null | |
| 5 | `sample` | `text` | null | |
| 6 | `organism` | `text` | null | |
| 7 | `treatment_context` | `text` | null | |
| 8 | `figure_label` | `text` | null | |
| 9 | `target` | `text` | null | |
| 10 | `condition` | `text` | null | |
| 11 | `band_detected` | `boolean` | null | |
| 12 | `confidence` | **`text`** | null | **diverges from canonical `real`** — see §5.2 |

**Indexes:** `western_blot_records_pkey (id)` — **and nothing else**. The
canonical base schema's trigram index
`idx_western_blot_records_target … using gin (target gin_trgm_ops)` is
**absent**, and with it the `pg_trgm` extension requirement.

### 1.2 `blot_results` — 2 rows

16 kB table + 32 kB index. Sixteen columns: `id` (PK `bigint`),
`protein_target_name` (not null), `cell_line_tissue`, `treatment_condition`,
`antibody_source_catalog`, `loading_amount`, `normalization_method`,
`is_loading_control` (`boolean`, default `false`), `molecular_weight` (`text`),
`image_confidence` (`text`), `bands` (`jsonb`), `figure_label`,
`figure_caption`, `pmid_doi`, `source_paper`, `created_at`
(`timestamptz`, default `now()`).

**Indexes:** `blot_results_pkey (id)`, `idx_protein` on
`lower(protein_target_name)`.

Both rows were inserted at `2026-06-28T06:22:30Z` — minutes after project
creation.

---

## 2. Row counts (exact, `Prefer: count=exact`)

| Table | Rows |
|-------|------|
| `western_blot_records` | **616** |
| `blot_results` | **2** |
| `hiveblot_feedback` | **does not exist** |

`western_blot_records`, broken down by `paper_id`:

| `paper_id` | Rows | Note |
|------------|------|------|
| `mmc2` | 332 | Not an identifier — the filename of a journal supplementary PDF (`mmc2.pdf`). No DOI/PMCID recorded. |
| `10.1158/1535-7163.MCT-19-0183` | 67 | ERK1/ERK2 siRNA + LY3214996, HCT116 |
| `fphar-17-1827794` | 64 | **Duplicate** of the row below under a filename-style id |
| `10.3389/fphar.2026.1827794` | 64 | **Same 64 rows**, DOI-style id (ids 333–396 vs 397–460, byte-identical on every non-`id`/`paper_id` column — verified) |
| `Single section Western blot_Improving the molecular diagnosis of the muscular dystrophies (1)` | 45 | Not an identifier — a filename |
| `10.1038/s41598-017-18765-1` | 44 | |

**616 stored rows = 5 distinct papers = 552 unique rows + 64 duplicates.**
Only **2 of 6** `paper_id` values are real identifiers; there are **zero**
PMIDs, PMCIDs, titles or source URLs anywhere (those columns do not exist).

Column fill rates across all 616 rows:

| Column | Null/empty | Distinct |
|--------|-----------:|---------:|
| `paper_id` | 0 | 6 |
| `page` | **323** | 8 |
| `western_blot_type` | 0 | 3 |
| `sample` | 46 | 20 |
| `organism` | **507** | 3 (`human`, `SD rats`, null) |
| `treatment_context` | **532** | 3 |
| `figure_label` | **532** | 3 (`C`, `Figure 1`, null) |
| `target` | 8 | 71 |
| `condition` | 23 | 119 |
| `band_detected` | 0 | 2 (580 true / 36 false) |
| `confidence` | **532** | 2 (`'0.9'` ×84, null ×532) |

Only 2 of 6 papers carry any `figure_label` or `treatment_context` at all;
`confidence` is a single hard-coded `'0.9'` where present, i.e. not a measured
score.

---

## 3. Migration-history status

```
supabase migration list
→ {"migrations":[
     {"local":"20260701000001","remote":""},
     {"local":"20260701000002","remote":""},
     {"local":"20260701000003","remote":""},
     {"local":"20260701000004","remote":""}]}
```

**`supabase_migrations.schema_migrations` on production is empty. All four
local migrations are unapplied remotely.**

Consequences:

- Production was built **by hand** (dashboard/SQL editor), never through the CLI.
- There is **no history to repair or reconcile** — and equally, no baseline the
  CLI can use to compute a safe diff. Any `supabase db push` aimed at this
  project would try to apply all four migrations from scratch. **Never point
  `db push` at `belalrbfrndxvdwvjxte`.**
- Migration `20260701000001` is a timestamped copy of `api/db/schema.sql`, which
  is written `create table if not exists` — so a push would *not* error loudly on
  the existing table; it would silently proceed to 001/002/003 and **alter the
  production table**. This is the single most dangerous accident available here,
  and it is why the beta must live in a different database (§7).

---

## 4. Old data worth preserving

**Verdict: `blot_results` — nothing. `western_blot_records` — nothing that is
safe to reuse as evidence; a small amount of value as a *paper shortlist*.**

### 4.1 `blot_results` (2 rows) — fabricated demo data, discard

Both rows are hand-written scaffolding, not extraction output:

- `source_paper`: `"p53 paper 1.pdf"`
- `pmid_doi`: `"10.1234/example.2024"` — a placeholder DOI that does not resolve
- `figure_caption`: `"p53 stabilization after Nutlin-3 treatment in HEK293 cells."`
- `bands`: `[{lane, condition, band_present, relative_intensity:"weak"/"strong"}]`

The `bands` JSONB *shape* is mildly interesting as prior art — it is a per-lane
array on the panel row, which is roughly what `BandObservation` became — but
`relative_intensity: "weak" | "strong"` is exactly what HiveBlot's
non-negotiable #6 forbids ("band presence is not densitometry"). Nothing here
should be carried forward.

### 4.2 `western_blot_records` (616 rows) — do not migrate as evidence

The rows come from an older extraction pipeline that pre-dates the Evidence
Record engine, and they fail HiveBlot's current biological contract on several
counts:

- **The banned p-prefix heuristic is baked into the stored data.** Of 105 rows
  typed `phospho_signaling`, **62 are `p53`** and **4 are `PARP`** — neither is
  a phosphoprotein. This is precisely the
  `target.startswith("p")` failure that HANDOFF *Decisions That Must Not Be
  Reversed* #1 exists to prevent. Meanwhile the same table types `c-PARP` and
  `cIPARP` (cleaved PARP) as `total_protein`. The classifier is not merely
  imprecise; it is wrong in the specific way the project has already ruled out.
- **No residue, no site, no modification envelope.** `pRSK1 (T359/S363)` keeps
  its site only inside the free-text target string. `modification_type`,
  `residue`, `residue_position`, `modification_status` do not exist.
- **No provenance, no evidence status, no candidates.** Every current invariant
  — field-level `{value, confidence, status, sources, candidates}`, `value=null`
  on CONFLICTING, raw wording preserved beside normalized values — has no
  storage here. A migrated row could never be audited or repaired.
- **No identity resolution.** No `canonical_target`, no `uniprot_id`. Loading
  controls appear as seven unnormalized spellings (`Actin`, `β-actin`,
  `b-actin`, `Beta-Actin`, `Tubulin`, `Actin (Coomassie)`, `MHC (Coomassie)`).
- **No provenance back to the source.** 4 of 6 `paper_id` values are filenames;
  no PMID/PMCID/DOI/title/URL columns exist; `page` is null on 323 rows and
  `figure_label` on 532. Most rows cannot be traced to a figure panel at all.
- **`confidence` is a constant.** `'0.9'` on 84 rows, null on 532.
- **8 rows have no `target`** (ids 56–63, `mmc2`) and 23 have an empty
  `condition` — unusable as evidence rows.
- **64 rows are exact duplicates** of another 64 under a second `paper_id`
  spelling.

**What *is* worth keeping — a 5-paper shortlist for re-ingestion.** The
underlying papers are real Western blot literature and broaden coverage beyond
the current three (STAT3/IL-6, mouse standard, co-IP): the ERK1/ERK2 siRNA +
LY3214996 study (`10.1158/1535-7163.MCT-19-0183`, HCT116), the SD-rat
`10.3389/fphar.2026.1827794` study, `10.1038/s41598-017-18765-1`, plus the two
unidentified sources behind `mmc2` (STING/TBK1/IRF3/TREX1 innate-immune
signalling, H1299/A549 — 332 rows, the largest block) and the muscular-dystrophy
single-section Western blot protocol paper (human muscle biopsy). The correct
treatment is to **re-ingest those PDFs through the current Evidence Record
pipeline**, not to copy any stored row. Two of the five need their DOI/PMCID
recovered from the filename first.

Snapshot for the record: full read-only JSON exports of both tables were taken
during this audit (616 + 2 rows). They live in the session scratchpad and were
deliberately **not** committed — the reviewed corpus in `eval/demo/` is the
repository's data of record, and checking in superseded extractions with a known
classification bug would invite exactly the reuse this section argues against.
Re-export at any time with a `select=*` read.

---

## 5. Comparison: legacy production vs current HiveBlot

### 5.1 Is production's `western_blot_records` an ancestor of the current schema?

**Yes — direct lineal ancestor of the *base* table, with one type divergence.**

Production's twelve columns are, in order: `id`, `paper_id`, `page`,
`western_blot_type`, `sample`, `organism`, `treatment_context`, `figure_label`,
`target`, `condition`, `band_detected`, `confidence`. That is **exactly the
column list and exactly the declaration order of `api/db/schema.sql`**,
including the `paper_id NOT NULL` constraint and the `bigserial` PK. The match
is far too specific to be coincidence: production is `api/db/schema.sql` at (or
near) the revision it was created from, and the canonical file kept evolving
afterwards while production did not.

It is **not** an ancestor of `blot_results`; that table is an unrelated
hackathon side-experiment with no descendant in the current codebase.

### 5.2 Field/schema comparison

| Layer | Canonical (`api/db/schema.sql` + migrations 001–003) | Production | Gap |
|---|---|---|---|
| Base columns | 12 | 12 | **match** (order and nullability included) |
| `confidence` type | `real` | **`text`** | **divergent** |
| `pg_trgm` extension | required | not evidenced | missing |
| `idx_western_blot_records_target` (GIN trigram) | required | **absent** | missing |
| Migration 001 — Evidence Record | **60 additive columns** | 0 | **entirely absent** |
| Migration 002 — feedback | table `hiveblot_feedback` + 4 indexes | **table absent** | **entirely absent** |
| Migration 003 — `stable_row_key` | column on both tables + 2 indexes | absent | **entirely absent** |
| Role `hive_readonly` | required (SELECT-only) | **does not exist** | missing |
| Role `hive_feedback` | required (INSERT+SELECT on feedback only) | **does not exist** | missing |

Role existence was confirmed against the full server role list
(`supabase inspect db role-stats`): production carries only stock Supabase roles
(`postgres`, `anon`, `authenticated`, `service_role`, `authenticator`,
`supabase_*`, `pg_*`, `dashboard_user`, `pgbouncer`) plus the CLI's
`cli_login_postgres`. Neither HiveBlot role is present.

The 60 missing Evidence Record columns are the whole current product:
identity/provenance (`pmid`, `pmcid`, `doi`, `title`, `authors`, `source_url`,
`panel_label`, `figure_caption`, `image_crop_ref`), resolution
(`raw_target_name`, `canonical_target`, `uniprot_id`, `aliases_used_in_paper`,
`protein_status`), modification (`modification_type`, `residue`,
`residue_position`, `modification_label`, `modification_status`,
`phospho_specific_antibody`), experiment (`experiment_type`, `experiment_flags`,
`experiment_type_confidence`, `experiment_type_evidence`), context (`cell_line`,
`tissue`, `genotype`, `treatment_name`, `dose`, `dose_unit`, `duration`,
`duration_unit`), antibodies (`antibody_target`, `antibody_vendor`,
`antibody_catalog_number`, `antibody_clone`, `antibody_dilution`,
`antibody_source_evidence`), bands (`band_state`, `lane_condition`,
`loading_control`), MW (`reported_molecular_weight_kda`,
`expected_molecular_weight_kda`, `molecular_weight_source`), audit
(`provenance`, `validation`, `anomaly_flags`, `needs_review`,
`extraction_stage`/`_model`/`_version`), and the ten reserved densitometry
columns.

### 5.3 Against the reviewed 3-paper / 91-experiment / 475-row seed

| | Production | Reviewed seed (`eval/demo/*/supabase_rows.json`) |
|---|---|---|
| Rows | 616 (552 unique) | **475** |
| Papers | 5 (2 with real identifiers) | 3, all with DOI + PMCID |
| Columns populated per row | up to 12 | **57** |
| Provenance JSONB | none | every row |
| `stable_row_key` | none | every row (`<record-hash>:<lane_index>`) |
| Human review | none | field-by-field, plus an independent scientific QA pass |
| Overlap with production papers | — | **zero** (`10.3892/br.2026.2108`, `10.3892/ijmm.2022.5188`, `10.1186/s12964-025-02385-8` appear nowhere in production) |

Zero paper overlap is a useful property: production and the beta corpus are
disjoint, so nothing needs merging or de-duplication between them.

### 5.4 Concrete incompatibilities if the seed were pointed at production

1. **`confidence` type mismatch — a hard failure.** `scripts/seed_remote.py`
   inserts via asyncpg, and the reviewed rows carry `confidence` as a Python
   **float** (`0.9`). asyncpg is strictly typed and will reject a float bound to
   a `text` column. The load would abort.
2. **Silent 45-column data loss.** `seed_remote.py` intersects each row against
   `information_schema.columns` and drops unknown keys (printing what it
   dropped). Against production's 12-column table it would discard every
   Evidence Record field — provenance, UniProt id, modification, validation,
   `stable_row_key` — and write 475 bare rows indistinguishable in kind from the
   legacy ones. Degrading gracefully is the right behaviour for the script and
   the wrong outcome for the beta.
3. **`stable_row_key` has nowhere to live**, so the reseed-proof feedback
   rehydration proven in session 9 would silently stop working.
4. **`POST /feedback` would 500** — `hiveblot_feedback` does not exist, and the
   `hive_feedback` role it connects as does not exist either.
5. **`/search` cannot start** — `DB_READONLY_URL` requires the `hive_readonly`
   role. There is no low-privilege role to connect as, so the second layer of
   defence behind `sql_guard.py` would be missing.
6. **Search quality/latency** — the GIN trigram index on `target` is absent, so
   every target search degrades to a sequential scan.
7. **Result grouping would mis-group legacy rows.** Grouping keys on paper +
   panel + target + experiment type + **cell line** + **modification label**;
   legacy rows have no `cell_line` and no `modification_label`, so 616 rows with
   null components would collapse into meaningless cards beside the reviewed
   ones.
8. **Data-quality contamination.** Legacy `p53`-as-phospho rows would surface in
   `phospho …` searches next to reviewed evidence, in a beta whose stated first
   priority is biological validity.

---

## 6. What production currently depends on

Nothing in this repository, and — on the available evidence — nothing else
either.

- **This repo does not read it.** `SUPABASE_URL` / `SUPABASE_KEY` /
  `DB_READONLY_URL` are unset locally; the running system uses the embedded
  pgserver database from `scripts/local_db.py`. The `hive_readonly` role that
  `/search` requires does not exist on production, so the API could not connect
  to it even if pointed there.
- **`blot_results` has no reader anywhere in the codebase** — the name appears
  in no source file. It is a dead hackathon experiment.
- **Usage counters are near-zero but only weakly informative.** All indexes and
  tables report `index_scans: 0` / `seq_scans: 0`, but
  `time_since_stats_reset` is **1h 14m** — that window covers only this audit.
  Treat it as *no traffic during the audit*, not as proof of lifetime disuse.
- **Unknown external consumers cannot be ruled out from here.** Any dashboard,
  notebook, or hackathon-era deployment holding the anon key can still read both
  tables (next bullet). This is the main reason to leave production alone rather
  than "clean it up".

**Security note (finding only — nothing was changed).** Both tables are fully
readable with the project's **anon** key: anon `SELECT` returned all 616 and
both `blot_results` rows, identical to `service_role`. RLS is therefore either
disabled or not restricting anonymous reads on either table. Write privileges
were **not** tested, because any write probe would have mutated production —
`INSERT`/`UPDATE`/`DELETE` exposure for `anon` remains **unverified** and should
be checked in the dashboard (Table Editor → RLS badge, Auth → Policies). This is
worth resolving regardless of the beta, since an anon key is public by design in
any client that ships it.

---

## 7. Phase 4 — recommended isolated beta strategy (not implemented)

### Recommendation: **Option A — a Supabase branch named `hive-beta`, created as a *persistent* branch.**

Branching is available on this project: `supabase branches list --project-ref
belalrbfrndxvdwvjxte` returns `{"branches":[]}` — the API answers, and no branch
exists yet. This matches the dashboard, where the production branch dropdown
exposes **Create branch**.

**Persistent, not preview.** A preview branch is scoped to a pull request and is
torn down when that PR merges or closes; its whole purpose is ephemeral CI
review. The beta is the opposite shape of work:

- It must stay reachable at a stable host for **UCSF researchers**, across days
  and across sessions — a URL that disappears on merge is unusable.
- Its **entire point is to accumulate `hiveblot_feedback` rows**. Researcher
  corrections are the deliverable; a branch that can be destroyed by a Git event
  would destroy them.
- The 475 reviewed rows are seeded once and reused, not rebuilt per PR.
- Persistent branches are not tied to a PR's lifetime and survive merges.

Use preview branches later, if desired, for per-PR migration CI — that is the
right tool for that job and it composes fine with a persistent `hive-beta`.

**Why a branch beats the alternatives:**

- vs. **Option B (a non-production schema, e.g. `hive_beta`, inside the same
  database)** — cheaper, but every safeguard becomes a convention. `db push`
  targets the same database; `search_path` mistakes reach production tables;
  `hive_readonly`/`hive_feedback` would be database-wide roles one `GRANT`
  slip away from production data; and the audit trail for "did we change
  production?" gets much harder to answer cleanly. Given an explicit owner
  constraint, physical isolation beats a naming convention.
- vs. **Option C (a brand-new standalone Supabase project)** — this is the
  strong fallback and is genuinely acceptable: total isolation, no plan
  dependency, and production stays linked to nobody. It loses the branch's
  built-in relationship to the parent project (shared org/settings, one
  dashboard, `supabase branches` lifecycle management) and adds a second project
  to keep track of. Take it if branching turns out to be gated (see below).

**Verify before creating (two things this audit could not settle):**

1. **Plan and cost.** Branching is a paid feature; each running branch is billed
   by compute-hour, and a *persistent* branch runs continuously. Confirm
   `SuhasKM's-Org` is on a plan that allows it and that the owner accepts the
   ongoing cost. If not → Option C.
2. **Data isolation semantics.** A Supabase branch clones **schema and roles,
   not table data** — a fresh branch starts empty, which is exactly what we
   want. `supabase branches create` has an explicit opt-in `--with-data` flag
   for cloning production data: **do not pass it.** Confirm in the dashboard
   before creating that the branch gets its own connection string, anon key, and
   service-role key (it does), so no beta credential can ever address
   production.

**One correction to expect.** Branch creation replays migrations from
`supabase/migrations/` onto the new branch. Because production's history is
empty and its base table already exists in a divergent form, the branch is
created from the *parent's schema*, which carries `confidence text` — while
`api/db/schema.sql` declares `confidence real` and the reviewed seed inserts
floats. **Verify the branch's `confidence` type immediately after creation and
before seeding** (§8 step 4). If it comes through as `text`, fix it **on the
branch only** with a one-line `ALTER TABLE … ALTER COLUMN confidence TYPE real
USING confidence::real` and, in the same change, add the corresponding note to
the canonical SQL so the divergence cannot silently return. Never run that
`ALTER` against production.

### How the four migrations and 475 rows deploy into `hive-beta`

Every command below is scoped to the branch. **`--project-ref` never points at
`belalrbfrndxvdwvjxte` again after step 1.**

1. **Create the branch** — dashboard (production dropdown → *Create branch* →
   name `hive-beta`, persistent) or
   `supabase branches create hive-beta --persistent` — **without
   `--with-data`**, so no production row is ever copied. Read back with
   `supabase branches list --project-ref belalrbfrndxvdwvjxte`; note the
   **branch's own project ref**.
2. **Re-link the repo to the branch:**
   `supabase link --project-ref <HIVE_BETA_REF>`. From here on the CLI cannot
   reach production by accident.
3. **Push the four migrations** — `supabase db push --dry-run` first (expect
   exactly `20260701000001`–`20260701000004`, all additive, matching
   `api/db/schema.sql` + `migrations/001` + `002` + `003`), then
   `supabase db push`. The pytest drift guard already proves the timestamped
   copies are byte-identical to the canonical files, so this applies the
   reviewed SQL and nothing else.
4. **Verify the schema before seeding:** `western_blot_records` has 72 columns
   (12 base + 60 from 001) plus `stable_row_key` from 003; `hiveblot_feedback`
   exists; the GIN trigram index on `target` exists; **`confidence` is `real`**
   (apply the branch-only `ALTER` above if it is not).
5. **Set the two restricted-role passwords** on the branch (branch SQL editor,
   freshly generated values, never reused from anywhere):
   `ALTER ROLE hive_readonly WITH PASSWORD '<generated>';` and
   `ALTER ROLE hive_feedback WITH PASSWORD '<generated>';`
6. **Seed the 475 reviewed rows** with the branch's **owner** connection string:
   ```bash
   export SEED_DATABASE_URL='<hive-beta owner connection string>'
   .venv/bin/python scripts/seed_remote.py eval/demo/*/supabase_rows.json
   .venv/bin/python scripts/seed_remote.py --check      # expect 475 rows
   ```
   The script deletes and reinserts **per `paper_id`**, so it is idempotent and
   re-runnable after any re-review. Watch its "dropped keys" output: on a
   correctly migrated branch it must drop **nothing**. Anything dropped means a
   migration did not apply — stop and fix before continuing.
7. **Point the app at the branch only** — `api/.env` gets the branch's
   `DB_READONLY_URL`, `DB_FEEDBACK_URL`, `SUPABASE_URL`, `SUPABASE_KEY`,
   `ALLOWED_ORIGINS`; the web host gets `API_BASE_URL` + `INTERNAL_API_KEY`.
   Grep the finished env files for `belalrbfrndxvdwvjxte` and confirm **zero**
   matches.
8. **Run the 8-step smoke checklist** in `DEPLOYMENT.md` §4, then confirm
   production is still exactly as this audit found it: 616 + 2 rows, 12 columns,
   empty migration history.

Because production's migration history stays empty and the beta lives in a
different database, promoting anything to production later remains a deliberate,
separate decision — not a side effect of a `db push`.

---

## 8. Verification commands used (all read-only)

```bash
supabase --version                                    # 2.113.0
supabase projects list                                # already authenticated
supabase link --project-ref belalrbfrndxvdwvjxte      # link only; no local diff
supabase migration list                               # remote history: empty
supabase inspect db table-stats                       # sizes + estimated counts
supabase inspect db index-stats                       # index inventory
supabase inspect db role-stats                        # full role list
supabase inspect db db-stats                          # db size, stats-reset age
supabase branches list --project-ref belalrbfrndxvdwvjxte   # []
# PostgREST, read-only over HTTPS:
GET /rest/v1/                                         # OpenAPI: columns/types/defaults/PK
GET /rest/v1/<table>?select=*  (Prefer: count=exact)  # exact counts + full export
```

Not run, deliberately: `supabase db push`, `supabase db pull`,
`supabase db reset`, `supabase migration repair`, any DDL, any seed, any
`POST`/`PATCH`/`DELETE` against production.
