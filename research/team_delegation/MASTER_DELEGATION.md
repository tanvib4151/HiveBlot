# HiveBlot Team Delegation

**Date:** 2026-08-18
**Source:** the founder walkthrough of the live hosted beta
(`/Users/niks/Downloads/HiveBlot-Founder-Walkthrough.md`), cross-checked against
`HANDOFF.md` and `research/TEAM_BETA_HANDOFF.md`.
**Rule for everything in this package: OBSERVE → UNDERSTAND → ASSIGN → then FIX.
Nothing in this document authorizes a deploy.**

---

## Current Product State

HiveBlot turns Western blot figures, captions, methods, paper context, and
biological metadata into structured, searchable experimental evidence.

The hosted beta is live and working end-to-end:

- **Web:** https://hiveblot-beta.vercel.app (Vercel Free)
- **API:** https://hiveblot-api.onrender.com (Render Free — sleeps after ~15 min
  idle; first request after a quiet spell takes ~20–30 s)
- **DB:** Supabase project `zafombwswztvnjikcsdm` (475 rows, two locked-down
  roles, feedback table at 0 rows and ready for real signal)

What works today, verified in the browser against the public stack:

- **Search** — 7 flagship queries return exactly the reviewed counts
  (`phospho STAT3 Tyr705` 3 experiments / 18 lanes, `co-IP PIK3CA` 4/14,
  `CST 9145` 3/18, `P-ERK` 2/10 Conflicting, `GAPDH mouse` 5/31,
  `needs review` 4/20, `BRCA1 MCF7 olaparib` 0 with correctly scoped copy).
- **Evidence records** — every card opens into a per-field evidence panel:
  value, status badge, provenance tag (via caption / antibody / UniProt /
  deterministic), verbatim quoted source sentence, normalization chain, lane
  strip, DOI link.
- **Figure crops** — real PNGs of the published blot panels, served by the API.
- **Conflicts abstain** — when sources disagree, the field stores no value and
  shows both competing claims with a generated "Why unresolved" sentence.
- **Feedback** — per-field ✓/✗/not-useful/suggest-correction, missing-info,
  record flags, search-understanding prompt. Stored beside the extraction,
  never over it; survives a reseed via `stable_row_key`.

The corpus is a **reviewed reference set**: **3 papers, 93 experiments,
475 evidence rows**, each row human-reviewed field-by-field plus an independent
scientific QA pass. The model-reading step was done agent-in-the-loop because
no model credentials exist yet.

**What that means, and everyone must internalize it:** this beta demonstrates
the *representation, search, provenance, and review experience* on trustworthy
data. It demonstrates **nothing** about automated extraction accuracy on a
paper HiveBlot has not been shown.

## What We Are NOT Doing Yet

- **Arbitrary-paper model automation.** No model credentials, no automated
  extraction evaluation has run, no accuracy claim is defensible.
- **Major scope expansion.** No new papers into the corpus without a reviewed
  ingestion pass; no literature-wide coverage claims.
- **Densitometry.** Band presence is categorical (present / absent /
  uncertain). We never infer intensity from an image. Multiplicity (doublet,
  smear) is descriptive only.
- **Broad production scaling.** The stack stays on the free tier; cold starts
  are a documented tradeoff, not an engineering project.

## Current Problems

Findings from the founder walkthrough, sorted by domain. Priority codes are
defined in the next section. "Where" points at the code so the assignee starts
in the right place — it does not mean "go edit it today".

### Scientific / biology

| # | Finding | Priority | Where |
|---|---|---|---|
| S1 | Scientific terminology unexplained in the UI: IgG, IP bait, phospho, loading control, doublet, kDa, expected vs reported MW. `/learn` explains none of them. | P1 | `web/app/learn/page.tsx`, `web/components/EvidencePanel.tsx` |
| S2 | Independent scientific QA has not been re-run against the corrected 93-experiment grouping (the Fig 3C/3D split changed what two cards show). | P1 | `eval/demo/`, the 3 papers |
| S3 | Biologically misleading presentation: the `?` marker means both "uncertain" and "legitimately varies by lane" (DURATION on a time course); a "not reported" MODIFICATION field quotes a full methods paragraph listing a dozen unrelated antibodies. | P1 | `web/components/EvidencePanel.tsx`, `api/app/record_detail.py` |

### Product / UX

| # | Finding | Priority | Where |
|---|---|---|---|
| U1 | Homepage gives a first-time user nothing: no corpus size, no example searches, no statement of what HiveBlot searches. Every good query in the walkthrough came from being told what to type. | P1 | `web/app/page.tsx` |
| U2 | `needs review` results never show WHY a row needs review. The triage query returns a list with no reason column; you must open every card. | P1 | `web/components/DatabaseResultCard.tsx`, `api/app/schemas.py` (flags live in the `validation` JSONB, which is deliberately excluded from list responses — surfacing a reason needs an API decision, not just CSS) |
| U3 | No next action after a good result: no save, export, cite, related experiments, or "more from this paper". Session dead-ends. **Product exploration first — do not build all of these.** | P2 | product exploration, then `web/` |
| U4 | Empty `WHY HIVEBLOT SAYS THIS` heading when protein identity is MISSING — reads as a broken panel. | P1 | `web/components/EvidencePanel.tsx` |
| U5 | Confidence is stored per field but never surfaced as a number; badge is the only signal. Open question whether it *should* be shown. | P2 | product decision first |
| U6 | Search page renders `RESULTS -` (bare dash) while loading. | P2 | `web/app/search/page.tsx` |

### CS / data / infrastructure

| # | Finding | Priority | Where |
|---|---|---|---|
| C1 | Public API returns absolute local filesystem paths (`/Users/niks/hive/...`) in `image_crop_ref`. Leaks username + directory layout. Sanitize eventually; note HANDOFF already has an open question about making refs relative to `CROP_BASE_DIR` (rewrites every seeded row — needs a plan, not a hotfix). | P1 | `api/app/schemas.py`, `api/db` column values, `DEPLOYMENT.md` |
| C2 | `GAPDH mouse` works by string coincidence, not an organism filter. A populated `organism` column exists and is unused for this. A mouse line named `NIH/3T3` would not match; a human sample treated with "mouse anti-X antibody" could. **Investigate before changing anything** — the deterministic parser must never hallucinate filters. | P1 | `api/app/bio_query.py`, `api/app/search_service.py` |
| C3 | Internal raw values leak into researcher-facing quote styling: `"ambiguous_family"`, `"{}"`, a CANDIDATES block listing a single candidate named "none". Presentation-layer issue; the underlying data is correct. | P1 | `api/app/record_detail.py`, `web/components/EvidencePanel.tsx` |
| C4 | Render Free cold start: ~20–30 s on the first request after idle, with only "Querying database…" shown. Not something to engineer around now; users and testers must understand it, and the UI could say what is happening. | P2 | `web/app/search/page.tsx` copy; `research/TEAM_BETA_HANDOFF.md` already documents it |

### Communication / positioning

| # | Finding | Priority | Where |
|---|---|---|---|
| M1 | `/about` publishes numbers the beta cannot support: "2.8K+ PAPERS PROCESSED", "12.4K+ BLOTS INDEXED", "520+ PROTEINS TRACKED" vs the real 3 / 93 / 475. Live on the public URL researchers will be sent to. **Single highest-risk finding.** | **P0** | `web/app/about/page.tsx` |
| M2 | `/about` implies automated arbitrary-paper ingestion ("automatically identify / extract / aggregate", "grows with every new publication"). Per HANDOFF this is future work. | **P0** | `web/app/about/page.tsx` |
| M3 | `/learn` documents Upregulated / Downregulated result categories and says band intensity "is what you're really measuring" — the product is explicitly categorical, not densitometry. A researcher reading `/learn` first expects quantification the product refuses to provide. | P1 | `web/app/learn/page.tsx` (lines ~86, ~104, ~111) |
| M4 | Nothing states who the product is for or its sharpest use case (the antibody-before-you-buy question). | P2 | `web/app/page.tsx`, `web/app/about/page.tsx` |
| M5 | Cold-start expectation setting for testers (overlaps C4; the team doc covers it, the site does not). | P2 | copy |

## Priority Levels

- **P0 — blocks researcher trust.** The product's entire competitive advantage
  is that it does not overclaim. Anything where the public site itself
  overclaims is P0. Currently that is exactly **M1 + M2** (the `/about` page).
  Nothing else made the bar.
- **P1 — should fix before wider beta.** Misleading-but-recoverable UI,
  honesty-adjacent copy (`/learn`), first-run experience, internal-value
  leaks, API path exposure, the organism-filter investigation, the QA re-run.
- **P2 — polish / later.** Next-action UX exploration, confidence display
  question, loading dash, cold-start copy, positioning sharpening.

## Suggested Workstreams

Four teammate workstreams plus Nik. Each has its own handoff file in this
directory; each file both assigns work and teaches the part of HiveBlot it
touches.

| Workstream | Handoff file | For | Covers |
|---|---|---|---|
| **A — Biology QA** | `BIOLOGY_QA_HANDOFF.md` | biology / science teammate(s) | S2, S3; field-by-field verification against the 3 papers; conflict/uncertainty review; biologically misleading UI |
| **B — Scientific Communication** | `SCIENTIFIC_COMMUNICATION_HANDOFF.md` | teammate comfortable with both the science and writing (biology + product hybrid) | M1, M2, M3, S1, M4, M5 — drafts, not deploys |
| **C — Product / UX** | `PRODUCT_UX_HANDOFF.md` | product / design teammate(s) | U1, U2 (presentation half), U3, U4, U5, U6 |
| **D — Search & Data Integrity** | `SEARCH_DATA_HANDOFF.md` | CS / data teammate(s) | C1, C2, C3, U2 (API half), C4 |
| **E — Founder** | `NIK_FOUNDER_LEARNING.md` | Nik | learning doc + the decisions listed below |

**On names:** the project docs identify collaborators only by infrastructure
actions — Suhas owns the legacy QIB Supabase project, Srushti provisioned the
clean beta Supabase project. That is not evidence of biology vs product vs CS
specialty, so this package deliberately assigns **roles, not people**. Nik maps
people to workstreams; one person can take two workstreams if the team is
small (B pairs naturally with A or C).

## Nik's Role

**Own (do not delegate):**

1. **The `/about` decision (P0).** Workstream B drafts the honest replacement;
   Nik approves the final positioning and is the only person who deploys it.
   The honest story — "3 papers, fully reviewed, every value traceable to the
   figure" — is the better pitch; deciding exactly how to tell it is a founder
   call.
2. **Evaluation strategy and model direction.** Obtaining model credentials
   (Bedrock or Anthropic) and running the staged automated-extraction
   evaluation (`research/automated_extraction_eval_protocol.md`). Until it
   runs, no arbitrary-paper accuracy claim exists.
3. **Roadmap triage.** Deciding which walkthrough findings become roadmap
   items — especially the next-action UX exploration (U3) and the confidence
   display question (U5), which are product-direction calls.
4. **Integration and merges.** All workstream output lands as drafts, findings
   docs, or reviewed PRs into `feature/bio-context-beta`. Nik merges and
   deploys. Nobody else touches Vercel, Render, or Supabase.
5. **Mapping people to workstreams A–D.**

**Delegate (do not do yourself):** field-by-field biology verification, copy
drafting, UX exploration and mockups, the organism-filter investigation, the
path-sanitation plan. Each has a handoff file.

## Coordination Rules

Read these before starting any workstream task. They come from `HANDOFF.md`
"Decisions That Must Not Be Reversed Casually" plus this delegation's own
workflow rule.

1. **Observe before fixing.** Every assignment starts with reproduction on the
   live beta and reading the relevant source. Findings first, diffs second.
2. **Preserve provenance.** Raw source wording is always kept beside any
   normalized value. Never remove an `as printed`, a quoted sentence, or a
   provenance tag to make a screen cleaner.
3. **No hallucinated biology.** Never invent a value the source does not
   contain, never infer phosphorylation from a name prefix, never present a
   guess as settled. If you are not sure a claim is in the paper, it is not.
4. **No silent conflict resolution.** CONFLICTING fields keep `value = null`
   and both candidates. Nobody "just picks the obvious one".
5. **Reviewed beta ≠ arbitrary ingestion accuracy.** Never write copy, docs,
   or commit messages implying automated extraction works on unseen papers.
6. **Update `HANDOFF.md` when meaningful work lands**, commit it with the
   implementation. Names only, never secrets.
7. **Tests before completion.** Engine suites, `api` pytest, and `tsc` must be
   green before any task is called done. New behavior gets a test.
8. **Never touch the legacy QIB Supabase project** (`belalrbfrndxvdwvjxte`).
   Read-only forever. The beta DB is `zafombwswztvnjikcsdm` and only Nik seeds
   or migrates it.
9. **No AI co-author trailers in commits.** Repository rule; history was
   scrubbed and re-audited. No exceptions.
10. **Work on `feature/bio-context-beta`**, never on `main`.
11. **Corrections are feedback, never edits.** Researcher/QA corrections go
    through the feedback system or a findings doc — never directly into the
    reviewed corpus without Nik's sign-off, because a corpus change means a
    reviewed reseed.
