# HiveBlot Frontend Integration Plan — Evidence Records

> Inspection + planning only. No code was changed by this document.
> Goal: surface the biological **Evidence Record** in the search UI using the
> **existing** HiveBlot visual identity (dark `#06090c` bg, teal `#4ad6b0`
> accent, Newsreader serif + IBM Plex Mono labels). **Not a redesign.**

---

## 1. Current-state map (components + data flow)

### Data flow (browser → DB), with file paths

```
SearchInput (web/components/SearchInput.tsx)
  └─ onSearch(query)  [debounced 400ms / Enter]
       └─ web/app/search/page.tsx  handleSearch()
            └─ POST /api/search        (same-origin, browser → Next BFF)
                 └─ web/app/api/search/route.ts   (Node runtime; adds Bearer INTERNAL_API_KEY)
                      └─ POST {API_BASE_URL}/search   (Next → FastAPI)
                           └─ api/app/routers/internal.py  search()   [require_internal_key + rate limit]
                                └─ api/app/search_service.py  execute_search()
                                     ├─ api/app/nlp.py  generate_sql()   (OpenAI NL→SQL)
                                     ├─ api/app/sql_guard.py  guard_and_limit_sql()  (AST validation + LIMIT)
                                     └─ api/app/db.py  run_readonly_query()  (asyncpg, hive_readonly role)
```

The FastAPI response is serialized through `response_model=SearchResponse`
(`api/app/routers/internal.py:62`), and the JSON returned to the browser is
`{ question, generated_sql, count, results[] }`. Note: `page.tsx` currently
reads only `count` and `results` and ignores `question`/`generated_sql`.

### Components (web/components/) and what renders today

| Component | Used by | Purpose / status |
|---|---|---|
| `SearchInput.tsx` | `search/page.tsx:74` | Debounced search box. Reusable, no change needed. |
| `DatabaseResultCard.tsx` | `search/page.tsx:127` | **The live result card.** Two-column grid + collapsible right "CITATION" rail. This is the card to extend. |
| `ResultsCard.tsx` | *imported but UNUSED* in `search/page.tsx:6` | Richer mock card (figure carousel, DOI link, confidence %). Design reference for the expanded rail — but its data shape (`model/comparison/readout/figures[]`) is a mock, not the API shape. |
| `ResultsTable.tsx` | *not imported anywhere in search flow* | Flat table view of the same 12 fields. Optional alt view. |
| `Navigation.tsx`, `OrbitCanvas.tsx` | layout / landing | Not part of results rendering. |

### Fields the live card (`DatabaseResultCard`) renders today
`target` (teal), `sample`, `western_blot_type` (`_`→` / `), `condition`,
`band_detected` (✓/✗ green/red), `paper_id`; metadata footer: `organism`,
`treatment_context`, `figure_label`, `page`. The right rail is a vertical
"CITATION" tab that expands to a **"Figure data coming soon" placeholder**
(`DatabaseResultCard.tsx:262-275`). `confidence` is in the type but **not
rendered** in this card (it is rendered in the unused `ResultsCard`).

### Reusable visual atoms already in the codebase (no library needed)
- **Field label**: IBM Plex Mono, 10px, `#6f857d`, `letterSpacing 0.4px`, uppercase.
- **Field value**: Newsreader serif, 14px, `#e7f0ee` (teal `#4ad6b0` for target/emphasis).
- **Card shell**: `rgba(255,255,255,.07)` bg, `6px` radius, 1px border, two-column grid with an animated collapsible right rail (`gridTemplateColumns` transition).
- **Positive/negative color**: `#4ad6b0` (present/yes) vs `#ff6b6b` (absent/no/error).
- **Design tokens** live in `web/app/globals.css:7-18` (`--color-accent` etc.). Components currently use **inline hex**, not the CSS vars — match that convention for consistency.

There are **no badge/chip/pill components yet** — status badges must be built (small, from the atoms above).

---

## 2. The API-shape gap (the critical finding)

The database already has all the Evidence Record columns
(`migrations/001_evidence_record.sql`) and the miner writes them via
`EvidenceRecord.to_supabase_rows()`
(`western_blot_miner/evidence_record.py:211-281`). The blocker is **not** the DB
— it is two API-layer chokepoints that silently drop the rich columns:

1. **`response_model` strips unknown fields.** `internal.py:62` declares
   `response_model=SearchResponse`, whose `results` are
   `WesternBlotRecord` (`api/app/schemas.py:9-26`) — only the **12 base
   columns**. Even though `sql_guard` forces `SELECT *` and asyncpg returns
   every column (`db.py:36` `dict(row)`), FastAPI serializes through the
   Pydantic model and **discards** `canonical_target`, `modification_label`,
   `antibody_vendor`, `needs_review`, `provenance`, etc. **This is why "Figure
   data coming soon" can never populate today — the data never reaches the
   browser.**

2. **The NL→SQL prompt only knows the 12 base columns.** `nlp.py:14-27`
   hard-codes the old `CREATE TABLE` in the prompt, so the LLM cannot filter on
   `modification_type`, `antibody_vendor`, `cell_line`, `residue`, etc. This
   only limits **querying** by new fields; display is unblocked by fixing (1)
   alone.

### Evidence Record fields available to surface (source: migration 001 + `to_supabase_rows`)

| UI concept | Flat column(s) | Envelope status column |
|---|---|---|
| Biological headline | `canonical_target` (+ `target` raw), `modification_label` (e.g. `phospho-Tyr705`) | `protein_status`, `modification_status` |
| Experiment type | `experiment_type`, `experiment_flags` (JSONB) | `experiment_type_confidence` |
| Sample / cell line | `sample`, `cell_line`, `organism`, `tissue`, `genotype` | — |
| Treatment (agent·dose·duration) | `treatment_name`, `dose`, `dose_unit`, `duration`, `duration_unit`, `treatment_context` | — |
| Antibody (vendor·catalog) | `antibody_target`, `antibody_vendor`, `antibody_catalog_number`, `antibody_clone`, `antibody_dilution` | — |
| Band state | `band_state` (present/absent/uncertain), `band_detected`, `lane_condition`/`condition`, `loading_control` | — |
| Molecular weight | `reported_molecular_weight_kda`, `expected_molecular_weight_kda`, `molecular_weight_source` | — |
| Identity / provenance | `uniprot_id`, `pmid`, `pmcid`, `doi`, `title`, `source_url`, `figure_caption`, `panel_label`, `image_crop_ref` | — |
| Validation status | `needs_review` (bool), `validation` (JSONB), `anomaly_flags` (JSONB), `provenance` (JSONB — per-field `{value,confidence,status,sources,candidates}`) | record-level `validation.record_status` |
| Extraction audit | `extraction_stage`, `extraction_model`, `extraction_version` | — |

Status vocabulary (from `evidence_record.py:19-22` + `HANDOFF.md` "Current
Biological Contract"): **SUPPORTED / AMBIGUOUS / CONFLICTING / MISSING**. A
CONFLICTING field has `value = null` with competing candidates preserved in
`provenance`. `needs_review = true` → surface as **"Needs review"**;
SUPPORTED + `needs_review=false` → **"Supported"**.

---

## 3. Minimal result-card design (collapsed) — biological headline

Keep `DatabaseResultCard`'s existing shell and grid. Change only the headline
and add a status badge + a couple of high-value fields. All using existing atoms.

**Headline** (replaces the bare `TARGET` value at `DatabaseResultCard.tsx:54-78`):
```
STAT3 · phospho-Tyr705            [Supported]
^teal #4ad6b0, Newsreader 18px    ^status badge (right-aligned)
```
- Compose from `canonical_target` (fallback `target`) + `modification_label`
  when `modification_type` is present. Join with ` · `.
- If `canonical_target` differs from raw `target`, show raw as a small muted
  subtitle (`raw_target_name`), honoring the "raw wording always preserved" rule.

**Status badge** (new small atom, no library): pill, IBM Plex Mono 10px, uppercase.
- `Supported` → teal (`#4ad6b0` text, `rgba(74,214,176,.12)` bg, `.25` border).
- `Needs review` → gold (`#e0a458`, already a token `--color-gold`).
- `Conflicting` → red-ish (`#ff6b6b`).
- Derivation: `needs_review===true` → "Needs review"; else if any surfaced
  field status is CONFLICTING → "Conflicting"; else "Supported". Keep the
  mapping in one helper so it is testable.

**Collapsed body** (reuse the existing 2-col label/value grid): keep `SAMPLE`
(prefer `cell_line` then `sample`), add `EXPERIMENT` (`experiment_type`,
`_`→` `), keep `CONDITION` (`lane_condition`/`condition`), replace the raw
`BAND DETECTED` boolean with **`BAND STATE`** (`band_state`: present=teal ✓,
absent=red ✗, uncertain=gold ~). Keep the `paper_id`/metadata footer.

**Guardrails for empty data:** every new field must render only when non-null
(the footer already does this at `DatabaseResultCard.tsx:217`). Never print
`null`, `undefined`, or a fabricated value (HANDOFF invariant #8). For
CONFLICTING fields the flat column is already `null`, so they naturally hide in
the collapsed view and surface only in the expanded conflicts section.

---

## 4. Expanded-card plan (right rail) — evidence + provenance

Reuse the existing collapsible rail (`DatabaseResultCard.tsx:249-302`; the
`gridTemplateColumns: '1fr 240px'` expand animation already works). Consider
widening the expanded rail (e.g. `360px`) since there is real content now.
Replace the "Figure data coming soon" placeholder with stacked sections:

1. **Figure crop** — `image_crop_ref` as `<img>` when present (mirror
   `ResultsCard.tsx:264-284`'s image treatment: black bg, contained). If null,
   omit the block (do **not** show a broken image). Requires a decision on how
   `image_crop_ref` resolves to a URL (see Risks / Open Qs).
2. **Caption / methods evidence** — `figure_caption` + `panel_label`;
   Newsreader 11px muted, scrollable (pattern already at `ResultsCard.tsx:304-316`).
3. **Antibody block** — `antibody_vendor · antibody_catalog_number`
   (+ clone/dilution). UCSF-critical per migration comment (`001:74`).
4. **Treatment block** — compose `treatment_name` + `dose dose_unit` +
   `duration duration_unit` into one line (e.g. "Nutlin-3, 10 µM, 6 h").
5. **Molecular weight** — show `reported` vs `expected` **distinctly labeled**
   (HANDOFF invariant #4); never merge them.
6. **Field-level provenance** — from the `provenance` JSONB (full
   `EvidenceRecord.model_dump`): for each surfaced field show its
   `status` + top `sources[].type/locator` (e.g. "antibody", "fig3A_caption").
   A small "why did HiveBlot say this?" affordance. Keep it collapsible/terse.
7. **Ambiguity / conflicts** — when `anomaly_flags` is non-empty or a field is
   CONFLICTING, render the competing `candidates[]` (value + source) side by
   side with a red/gold heading. **Do not pick a winner** — this is the core
   biological-honesty requirement (HANDOFF corrections #1/#3).
8. **Provenance / citation footer** — `doi`→`https://doi.org/{doi}` link,
   `pmid`/`pmcid`, `source_url`, `title` (reuse DOI-link pattern
   `ResultsCard.tsx:404-425`); plus small `extraction_model`/`_version` audit line.

---

## 5. Exact files to change, in order

**Phase A — unblock the data (API). Do this first; it is invisible to the UI
until Phase B but is the prerequisite.**

1. `api/app/schemas.py` — extend `WesternBlotRecord` with the Evidence Record
   columns as **`Optional[...] = None`** (all nullable). This is purely
   additive: existing 12 fields keep their types. Optionally set
   `model_config = ConfigDict(extra="ignore")` explicitly. This alone makes the
   new columns flow to the browser (because `SELECT *` already returns them).
   Consider typing `provenance`/`validation`/`anomaly_flags`/`experiment_flags`
   as `dict|list|None` (JSONB passthrough) rather than fully modeling them yet.
2. `api/app/nlp.py` — update the `CREATE TABLE` in `SQL_PROMPT` to list the new
   filterable columns (canonical_target, modification_type, residue,
   experiment_type, cell_line, antibody_vendor, antibody_catalog_number,
   band_state, needs_review, …) with the same ILIKE/numeric rules. **Only
   needed to let users *query* by these fields**; display works without it.
   Lower risk to ship Phase A step 1 first, then this.
3. (Optional, later) `api/app/schemas.py` `SearchResponse` is unchanged in
   shape; no route signature change needed. `sql_guard.py` needs **no** change
   — it already allows `SELECT *` and does not whitelist columns.

**Phase B — render it (web). Backward-compatible because every new field is
optional and guarded.**

4. `web/app/search/page.tsx` — widen the `DatabaseResult` interface (lines
   9-22) to include the new optional fields; no logic change to `handleSearch`.
5. `web/components/DatabaseResultCard.tsx` — (a) widen its local
   `DatabaseResult` interface to match; (b) add the headline + status badge;
   (c) add BAND STATE / EXPERIMENT fields; (d) replace the "coming soon" rail
   with the expanded sections from §4. Keep all existing fields as fallbacks.
6. (Optional) extract a tiny `StatusBadge` and `EvidenceField` label/value into
   `web/components/` if reuse across table view is wanted; otherwise keep inline
   to match the current inline-style convention.
7. (Optional) `web/components/ResultsTable.tsx` — add columns if the table view
   is ever wired in; not on the critical path.

**Suggested minimal shippable increment:** schemas.py (A1) + page.tsx interface
(B4) + DatabaseResultCard headline/badge/band-state (B5 collapsed only). That
delivers the biological headline with zero query-path risk. Expanded rail and
NL-query extension follow.

---

## 6. Risks — "do not break working search"

1. **`response_model` is load-bearing.** Widening `WesternBlotRecord` with
   Optional fields is safe; **narrowing or retyping** an existing field (e.g.
   making `target` required, or changing `confidence` type) would break
   serialization for legacy rows. Keep all additions `Optional = None`.
2. **Legacy rows have NULLs + `needs_review=true`** by migration design
   (`001` header comment). The UI must treat null as "not reported" and render
   nothing — never "false"/"0"/"unknown-as-fact". The badge will show "Needs
   review" for all un-enriched rows; that is correct, not a bug.
3. **`band_detected` vs `band_state`.** `band_detected` (bool) still exists and
   is what current filters/SQL use. `band_state` is the richer categorical.
   Show `band_state` when present, fall back to `band_detected`. Do not remove
   `band_detected` from the schema or SQL prompt.
4. **NL→SQL prompt changes can regress existing queries.** Editing `nlp.py`'s
   prompt risks the LLM emitting SQL against columns that a given Supabase
   project has not migrated yet (if `migrations/001` isn't applied there — an
   HANDOFF open question). Mitigation: ship the display path (Phase A1/B)
   first; gate prompt changes behind confirmation that 001 is applied to the
   beta project. A query referencing a non-existent column would 500 at
   `run_readonly_query`.
5. **`sql_guard` allowlist is tight** (`ALLOWED_FUNCTIONS = {lower, upper,
   coalesce, count, cast}`). New display work needs no new functions. If NL
   queries start using JSONB operators (`->>`) for `provenance`/`experiment_flags`,
   the guard will reject them — keep JSONB filtering out of scope for now.
6. **`image_crop_ref` has no resolved URL yet.** It is a ref string, not a
   hosted URL. The figure-crop block must no-op until an image-serving decision
   exists (Supabase Storage bucket / signed URL / API passthrough). Do not ship
   a broken `<img>`. This is the one expanded-rail item with an external
   dependency; everything else (caption, antibody, treatment, provenance,
   conflicts) is pure text already in the row.
7. **`provenance` JSONB is large** (full `model_dump` of the record, embeds the
   whole envelope tree — see `evidence_record.py:263`). Returning it on every
   search row inflates payloads. Consider (later) selecting it only on expand,
   or trimming server-side; for the beta it is acceptable but note the cost.
8. **Two unused components** (`ResultsCard`, `ResultsTable`) can mislead an
   implementer into wiring the wrong card. The live card is
   `DatabaseResultCard` only (`search/page.tsx:127`). Reference the others for
   visual patterns, not data shape.
9. **Inline styles, no design system.** There is no Tailwind usage in the cards
   despite Tailwind being configured; matching the existing inline-hex style
   keeps the diff visually consistent. Introducing Tailwind classes here would
   look inconsistent.

---

## Appendix — key path:line references
- Live card: `web/components/DatabaseResultCard.tsx:24` (component), `:54-78`
  (target headline), `:161-186` (band bool), `:217-246` (metadata footer),
  `:262-275` ("coming soon" placeholder to replace).
- Search page: `web/app/search/page.tsx:9-22` (result interface), `:50-53`
  (fetch), `:124-130` (card map).
- BFF: `web/app/api/search/route.ts:26-45`.
- API response strip point: `api/app/routers/internal.py:62`;
  `api/app/schemas.py:9-33`.
- NL→SQL prompt schema: `api/app/nlp.py:14-27`.
- SQL guard (SELECT *, no column whitelist): `api/app/sql_guard.py:68-114`.
- Rich columns (DB): `migrations/001_evidence_record.sql:26-98`.
- Flat projection (what the miner writes): `western_blot_miner/evidence_record.py:211-290`.
- Status vocabulary + envelope: `western_blot_miner/evidence_record.py:19-82`.
- Design tokens: `web/app/globals.css:7-18`.
