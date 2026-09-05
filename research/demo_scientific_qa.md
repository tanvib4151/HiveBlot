> **CORRECTION (2026-08-13, after independent QA):** this self-audit contains
> errors — see `research/independent_scientific_qa.md` (finding C3). Its M2
> claim that ubiquitin rows carried `MODIFICATION_CONFLICT`/`needs_review` was
> wrong (they were SUPPORTED with no flags until fixed); its Minor #1
> misattributed the two-experiments-in-one-crop problem (that was Critical C1,
> fixed); and one catalog it lists as verified (SC-293172) does not appear in
> the records. Treat the independent QA as authoritative.

# Scientific QA — 3-paper demo dataset (91 records / 452 rows)

**Method note:** the planned independent Opus QA agent was killed by session
limits before producing output; this audit was performed by the integration
agent (which also produced the Stage-2 observations). It is therefore a
*self-audit with fresh eyes on the artifacts*, not an independent review —
treat severity judgments accordingly, and re-run an independent QA before the
UCSF beta. Inputs: `eval/demo/*/evidence_records.json`, panel crops,
`research/real_pipeline_report.md`, live UniProt spot checks.

## Executive summary
- **Critical: 0 open.** (Five critical-class engine bugs were found and fixed
  during sessions 2–3, with regression tests: ERK→EPHB2 false identity,
  p53/PARP prefix mangling, page-level co-IP bleed, bare-mention fake
  conflicts, page-blob reported-MW attribution.)
- **Major: 2 open** (below — both representational, both surfaced honestly in
  the UI as lane-level data, neither fabricates a value).
- **Minor: 3 open.**

## Major

### M1 — Record-level duration on time-course panels
Fig 2A/3A rows (PMC12856536) carry `treatment.duration = 60 min` while the
panel is a 0–60 min **time course**. 60 is the parse of "for the indicated
times (0, 5, 10, 20, 30, 60 min)" — technically the last stated time, not THE
duration. Per-lane times are correctly preserved in `lane_condition`
(0/5/10/20/30/60 min), so nothing is fabricated, but a scalar duration on a
time-course record over-summarizes. **Root cause (generalizable):** the
deterministic treatment parser takes one dose/duration per row (known
limitation, HANDOFF "Multi-dose lane extraction"). **Recommended fix (not
tonight):** when >1 duration/dose matches the treatment context, store
value=null with candidates (range), status AMBIGUOUS. Same applies to the
CL-E dose-response rows carrying `dose = 60 µg/ml` from "10, 30 and 60 µg/ml".

### M2 — `Ubiquitin` rows (PMC9559174) surface a modification question
The anti-ubiquitin blot rows carry anomaly flags (MODIFICATION_CONFLICT via
the "ubiquitin(ation)" wordform + ANTIBODY_TARGET_MISMATCH) and stay
`needs_review=true`, canonical MISSING. That is honest, but the underlying
question — "is this a ubiquitin-protein blot or a ubiquitination readout of
conjugates?" — is genuinely ambiguous in the source and our record can't
represent "poly-Ub conjugate smear" as a concept. Correct behavior for now
(unsettled + review), logged as a schema gap (band multiplicity/smear —
already Tier-1-adjacent in RESEARCH_SYNTHESIS).

## Minor
1. Some lane labels in H1299/H1792 inhibitor panels (Fig 3C/D, PMC12856536)
   compress the printed +/− matrix into text like "IL-6 + CL-E + U0126";
   faithful in content but not verbatim lane text (the figure prints a ±
   grid). Presentation-level.
2. `sample` and `cell_line` duplicate each other for cell-line papers
   (builder aliases them); harmless, slightly redundant in the detail panel.
3. `P62` antibody has no vendor/catalog because the methods list omits it —
   correct abstention, but the UI shows an antibody row with only a target;
   could be labeled "antibody not listed in methods" explicitly.

## Verification spot-checks (passed)
- UniProt: STAT3 P40763 (88.1), AKT1 P31749 (55.7), PIK3CA P42336, RPS6KB1
  P23443, EIF4EBP1 Q13541, BEX2 Q9BXY8; mouse Stat3 P42227, Gapdh P16858,
  Actb P60710, Tuba1b P05213 — all live-resolved, organism-correct.
- Catalog↔target claims match the papers' own methods lists verbatim (CST
  9145/9134/4904/4370/4695/4967/9271/9272/9234/9202/9451/9452/2775/12994,
  Sigma A1978/C3956, Proteintech 60225-1-Ig, Santa Cruz SC-398486/SC-293172,
  Yurogen 20200728, Abcam ab108629). HiveBlot asserts the paper's pairing,
  not vendor-site truth — correct scope.
- Phospho vs total separation, co-IP bait=PIK3CA scoping, IgG-control lanes,
  4+4+... non-WB rejections (22 total), reported-MW abstention everywhere
  (no MW stated near targets in any of the three papers): all correct.

## Structural fixes recommended (queue, not tonight)
1. Multi-dose/duration → AMBIGUOUS-with-candidates instead of first/last
   scalar (fixes M1 class generally).
2. Band multiplicity/smear concept (doublet, conjugate ladder) — unlocks M2
   class and the LC3B-I/II doublet seen in PMC12706926.
3. Verbatim lane-label capture guidance for Stage-2 (± grids).
