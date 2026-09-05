# Assignment — Search & Data Integrity (Workstream D)

**For:** a CS / data / software teammate.
**Mode:** investigate before changing. Two of your four tasks are explicitly
investigations that end in a written plan, not a diff.

## Why this matters

The search path is where HiveBlot either keeps or breaks its core promise: it
must never pretend to a filter, a value, or a precision it does not have. The
walkthrough found the `GAPDH mouse` query "working" by string coincidence, the
public API leaking the developer's home directory, and internal enum values
rendered in the same quotation styling as sentences from published papers.
None of these are data corruption — the underlying corpus is correct — but all
three erode the exact trust the product sells.

## What to learn first

1. Run the flagship searches against the live site and watch the network tab —
   the web app proxies through `web/app/api/search/route.ts` to the FastAPI
   backend. (First request after ~15 min idle takes ~20–30 s: Render Free
   cold start, known, documented.)
2. Read the search path in order: `api/app/routers/` → `api/app/search_service.py`
   → `api/app/bio_query.py` (the deterministic biological-query→SQL parser used
   when no `OPENAI_KEY` is set — which is the production configuration) →
   `api/app/sql_guard.py` (AST validation) → the read-only `hive_readonly`
   role. Understand why every layer exists.
3. Read `api/app/schemas.py` (`WesternBlotRecord` — the list response; note
   the `provenance`/`validation` JSONB blobs are deliberately excluded) and
   `api/app/record_detail.py` (the detail-shaping layer where envelope data
   becomes UI-facing fields).
4. Read `HANDOFF.md` sessions 14 and 9 for the `stable_row_key` identity model
   — you must not break it.

## Your tasks

1. **`GAPDH mouse` organism investigation (investigate ONLY).** Confirm
   exactly what `bio_query.py` generates for this query (per the walkthrough:
   a second free-text ILIKE for the string `mouse` ANDed across the same
   columns, not a predicate on the populated `organism` column). Document:
   what the parser recognizes today, what a true organism filter would look
   like, which queries would change results (e.g. a mouse line named
   `NIH/3T3`; a human sample whose text mentions "mouse anti-X antibody"),
   and the false-positive/false-negative tradeoff. Deliver a written
   recommendation. **Do not change the parser** — a wrong "improvement" here
   hallucinates filters, which is worse than string matching.
2. **`image_crop_ref` sanitation plan (plan ONLY).** The public list response
   returns absolute authoring paths (`/Users/niks/hive/...`). Map every
   consumer of `image_crop_ref` (API schemas at `api/app/schemas.py`, the
   crop-serving endpoint and its `CROP_BASE_DIR` validation, the Dockerfile
   line that reproduces the authoring path, the seeded DB values, tests).
   Propose the fix: likely serialize a sanitized/relative ref (or omit the
   column from public responses entirely — the UI fetches crops via
   `/api/record/{id}/crop`, so check whether the frontend reads the raw ref at
   all), vs rewriting seeded rows (needs a reviewed reseed — Nik's call).
   HANDOFF's Open Questions already flags this; extend it, don't duplicate.
3. **Raw-value presentation fixes (may implement after findings are agreed).**
   In `api/app/record_detail.py` + `web/components/EvidencePanel.tsx`:
   `"ambiguous_family"` and `"{}"` rendered as if quoted from the paper; a
   CANDIDATES block listing a single candidate named "none". Root-cause each:
   these are internal envelope values flowing into a UI slot styled for
   verbatim source text. Fix at the shaping layer (label internal provenance
   as internal, suppress empty-dict sources, render no-candidates as an
   explicit empty state), never by mutating stored provenance. Coordinate
   with Workstream C on wording.
4. **`needs review` reason field (design with Workstream C, small
   implementation).** The flags (e.g. `MODIFICATION_CONFLICT`) live in the
   `validation` JSONB excluded from list responses. Propose the minimal
   addition — likely a short `review_reasons: list[str]` derived server-side —
   without shipping the full JSONB to the list endpoint. Implement once C's
   design and Nik's approval land.
5. **Cold-start handling note (small, optional).** Confirm nothing should be
   engineered around Render Free spin-down right now; propose only the cheap
   mitigation (frontend message that explains the ~30 s first-search wait).
   Anything beyond copy is out of scope.

## What to test

- Flagship queries with exact expected shapes: `phospho STAT3 Tyr705` 18 rows /
  3 groups, `co-IP PIK3CA` 14/4, `CST 9145` 18/3, `P-ERK` 10/2, `GAPDH mouse`
  31/5, `needs review` 20/4, `BRCA1 MCF7 olaparib` 0. Any change you make must
  keep every one of these identical unless the change's purpose is to alter it
  — and then the alteration is documented and approved first.
- `cd api && pytest` — 113/113 must stay green; new behavior gets new tests.
- `cd web && npx tsc` clean.
- For task 3: the `P-ERK` cards (ambiguous_family, `{}`, candidate "none") and
  the `p85` co-IP card.

## What NOT to change

- **`sql_guard.py` and the auth/role model.** The AST guard + read-only role
  are the security boundary; loosening them is never in scope.
- **`stable_row_key` / identity hashing** (`record_builder.identity_sample()`
  and friends). Feedback isolation depends on it; it is pinned by a 34-test
  suite for a reason.
- **Stored provenance JSONB.** All fixes are presentation/serialization-layer.
  The database rows are the reviewed corpus.
- **The parser's abstention behavior.** `bio_query.py` must never generate a
  filter the query didn't clearly ask for. When unsure, broad-and-honest beats
  narrow-and-guessed.
- The live DB (`zafombwswztvnjikcsdm`) — read-only for you; the legacy QIB
  project (`belalrbfrndxvdwvjxte`) — untouchable, period. No deploys; Nik
  ships.

## What you should understand before finishing

- **Biological-query → structured SQL.** With no `OPENAI_KEY` (production),
  `bio_query.py` deterministically recognizes protein names, phospho-sites
  (Tyr705/S473), vendor+catalog pairs, co-IP, loading-control, needs-review,
  and cell-line terms, and emits SQL that still passes `sql_guard` and runs as
  `hive_readonly`. Everything it does not recognize becomes free-text
  matching. That boundary — recognized structure vs text fallback — is
  exactly where the `GAPDH mouse` finding lives.
- **Why query parsing must not hallucinate unsupported filters.** A silent
  wrong filter produces confidently wrong result sets — the worst failure
  mode for a scientific tool. String matching that over-returns is honest
  noise; a hallucinated `organism = mouse` predicate that mis-fires is a lie
  with a straight face. This asymmetry drives every parser decision.
- **Text matching vs true structured fields.** The DB has real structured
  columns (`organism`, `experiment_type`, `antibody_catalog_number`…). Some
  queries hit them (`co-IP` → `experiment_type = 'co_ip'`; `needs review` →
  `needs_review = TRUE`); some only appear to (`GAPDH mouse`). Knowing which
  is which, per query term, is the deliverable of task 1.
- **The stable identity model, at altitude.** Each experiment's identity is a
  hash of observation data only (paper + figure + panel + crop + raw target +
  treatment context + normalized sample); `stable_row_key = hash:lane_index`.
  Search grouping and feedback attachment both read that same key, so the card
  boundary and the feedback boundary are one thing, and reseeds cannot orphan
  corrections. Engine outputs (confidence, needs_review…) are deliberately
  excluded so engine improvements never change identity.

## Definition of done

- Task 1: a written organism-filter report — current SQL, recognized-vs-text
  analysis, recommendation with tradeoffs. No code change.
- Task 2: a written sanitation plan covering every consumer, with the
  recommended option and its blast radius. No code change without Nik's pick.
- Task 3: findings agreed with Nik, then shaping-layer fixes with tests; the
  three leaks no longer render as paper quotes; api pytest green, tsc clean.
- Task 4: agreed API shape documented; implementation only after C + Nik sign
  off.
- All seven flagship query shapes verified unchanged after any merged code.

## What to report back to Nik

- **What you found:** the actual generated SQL for `GAPDH mouse`, the full
  `image_crop_ref` consumer map, root causes for the three raw-value leaks.
- **What you changed, if authorized:** PRs with tests, flagship shapes
  re-verified.
- **Unresolved questions:** organism-filter recommendation tradeoffs; whether
  sanitation should wait for the next reviewed reseed.
- **Examples:** request/response captures for each finding (redact nothing —
  these are internal docs — but never commit secrets).
- **Needs Nik's decision:** organism filter go/no-go, sanitation option,
  reseed timing, `review_reasons` API addition.
