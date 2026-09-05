# HiveBlot demo readiness review (live dry-run)

**Date:** 2026-08-13 · **Method:** every check below was executed with curl
against the running local API (`http://localhost:8000`, embedded pgserver DB,
452 rows / 3 papers, auth via the local `INTERNAL_API_KEY` — value not
reproduced here). Web-UI-only behaviors are marked as such. One clearly-labeled
test feedback row was written (see "Test artifacts"); no other data was
modified. This review does not modify core code.

---

## 1. Headline finding: the stack is HALF up

At review time only FastAPI (:8000) and the embedded Postgres were running.
**Next.js was NOT listening on :3000.** The demo front door is the web UI, so
the pre-demo checklist in `research/HACKATHON_DEMO_FLOW.md` (start `npm run
dev`, confirm one search in the browser) is load-bearing — run it, don't skip
it. Everything below the web layer was verified working via the API.

Also observed live: **the API restarted mid-review** (new PID) because
crop-serving work was being landed concurrently (see §5). It came back healthy
with all 452 rows intact — good evidence for restart resilience, but it means
**uncommitted working-tree code is what's actually running**. Freeze/commit
before the demo.

---

## 2. Recommended demo order (concrete queries, all verified)

| # | Query / action | Why here | Verified payload |
|---|---|---|---|
| 1 | `phospho STAT3 Tyr705` | Fastest wow: 3 experiment cards from 15 lane records, full biological identity | 3 groups (crops `page_004_cand_0028/0029`, `page_005_cand_0034`), STAT3 → UniProt P40763 SUPPORTED, Hep3B, phospho_western, CST #9145 @ 1:1,000, IL-6 10 ng/ml, expected 88.1 kDa (uniprot_reference), reported MW = null |
| 2 | Open record detail (e.g. id 1537) | The "why HiveBlot says this" beat | Evidence envelopes with the exact snippet `"p-STAT3 (Tyr705; 1:1,000; CST #9145)"`; **duration = AMBIGUOUS with all 6 timepoints preserved as candidates** and per-lane `lane_duration` 0→60 min; lane strip runs absent → present (0-min lane has no p-STAT3 — biologically right, say so) |
| 3 | `needs review P-ERK` | Honest-uncertainty story, direct | 2 cards, both `modification_status=CONFLICTING`, `needs_review=true`; detail (id 1577): candidates "phosphorylation (via antibody, 0.6)" vs "none (row label, 0.5)", canonical = MAPK1/MAPK3 family, uniprot = null; bonus: every lane carries `band_pattern=doublet`, `band_count=2`, note "two closely spaced bands visible in each lane" |
| 4 | `co-IP PIK3CA` | Experiment-context story | 4 co_ip cards. p85 prey card (id 1799, H1792): detection ab Proteintech #60225-1-Ig, PIK3CA with role `immunoprecipitation`, `ip_bait_protein` field, Input/IP:PIK3CA lanes. **For Input/IgG/IP in ONE panel open the H1299 PIK3CA (id 1835/1836) or BEX2 (id 1838/1839) card** — the p85 card has no IgG lane |
| 5 | `LC3B H1299` | New band-pattern feature | 2 cards (CST #2775); detail (id 1787): all 6 lanes `doublet`, `band_count=2`, SUPPORTED, with observer note — the LC3B-I/II doublet without ever claiming isoform identity |
| 6 | `CST 9145` | Reverse lookup by catalog number | 3 cards, all P-STAT3 (Tyr705) / CST #9145 — "search by the reagent in your fridge" |
| 7 | `GAPDH mouse` | Cross-organism + loading controls | 5 cards, organism=mouse, mouse SMG tissue, experiment_type=loading_control, CST #5174s |
| 8 | Feedback click (UI) | Close the loop | API path verified: POST /feedback → stored in `hiveblot_feedback` beside the AI value (insert-only role) |

**Opening query: `phospho STAT3 Tyr705`.** It is the only query where every
single card element named in the demo script was verified present in the API
response, and its evidence panel now also renders the real panel crop (§5).

**Closing line fix:** "Three real papers, 91 records" — the live DB is
**3 papers, 452 lane rows, exactly 91 experiment groups** (verified by SQL with
the UI's grouping key). Say "3 papers, 91 experiments, 452 lane records".

---

## 3. Demo-script mismatches (HACKATHON_DEMO_FLOW.md predates current behavior)

| Doc says | Actual current behavior | Action |
|---|---|---|
| Step 3: "Search `ERK` → open a P-ERK 1/2 record" | `ERK` returns **8 cards** and sorts `needs_review` LAST, so both P-ERK conflict cards are at the bottom; 4 of the 8 (P-STAT3 ×2, T-STAT3, β-actin) match only because their `treatment_context` mentions "MEK/ERK inhibitor U0126" | Use **`needs review P-ERK`** (exactly the 2 conflict cards), or warn the presenter to scroll; be ready to explain why β-actin appears under "ERK" |
| Step 4: "Input/IgG/IP lanes" | True for the H1299 records; the p85/H1792 card has Input + IP lanes only | Open an H1299 co-IP card if IgG must be on screen |
| Evidence panel is text-only (also DEPLOYMENT.md "crop serving not enabled anywhere") | **Stale — in the good direction.** `GET /records/{id}/crop` exists (uncommitted working-tree change), serves real PNGs (verified 200 + 138–362 KB on all 6 demo records above), path-guarded to `western_blot_miner/data/pdf_runs`, proxied by `web/app/api/record/[id]/crop` | Update both docs; showing the actual blot crop next to its evidence is a wow beat the script doesn't even claim |
| Step 1 card: "IL-6 · 10 ng/ml" | Still true; additionally duration is now (correctly) AMBIGUOUS across the 0–60 min time course with per-lane values | Turn it into a talking point: "the old version reported 60 min as THE duration; now it refuses to pick" |
| "91 records" close | 91 = experiment groups; lane rows = 452 | Reword (see §2) |

---

## 4. Reliability risks

| Severity | Risk | Evidence | Mitigation |
|---|---|---|---|
| HIGH | Web UI not running at review time | :3000 refused connections; API+DB fine | Run the pre-demo checklist; browser smoke test one search + one evidence panel + one crop image |
| HIGH | Demo runs on uncommitted code | `git status`: modified `api/app/routers/internal.py`, `api/app/config.py`, `web/components/EvidencePanel.tsx`, new `web/app/api/record/[id]/crop/`; the running API already restarted once mid-review as this landed | Commit/freeze before demo; re-run api tests; no code edits after the freeze |
| MEDIUM | Rate limit 20/min per IP on `/search` | Verified live: request 21 within a minute → HTTP 429; all browser searches funnel through the Next.js server = **one shared bucket** | The scripted ~7 searches are safe; risk is post-demo audience-driven exploration or rapid retyping. `/records/{id}` and `/crop` are NOT rate-limited, so opening evidence panels never burns budget. If 429 hits, wait ~60 s (limiter is in-memory; an API restart also clears it) |
| MEDIUM | Audience-suggested queries can return zero | `p53` → 0 results (dataset has no p53), `banana` → 0, both clean 200s | Keep to the 3-paper vocabulary (STAT3, ERK, LC3B, BEX2, PIK3CA, GAPDH, β-actin); frame zero results as "3 papers ingested so far" |
| LOW | Weird input handling | empty query → 422 (min_length 1); 600-char query → 422 (max 500); `β-actin` unicode → 25 rows, correct targets; no-auth → 401 | API side is solid; how the UI renders a 422/429 (`Backend returned <status>`) was not testable with the web down |
| LOW | API restart during demo | Observed live: DB is a separate pgserver process, disk-backed at `/Users/niks/hive/.localdb`; all 452 rows + feedback rows survived | If uvicorn dies, restart it — data and even feedback survive; keep the start command on a sticky note |
| LOW | `GET /` on the API returns 500 | Verified: root endpoint requires Supabase (PostgREST) and fails without creds | Never open `http://localhost:8000/` on screen; `/health` is the liveness URL |

---

## 5. Do NOT demo (verified dead ends)

- **`/proteins`** — verified 500 "Supabase query failed" (needs cloud Supabase). Same for API root `/`.
- **API home `http://localhost:8000/`** — 500s (above). Use `/health` for the "it's alive" beat.
- **Web home page hero** — it is no longer the legacy table (it client-side routes `window.location.href = /search?q=...`), but the script's advice stands: start at `/search` directly.
- **Anything implying the automated model path is validated** — `OPENAI_KEY` is empty; search runs on the deterministic `bio_query` generator (this is fine and inspectable — the `generated_sql` field is in every response), and extraction rows are labeled `agent-in-the-loop`.
- **Densitometry/quantitation** — band evidence is categorical (`band_state`, descriptive `band_pattern`); nothing numeric exists to show.

---

## 6. Deployment readiness (per DEPLOYMENT.md checklist)

**Genuinely ready now (verified locally):**
- Schema + `migrations/001_evidence_record.sql` + `002_feedback.sql` (with down-migrations) exist and are what the live DB runs.
- Seed data exists: `eval/demo/{phospho_PMC12856536,standard_PMC9559174,coip_PMC12706926}/supabase_rows.json` (2.7–6.2 MB each) — the documented table-editor import workaround is available.
- API works with **no** OpenAI key (deterministic search verified end-to-end) and **no** Supabase for the core `/search` → `/records/{id}` → `/feedback` flow.
- Auth (401 without bearer), sql_guard, per-endpoint rate limits, insert-only feedback role: all exercised live.
- Web needs only `API_BASE_URL` + `INTERNAL_API_KEY` (both present locally; key length 43 chars) and keeps secrets server-side.

**Blocked on user credentials / accounts (presence checked, values never read into this report):**
- `SUPABASE_URL`, `SUPABASE_KEY`, `OPENAI_KEY` are **empty** in `api/.env`. Cloud DB provisioning, role passwords (`hive_readonly`, `hive_feedback`), and remote `DB_READONLY_URL`/`DB_FEEDBACK_URL` are all user-account work.
- The dev `INTERNAL_API_KEY`/`AGENT_API_KEYS` are marked DEV-ONLY in the env file — regenerate for any deployed environment.
- `ALLOWED_ORIGINS` must be set to the deployed web origin.

**Gaps to know about before deploying:**
- No dedicated remote-seed script (documented TODO in DEPLOYMENT.md).
- `image_crop_ref` stores **absolute local paths** (`/Users/niks/hive/western_blot_miner/data/pdf_runs/...`). On a cloud API host those files won't exist → crop endpoint 404s → UI falls back to text-only (graceful, by design), but the demo's crop-image wow is **local-only** until the crop archive ships with the API host and `crop_base_dir` is set.
- The crop-serving code itself is **uncommitted** (see §4 HIGH risk).
- Doc nit: DEPLOYMENT.md says API needs Python ≥ 3.13; the local venv is 3.12 and the running server is Homebrew 3.14 — pick one story before someone deploys with the wrong runtime.
- DEPLOYMENT.md's "crop serving is not enabled anywhere" line is now stale.

---

## Test artifacts from this dry-run

- One feedback row written via `POST /feedback`: `feedback_id=5`, scope `field`,
  record 1537, comment "TEST ROW - demo readiness dry-run 2026-08-13 (safe to
  delete)", `ui_location=demo-readiness-review-curl`. Safe to delete before the
  demo if the feedback table goes on screen (4 prior rows exist).
- No other rows or files in the repo were modified.
