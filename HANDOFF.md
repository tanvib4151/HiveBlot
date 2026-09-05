# HiveBlot Agent Handoff

> Read this file first. It is the single source of truth for **current project
> state**. Any agent (Claude Code, another Claude session, Codex, a human) should
> be able to read this and immediately know what HiveBlot is, what's done, what's
> blocked, and the exact next task.

## Last Updated
- **2026-08-27 (session 30)** — Claude Code (Fable 5). **PROFESSOR ORCHESTRATION
  BRIEF (docs only — no code, no deploy, no DB change).**
  `research/PROFESSOR_ORCHESTRATION_BRIEF.md`: a ~5-minute technical handoff
  for an external AI/ML professor reviewing our model orchestration. Contents:
  system overview, problem motivation, the ingestion cascade (CV Stage 1 →
  cheap-model Stage 2 → deterministic reconcile Stage 3 → status-gated Stage 4
  escalation) and query path as an annotated pipeline + component table
  (model / retrieval / deterministic / routing), current metrics with the
  central caveat stated plainly (Stage 2 has only ever run agent-in-the-loop;
  unseen-paper F1, escalation rate, token cost all unmeasured), a ranked
  optimization-candidate table (measure-first eval set → calibrated
  confidence routing → deterministic early-exit → error-specific escalation →
  k-sample agreement → panel batching), and 5 specific questions for the
  professor. Shareable web version published as a Claude artifact (URL inside
  the doc). Also: root `.gitignore` now ignores `.serena/` (local MCP tool
  state that appeared untracked). No tests affected.
- **2026-08-26 (session 29)** — Codex. **LIGHT/DARK THEME SYSTEM
  (frontend theme/styling only; no backend, search API, query semantics, URL,
  result schema, filters, database, evidence logic, ranking, extraction, or
  result-state change).** Added a compact, keyboard-accessible Light/Dark
  segmented control beside the header navigation. Theme selection updates the
  document immediately without reload/API activity, stores the explicit choice
  in browser `localStorage` under `hiveblot-theme`, and otherwise follows the
  initial system `prefers-color-scheme`. A pre-hydration script in the root
  layout applies `data-theme` and `color-scheme` before body rendering to avoid
  wrong-theme flash. Refactored the frontend around shared semantic CSS tokens
  for background/surfaces/text/borders/accent/status/chips/overlay/focus states,
  retaining the existing dark palette as the default and adding the intentional
  light scientific palette (`#f7f8f6` page, white cards/inputs, soft green-gray
  sidebar, dark text, deep teal accents, restrained purple, amber warnings,
  muted red errors). Converted hard-coded theme colors across home, About,
  Learn, search/results, filters, feedback, evidence, legacy results, and header
  surfaces to those tokens. Search is white with a filled teal submit action in
  light mode; cards remain white and restrained; figure/panel image backgrounds
  remain white in both themes. IBM Plex typography, all layout/data hierarchy,
  mobile filter drawer, and responsive behavior remain intact; on small screens
  theme labels collapse to icons and the wordmark text hides at <=520px to
  prevent header crowding. Files changed: `web/app/layout.tsx`,
  `web/app/globals.css`, active frontend pages/components with theme colors,
  new `web/components/ThemeToggle.tsx`, and this handoff. Verification: final
  `cd web && npm run build` passed; targeted ESLint passed for layout,
  ThemeToggle, Navigation, search page, filters, DatabaseResultCard, and
  BetaFeedback; `SearchFeedback.tsx` still has its documented pre-existing
  `react-hooks/set-state-in-effect` error unrelated to theme styling; `git diff
  --check` passed; live `/search?q=phospho%20STAT3%20Tyr705` returned 200 and
  server HTML contained both accessible theme labels plus the pre-hydration
  `hiveblot-theme` script; required biology checks passed under `.venv`:
  biology 165/165, reconcile 21/21, loader enrichment 18/18, extract 10/10,
  pipeline wiring 11/11, benchmark 34/34. Automated browser screenshots were
  unavailable because the in-app browser control tool was not exposed; the
  local themed page was opened for direct inspection. No environment values or
  secrets were committed.
- **2026-08-26 (session 28)** — Codex. **SEARCH BAR ALIGNMENT VISIBILITY
  CORRECTION (frontend CSS only; no layout ownership, search behavior, filters,
  API, URL semantics, backend, schema, data, or evidence change).** Follow-up
  to session 27 after user feedback that the search bar itself did not look
  changed. The shared workspace grid was live, but the retained 920px search
  max-width and near-identical dimensions made the alignment shift too subtle.
  Removed the desktop max-width cap so the search control and examples visibly
  span the full results column, reduced control height from 52px to 48px,
  reduced the search heading from 22px to 19px, and tightened heading/helper
  spacing. The left edge remains exactly aligned with results and all search
  interactions/API behavior are unchanged. File changed:
  `web/app/globals.css` plus this handoff. Verification: final `cd web && npm
  run build` passed; targeted search/filter ESLint passed; `git diff --check`
  passed; reopened the local search route with a cache-busting URL; required
  biology checks passed under `.venv`: biology 165/165, reconcile 21/21,
  loader enrichment 18/18, extract 10/10, pipeline wiring 11/11, benchmark
  34/34. No environment values or secrets were committed.
- **2026-08-26 (session 27)** — Codex. **SEARCH/RESULTS RESEARCH-WORKSPACE
  ALIGNMENT + MOBILE FILTER DRAWER (frontend presentation only; no search API,
  query semantics, URL parameters, database, backend, ranking, schema, filter
  composition, extraction, or evidence-classification change).** Reframed
  `/search` around one shared desktop workspace grid: the search heading,
  control, and examples now begin on the same horizontal axis as the results
  column while the persistent filter sidebar occupies the first grid track.
  Reduced search-section and result-card whitespace, tightened the desktop
  faceted sidebar, and retained the existing wide card hierarchy, prominent
  Western blot preview, temporary-preview disclosure, metadata, IBM Plex
  typography, dark theme, and teal accents. At <=900px, the sidebar is removed
  from document flow and exposed through a real Filters button as a scrollable
  off-canvas panel with backdrop, close control, Escape dismissal, background
  scroll lock, active-filter count, and hidden-when-closed keyboard behavior.
  The drawer reuses the same draft/applied filter state and existing
  Apply/Reset handlers; Apply still builds the same query and now also closes
  the drawer. No fake controls were added and View Evidence remains absent.
  Files changed: `web/app/search/page.tsx`, `web/components/FiltersBar.tsx`,
  `web/app/globals.css`, and this handoff. `SearchInput.tsx` and
  `DatabaseResultCard.tsx` were inspected but required no changes because their
  preserved content/behavior already matched the requested hierarchy.
  Verification: `cd web && npm run build` passed; targeted ESLint on search,
  filters, SearchInput, and DatabaseResultCard passed; `git diff --check`
  passed; live `/search?q=phospho%20STAT3%20Tyr705` returned 200 and the
  unchanged local `/api/search` proxy returned 200; required biology checks
  passed under `.venv`: biology 165/165, reconcile 21/21, loader enrichment
  18/18, extract 10/10, pipeline wiring 11/11, benchmark 34/34. Automated
  browser screenshots were unavailable because the in-app browser control tool
  was not exposed in this session. No environment values or secrets were
  committed.
- **2026-08-26 (session 26)** — Codex. **IBM PLEX TYPOGRAPHY SYSTEM
  (frontend styling only; no layout structure, search behavior, filters, API,
  backend, schema, data model, extraction, or result-data change).** Replaced
  the render-blocking Google Fonts CSS `@import` (Newsreader + Manrope + IBM
  Plex Mono) with Next.js `next/font/google` loading for IBM Plex Serif, IBM
  Plex Sans, and IBM Plex Mono. The optimized font variables are exposed as
  `--font-serif`, `--font-sans`, and `--font-mono` from the root layout and used
  consistently across the frontend. Semantic mapping now uses Serif for the
  HiveBlot/scientific identity, research headings, target/modification titles,
  experimental descriptions, and figure-caption text; Sans for navigation,
  search controls, result counts, filter values/actions, feedback controls,
  ordinary metadata values, and general UI copy; Mono for section/field labels,
  status/technical chips, lanes, and identifiers. Reduced prior monospace
  overuse in navigation/sidebar controls and removed all remaining
  Newsreader/Manrope declarations. Preserved existing dimensions, spacing,
  colors, borders, card/sidebar hierarchy, and behavior. Files changed:
  `web/app/layout.tsx`, `web/app/globals.css`, frontend pages under `web/app/`,
  typography-bearing components under `web/components/`, and this handoff.
  Verification: `cd web && npm run build` passed; targeted ESLint on the root
  layout, search page, result card, filters, and canvas passed; `git diff
  --check` passed; source scan found no legacy Newsreader/Manrope/font-import
  declarations; live `/search?q=phospho%20STAT3%20Tyr705` returned 200,
  preloaded optimized local WOFF2 assets, and exposed all three CSS variables;
  required biology checks passed under `.venv`: biology 165/165, reconcile
  21/21, loader enrichment 18/18, extract 10/10, pipeline wiring 11/11,
  benchmark 34/34. Automated browser inspection was unavailable because the
  in-app browser control tool was not exposed in this session. No environment
  values or secrets were committed.
- **2026-08-26 (session 25)** — Codex. **COMPACT SEARCH RESULTS VERTICAL
  RHYTHM (frontend styling/layout only; no search behavior, filters, API,
  backend, schema, query, extraction, or result-data change).** Tightened the
  `/search` workspace from the search heading through the first result card:
  reduced heading-to-input and input-to-example spacing, reduced search-header
  bottom padding while retaining its divider, moved the results workspace
  closer to that divider, and replaced the results header's large inline
  margins with scoped classes for compact title/count/feedback/card spacing.
  Preserved the current sidebar, result cards, typography sizes, dark/teal
  visual system, and responsive layout; the mobile breakpoint receives the
  same proportional tightening. Files changed: `web/app/globals.css`,
  `web/app/search/page.tsx`, `web/components/SearchFeedback.tsx`, and this
  handoff. Verification: `cd web && npm run build` passed; targeted ESLint on
  `app/search/page.tsx` passed; `git diff --check` passed; local
  `/search?q=phospho%20STAT3%20Tyr705` returned 200; required biology checks
  passed under `.venv`: biology 165/165, reconcile 21/21, loader enrichment
  18/18, extract 10/10, pipeline wiring 11/11, benchmark 34/34. Automated
  browser inspection was unavailable because the in-app browser control tool
  was not exposed in this session; the page was instead verified via the
  production build and live local HTTP route. No environment values or secrets
  were committed.
- **2026-08-26 (session 24)** — Codex. **SEARCH BAR UX/UI REFINEMENT
  (frontend presentation/interaction only; no backend/API/schema/query/filter/
  extraction/evidence data change, no deploy, no cloud DB/Supabase change, no
  production secrets).** Reworked the reusable `SearchInput` and `/search`
  header into one compact scientific search control: cohesive input + teal
  submit button with matching height and coordinated borders, inline accessible
  SVG search icon, improved placeholder (`Search protein, phosphosite,
  antibody, cell line...`), keyboard-accessible clear control, subtle clickable
  example queries that populate the field without submitting, preserved
  submitted query display, and loading/disabled `SEARCHING...` button state
  wired to the existing frontend `loading` flag. Reduced `/search` header/body
  vertical whitespace and widened/aligned the search control to the results
  workspace. Confirmed the search API contract is unchanged: `web/app/search/
  page.tsx` still submits only the query string to the existing `/api/search`
  proxy, URL `q` behavior remains in `handleSearch`, and no backend/filter
  query logic changed. Files changed: `web/components/SearchInput.tsx`,
  `web/app/search/page.tsx`, `web/app/globals.css`, and this handoff.
  Verification: `cd web && npm run build` passed; targeted ESLint on
  `components/SearchInput.tsx` and `app/search/page.tsx` passed; full
  `npm run lint` still fails only on pre-existing unrelated issues in
  `web/app/learn/page.tsx`, `web/app/page.tsx`,
  `web/components/Navigation.tsx`, `web/components/ResultsCard.tsx`, and
  `web/components/SearchFeedback.tsx` (SearchInput is no longer part of the
  full-lint failure list); local `/search?q=phospho%20STAT3%20Tyr705` returned
  200; local web `/api/search` proxy returned 200; required biology checks
  passed under `.venv`: biology 165/165, reconcile 21/21, loader enrichment
  18/18, extract 10/10, pipeline wiring 11/11, benchmark 34/34. The plain
  `python3` biology commands failed on this machine because that interpreter
  lacks `pydantic`; rerunning the same commands with `.venv/bin/python` passed.
  Browser automation was unavailable in this Codex session (`node_repl js` was
  not exposed and Playwright was not installed), so UI QA was limited to build/
  lint, local HTTP checks, and opening the local page for inspection. Local
  gitignored env files may exist for the dev stack; no env values were
  committed.
- **2026-08-25 (session 23)** — Claude Code (Sonnet 5). **COMMIT LONG-STANDING
  LOCAL DEV CONFIG (frontend dev-server config only; no app/backend/schema/
  deploy change, no production secrets).** Committed `web/next.config.ts`'s
  `allowedDevOrigins: ["127.0.0.1"]`, which sessions 17–22 repeatedly noted as
  "existing uncommitted... left untouched." This silences Next.js's dev-server
  cross-origin warning when the local API/web stack is accessed via
  `127.0.0.1`; it has no effect on production builds. No tests affected (no
  code path changed).
- **2026-08-26 (session 22)** — Codex. **HIDE SEARCH-RESULT EVIDENCE PANEL
  INTERACTION (frontend presentation-only; no backend/API/schema/query/filter/
  extraction/evidence data change, no deploy, no cloud DB/Supabase change, no
  production secrets).** Removed the user-facing `View Evidence` interaction
  from `DatabaseResultCard`: no evidence button, no expandable `EvidencePanel`,
  and no visible field-level feedback/provenance controls in the current search
  results experience. The underlying `EvidencePanel.tsx`, record/feedback API
  routes, evidence/provenance fields, extraction pipeline, stored data, and
  backend behavior were left intact. Search result cards still show target,
  modification/status, sample, experiment, treatment, lanes, figure preview,
  chips, antibody/catalog, molecular weight, UniProt, page, and DOI/source.
  Files changed: `web/components/DatabaseResultCard.tsx`,
  `web/app/globals.css`, and this handoff. Verification: `cd web && npm run
  build` passed; targeted ESLint on `components/DatabaseResultCard.tsx` passed;
  search-card path grep found no remaining `View Evidence`/`EvidencePanel`/
  visible evidence-panel strings; full `npm run lint` still fails only on
  pre-existing unrelated lint issues in `web/app/learn/page.tsx`,
  `web/app/page.tsx`, `web/components/Navigation.tsx`,
  `web/components/ResultsCard.tsx`, `web/components/SearchFeedback.tsx`, and
  `web/components/SearchInput.tsx`; local
  `/search?q=phospho%20STAT3%20Tyr705` returned 200; local web `/api/search`
  proxy returned count 18; required biology checks passed again: biology
  165/165, reconcile 21/21, loader enrichment 18/18, extract 10/10, pipeline
  wiring 11/11, benchmark 34/34. Existing uncommitted `web/next.config.ts`
  (`allowedDevOrigins`) was present before this task and left untouched.
- **2026-08-26 (session 21)** — Codex. **RESULT CARD SAMPLE/EXPERIMENT +
  COMPACT METADATA REBALANCE (frontend layout-only; no backend/API/schema/
  query/filter/evidence/DOI/image change, no deploy, no cloud DB/Supabase
  change, no production secrets).** Refined `DatabaseResultCard` to remove the
  dedicated large Evidence/Source column from the main card layout. Desktop
  result rows now follow **primary result | sample/experiment | treatment/lanes
  | figure | tags + compact metadata | action**. Primary result now contains
  only the target/modification identity, status, as-printed label, and
  descriptive context. `Sample`, `Experiment`, organism, and IP bait moved into
  their own simple scan column. Treatment/lanes remain in their dedicated
  column. The former source metadata is preserved but compacted into the tags/
  metadata column alongside the existing-data chips (`WB`/`co-IP`, `Phospho`,
  design tag, lane count): antibody/catalog, molecular weight, UniProt, page,
  and DOI still render, but no longer occupy a standalone evidence/source
  column. `View Evidence` behavior is unchanged and still toggles the existing
  `EvidencePanel`. Files changed: `web/components/DatabaseResultCard.tsx`,
  `web/app/globals.css`, and this handoff. Verification: `cd web && npm run
  build` passed; targeted ESLint on `components/DatabaseResultCard.tsx` passed;
  full `npm run lint` still fails only on pre-existing unrelated lint issues in
  `web/app/learn/page.tsx`, `web/app/page.tsx`,
  `web/components/Navigation.tsx`, `web/components/ResultsCard.tsx`,
  `web/components/SearchFeedback.tsx`, and `web/components/SearchInput.tsx`;
  local `/search?q=phospho%20STAT3%20Tyr705` returned 200; local web
  `/api/search` proxy returned count 18; required biology checks passed again:
  biology 165/165, reconcile 21/21, loader enrichment 18/18, extract 10/10,
  pipeline wiring 11/11, benchmark 34/34. Existing uncommitted
  `web/next.config.ts` (`allowedDevOrigins`) was present before this task and
  left untouched.
- **2026-08-26 (session 20)** — Codex. **DEDICATED TREATMENT/LANES RESULT
  COLUMN (frontend layout-only; no backend/API/schema/query/filter/evidence
  change, no deploy, no cloud DB/Supabase change, no production secrets).**
  Refined `DatabaseResultCard` so desktop result rows now follow
  **primary result info | treatment + lanes | figure preview | experiment tags
  | evidence/source | action**. Treatment and lane chips moved out of the
  primary identity section into their own adjacent column; all lane chips now
  render and wrap naturally instead of truncating after eight lanes. Primary
  result info keeps target/modification, status, as-printed label, context,
  sample, experiment type, organism/IP bait when present. Figure preview,
  compact existing-data chips, source metadata, and `View Evidence` behavior
  are unchanged except for grid placement; dose/duration display now includes a
  space before units (`10 ng/ml`) as a frontend formatting-only cleanup. Medium
  screens reflow to two rows (**primary | treatment/lanes | figure**, then
  **tags | source | action**); mobile stacks in reading order. Files changed:
  `web/components/DatabaseResultCard.tsx`, `web/app/globals.css`, and this
  handoff. Verification: `cd web && npm run build` passed; targeted ESLint on
  `components/DatabaseResultCard.tsx` passed; full `npm run lint` still fails
  only on pre-existing unrelated lint issues in `web/app/learn/page.tsx`,
  `web/app/page.tsx`, `web/components/Navigation.tsx`,
  `web/components/ResultsCard.tsx`, `web/components/SearchFeedback.tsx`, and
  `web/components/SearchInput.tsx`; local `/search?q=phospho%20STAT3%20Tyr705`
  returned 200; local web `/api/search` proxy returned count 18; required
  biology checks passed again: biology 165/165, reconcile 21/21, loader
  enrichment 18/18, extract 10/10, pipeline wiring 11/11, benchmark 34/34.
  Existing uncommitted `web/next.config.ts` (`allowedDevOrigins`) was present
  before this task and left untouched.
- **2026-08-26 (session 19)** — Codex. **SEARCH RESULTS ROW REFINEMENT
  (frontend-only; no backend/API/schema/query change, no deploy, no cloud
  DB/Supabase change, no production secrets).** Refined the session-18
  `/search` layout so result cards read less like three rigid database columns
  and more like one wide scientific catalog row. The left filter sidebar stayed
  intact and visually secondary; results now dominate the page width. Each
  desktop result row is organized as **primary scientific identity | centered
  figure preview | compact experiment chips | source metadata | action** with
  only one subtle outer card border, wider internal spacing, no heavy vertical
  panel dividers, a larger contained figure preview, compact chips derived only
  from existing result data (`WB`/`co-IP`, `Phospho`, design tag, lane count),
  lighter metadata rows for antibody/MW/UniProt/source, and a compact
  right-aligned `View Evidence` action that still toggles the same
  `EvidencePanel`. The STAT3 temporary image remains frontend-only at
  `/images/STATE3.png` and is labeled "Sample figure preview" so it is not
  presented as confirmed provenance. Files changed:
  `web/components/DatabaseResultCard.tsx`, `web/app/globals.css`,
  `web/app/search/page.tsx`, and this handoff. Verification:
  `cd web && npm run build` passed; targeted ESLint on changed frontend files
  passed; full `npm run lint` still fails only on pre-existing unrelated lint
  issues in `web/app/learn/page.tsx`, `web/app/page.tsx`,
  `web/components/Navigation.tsx`, `web/components/ResultsCard.tsx`,
  `web/components/SearchFeedback.tsx`, and `web/components/SearchInput.tsx`;
  local API `/health` returned OK; local `/search?q=phospho%20STAT3%20Tyr705`
  returned 200; local web `/api/search` proxy returned count 18; required
  biology checks passed again: biology 165/165, reconcile 21/21, loader
  enrichment 18/18, extract 10/10, pipeline wiring 11/11, benchmark 34/34.
  In-app browser automation was unavailable in this Codex session, so visual
  QA was limited to local server checks plus opening the page for manual
  inspection. Existing uncommitted `web/next.config.ts` (`allowedDevOrigins`)
  was present before this task and left untouched.
- **2026-08-26 (session 18)** — Codex. **SEARCH RESULTS INFORMATION
  ARCHITECTURE REDESIGN (frontend-only; no backend/API/schema/query change, no
  deploy, no cloud DB/Supabase change, no production secrets).** Rebuilt the
  `/search` results surface around the requested BenchSci/ASCEND-style
  information hierarchy while keeping HiveBlot's existing dark visual system:
  top search bar, persistent left filter sidebar, active filter chips above the
  result list, and desktop result cards split into **Experiment information |
  Figure preview | Evidence / source**. Reused the existing filter concepts
  (protein, site/modification, experiment, cell line, vendor, catalog number,
  needs review) with the same explicit **Apply** action; filters still compose
  a plain query string that the existing deterministic backend parser already
  understands, and `/api/search` still receives only `{query}`. Evidence
  accordion, record-detail fetches, feedback paths, search URL behavior, and
  grouping by `stable_row_key` were preserved. Added/used the provided
  development image at `web/public/images/STATE3.png`; STAT3 cards show it via
  frontend-only `/images/STATE3.png`, with no image API or backend crop-path
  change. Files changed: `web/app/search/page.tsx`,
  `web/components/FiltersBar.tsx`, `web/components/DatabaseResultCard.tsx`,
  `web/app/globals.css`, `web/public/images/STATE3.png`, and this handoff.
  Verification: `cd web && npm run build` passed; targeted ESLint on changed
  frontend files passed; full `npm run lint` still fails only on pre-existing
  unrelated issues in `web/app/learn/page.tsx`, `web/app/page.tsx`,
  `web/components/Navigation.tsx`, `web/components/ResultsCard.tsx`,
  `web/components/SearchFeedback.tsx`, and `web/components/SearchInput.tsx`;
  `curl -I http://127.0.0.1:3000/search?q=phospho%20STAT3%20Tyr705` returned
  200; local web `/api/search` proxy returned 18 rows for
  `phospho STAT3 Tyr705`; required biology checks passed again: biology
  165/165, reconcile 21/21, loader enrichment 18/18, extract 10/10, pipeline
  wiring 11/11, benchmark 34/34. Existing uncommitted `web/next.config.ts`
  (`allowedDevOrigins`) was present before this task and left untouched.
- **2026-08-25 (session 17)** — Codex. **LOCAL DEV REQUIREMENTS WIRED +
  LOCAL STACK OPENED (docs/dependency only; no production code path change, no
  deploy, no cloud DB/Supabase change, no production secrets).** Added root
  `requirements-local.txt` for teammates who need local search/results/cards:
  it includes `api/requirements.txt`, `western_blot_miner/requirements.txt`,
  and local-only `pgserver`. Updated `research/team_delegation/ENV_SETUP.md`
  so the setup command installs `requirements-local.txt`; Render/production
  continues to install `api/requirements.txt` only, so `pgserver` stays out of
  the production API dependency surface. Local verification on
  `feature/bio-context-beta`: `python3.12 -m venv .venv`; pip install from
  `requirements-local.txt` succeeded; `scripts/local_db.py up` started embedded
  Postgres at `.localdb/` (local pg_trgm unavailable, index skipped as expected
  per helper); `scripts/local_db.py load eval/demo/*/supabase_rows.json` loaded
  475 rows; `scripts/local_db.py status` confirmed 475 rows; local FastAPI
  `/health` returned 200; local `/search` for `phospho STAT3 Tyr705` returned
  18 rows; existing local Next dev server on `http://127.0.0.1:3000` served 200
  and proxied `/api/search` to the local API with 18 rows. Created gitignored
  local `.env` files only for this machine using local values; no env values
  were committed. Required checks run after setup: biology 165/165, reconcile
  21/21, loader enrichment 18/18, extract 10/10, pipeline wiring 11/11,
  benchmark 34/34. Existing uncommitted `web/next.config.ts` change
  (`allowedDevOrigins`) was present before this task and left untouched.
- **2026-08-24 (session 16)** — Claude Code (Fable 5). **TEAM LOCAL-DEV ENV
  PLAN (docs + .gitignore only; no code, no deploy, no credential rotation,
  no Supabase change, QIB untouched).** `research/team_delegation/
  ENV_SETUP.md`: per-teammate least-privilege env plan for the 6-person team
  (Suhas D, Ananya A+D, Srushti C, Tanvi B+A, Yashvi coordination, Nik
  owner). Core: **the local stack needs ZERO production secrets** —
  `scripts/local_db.py` embedded Postgres + self-generated local
  `INTERNAL_API_KEY`/`AGENT_API_KEYS`; cloud `SUPABASE_*`/`OPENAI_KEY` stay
  empty. Only shared credential: cloud `DB_READONLY_URL` (`hive_readonly`,
  SELECT-only on `western_blot_records`, session-12-audited) to **Suhas
  only**, staged outside the repo at `~/hiveblot-env-handoff/suhas/` (0600)
  for password-manager share or AirDrop — never messaging apps. Forbidden to
  distribute: cloud `DB_FEEDBACK_URL` (write-capable), `SUPABASE_KEY`,
  production `INTERNAL_API_KEY`/`AGENT_API_KEYS`, Nik's model keys,
  Vercel/Render auth. **Gap fixed: `western_blot_miner/.env` was NOT
  gitignored** (api/ and web/ ignore their own; the miner had no rule) —
  root `.gitignore` now ignores `western_blot_miner/.env*` except the
  example. Verified: no `.env` tracked in git (examples only). PR #1
  (branch → main) remains open, unmerged; all work stays on
  `feature/bio-context-beta`.
- **2026-08-18 (session 15)** — Claude Code (Fable 5). **TEAM DELEGATION
  PACKAGE (docs only — no product code, no deploy, no DB change).** The
  founder-walkthrough findings (`/Users/niks/Downloads/
  HiveBlot-Founder-Walkthrough.md`) were turned into
  `research/team_delegation/`: `MASTER_DELEGATION.md` (product state,
  scope guardrails, findings by domain with priorities, 4 workstreams + Nik,
  coordination rules), four role-based handoffs (`BIOLOGY_QA_HANDOFF.md`,
  `SCIENTIFIC_COMMUNICATION_HANDOFF.md`, `PRODUCT_UX_HANDOFF.md`,
  `SEARCH_DATA_HANDOFF.md` — each teaches the concept it touches via a
  "What you should understand before finishing" section), and
  `NIK_FOUNDER_LEARNING.md`. Role-based, not named: project docs identify
  collaborators only by infra actions (Suhas: legacy QIB; Srushti: clean
  Supabase project), insufficient to map specialties — Nik assigns.
  **Priorities: P0 = `/about` fabricated numbers (2.8K/12.4K/520) +
  automated-ingestion claims (only P0).** P1: `/learn`
  Upregulated/Downregulated + densitometry mismatch, homepage first-run
  guidance, needs-review reason not shown in lists, internal values rendered
  as paper quotes (`ambiguous_family`, `{}`, candidate "none", empty WHY
  section), `image_crop_ref` absolute-path leak (plan only — ties to the
  existing relative-ref open question), `GAPDH mouse` organism
  investigation (investigate-only; parser must not hallucinate filters),
  scientific QA re-run vs the 93-experiment grouping, terminology glossary.
  P2: next-action UX exploration, confidence-display question, `RESULTS -`
  dash, cold-start copy, audience statement. Workflow: OBSERVE → UNDERSTAND
  → ASSIGN → then FIX; all fixes deferred to workstreams; Nik alone deploys.
- **2026-08-18 (session 14)** — Claude Code (Opus 5). **P0 IDENTITY FIX + FULL
  HOSTED BETA LIVE.** **Web https://hiveblot-beta.vercel.app · API
  https://hiveblot-api.onrender.com · DB Supabase `zafombwswztvnjikcsdm`.**
  Old QIB untouched (never linked, queried or seeded).
  **ROOT CAUSE.** `_record_id` hashed paper + figure/panel + crop + raw target
  + treatment context but **omitted the biological system**. Crop
  `page_004_cand_0025.png` (PMC12706926) prints **H1792 and A549 side by
  side**, so P62/LC3B/ACTB each collapsed two distinct experiments into one id
  — 12 duplicate keys / 24 of 475 rows; feedback on the H1792 arm could
  rehydrate onto the A549 arm. Diffed every collision field-by-field: **all 3
  groups differed ONLY by `cell_line`/`sample` — one class, one cause.**
  The deeper flaw: **two disagreeing notions of "one experiment"** — search
  grouping had its own composite key.
  **NEW STABLE IDENTITY.** `stable_row_key = <experiment hash>:<lane_index>`;
  hash = sha1(paper doi/pmcid/pmid | figure_label | panel_label | crop filename
  | raw_target | treatment_context | **normalized sample**)[:16], via new
  `record_builder.identity_sample()` (same `sample or cell_line` precedence as
  `_sample_info`; case/whitespace-folded — deliberately NOT applied to target
  labels, where case is semantic: uppercase `P-` is not a phospho marker).
  **Only OBSERVATION data feeds it** — reconciliation outputs
  (modification/experiment_type/ip_bait/protein_status/confidence/needs_review),
  DB serials and display text are excluded and each is pinned by a test, so
  engine improvements can never orphan stored corrections. Lane identity stays
  the reviewed panel's **index**, not its printed condition (immune to the
  display-only lane formatter). **Search grouping now reads that same hash**
  (`stable_row_key` added to the list schema `WesternBlotRecord`), so the card
  boundary and the feedback boundary are one thing.
  **SECOND COLLISION CLASS FOUND (same flaw, opposite direction).** The old
  grouping key carried no treatment context, so on crop `page_005_cand_0034` —
  which holds **two** experiments — it concatenated the 6-lane **Fig 3C (no
  IL-6)** strip and the 7-lane **Fig 3D (with IL-6)** strip into ONE 13-lane
  card for T-Stat3 and β-actin. That is exactly session 7's C1 conflation,
  still live in the UI. **Experiment count 91 → 93 is a CORRECTION, not
  drift**: it splits 2 cards that should never have been one; no flagship query
  changes its card count. Verified in the hosted UI (T-Stat3 now renders 6-lane
  and 7-lane cards with their own Fig 3C / Fig 3D identity lines).
  **UNIQUENESS PROOF.** Artifacts regenerated through the REAL pipeline (not
  patched); diffing each regenerated file against its committed version shows
  **every biological field, provenance envelope and validation flag
  byte-identical, `record_id` the only change**. Corpus + remote DB both:
  **475 rows / 3 papers / 475 distinct `stable_row_key` / 0 duplicate groups /
  93 experiment hashes / 0 null provenance / 21 crop refs valid / 0 legacy QIB
  rows.**
  **FEEDBACK ISOLATION PROOF (real, against cloud).** A = P62/H1792
  (`d95fb4cda43a320f:1`), B = P62/A549 (`8ee3bb5a3555e3cd:1`) — same crop, same
  target, formerly ONE id. Feedback → A: appears on A, **absent on B**. Then a
  full reseed regenerated serials (A 594→1069, B 610→1085): A's feedback
  **rehydrated by stable key onto the new id**, B still clean. Repeated
  end-to-end through the hosted stack. All smoke rows deleted;
  `hiveblot_feedback` back to **0 rows**.
  **DEPLOY.** Render `hiveblot-api` (`srv-da1rbvs9v7es738635ug`), **plan free**,
  Docker, repo `nikhilesh-s/hive`, branch `feature/bio-context-beta`,
  `autoDeploy: false`; deployed commit `bc923bb` → status **live**, `/health`
  200 (~0.15 s warm), and the deployed revision proven new (list rows now carry
  `stable_row_key`). Vercel `hiveblot-beta` production re-pointed to the Render
  origin and redeployed; `ALLOWED_ORIGINS` is the Vercel origin only (never
  `*`). Seeding again used a temporary `hive_seed` role, revoked + DROPped
  after (only `hive_readonly` / `hive_feedback` remain).
  **HOSTED VERIFICATION (all through the public frontend):** `/` and `/search`
  200; `phospho STAT3 Tyr705` 18 rows/3 cards (88.1 expected, reported null —
  distinct; CST 9145), `co-IP PIK3CA` 14/4 with **IP BAIT = PIK3CA** and
  Input/IgG/IP lanes, `CST 9145` 18/3, `P-ERK` 10/2 **Conflicting** with the
  "Why unresolved" sentence and both competing claims and no winner,
  `GAPDH mouse` 31/5 mouse loading-control, `needs review` 20/4,
  `BRCA1 MCF7 olaparib` **0** with scoped copy. Crops served as real PNGs over
  the hosted proxy (442,670 B and 247,631 B, PNG signature verified).
  **15 hosted browser assets scanned: no DSN, no DB user/password, no pooler
  host, no INTERNAL_API_KEY, no Supabase key/JWT, no `NEXT_PUBLIC_*`.**
  Tests: biology **165/165**, reconcile 21/21, loader ok, extract 10/10,
  pipeline 11/11, **stable-row-key 34/34 (NEW suite)**, benchmark 34/34,
  harness 3/3 papers EXACT, api **113/113**, `tsc` clean.
  **Model automation remains future work — the 3/3 EXACT harness is a
  self-consistency check on the reviewed reference set and says NOTHING about
  extraction accuracy on an unseen paper.**
- **2026-08-17 (session 13)** — Claude Code (Opus 5). **ZERO-COST STACK: WEB
  DEPLOYED, API ONE LOGIN AWAY.** Stack is now **Supabase Free + Render Free
  Web Service + Vercel Free**. **Railway is dropped** as the recommended API
  host (kept as a one-line alternative only).
  **WEB IS LIVE: https://hiveblot-beta.vercel.app** — Vercel project
  `hiveblot-beta` (org `nikhilesh-suravarjjalas-projects`), Hobby/free,
  production deploy Ready, HTTP 200 publicly. `API_BASE_URL` +
  `INTERNAL_API_KEY` set on Production/Preview/Development; **neither is
  `NEXT_PUBLIC_*`**. `API_BASE_URL` currently holds a PLACEHOLDER
  (`https://hiveblot-api.onrender.com`) and **must be re-set + redeployed**
  once the real Render host exists — Vercel does not hot-swap env values into
  an existing build.
  **API NOT DEPLOYED — the one blocker is a Render browser login.** Render CLI
  v2.23.0 installed (`brew install render`) but unauthenticated (no
  `~/.render`), so the canonical path is the dashboard Blueprint. Added
  **`render.yaml`** (committed): one web service `hiveblot-api`, `runtime:
  docker`, **`plan: free`**, `dockerfilePath: ./api/Dockerfile`,
  `dockerContext: .`, `healthCheckPath: /health`, `autoDeploy: false`, branch
  `feature/bio-context-beta`; the 4 secrets are `sync: false` (dashboard-only,
  never in git) and `ALLOWED_ORIGINS` is already pinned to the live Vercel
  origin.
  **Render compatibility audited:** CMD already binds `0.0.0.0:${PORT:-8000}`
  so Render's injected `PORT` works and local dev is unchanged; config reads
  pure env vars (no `.env` in the image); `/health` is unauthenticated.
  **Audited and confirmed: the API performs ZERO runtime filesystem writes** —
  Render's ephemeral disk is therefore safe, and Supabase remains the only
  persistence layer (feedback included).
  **`api/crops/` is now TRACKED (21 PNGs, ~6 MB)** — Render builds from the
  GitHub clone, so gitignored crops would have meant no figure evidence in the
  hosted beta; verified all 21 DB `image_crop_ref` values map to a staged file.
  **Supabase re-verified:** still linked to `zafombwswztvnjikcsdm`, 475 rows /
  3 papers / **91 experiment groups**. **Smoke-test feedback rows CLEARED** —
  `hiveblot_feedback` is now **0 rows**, ready for the team.
  **⚠ `stable_row_key` uniqueness is NOT 100% — 463 distinct of 475, 12
  duplicate keys (24 rows).** The session-12 follow-up was never run; this is
  the same pre-existing co-IP defect (the `page_004_cand_0025.png` crop prints
  H1792 and A549 side by side; `_record_id` omits cell line). Feedback on one
  of those rows can surface on its twin. Deploying does not make it worse, but
  it is live in the hosted beta and is disclosed in the team doc.
  Docs: `DEPLOYMENT.md` rewritten around the free stack incl. Render's
  spin-down / cold-start / ephemeral-disk behaviour;
  `research/TEAM_BETA_HANDOFF.md` carries the live web URL and the cold-start
  warning. Tests: biology **165/165**, reconcile 21/21, loader ok, extract
  10/10, pipeline 11/11, benchmark **34/34**, harness **100% EXACT**, api
  **113/113**, web `tsc` clean + production build clean.
- **2026-08-17 (session 12)** — Claude Code (Opus 5). **CLOUD DATABASE LIVE ON
  THE CLEAN BETA PROJECT.** Deployment target is now Supabase
  **`zafombwswztvnjikcsdm`** (`https://zafombwswztvnjikcsdm.supabase.co`,
  us-east-1, PG 17.6). **The old QIB project `belalrbfrndxvdwvjxte` is NO
  LONGER A DEPLOYMENT TARGET** — never link/push/seed to it (empty migration
  history means a `db push` would ALTER Suhas's production tables).
  **Migrations:** repo re-linked; project verified fresh (0 tables, 0
  migrations, no hive roles); `db push --dry-run` showed exactly the canonical
  4-migration chain, no seeds, no `roles.sql`; pre-flight proved all 57 seed
  columns exist in the 73 migration columns; **push applied all 4, all recorded
  in remote history**. **Remote schema verified:** `western_blot_records` 73
  cols, `hiveblot_feedback` 16 cols, **`confidence` = `real`**, `stable_row_key`
  TEXT on both tables, `pg_trgm` 1.6, **17 indexes** (incl. the GIN trigram on
  `target`). **Security verified against `information_schema` + `pg_authid`:**
  `hive_readonly` = SELECT only; `hive_feedback` = INSERT+SELECT on
  `hiveblot_feedback` ONLY with **zero grants on `western_blot_records`** and
  USAGE on only the feedback sequence; neither role is superuser/createrole/
  createdb/bypassrls; both passwords set (SCRAM confirmed — note `pg_roles.
  rolpassword` always reads non-null and proves nothing). Roles are created **by
  the migrations**, not a `supabase/roles.sql`. Seeding needed INSERT, which
  neither restricted role has by design, so a **temporary `hive_seed` role was
  created, used, then revoked and DROPped** (verified: only the two designed
  roles remain). **Seed: 475 rows / 3 papers / 91 experiment groups**, zero
  dropped keys, 0 null `stable_row_key`, 0 null `provenance`, and **zero legacy
  QIB data** (0 `p53` rows, 0 legacy paper_ids). **Cloud verification (local API
  → cloud DB, all green):** `/health`; all 7 flagship searches — `phospho STAT3
  Tyr705` 3 groups/18 lanes, `co-IP PIK3CA` 4 co-IP groups + IP BAIT=PIK3CA,
  `CST 9145`, `GAPDH mouse` 5 groups with DEVELOPMENTAL SERIES on the E14.5/P0/
  P28 panels and correctly **untagged** ligation panels, `needs review`,
  `P-ERK` = MAPK1/MAPK3 **Conflicting** with both claims and no winner,
  `BRCA1 MCF7 olaparib` 0 results with scoped copy; record detail; **crops
  served (1153x909 PNG)**; feedback INSERT + rehydration (2 smoke rows render
  as RESEARCHER FEEDBACK beside the fields); lane-specific durations and
  "varies by lane: 0-60 min"; explicit-submit proven again (30 chars typed +
  2.5 s → **zero** fetches); **21 browser assets scanned: no DSN, no
  INTERNAL_API_KEY, no Supabase key, no `NEXT_PUBLIC_*`**.
  **Deployment prep:** `api/Dockerfile` (+ `Dockerfile.dockerignore`) and
  `scripts/stage_crops.py` (21 crops / 6.2 MB staged into `api/crops/`, so the
  container serves crops with zero code and zero corpus change);
  `DEPLOYMENT.md` rewritten for the new project incl. the **pooler-not-direct**
  rule (`db.<ref>` is IPv6-only; use Supavisor **session mode 5432**, not
  transaction 6543 which breaks asyncpg prepared statements).
  `research/TEAM_BETA_HANDOFF.md` written.
  **NOT DEPLOYED YET — one credential boundary:** Vercel CLI is authenticated
  (`nikhilesh-s`) so web can ship, but no container host is logged in
  (`railway login` needed; no Fly/Render CLI). Web alone is useless without the
  API, so nothing was published.
  **NEW KNOWN ISSUE (pre-existing, not caused by deployment): 12 duplicate
  `stable_row_key` values across 24 of 475 rows.** The co-IP crop
  `page_004_cand_0025.png` prints **H1792 and A549 side by side**; the search
  grouping key includes `cell_line` (so the UI correctly shows 2 cards) but
  `_record_id` does **not**, so P62/LC3B/ACTB collide across the two cell lines
  and feedback on one rehydrates onto its twin. Session 9's "113/113 unique"
  covered the phospho paper only. Fix = add cell line to `_record_id`; that
  rehashes every `stable_row_key` and needs a reviewed reseed, so it is
  deliberately NOT done here. Tests: biology **165/165**, reconcile 21/21,
  loader ok, extract 10/10, pipeline 11/11, benchmark **34/34 (100%)**, harness
  **100% EXACT** on all 3 papers, api **113/113** (incl. migration drift
  guard), web `tsc` clean + production build clean.
- **2026-08-17 (session 11)** — Claude Code (Opus 5). **BETA-TABLE INSPECTION +
  PLAN (READ-ONLY). Nothing altered, in QIB or anywhere.** Suhas created
  `western_blot_records_beta` and `blot_results_beta` inside the QIB production
  database. Full analysis: **`research/supabase_beta_table_plan.md`**.
  **Inspection:** both exist, both **0 rows**, and both are **exact structural
  copies of the legacy production tables** — identical column names, order,
  types, defaults and nullability (diffed field-by-field; only the copied
  functional index is auto-renamed `blot_results_beta_lower_idx`, the signature
  of `CREATE TABLE … (LIKE … INCLUDING ALL)`). So
  `western_blot_records_beta` is 12 columns with **`confidence text`** and a
  pkey-only index — it inherits *every* gap from the legacy audit. Still absent
  project-wide: `hiveblot_feedback` (any form), **`hive_readonly`**,
  **`hive_feedback`**, the trigram index, and any migration history.
  **Gap vs canonical: 61 missing columns** (60 from migration 001 +
  `stable_row_key`), 1 type change (`confidence text → real`, **required** —
  the seed inserts floats and asyncpg is strict), 10 missing indexes, plus a
  whole feedback table. `stable_row_key` itself would port cleanly (plain TEXT
  + b-tree, name-independent). Note numbering: CLI copy `…0004` **is**
  canonical `migrations/003`; there is no fifth migration.
  **RECOMMENDATION — do NOT use the beta tables; wait for Srushti's separate
  HiveBlot project.** The blocker is not effort: `/search` needs the
  `hive_readonly` role and `/feedback` needs `hive_feedback`, and Postgres
  **roles are cluster-level, not table-level**; the trigram index needs
  database-wide `CREATE EXTENSION pg_trgm`. All three land outside the two beta
  tables, against the "do not modify production roles/schema" constraint — so
  Option A **cannot be executed** without a fresh exception from Suhas. Also:
  `supabase db push` is unusable against QIB (empty remote history ⇒ it would
  apply the production-targeted migrations; the only fix writes production
  migration history, also forbidden), so the beta route means hand-pasting a
  ~700-line `_beta` SQL fork that sits **outside** the drift guard, plus code
  edits to `api/app/db.py` (feedback table is hardcoded) and
  `scripts/seed_remote.py` — all of it reverted later. `TABLE_NAME` is already
  env-configurable, so the records table alone would have been config-only.
  **This supersedes session 10's `hive-beta` branch recommendation:** Srushti's
  separate project is the same isolation with no plan upgrade, no per-hour
  branch compute, and HiveBlot ownership. Keep the persistent branch as the
  fallback only if her project stalls. Two items left unverified because they
  need a SQL console (neither changes the recommendation): whether the beta
  `id` default points at production's sequence, and RLS/policy state on the
  beta tables — exact read-only queries are in the plan doc §1.5. Production
  re-verified untouched: 616 + 2 rows. Docs only; api tests 113/113.
- **2026-08-17 (session 10)** — Claude Code (Opus 5). **LEGACY SUPABASE AUDIT
  (READ-ONLY). No production change.** The original hackathon project `QIB`
  (`belalrbfrndxvdwvjxte`, org SuhasKM's-Org, us-west-2, PG 17.6) is now
  linked; CLI 2.113.0, already authenticated. Full findings:
  **`research/supabase_legacy_audit.md`**. Headlines: production `public` holds
  exactly two tables — **`western_blot_records` 616 rows** (5 papers, 64 of
  those rows an exact duplicate of another 64 under a second `paper_id`
  spelling) and **`blot_results` 2 rows** (fabricated demo: `p53 paper 1.pdf`,
  placeholder DOI `10.1234/example.2024`; referenced by no source file).
  **Migration history is EMPTY** — all four local migrations unapplied; prod was
  built by hand, so `db push` must never target it (`create table if not
  exists` would sail past and then ALTER prod). Production's 12 columns are
  exactly `api/db/schema.sql`'s list and order ⇒ **it IS a lineal ancestor of
  the current base table**, with one divergence: **`confidence` is `text`, not
  `real`** (the reviewed seed inserts floats ⇒ asyncpg would hard-fail). Also
  absent: all 60 migration-001 columns, `hiveblot_feedback`, `stable_row_key`,
  the GIN trigram index on `target`, and **both `hive_readonly` and
  `hive_feedback` roles** (verified against the full server role list).
  Legacy data is **not** worth migrating as evidence — it bakes in the banned
  p-prefix heuristic (62 `p53` + 4 `PARP` rows typed `phospho_signaling`), has
  no provenance/UniProt/residue/status, 4 of 6 `paper_id`s are filenames, and
  `confidence` is a constant `'0.9'`. Its one real value is a **5-paper
  shortlist for re-ingestion** through the current pipeline (zero paper overlap
  with the reviewed corpus). **Security finding (no action taken): both tables
  are fully readable with the project's anon key** — RLS is off or not
  restricting anon reads; write exposure deliberately untested (a probe would
  have mutated prod) — verify in the dashboard.
  **Recommendation (NOT implemented): a Supabase branch `hive-beta`, created
  PERSISTENT, not preview** — the beta must outlive any PR because collecting
  `hiveblot_feedback` from UCSF researchers IS the deliverable. Branching is
  available (`supabase branches list` → `[]`). Create **without `--with-data`**,
  re-link to the branch ref, `db push` the four migrations, verify
  `confidence real` (branch-only `ALTER` if the parent's `text` carries over),
  set the two role passwords, then `seed_remote.py` → 475 rows. Fallback if
  branching is plan-gated: a separate standalone project. No files outside
  `research/` + this HANDOFF changed; no tests affected.
- **2026-08-16 (session 9)** — Claude Fable 5. **FINAL INTERNAL-BETA FIX PASS.**
  All reproducible manual-beta findings fixed; no scientific regressions.
  **P0 feedback persistence/rehydration — diagnosed, fixed durably.** The
  manual P-ERK correction HAD persisted (row 6); the gap was (a) no retrieval
  path and (b) a worse latent hazard: reseeds regenerate serial ids, orphaning
  ALL feedback (verified: every stored row pointed at a dead id). Fix at the
  data layer: **migration 003** adds `stable_row_key` (= record-hash:lane_index,
  computed from reviewed observation data, reseed-proof) to both tables;
  `_record_id` strengthened with crop + treatment context so the Fig 3C/3D twin
  records no longer collide (20/20 distinct; 113/113 unique row keys).
  `GET /records/{id}/feedback` rehydrates by serial id OR stable key; the
  evidence panel shows prior feedback as a clearly-labeled RESEARCHER FEEDBACK
  annotation beside (never inside) the extraction. **Proven live: feedback
  submitted on id 4019 rehydrated on id 4494 after a full reseed.** Pre-003
  feedback rows (1–6) lack stable keys and stay orphaned-but-preserved.
  **P0 lane-series representation:** series-derived treatment candidates are
  now tagged `lane_series`; the UI renders "varies by lane: 0–60 min (see
  lanes below)" instead of a false "not reported" + pick-a-winner candidate
  list. **P0 design-tag false positives:** DOSE SERIES now requires explicit
  dose semantics (unit in lanes or context); developmental-stage lanes
  (E14.5/P0/P7/P28M) get their own DEVELOPMENTAL SERIES tag; ligation labels
  (L5d/DL14d) abstain. Verified on GAPDH mouse. **P0 multi-condition summary:**
  TREATMENT now reads e.g. "IL-6 (± CL-E, Bis II, U0126)" — co-conditions taken
  verbatim from the group's own lane labels. **P0 conflict explanation:** a
  generated "Why unresolved: …" sentence built only from the structured
  candidates (never picks a winner). **P1:** co-IP cards render "co-IP" + an
  IP BAIT field (from the panel's printed IP: lane); "DOI:" label; scoped
  zero-result copy ("…in the current HiveBlot beta dataset… does not mean no
  such evidence exists in the literature"). Supabase flow is now 4 migrations
  (docs + CLI copies + drift guard updated). Tests: engine suites green,
  benchmark 34/34, harness 100% EXACT, **api 113/113**, tsc clean. All seven
  flagship queries verified in-browser incl. zero-result and reseed-survival.
- **2026-08-13 (session 8, night sprint)** — Claude Fable 5. **MANUAL-TEST FIXES +
  SUPABASE READINESS.**
  (1) **Search is explicit-submit only** (manual issue 1): typing never fires a
  request; Enter or the new SEARCH button submits; submitted queries land in the
  URL via replaceState (shareable/refresh-safe); `?q=` auto-load unchanged and
  now also populates the input box. Browser-verified: 12 chars typed + 2 s wait
  → zero /api/search requests; button + real-KeyboardEvent Enter both submit.
  (2) **Experiment-card identity** (manual issue 2): each grouped card shows an
  identity line — a deterministic design tag derived ONLY from the group's own
  lane labels (≥3 pure timepoints → TIME COURSE; ≥3 shared-prefix distinct
  trailing numbers → DOSE SERIES) plus the reviewed record's verbatim
  `treatment_context` (truncated). Nothing invented; the Fig 3C/3D records
  carry their figure labels because the reviewed context text starts with them.
  The flagship query's three cards now read: TIME COURSE / "Fig 3D: …
  inhibitor matrix" / DOSE SERIES. Also removed the TREATMENT-field fallback to
  treatment_context (was duplicating the new identity line on co-IP cards).
  (3) **`IL-6 · 3D` RESOLVED — it was a fabricated duration** (manual issue 3):
  the paper never states a 3-day treatment; the case-insensitive duration regex
  parsed the FIGURE REFERENCE "Fig 3D" in the treatment context as "3 D(ays)"
  (same trap: "Fig. 3H" → 3 hours, "3D culture" → 3 days). Engine fix, two
  layers: single-letter units h/d must be lowercase (multi-letter units stay
  case-insensitive via scoped (?i:)), and `is_figure_reference_number()` guards
  every dose/duration/series match against a preceding fig/figure/panel
  reference (a rejected figure-list span is also consumed so its trailing
  number cannot leak back as a single). "Figure 2, 4 h exposure" keeps its real
  4 h. Phospho paper regenerated: Fig 3D records now duration=MISSING (the
  captured context states no duration). 10 new regressions.
  (4) **Lane readability** (manual issue 4): display-only formatter — trailing
  +/− state markers get colons and " / " becomes " · " ("IL-6: + · CL-E: −");
  conjunction "+" ("CL-E + Bis II") untouched; semantics unchanged.
  (5) **Supabase CLI readiness**: `supabase/config.toml` + timestamped
  `supabase/migrations/` copies of the canonical SQL, `scripts/
  sync_supabase_migrations.py`, and a pytest drift guard (byte-equality) so
  `supabase db push` and the SQL-editor flow can never diverge. Role grants
  audited: hive_feedback = INSERT+SELECT on hiveblot_feedback only, zero grants
  on western_blot_records. DEPLOYMENT.md rewritten: exact CLI sequence (login →
  link → db push --dry-run → push → role passwords → seed_remote.py, expect 475
  rows), exact env-var NAMES from api/app/config.py, 8-step smoke checklist.
  Browser-verified end-to-end: flagship query → 3 experiments (18 lanes) with
  distinct identities; co-IP PIK3CA → 4 grouped co-IP experiments, bait/IgG/
  Input intact; evidence panel + crop (1153 px PNG) + 33 feedback controls on
  grouped cards. Tests: **biology 165/165**, api **112/112**, benchmark 34/34,
  harness self-test 100% EXACT, tsc clean. Model creds + cloud Supabase:
  re-checked, still absent (user actions below).
- **2026-08-13 (session 7)** — Claude Fable 5. **REVIEW SWEEP + CROP SERVING +
  RULE HARDENING.** Three parallel review agents ran; main agent implemented.
  (1) **Figure crops now render in the evidence panel**: `GET /records/{id}/crop`
  serves the record's own panel PNG (path from the DB column only, validated
  inside `CROP_BASE_DIR`, .png-only; 404→text fallback in deployments without
  the archive; 5 new API tests incl. traversal). Verified live end-to-end.
  (2) **Band-pattern rules hardened** — the independent probe-driven review
  (`research/band_pattern_scientific_review.md`) found 4 ship-blockers, all
  fixed with regressions: negation now abstains ("no smearing" no longer
  asserts smear); singular "higher-MW band" is not a ladder; caption-derived
  patterns on multi-lane panels are AMBIGUOUS, never per-lane SUPPORTED;
  absent+pattern contradictions raise BAND_PATTERN_STATE_MISMATCH (+ eval
  stamps corrected to present lanes only → 26 doublet lanes). Plus:
  "polyubiquitin smear"→ladder via containment pruning; count guard for
  "Fig. 3 bands"/"n = 3"/"1-2 bands"; parenthetical patterns no longer leak
  across "and".
  (3) **Demo dry-run** (`research/demo_readiness_review.md`): every scripted
  query verified live against the API; demo doc fixed (`needs review P-ERK`
  step, crop beat, 91-experiments close line, 20/min rate-limit warning).
  (4) **`scripts/seed_remote.py`** closes the DEPLOYMENT.md remote-seed TODO.
  (5) **Independent scientific QA delivered and acted on**
  (`research/independent_scientific_qa.md`: 3 Critical / 12 Major / 8 Minor /
  12 verified-correct). All three Criticals FIXED + regression-tested:
  **C1** — one CV crop (phospho paper cand_0034) held TWO experiments (Fig 3C
  + 3D); the collapsed observation asserted IL-6 on the Ser727 arm although
  the legend says Fig 3C ran WITHOUT IL-6. Reference data corrected to the
  printed 6-/7-lane matrices (unverifiable band states → `uncertain`); README
  correction note added. Phospho paper now 20 records / 113 rows; DB 475.
  **C2** — engine bug: an anti-ubiquitin antibody's own antigen name asserted
  `modification_type=ubiquitination` SUPPORTED (same failure class as the
  banned p-prefix rule). detect_modification now treats a mod-word that IS the
  whole target as protein identity; "ubiquitinated EGFR" still claims.
  **C3** — the session-4 self-audit contained false claims; correction banner
  added, independent QA is authoritative. Majors fixed: **M6** (µ-sign doses
  were dropped; series regex fabricated "1 nM" from "BafA1" — both fixed),
  **M7** (ACTB/TUBA1B now loading controls — 81 rows were misclassified),
  **M9** (doubtful BEX2 doublet removed; QA-confirmed Fig 1C LC3B doublet
  added; β-actin Greek-letter now resolves via beta-normalization), **M10**
  (README coverage note: Fig 5A/5B fell below the CV threshold — post-filter
  count ≠ paper content). Still open (documented, next-queue): M5 per-lane
  dose coverage (lane labels carry bare numbers, unit lives in the axis
  label), remaining Majors/Minors listed in the QA file.
  Creds RE-CHECKED: model backend + cloud Supabase both still absent — those
  two user actions remain the only blockers to automated extraction and
  hosted deployment. Tests: **biology 155/155**, api 111/111, benchmark 34/34,
  harness self-test 100% EXACT, tsc clean.
- **2026-08-13 (session 6)** — Claude Code. **M2 CLOSED: descriptive band
  multiplicity / smear representation.** Additive `BandObservation` fields
  `band_pattern` (single|doublet|multiple|smear|ladder|uncertain) + `band_count`
  (only when literally countable/stated) + `band_notes` (verbatim wording), each
  a full EvidenceField envelope. **Additive to `band_state`, never a replacement**
  (a smeared/doublet band is still `present`); null pattern = "source didn't
  say", NOT "single band". Two evidence channels only: (1) deterministic parsing
  of explicit wording (`biology.detect_band_pattern`: doublet, "two/three
  bands", smear(ed), ladder-like, polyubiquitin ladder/conjugates, high-MW
  species, multiple/additional/non-specific bands, single band; hedged wording →
  AMBIGUOUS; conflicting descriptions → uncertain), **clause-scoped to the
  target** so "LC3B resolved as a doublet, while ACTB…" never marks ACTB; and
  (2) explicit observer claims in Stage-2 output (contract updated with strict
  omit-when-in-doubt + no-identity-inference rules). **False-positive audit on
  the real 452-band set: with text-only evidence, zero patterns asserted**
  (correct — no paper states multiplicity wording); observer doublet claims
  were then added ONLY for the 4 targets visibly resolving as two bands in the
  inspected crops (LC3B, BEX2, P-ERK 1/2, T-ERK 1/2 → 30 lanes), each carrying
  image provenance + verbatim note. Phospho+total pairs, loading controls and
  multi-row panels remain pattern-free (multiplicity belongs to ONE band
  observation, never to row count). Exposed in `GET /records/{id}` + evidence-
  panel lane strip with an explicit "descriptive only — no isoform/cleavage
  interpretation" note. LIMITATIONS: no image-based smear/multiplicity detection
  (text/observer evidence only); no isoform/cleavage/dimer assignment ever; the
  no-creds automated model has not been tested against the new contract fields.
  Tests: **biology 124/124** (+30), api 106/106, benchmark 34/34, harness
  self-test 100% EXACT, tsc clean. Demo artifacts + DB regenerated (452 rows).
  Model creds re-checked: still absent. Optional QA sub-agent not spawned (the
  empirical zero-FP audit on all real bands stood in for it; flag for the
  independent pre-UCSF QA pass).
- **2026-08-13 (session 5, hackathon day)** — Claude Code. **RESULT GROUPING + MULTI-DOSE
  REPRESENTATION.** (1) Search results now group into one card per EXPERIMENT
  (paper + panel + target + experiment type + **cell line** + **modification label**)
  instead of one card per lane row: `phospho STAT3 Tyr705` reads "3 experiments
  (15 lane records)". The cell-line component is load-bearing — one real crop
  (PMC12706926 `page_004_cand_0025`) prints **H1792 | A549 side by side**, and the
  first key merged them. Verified against all 374 demo rows: 77 groups, **zero**
  groups containing >1 distinct target / canonical target / modification / residue /
  experiment type / UniProt / figure / cell line / catalog / organism.
  (2) **Multi-dose / time-course representation (QA finding M1 closed).** The old
  scalar took `values[0]`, which reported the **CL-E dose (60 µg/ml) as the IL-6
  dose** and **60 min as THE duration of a 0–60 min time course**. Now:
  enumerations sharing one unit expand (`extract_dose_series` /
  `extract_duration_series`: "10, 30 and 60 µg/ml" → 3 values; "(0, 5, 10, 20, 30,
  60 min)" → 6 timepoints); >1 distinct value ⇒ the panel scalar becomes
  **value=null, status=AMBIGUOUS with every value preserved as a candidate**
  (DB scalar NULL, never a wrong number); per-lane values are parsed from each
  lane's own printed condition into new `BandObservation.lane_dose/lane_duration`
  and served by `GET /records/{id}`. "for the indicated times/doses" is
  kind-specific, so a time course keeps its settled single stimulus concentration.
  Tests: **biology 94/94** (+17), api 106/106, benchmark 34/34, harness self-test
  100% EXACT, tsc clean. Demo artifacts + local DB regenerated (452 rows).
  **Model backend still blocked — no credentials present (re-verified).**
- **2026-08-13 (session 4)** — Claude Code (Opus 4.8). **SCIENTIST-REVIEW BETA COMPLETE.**
  Full provenance + researcher-feedback loop live end-to-end locally:
  `GET /records/{id}` serves curated field-level evidence envelopes (value /
  status / source snippets / competing candidates); the card's evidence panel is
  now a full-width accordion with the normalization chain (raw → canonical →
  UniProt), per-field audit rows + ✓/✗/not-useful/suggest-correction controls,
  equal-weight CONFLICTING candidate display ("Which is right?"), antibody
  roles, lane strip, `+ Missing information?`, result flagging, post-search
  "did HiveBlot understand?" prompt, and a general BETA FEEDBACK widget.
  **Migration 002** adds `hiveblot_feedback` + insert-only `hive_feedback` role:
  human corrections persist BESIDE the AI extraction (model_value snapshot),
  never over it. Verified in the real browser: feedback rows land in Postgres
  from UI clicks. Also: home-page search now routes to /search (legacy table
  retired); advanced-filters bar; `eval/model_comparison/compare_records.py`
  harness (self-test 100% EXACT on all 3 papers); boto3 installed → Bedrock
  path ready pending creds; `DEPLOYMENT.md`; `research/HACKATHON_DEMO_FLOW.md`;
  scientific QA self-audit (`research/demo_scientific_qa.md`: 0 critical open,
  2 major representational). Tests: engine 138 assertions green, benchmark
  34/34, **api 104/104**, web tsc clean. NOTE: two of three planned sub-agents
  (independent QA, eval design) were killed by session limits; QA was done as a
  self-audit and the eval harness written directly — re-run independent QA
  before UCSF.
- **2026-08-12 (session 3)** — Claude Code (Opus 4.8). **LIVE SEARCH LOOP WORKS.**
  `phospho STAT3 Tyr705`, `phospho AKT Ser473`, `co-IP PIK3CA`, `CST 9145`,
  `GAPDH mouse` all return real paper-derived Evidence Records in the running
  HiveBlot frontend. Stood up an **embedded local Postgres** (`scripts/local_db.py`,
  pgserver — no cloud creds needed) with schema + migration 001 + **452 rows from
  3 real papers**; added a **deterministic biological SQL generator**
  (`api/app/bio_query.py`) for the no-OPENAI_KEY path; fixed a latent sql_guard
  bug (AND/OR rejected with sqlglot≥30); made the Supabase client lazy; processed
  papers 2+3 (mouse standard PMC9559174, co-IP PMC12706926) agent-in-the-loop;
  threaded **organism into UniProt** (mouse accessions correct); fixed 4 more
  structural biology bugs found by real-paper inspection (one-letter phosphosites,
  page-level co-IP bleed, bare-mention fake total claims, page-blob reported-MW).
  Tests: biology 77/77, engine suites green, benchmark 34/34, api 95/95.
- **2026-08-12 (session 2)** — Claude Code (Opus 4.8). **First real paper end-to-end.**
  Built the `.venv` (py3.12) + installed ingestion deps; live UniProt transport
  validated; ran a real phospho-STAT3 paper (PMC12856536) through the full records
  path via **agent-in-the-loop** Stage-2 extraction (no live model backend available).
  Field-by-field inspection found + fixed a **structural identity bug** (`P-ERK 1/2`→
  EPHB2 false-friend; p53/p38/PARP prefix mangling; ambiguous-family-as-SUPPORTED),
  with regression tests. Widened the API model additively; rebuilt the result card;
  wrote `research/RESEARCH_SYNTHESIS.md`. Demo run committed under `eval/demo/`.
- **2026-08-12 (session 1)** — Migrated Phase 2+3 into `/hive`; wired the Evidence
  Record engine into `pipeline.py` behind `WBM_EXTRACTION_MODE`; validated UniProt parsing.

## Product North Star
HiveBlot is a **biologically accurate Western blot evidence search / context
platform**. It turns Western blot figures, captions, methods, and paper context
into structured, searchable, **auditable** experimental evidence, so a researcher
can move between what a blot shows, the conditions that produced it, and
comparable evidence in the literature.

- **Biological validity is the #1 beta priority** — above feature count and UI polish.
- **HiveBlot and AGeneTic are separate projects.** AGeneTic must NOT shape this
  repository, its schema, or its scope.
- **Immediate user target: UCSF wet-lab researchers.**
- This is a **beta** whose explicit purpose is to collect detailed researcher
  feedback. Surface uncertainty; never present a guess as a settled fact.

## Canonical Repository
- **Repo:** `git@github.com:nikhilesh-s/hive.git` (this `/hive` working tree).
- **Branch:** `feature/bio-context-beta` (do NOT build features on `main`).
- **Latest finalized commit before this handoff entry:** `f3455ce` (visible
  search-workspace alignment correction). This theme-system change commits on top; run
  `git log -1` for the exact current tip after this handoff commit lands.
- The old `Ananya-Jha-code/QBI` repo is **superseded**. Do not build there.

## Current Architecture
- **Frontend** — `web/` (Next.js App Router, TypeScript). Search UI → `web/app/api/search/route.ts` → API.
- **Backend API** — `api/` (FastAPI). Split routers: `internal` (frontend-only, `INTERNAL_API_KEY`)
  and `external` (agent-facing `/v1/search`, `AGENT_API_KEYS`). Security: `sql_guard.py`
  (AST validation of LLM-generated SQL) + a low-privilege `hive_readonly` Postgres role.
- **Supabase (Postgres)** — table `western_blot_records` (`api/db/schema.sql`), extended
  additively by `migrations/001_evidence_record.sql` with the biological Evidence Record columns.
- **Literature / PDF ingestion** — `western_blot_miner/` package. Free NCBI E-utilities +
  BioC (`pmc.py`) for literature; local PDF render via PyMuPDF (`pdf_preprocess.py`).
- **Deterministic CV filtering** — `pdf_preprocess.py` (OpenCV): renders pages, scores
  panel candidates (saturation / dark-fraction / horizontal morphology / intensity
  profiles), keeps only above-threshold crops before any model call. This is the cheap
  first stage of the cascade.
- **Biological Evidence Record engine** — `evidence_record.py` (schema), `biology.py`
  (deterministic biology), `reconcile.py` (evidence-hierarchy reconciliation),
  `record_builder.py` (assembly + validation/anomalies), `extract_records.py` (Stage 2→3→4).
- **LLM abstraction** — `llm_client.py`: **Bedrock-first** (`converse`), plus Anthropic /
  OpenAI-compatible / Mock backends. No RunPod dependency.
- **UniProt resolver** — `resolve.py`: live UniProt REST (reviewed, organism-scoped) +
  on-disk cache + local-map fallback. Never guesses an accession.

Cascade (low-compute by design): deterministic Stage 1 → cheap hosted model Stage 2 →
validation Stage 3 → expensive-model escalation Stage 4 only for ambiguous/conflicting.

## Provenance & Feedback (session 4)
- **Record detail**: `GET /records/{id}` (internal auth) → curated `RecordDetail`:
  source identity, biological scalars, `fields{name → {value, confidence, status,
  sources[{type,text}], candidates[]}}` extracted from the provenance JSONB,
  antibodies (role + detection vs association confidence), per-lane bands,
  validation. Shaping: `api/app/record_detail.py`. Web proxy: `/api/record/[id]`.
- **Feedback**: `POST /feedback` (internal auth) → `hiveblot_feedback`
  (**migration 002**) via the **insert-only `hive_feedback` role**
  (`DB_FEEDBACK_URL`) — physically cannot touch `western_blot_records`.
  Scopes: `field` (correct/incorrect/not_useful/missing_context + suggested_value),
  `record` (9 flag types), `missing_field`, `search` (understood yes/partially/no),
  `ui`. `model_value` snapshots the AI claim at feedback time → every row is an
  auditable "AI claim → human correction" pair; corrections are NEVER auto-applied.
  Web proxy: `/api/feedback` (key-allowlisted); anonymous localStorage session id.
- **Frontend**: `EvidencePanel.tsx` (full-width accordion: normalization chain,
  per-field audit + feedback, conflict candidates "Which is right?", antibodies,
  lane strip, missing-info + flag-result forms, DOI link), `SearchFeedback.tsx`,
  `BetaFeedback.tsx`, `FiltersBar.tsx` (persistent sidebar that composes queries
  for the deterministic parser). Home-page search now routes to `/search?q=…`
  (legacy table retired).

## Completed Work
- **Phase 1 — Repository audit / canonical architecture.** Identified the real system
  and canonical components across the messy QBI branches.
- **Phase 2 — Biological schema + phospho classification fix.** `biology.py`; removed the
  `target.startswith("p")` heuristic; additive `migrations/001`. Tests: **test_biology 38**,
  **test_loader_enrichment 18**.
- **Phase 3 — Evidence Record + provenance + reconciliation + resolver + benchmark.**
  Field envelope, evidence hierarchy, conflict handling, UniProt resolver, Bedrock
  abstraction, antibody detection-vs-association, co-IP roles, MW reported-vs-expected,
  validation/anomaly flags. Tests: **test_reconcile 21**, **test_extract_records 10**;
  **eval benchmark 34/34** field-level across 4 seed cases.
- **Migration → /hive**: engine + migrations + eval brought into the canonical repo.
- **Pipeline wiring**: `pipeline.py` now supports `WBM_EXTRACTION_MODE=records`, routing the
  OpenCV panel candidates through the Evidence Record engine (`run_records_stage`); legacy
  path preserved. **113 assertions + 34/34 benchmark verified from `/hive`**
  (test_biology 53, test_reconcile 21, test_loader_enrichment 18, test_extract_records 10,
  test_pipeline_records 11) + **api pytest 81/81**.
- **UniProt resolver live-validated**: parsing checked against the live UniProt API via
  stdlib urllib — STAT3→P40763 (88.1 kDa), AKT1→P31749, TP53→P04637, EGFR→P00533,
  GAPDH→P04406, all exact. **`requests` transport now also live-validated** in the venv.
- **Session 2 — first real paper end-to-end** (`eval/demo/phospho_PMC12856536/`):
  Jang et al. 2026, DOI 10.3892/br.2026.2108, PMC12856536 (phospho-STAT3, Hep3B, IL-6).
  PDF → PyMuPDF → OpenCV (55→9 candidates) → **agent-in-the-loop** Stage-2 → build →
  reconcile → **live UniProt** → validation → **18 Evidence Records / 90 Supabase rows**;
  the 4 bar-chart candidates correctly produced 0 records. Verified correct: phospho vs
  total split, Tyr705/Ser727 residues, loading-control (β-actin), treatment parse
  (IL-6 10 ng/ml, 60 min), expected-MW 88.1 kDa, reported-MW null (never conflated).
  *Transport note:* no live model backend was available, so Stage-2 was performed by
  the agent (real observations in `responses_observed.json`); ALL downstream biology is
  the real production path. Reproducible via `eval/tools/manual_pipeline.py`.
- **Structural bug fixes (session 2, with tests):** `biology._core_symbol` rewritten —
  it stripped a lone `p`/`P` from any p-word (`p53`→`53`, `p38`→`38`, `PARP`→`ARP`),
  ignored total-protein `T-`, and dropped isoform suffixes (`P-ERK 1/2`→`ERK`→ UniProt
  **EPHB2**, a gene-synonym false-friend). Now: separators required for p-/t- stripping,
  glued lowercase-`p` only before uppercase, isoform preserved (`ERK 1/2`→`ERK1/2`).
  Resolver: curated **ambiguous families win over UniProt** (ERK→MAPK1/MAPK3, never one
  wrong accession). `record_builder`: an ambiguous-with-family resolution stays AMBIGUOUS
  (was falsely SUPPORTED) → flips `needs_review`. Tests: **test_biology now 53** (added 15).
- **API widened (additive):** `api/app/schemas.py::WesternBlotRecord` gained the
  migration-001 Evidence Record fields as Optional (Pydantic was silently dropping DB
  columns the frontend never received). The giant `provenance`/`validation` JSONB blobs
  are intentionally kept OUT of list responses. **api pytest 81/81.**
- **Frontend result card rebuilt** (`web/components/DatabaseResultCard.tsx`): biological
  headline (`STAT3 · phospho-Tyr705`) + review badge (Supported / Needs review /
  Conflicting) + antibody/treatment/band/MW (reported≠expected) + an evidence panel
  ("Why HiveBlot says this"). Additive + guarded (legacy rows still render); `tsc` clean.
- **Research tracks delivered** (`research/`): `biologist_western_workflow.md`,
  `biopharma_workflows.md`, `frontend_integration_plan.md`, `benchmark_candidates.md`
  (+ `eval/candidates.json`, 26 verified papers), `real_pipeline_report.md`, and the
  integration `RESEARCH_SYNTHESIS.md`.
- **Session 18 — Search-results IA redesign**: `/search` now keeps the search
  bar on top, moves filters into a persistent left sidebar with explicit Apply,
  shows removable active chips above results, and lays each desktop result card
  out as experiment information, figure preview, and evidence/source. This is a
  frontend-only change; `/api/search`, record detail, evidence feedback, schema,
  and local/production env requirements are unchanged.

## Current Biological Contract
Every important field is an **Evidence Field envelope**: `{value, confidence, status,
sources, candidates}` — **field-level** confidence, not just record-level. Statuses:
- **SUPPORTED** — evidence agrees; value is settled.
- **AMBIGUOUS** — under-supported or resolver returned multiple candidates; value is a
  best-guess flagged unsettled.
- **CONFLICTING** — credible sources disagree. **`value = null`** (never a falsely settled
  scalar); competing **candidates + their evidence are preserved** for review/repair.
- **MISSING** — not reported. Preserved in the record but not given prominent UI treatment;
  surfaces when relevant to a query, evidence review, or feedback.

Other invariants: **raw source wording is always preserved** alongside any normalized value;
**provenance** (which source: antibody / caption / methods / model_target / image / uniprot)
travels with each field; a disputed modification keeps its residue **unsettled** too.

## Known Biological Edge Cases (current gaps)
- **FIXED (session 3) — one-letter phosphosites in row labels.** `p-AKT (S473)`,
  `p-RPS6KB1 (T389)`, `p-EIF4EBP1 (S65)` now yield residue+position (the phospho marker
  and site share one short label, satisfying the one-letter context guard). Bare `S473`
  without a marker still never claims phospho.
- **FIXED (session 3) — page-level co-IP bleed.** co_ip now requires panel-scoped
  evidence (IP-role antibody / co-IP caption / IP:,IgG,input lane labels); a methods-only
  mention becomes a non-settling `co_ip_context` flag. `ip_bait` extraction follows the
  same scoping.
- **FIXED (session 3) — bare mentions are not total claims.** "PI3K/AKT/mTOR signaling"
  no longer manufactures a `MODIFICATION_CONFLICT` against a phospho row; only explicit
  `total X` / `T-X` / `pan-X` wording asserts total, and mixed forms still abstain.
- **FIXED (session 3) — page-blob reported MW.** A kDa figure counts as reported only
  near a mention of the target's core symbol (caption-only fallback when the core is
  absent from a short caption). No more "BEX2 reported 70 kDa" from ladder text.
- **FIXED (session 3) — phospho-specific antibody vs uppercase P- label.** Uppercase
  `P-` is never a phospho *marker* (P-selectin, P-cadherin), but an explicit
  `phospho_specific=true` antibody claim now prevents settling the row as total:
  `P-ERK 1/2` + CST #4370 → modification CONFLICTING, value null, needs_review.
- **NEW (session 3) — organism threading.** `biology.organism_taxon_id` maps explicit
  human/mouse/rat wording → taxon id for the UniProt query (default human 9606, as
  before). Mouse validated live: Stat3→P42227, Gapdh→P16858, Actb→P60710, Tuba1b→P05213.
  Cell-line→organism inference is still NOT used for resolution (only explicit claims).
- **FIXED — ERK/family shorthand false-friend.** `P-ERK 1/2` used to resolve to EPHB2
  (P29323); now resolves to the ambiguous **MAPK1/MAPK3** family (status AMBIGUOUS,
  `needs_review=true`, no single accession). Curated ambiguous families now beat a
  UniProt synonym hit.
- **P-ERK 1/2 is NOT classified as phospho** (mod=`-`, experiment=`standard_western`)
  because there is no explicit site and `P-` alone isn't accepted as phospho evidence.
  Conservative-correct, but the phospho-specific antibody (rank-1) is a hint we don't yet
  use for site-less phospho labels — candidate improvement.
- **Non-human UniProt resolution ordering** — resolver defaults to `organism_id=9606`;
  mouse/rat targets can resolve wrong or expected-MW wrong until organism is threaded in.
- **Unusual phospho notation** far from the target mention (e.g. glued `STAT3(pY705)`, or
  "phosphorylated at Y705" across a clause) can be missed → falls back to antibody/model.
- **Antibody-to-panel association ambiguity** — "which antibody detected which row" in a
  dense reagents paragraph is *flagged* via `association_confidence`, not fully solved.
- **Dual modifications** (e.g. cleaved AND phospho on one target) → treated as a conflict,
  not yet represented as co-occurring.
- **FIXED (session 5) — multi-dose / time-course collapse.** Enumerated series now
  expand; a panel with >1 distinct dose/duration keeps `value=null` + AMBIGUOUS +
  candidates instead of asserting one lane's value (which had cross-attributed the
  CL-E dose to IL-6). Per-lane values live on `BandObservation.lane_dose` /
  `lane_duration`, parsed only from that lane's own printed condition.
- **IP-bait heuristic** (`_first_gene_after`) is best-effort; robust for "anti-EGFR", brittle in messy methods.

## Current Technical Blockers
- **RESOLVED — real paper end-to-end**: done (session 2, `eval/demo/phospho_PMC12856536/`).
- **RESOLVED — ingestion deps**: `.venv` (py3.12) at repo root has PyMuPDF, opencv-headless,
  numpy, requests, pydantic, anthropic. Recreate with
  `python3.12 -m venv .venv && .venv/bin/pip install -r western_blot_miner/requirements.txt`.
- **RESOLVED — `requests` / UniProt transport**: installed + live-validated in the venv.
- **RESOLVED — representative PDFs**: 3 real open-access PDFs in `research/papers/`
  (standard PMC9559174, phospho PMC12856536, co-IP PMC12706926); gitignored (fetch via
  the PMCIDs in `research/real_pipeline_report.md`).
- **OPEN — no live model backend** (unchanged, re-verified session 3: no `~/.aws`, no
  `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`/`WBM_LLM_*`). All three real papers used
  **agent-in-the-loop** Stage-2 (honest, documented per demo README). For an automated
  run set `WBM_LLM_BACKEND` + matching creds, then diff against
  `eval/demo/*/responses_observed.json` + `evidence_records.json` as reference.
- **WORKED AROUND — cloud Supabase still not provisioned** (`SUPABASE_URL`/`KEY` empty
  in `api/.env`), but the live loop no longer needs it locally: `scripts/local_db.py`
  runs an embedded Postgres (pgserver, data in gitignored `.localdb/`), applies the
  SAME `api/db/schema.sql` + `migrations/001` (pg_trgm index skipped locally — not
  bundled), creates `hive_readonly`, and loads the demo rows. `api/.env`'s
  `DB_READONLY_URL` points at it. `/search` runs asyncpg-only, so against this DB the
  search path is the real production path; PostgREST-only endpoints (`/proteins`, `/`)
  still need real Supabase. **Cloud Supabase remains a user action for the hosted
  beta**: create the project, run schema+migration, load `eval/demo/*/supabase_rows.json`,
  fill `SUPABASE_URL`/`SUPABASE_KEY`/`DB_READONLY_URL`.
- **NOTE — /search SQL generation without OpenAI**: with `OPENAI_KEY` empty, /search
  uses the deterministic biological parser (`api/app/bio_query.py`) — protein,
  phospho-site (Tyr705/S473), vendor+catalog, co-IP, loading-control, needs-review,
  cell-line terms — through the same `sql_guard` + read-only role. With a key set, the
  legacy OpenAI NL→SQL path is unchanged (bio parser is the fallback on its failure only
  when no key; generation errors still 502).

## Immediate Next Task
~~Provenance detail endpoint + researcher feedback system + evidence UI~~ — **DONE (session 4)**.
~~Result grouping + multi-dose/time-course representation~~ — **DONE (session 5)**.
~~Manual-test fixes (search submit, card identity, IL-6·3D, lanes) + Supabase CLI prep~~ — **DONE (session 8)**.

~~Legacy Supabase production audit~~ — **DONE (session 10)**,
`research/supabase_legacy_audit.md`.
~~Beta-table inspection + plan~~ — **DONE (session 11)**,
`research/supabase_beta_table_plan.md`.

~~Wait for Srushti's clean Supabase project~~ — **DONE (session 12)**: linked,
migrated, seeded, verified on `zafombwswztvnjikcsdm`.

~~Deploy the web app~~ — **DONE (session 13)**: https://hiveblot-beta.vercel.app

~~Create the Render service, re-point Vercel~~ — **DONE (session 14)**.
~~Fix the duplicate `stable_row_key`~~ — **DONE (session 14)**, 475/475 distinct.
~~Search-results information architecture redesign~~ — **DONE (session 18)**,
frontend-only, using the provided `/images/STATE3.png` preview asset for STAT3
cards.
~~Search-results row refinement~~ — **DONE (session 19)**, frontend-only:
lighter wide rows, centered preview, compact existing-data chips, lighter
source metadata, compact right-aligned evidence action.
~~Dedicated treatment/lanes result column~~ — **DONE (session 20)**,
frontend layout-only: treatment and all lane chips now occupy their own
desktop column immediately after primary identity, with medium/mobile reflow.
~~Sample/experiment column + compact metadata rebalance~~ — **DONE (session
21)**, frontend layout-only: removed the large evidence/source column from the
main card, moved sample/experiment into their own column, and kept source
metadata compact beside tags.
~~Hide search-result evidence panel interaction~~ — **DONE (session 22)**,
frontend presentation-only: `View Evidence` and the expandable evidence/
feedback panel are no longer shown from result cards; underlying evidence code
and routes remain.

**The hosted internal beta is READY to distribute.**
Send `research/TEAM_BETA_HANDOFF.md` + https://hiveblot-beta.vercel.app.

**NEXT, in order:**
0. **Nik: read `research/team_delegation/NIK_FOUNDER_LEARNING.md`, map people
   to workstreams A–D (`research/team_delegation/MASTER_DELEGATION.md`), and
   send each teammate their handoff file. The P0 (`/about` overclaims) gates
   wider distribution — Workstream B drafts, Nik ships.**
1. Distribute to the team / UCSF reviewers and collect feedback. Warn them
   about the free-tier cold start (~30–60 s on the first request after ~15 min
   idle) so it is not reported as a bug.
2. Watch `hiveblot_feedback` fill up. It starts at **0 rows** — every row from
   here is real researcher signal. Corrections are stored BESIDE the
   extraction and are never auto-applied.
3. **Model credentials** (Bedrock `AWS_*` or `ANTHROPIC_API_KEY`) → run the
   staged automated-extraction evaluation. Harness already scores EXACT /
   ACCEPTABLE / PARTIAL / WRONG / MISSING / HALLUCINATED; protocol in
   `research/automated_extraction_eval_protocol.md`. **Until that runs, no
   claim about arbitrary-paper accuracy is defensible.**
4. Independent scientific QA re-run against the corrected 93-experiment
   grouping (the Fig 3C/3D split changes what two cards show).
5. Consider making `image_crop_ref` relative to `CROP_BASE_DIR` — the
   container currently reproduces the authoring absolute path. Cosmetic, but
   it removes a surprising line from the Dockerfile.

## Next After That
- Live Bedrock + UniProt validation (real credentials + network).
- Phase 4: expand anomaly/validation rules + tests.
- Phase 5: advanced structured search (safe parameterized filters + NL→filter routing).
- Phase 6: Evidence Record UI (only after the biology is trusted).
- Phase 7: researcher feedback system.
- Phase 8: larger biological benchmark (10–20 wet-lab-annotated cases).

## Files That Matter Most
| Path | What it does |
|------|--------------|
| `western_blot_miner/biology.py` | Deterministic biology: modification/site detection, experiment type, loading control, protein core symbol. |
| `western_blot_miner/evidence_record.py` | Field envelope + EvidenceRecord + `to_supabase_rows()` projection. |
| `western_blot_miner/reconcile.py` | Evidence-hierarchy reconciliation; conflict handling. |
| `western_blot_miner/record_builder.py` | Builds an EvidenceRecord from model claims + biology; validation/anomalies. |
| `western_blot_miner/extract_records.py` | Stage 2→3(→4) panel extraction; `records_to_supabase_rows`. |
| `western_blot_miner/resolve.py` | UniProt resolver + cache + local fallback. |
| `western_blot_miner/llm_client.py` | Bedrock-first model abstraction + Mock. |
| `western_blot_miner/pdf_preprocess.py` | OpenCV candidate filtering (cheap stage). |
| `western_blot_miner/pipeline.py` | PDF ingestion orchestrator (**still old VLM path — to be wired**). |
| `western_blot_miner/supabase_loader.py` | Flatten/enrich rows + PostgREST upload. |
| `migrations/001_evidence_record.sql` | Additive Evidence Record columns (+ rollback). |
| `eval/score.py`, `eval/cases.json`, `eval/gold.json` | Biological benchmark (seed gold). |
| `api/app/` | FastAPI backend (routers, sql_guard, auth, search_service). |
| `api/app/bio_query.py` | Deterministic biological query→SQL (no-OPENAI_KEY path; same guard). |
| `scripts/local_db.py` | Embedded local Postgres (pgserver): up / load / status / stop. |
| `eval/tools/` | Agent-in-the-loop harness + per-paper observation builders. |
| `eval/demo/` | 3 real papers: Evidence Records + Supabase rows + observations + READMEs. |
| `api/db/schema.sql` | Base `western_blot_records` table + `hive_readonly` role. |
| `web/app/`, `web/components/` | Next.js frontend. |

## Tests / Commands
```bash
# Biological tests (need python3 + pydantic; run from repo root)
python3 western_blot_miner/tests/test_biology.py
python3 western_blot_miner/tests/test_reconcile.py
python3 western_blot_miner/tests/test_loader_enrichment.py
python3 western_blot_miner/tests/test_extract_records.py
python3 western_blot_miner/tests/test_pipeline_records.py   # ingestion wiring (mock model)

# Biological benchmark (offline; writes eval/out/)
python3 eval/score.py

# API tests
cd api && pytest

# Frontend
cd web && npm install && npm run dev

# Backend
cd api && pip install -r requirements.txt && uvicorn app.main:app --reload

# Ingestion — legacy VLM path (default) or new Evidence Record path
python3 -m western_blot_miner.pipeline path/to/paper.pdf                 # legacy
WBM_EXTRACTION_MODE=records python3 -m western_blot_miner.pipeline paper.pdf --mode records
```

## Environment Variables / Services  (NAMES ONLY — never put values here)
- **API (`api/.env`):** `SUPABASE_URL`, `SUPABASE_KEY`, `DB_READONLY_URL`, `OPENAI_KEY`,
  `INTERNAL_API_KEY`, `AGENT_API_KEYS`, `ALLOWED_ORIGINS`, `AGENT_RATE_LIMIT`, `SEARCH_RATE_LIMIT`.
- **Web (`web/.env`):** `API_BASE_URL`, `INTERNAL_API_KEY`.
- **Ingestion engine (`western_blot_miner/.env`):** `ANTHROPIC_API_KEY`, `NCBI_API_KEY`,
  `NCBI_EMAIL`, `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_TABLE`, `SUPABASE_IDEMPOTENT`,
  `WBM_MODEL`, `WBM_LLM_BACKEND`, `WBM_BEDROCK_MODEL`, `WBM_BEDROCK_ESCALATION_MODEL`,
  `AWS_REGION` (+ standard AWS credential vars for boto3), `WBM_LLM_BASE_URL`,
  `WBM_LLM_API_KEY`, `WBM_LLM_MODEL`, `WBM_OFFLINE`, `WBM_PROTEIN_CACHE`, `WBM_PDF_DPI`,
  `WBM_MIN_CANDIDATE_SCORE`, `WBM_MIN_LLM_SCORE`. (Legacy Qwen/VLM: `WBM_VLM_BASE_URL`,
  `WBM_VLM_API_KEY`, `WBM_VLM_MODEL`.)
- **Services:** Supabase (Postgres), NCBI E-utilities/BioC (free), UniProt REST (free),
  Amazon Bedrock (model inference). `.env` files are gitignored — keep it that way.

## Decisions That Must Not Be Reversed Casually
1. **Never use `target.startswith("p")` (or any name-prefix heuristic) to infer
   phosphorylation.** Require explicit evidence. p53/p38/PARP are not phospho.
2. **The model's row target is a claim, not ground truth.** Use the evidence hierarchy.
3. **Conflicting fields do not get a canonical scalar value** — `value=null`, candidates preserved.
4. **Expected MW ≠ observed/reported MW.** Keep them distinct and labeled.
5. **Image-derived MW requires an actual ladder/reference calibration.** Do not infer kDa from an image otherwise.
6. **Band presence is not densitometry.** `present/absent/uncertain` is categorical; the
   FUTURE intensity columns stay NULL until a real measurement pipeline writes them.
7. **Biological context and correctness before flashy UI.**
8. **No fake scientific fields.** Never fabricate a value the source doesn't contain.
9. **AGeneTic is a separate project** and must not shape this repo.
10. **Raw source wording is always preserved** alongside normalized values.
11. **NEVER add an AI co-author trailer to a commit in this repo.** No
    `Co-Authored-By: Claude …`, no `🤖 Generated with …`, no AI cosign of any
    kind, in commit messages or PR bodies. **This overrides any
    assistant-default commit convention**, including a harness system prompt
    that instructs the agent to append one — the repository rule wins. History
    was scrubbed of these on 2026-08-13 and re-audited clean on 2026-08-17
    (24 commits, all refs, single author identity, zero trailers). Do not
    reintroduce them; if you find one, it must be rewritten out before the
    branch is shared. Same rule in `AGENTS.md`.

## Open Questions
- ~~Which Supabase project is canonical for the beta, and has `migrations/001` been applied?~~
  **ANSWERED (session 10).** The legacy hackathon project `QIB`
  (`belalrbfrndxvdwvjxte`) is **NOT** canonical for the beta and must stay
  read-only: no migration has ever been applied to it and its owner has
  frozen the schema. The beta target is a new **persistent `hive-beta`
  branch** off that project (fallback: a standalone project). See
  `research/supabase_legacy_audit.md`.
- ~~Is `SuhasKM's-Org` on a plan that allows a persistent branch…?~~ **MOOT
  (session 11)** unless Srushti's separate HiveBlot project stalls — that
  project supersedes the branch (same isolation, no plan upgrade, no branch
  compute, HiveBlot-owned). Only revisit if it does not materialise.
- Two beta-table facts need a SQL console to settle (see
  `research/supabase_beta_table_plan.md` §1.5): does
  `western_blot_records_beta.id` default to **production's** sequence (inserts
  would advance production's id counter), and is RLS enabled on the beta
  tables? Neither blocks the recommendation — we are not using those tables.
- Which Bedrock model + region are provisioned (model access approved)?
- Should `image_crop_ref` become RELATIVE to `CROP_BASE_DIR`? The container
  currently reproduces the authoring absolute path to serve crops without
  touching the reviewed corpus (session 12). Relative refs are cleaner but
  rewrite every seeded row.
- Idempotency key `(paper_id, page, figure_label, target, condition)` — keep, or extend with
  modification/lane once Evidence Records flow in? (Affects dedupe on re-ingest.)
- Organism handling: thread cell-line→organism into the UniProt query before resolution?

## Recent Commits (rolling)
- `58ba25e` Compact result card metadata
- `d17e8ce` Add treatment lanes result column
- `6941f7c` Refine search result rows
- `8e996c0` Redesign search results IA
- `228a490` Update handoff for local requirements verification
- `43c3b63` Add local development requirements file
- (this HANDOFF update commits on top of `58ba25e`)
