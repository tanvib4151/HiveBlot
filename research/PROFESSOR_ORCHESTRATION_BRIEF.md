# HiveBlot Orchestration Brief

Technical handoff prepared for an external AI/ML advisor (2026-08-27). Goal:
expert feedback on how we architect and orchestrate models — not on improving
any single model. ~5-minute read. Shareable web version:
https://claude.ai/code/artifact/97e6cafb-9129-4948-ac30-d011dd44ead5

## 1. HiveBlot at a glance

HiveBlot turns Western blot figures, captions, and methods text from published
papers into structured, searchable, **auditable** experimental evidence. It is
built for wet-lab researchers (initial users: UCSF) who need to move between
what a blot shows, the conditions that produced it, and comparable evidence in
the literature. The core technical problem is faithful structured extraction
from a noisy multimodal source (figure panel image + caption + methods prose)
*without fabrication*. The main output is an **Evidence Record**: per-field
envelopes of `{value, confidence, status, source snippets, competing
candidates}`, where status ∈ SUPPORTED / AMBIGUOUS / CONFLICTING / MISSING and
conflicting fields carry `value = null` with all candidates preserved.

## 2. Problem we chose

- Western blot results — the workhorse evidence type in molecular biology —
  are locked inside figure panels. Literature search returns papers, not
  experiments; a researcher cannot query "phospho-STAT3 Tyr705 in Hep3B under
  IL-6" and get lane-level evidence with provenance.
- Naive LLM extraction fabricates biology. Our own predecessor system inferred
  phosphorylation from a "p-" name prefix (p53 → "phospho"), and early LLM
  passes produced synonym false-friends (P-ERK 1/2 → the wrong gene EPHB2) and
  figure-reference misparses ("Fig 3D" → a 3-day treatment). For scientific
  users, one confident fabrication destroys trust.
- Opportunity: a system that **abstains and shows its evidence** beats one
  that answers everything. No existing tool offered field-level provenance,
  conflict preservation, and a researcher-correction loop.

## 3. Our approach

Two pipelines share one database: an offline **ingestion cascade** (paper →
Evidence Records) and an online **query path** (researcher query → grouped
experiment cards). The architecture is deliberately **deterministic-heavy**:
models are used only where symbolic code cannot go (reading a figure panel),
and every model claim is treated as a claim, not ground truth, then reconciled
against deterministic signals through an evidence hierarchy.

- **Inputs:** open-access papers via NCBI E-utilities / BioC full text
  (`pmc.py`) plus the PDF; researcher free-text queries at search time.
- **Ingestion:** PyMuPDF renders pages; OpenCV scores panel candidates
  deterministically (saturation, dark fraction, horizontal band morphology)
  and discards most of the page *before any model call*. A cheap
  vision/language model (Stage 2) emits raw observed claims per surviving
  panel. Deterministic code (Stage 3) parses biology from text (targets,
  phospho-sites, doses, durations, antibody roles), resolves proteins against
  live UniProt (cached, organism-scoped, never guessed), reconciles model
  claims vs. deterministic signals vs. caption/methods evidence, and
  validates. Stage 4 optionally re-runs only AMBIGUOUS/CONFLICTING panels
  through a stronger model.
- **Query:** a deterministic biological query parser (`bio_query.py`) compiles
  most searches straight to SQL; an optional LLM NL→SQL path exists behind an
  AST-level SQL guard (`sql_guard.py`) and a SELECT-only Postgres role.
  Results group into one card per experiment via a content-derived stable
  hash; a feedback API stores researcher corrections *beside* the AI claim
  (with the model's value snapshotted), never overwriting it.
- **LLM abstraction:** `llm_client.py` — Bedrock-first, with Anthropic /
  OpenAI-compatible / mock backends; escalation client is separately
  configurable.

## 4. Current model orchestration

```
INGESTION (offline, per paper)
PDF + BioC text
  → [D] PyMuPDF page render
  → [D] Stage 1: OpenCV panel scoring          (e.g. 55 → 9 candidates)
  → [M] Stage 2: cheap VLM/LLM per panel       ("observed claims": rows, lanes,
                                                antibodies, verbatim context)
  → [D] Stage 3: biology.py parse + reconcile.py evidence hierarchy
        + [R] UniProt REST (cached)  + record_builder validation
  → [M] Stage 4: strong-model escalation       ONLY if record is
        (env-gated, off by default)             AMBIGUOUS / CONFLICTING
  → [D] stable_row_key hashing → Postgres (Supabase)

QUERY (online, per search)
query → [D] bio_query.py deterministic parser → SQL   (default path)
      ↘ [M] optional LLM NL→SQL → [D] sql_guard AST check → SELECT-only role
  → [D] experiment grouping by stable hash → cards + evidence panel
  → [D] feedback POST → insert-only role, stored beside extraction
```

| Component | Kind | In → Out | Called |
|---|---|---|---|
| OpenCV panel filter | Deterministic | page images → scored panel crops | Always |
| Stage 2 extractor | Model | panel crop + local text → raw claim JSON | Per surviving panel |
| biology.py / reconcile.py | Deterministic | claims + text → per-field envelopes w/ status | Always |
| UniProt resolver | Retrieval | symbol + organism → accession, expected MW | Per target, disk-cached |
| Stage 4 escalation | Model | unsettled panel → second-pass claims | Conditional (status-gated) |
| bio_query parser | Deterministic | query text → SQL | Always (default) |
| NL→SQL + sql_guard | Model + routing | query → guarded SQL | Optional path |
| Grouping / feedback | Post-processing | rows → experiment cards; corrections stored | Always |

Key dependency: the reconciliation layer (Stage 3) is the arbiter — a Stage 2
claim never reaches the database unmediated, and the routing signal for
Stage 4 is Stage 3's own status output.

## 5. Current performance / constraints

- **Dataset:** 475 rows / 3 papers / 93 experiment groups / 21 figure crops.
  Hosted beta live (Vercel + Render free tier + Supabase free).
- **Correctness testing:** 165 biology-engine tests, 113 API tests, 34/34
  field-level benchmark, all green. A model-comparison harness scores 3/3
  papers EXACT — but this is a **self-consistency check against the reviewed
  reference set, not a measure of extraction accuracy on unseen papers**.
- **Known error classes (found by manual QA, all fixed with regressions):**
  panel-conflation (two experiments in one crop merged into one record),
  figure-reference misparse ("Fig 3D" → 3 days), synonym false-friends,
  antibody-antigen self-claims. Notably, most were **orchestration/parsing
  errors, not model errors**.
- **Latency:** warm API health ~0.15 s; free-tier cold starts of ~1 min.
  Search latency dominated by one SQL query. Ingestion latency: not yet
  measured with a live model backend.

> **The central honest caveat:** production model credentials have never been
> present, so Stage 2 has so far run *agent-in-the-loop* (a human/agent played
> the model; everything downstream is the real production path).
> Precision/recall/F1 on unseen papers, Stage 4 escalation rate, per-paper
> token cost, and per-call latency are all **unmeasured**. The deterministic
> scaffolding is well-tested; the automated-model regime is not.

## 6. Where we think the orchestration can improve

### Accuracy

- **Status-as-router is coarse.** Stage 4 currently keys on the categorical
  status (AMBIGUOUS/CONFLICTING). Field-level confidence scores exist but are
  uncalibrated and unused for routing. Calibrated confidence could route
  borderline SUPPORTED records too — likely the highest-value accuracy change.
- **Escalation re-runs the same task.** Stage 4 is "same prompt, bigger
  model." Error-specific escalation (e.g. a targeted panel-boundary check for
  suspected conflation, a disambiguation-only call for family shorthand) might
  beat generic re-extraction.
- **No ensemble/self-consistency at Stage 2.** One model, one pass per panel.
  Given fabrication is the failure mode we fear most, k-sample agreement or a
  cheap verifier model could feed the reconciler as an extra evidence source
  without changing its logic.
- **Orchestration-caused errors are real:** both P0 defects to date (identity
  collision merging two cell lines; two experiments concatenated into one
  card) came from key/grouping logic, not model output. Structural checks
  (does this crop contain >1 lane grid?) may belong in the cascade.

### Compute / cost

- **Already cheap by design:** CV pre-filter removes ~85% of candidates before
  any model call; UniProt is disk-cached; the default query path uses zero
  model calls.
- **Possible early exits:** panels where Stage 1 deterministic signals +
  caption parsing already settle every field could skip Stage 2's vision call,
  or get a text-only cheap call.
- **Batching/parallelism:** panels are processed sequentially per paper;
  Stage 2 calls are independent and trivially parallelizable. Multiple panels
  from one figure could share a single batched call, at some risk of the
  panel-conflation class we just fixed.
- **Context pruning:** Stage 2 currently receives page-scoped text context;
  retrieval-style narrowing (caption + matched methods sentences only) would
  cut tokens per call.

### Candidate changes, ranked (our current guess)

| Change | Impact | Difficulty | Compute | Accuracy risk |
|---|---|---|---|---|
| Measure first: unseen-paper eval set + live-model baseline | High (prereq) | Low–Med | Small one-off cost | None |
| Calibrated confidence-based Stage-4 routing | High | Med | Neutral / small ↑ | Low |
| Deterministic early-exit before Stage 2 | Med | Low | ↓ per-paper calls | Med (missed image-only evidence) |
| Error-specific escalation prompts | Med–High | Med | Neutral | Low |
| k-sample Stage-2 agreement on hard panels only | Med | Low | ↑ (bounded if routed) | Low |
| Panel batching per figure | Low–Med (cost only) | Med | ↓ | Med (conflation regression) |

## 7. Questions for you

1. Our escalation trigger is the reconciler's categorical status. Would you
   invest in calibrating field-level confidence for continuous routing (and if
   so, calibrated against what, given we have 3 gold papers), or is the
   categorical gate the right granularity at this data size?
2. Is a cheap-model-first / strong-model-escalation cascade the right shape
   here at all, versus one strong-model pass per panel with a deterministic
   verifier — given panels per paper are few (~10–20) and the cost of one
   fabrication is very high?
3. For the fabrication failure mode specifically: would you add
   self-consistency sampling at Stage 2, a separate small verifier model, or
   lean further into deterministic cross-checks? Which gives the best accuracy
   per added call?
4. Both of our P0 bugs were orchestration bugs (identity/grouping keys), not
   model errors. What structural or invariant checks would you build into a
   multi-stage extraction cascade to catch "two experiments fused into one
   record" classes before they reach the database?
5. If the goal is best F1 per dollar on the next 25 papers, what would you
   change first: the routing policy, the Stage-2 model choice, the context
   handed to Stage 2, or the evaluation harness?

---

Facts above come from HANDOFF.md and the code; unmeasured quantities are
labeled as such — nothing is estimated.
