# Independent Scientific QA — 3-paper reference dataset (91 records / 452 rows)

**Auditor:** independent QA agent (no involvement in producing the dataset).
**Date:** 2026-08-13. **Tree:** `feature/bio-context-beta` @ `17356cf`, working tree clean.
**Scope:** `eval/demo/*/evidence_records.json` (91 records), `eval/demo/*/supabase_rows.json`
(452 rows), the panel crops under `western_blot_miner/data/pdf_runs/*/panel_candidates/`,
the three source PDFs in `research/papers/`, and the engine code paths that produced
the artifacts. Also verifies the claims in `research/demo_scientific_qa.md` (the prior
self-audit) and in the three `eval/demo/*/README.md` files.
**Method:** every record dumped and read field-by-field; every extracted panel crop opened
and compared lane-by-lane against the record; all three PDFs re-extracted with PyMuPDF and
the methods/legends read verbatim; all UniProt accessions re-resolved against the live REST
API today; the dose/duration/band-pattern parsers exercised directly against real caption
strings; the artifacts diffed across the three commits that produced them.
**No code was modified.**

---

## Executive summary

| Severity | Count |
|---|---|
| **Critical** | 3 |
| **Major** | 12 |
| **Minor** | 8 |

**Single most important finding — C1.** In `PMC12856536`, one CV crop
(`page_005_cand_0034.png`) contains **two different experiments** (Fig 3C and Fig 3D).
The four records built from it collapse both into a single panel, assert
`treatment_name = IL-6` (SUPPORTED) on the Ser727 rows — for a panel the paper explicitly
states was run **"in the absence of IL-6"** — and print lane conditions
(`IL-6 -`, `IL-6 + CL-E`, `IL-6 + CL-E + Bis II`, `IL-6 + CL-E + U0126`) that do not exist
in either panel. Lane counts are 4 where the figure has 6 (panel C) and 7 (panel D).
All four records are `record_status = SUPPORTED`, `needs_review = false`. A researcher
searching *IL-6 STAT3 Ser727* gets a confident hit that inverts the paper's stated
condition. This is the only finding in the set that is affirmatively, checkably wrong
about biology while presenting itself as settled.

**Second headline.** The prior self-audit's central claim — *"Critical: 0 open"* — does not
survive an independent read, and one of its two Major write-ups (**M2, the ubiquitin rows**)
describes state that has never existed in the artifact (see **C3**). Both facts matter
because that document has been used to close issues.

**What held up well.** Protein identity, phosphosite assignment, phospho/total separation,
the P-ERK 1/2 CONFLICTING handling, co-IP bait/IgG/input representation, organism threading,
reported-MW abstention, and non-Western rejection are all correct and, in several places,
correct in exactly the way a skeptical reviewer would want (details in
[Verified as correct](#verified-as-correct), 12 items). The failures cluster in
**panel/lane geometry, treatment context, and the two newest features (M1 dose/duration,
M2 band pattern)** — not in the protein biology.

---

## Critical

### C1 — Fig 3C/3D merged into one panel; Ser727 rows assert an IL-6 condition the paper denies

**Where:** `eval/demo/phospho_PMC12856536/evidence_records.json`, crop
`page_005_cand_0034.png`, records `5eb7a96908f62ee1` (P-STAT3 Ser727),
`e31011d758606b47` (P-STAT3 Tyr705), `952877a29c3def7a` (T-STAT3),
`443243276be4aff9` (β-actin). 16 DB rows.

**What the crop actually contains** (opened and read):

* **Panel C** — rows P-STAT3 (Ser727), T-Stat3, β-actin; **6 lanes**; ± matrix printed as
  Bisindolylmaleimide II (20 µM) `− − + − + −`, U0126 (20 µM) `− − − + − +`,
  CL-E (60 µg/ml) `− + + + − −`. **There is no IL-6 row in panel C.**
* **Panel D** — rows P-STAT3 (Tyr705), T-Stat3, β-actin; **7 lanes**; adds
  IL-6 (10 ng/ml) `− + + + + − −`.

**What the paper says** (Fig 3 legend, verbatim from the PDF): panel C — *"cells were
treated with CL-E (60 µg/ml), PKC inhibitor bisindolylmaleimide II (20 µM), and/or the
MEK1/2 inhibitor U0126 (20 µM) for 1 h **in the absence of IL-6**"*; panel D — *"cells were
pretreated with CL-E, U0126 and/or bisindolylmaleimide II (20 µM) for 1 h before IL-6
stimulation (10 ng/ml, 30 min)"*.

**What the records say:**

| record | lanes stored | reality |
|---|---|---|
| Ser727 | `IL-6 -`, `IL-6 + CL-E`, `IL-6 + CL-E + Bis II`, `IL-6 + CL-E + U0126` | panel C, 6 lanes, **no IL-6 anywhere** |
| Tyr705 | `IL-6 -`, `IL-6 +`, `IL-6 + CL-E`, `IL-6 + CL-E + U0126` | panel D, 7 lanes |
| T-STAT3 | `lane1`…`lane4` | appears in *both* C and D; conditions lost |
| β-actin | `lane1`…`lane4` | same |

Three independent errors compound: (a) two experiments share one panel identity; (b) the
lane conditions of two rows on the same "panel" contradict each other (lane 2 is `IL-6 +`
for Tyr705 and `IL-6 + CL-E` for Ser727 — impossible if they are one panel); (c) the Ser727
record's `treatment_name = IL-6` is contradicted by the source. Nothing is flagged:
`anomaly_flags = []`, `needs_review = false`.

**Suggested general fix.** (1) A crop containing more than one panel letter / more than one
column-header block must not be reduced to one panel — split it, or emit a
`PANEL_MERGE_SUSPECTED` anomaly and refuse to settle panel-level scalars. (2) Add a
structural invariant: rows attributed to one panel must agree on lane count and on lane
condition strings; disagreement ⇒ `LANE_GEOMETRY_CONFLICT` + `needs_review`. (3) A
treatment scalar must be supported by that panel's own printed condition matrix, not by
neighbouring prose — a `±` grid that never names the agent is positive evidence of absence,
not of ambiguity.

---

### C2 — An anti-ubiquitin blot is asserted as `modification_type = ubiquitination`, SUPPORTED, on a null target

**Where:** `eval/demo/standard_PMC9559174/evidence_records.json`, record
`ca61b290b735e198`, all 5 panels, **31 DB rows**.

```
raw_target        "Ubiquitin"
canonical_target   null      (MISSING)
uniprot_id         null      (MISSING)
modification_type "ubiquitination"  status SUPPORTED  confidence 0.9
normalized_label  "ubiquitination"  status SUPPORTED
record_status      SUPPORTED   needs_review false   anomaly_flags []
```

The evidence cited is the antibody's own name — `"anti-ubiquitin (1:400 dilution; cat. no.
20200728, Yurogen Biosystems LLC)"` (rank 1) — plus the row label `"Ubiquitin"` (rank 4).
Root cause is `biology._MODIFICATIONS["ubiquitination"] = r"\bubiquitin|poly[-\s]?ub\b|…"`,
which fires on the *antigen name* rather than on a modified-substrate construction.

**Why this is wrong to a wet-lab reader.** Anti-ubiquitin blotting of whole tissue lysate
detects ubiquitin itself (free and conjugated); it is not a ubiquitination readout *of some
other protein*. The record therefore states "ubiquitination of **nothing**" as a settled
fact. I opened all five crops: the ubiquitin row is a **single discrete band** in every
panel — not a poly-Ub conjugate ladder or smear — which removes the one reading under which
"ubiquitination" could be defended. This is structurally the same failure mode as the
forbidden `target.startswith("p")` heuristic (AGENTS.md non-negotiable #1), in a different
vocabulary; note that the engine is correctly conservative on the analogous `P-ERK 1/2`
case and settles here.

**Suggested general fix.** A modification pattern must not fire when the matched wording
*is* the target / antigen name. Require an explicit substrate construction
("ubiquitinated X", "X-Ub", "poly-Ub conjugates of X", "K48-linked X") before asserting a
PTM; otherwise resolve the target as the ubiquitin gene family (UBB / UBC / UBA52 / RPS27A →
genuinely AMBIGUOUS, no single accession) with `modification MISSING` and
`needs_review = true`. The same guard should cover SUMO, NEDD8, GST, FLAG, MYC-tag rows.

---

### C3 — The prior self-audit mis-describes the artifact it audited, and the demo README repeats it

**Where:** `research/demo_scientific_qa.md` and `eval/demo/standard_PMC9559174/README.md`.

`demo_scientific_qa.md` §M2 states the ubiquitin rows *"carry anomaly flags
(MODIFICATION_CONFLICT via the 'ubiquitin(ation)' wordform + ANTIBODY_TARGET_MISMATCH) and
stay `needs_review=true`, canonical MISSING"*, and concludes *"Correct behavior for now
(unsettled + review)"*. The README repeats it: *"Ubiquitin stays honestly unsettled
(canonical MISSING, `needs_review`)"*.

I checked the artifact at all three commits that ever wrote it:

```
680cacd  mod=ubiquitination SUPPORTED | rec=SUPPORTED needs_review=False flags=[]
79ddc25  mod=ubiquitination SUPPORTED | rec=SUPPORTED needs_review=False flags=[]
17356cf  mod=ubiquitination SUPPORTED | rec=SUPPORTED needs_review=False flags=[]
```

The described state has never existed. A genuine Critical (C2) was written up as an
acceptable Major on the strength of a flag that was not there.

Two further inaccuracies in the same document:

* §Minor 1 attributes the Fig 3C/D problem to *"H1299/H1792 inhibitor panels"* — those are
  the **other** paper's cell lines; Fig 3C/D of PMC12856536 is Hep3B. It then rates the
  issue *"presentation-level"*; it is C1 above.
* §Verification spot-checks lists `Santa Cruz SC-398486/SC-293172` among catalog↔target
  claims that *"match the papers' own methods lists verbatim"*. **SC-293172 does not appear
  anywhere in the 91 records** (see M12) — it cannot have been verified against the data.

**Suggested general fix.** QA claims about artifact state must be produced by re-reading the
artifact programmatically (a checked-in assertion script), not written from working memory,
and the severity ledger should carry the exact record id + a reproducible one-liner.

---

## Major

### M1 — `record_id` collides: 91 records collapse to 24 unique ids

`record_builder._record_id()` hashes `doi | figure_label | panel_label | raw_target`, and
`figure_label` / `panel_label` are **null in 100% of the 91 records** (see M2). The id is
therefore a per-paper, per-target hash.

```
716c097c4b8dd97f  n=12  BEX2   across 11 panels, cell lines A549/H1299/H1792
22abbc182bfd757b  n=11  ACTB   across 10 panels, 3 cell lines
7c722b4d8d2e417e  n=9   LC3B   across  8 panels, 3 cell lines
…18 colliding ids in total; 91 records → 24 ids
```

`GET /records/{id}` currently keys on the DB serial, so the beta UI is not broken today —
but the artifact's own identity is not an identity, and anything that later keys on
`record_id` (idempotent upsert, dedup, feedback join, cache) silently merges twelve distinct
experiments into one.

**Fix:** include the panel identity that actually exists (`image_crop_ref` basename, or
page + crop index) in the hash, *and* populate figure/panel labels (M2).

---

### M2 — Figure/panel labels are absent, and the "figure_caption" provenance is agent paraphrase, not source text

* `figure_label`, `panel_label`, `figure_caption` are **null / empty in all 91 records and
  all 452 DB rows**. A researcher cannot cite "Fig 4B"; the evidence panel cannot quote a
  caption.
* The snippets that *are* labelled `type: figure_caption` come from the Stage-2
  `treatment_context` field, which is an agent paraphrase. Example, record
  `e31011d758606b47` / crop `page_004_cand_0029.png`:

  > stored source: `"Hep3B cells treated with IL-6 (10 ng/ml) for the indicated times (0, 5, 10, 20, 30, 60 min)"`
  > actual Fig 2A caption: *"Hep3B cells were treated with IL-6 (10 ng/ml) for the indicated time periods (0-60 min)"*

  The enumeration is not in that caption at all; the nearest enumeration in the paper is
  Fig 3A's *"(0, 5, 10, 30 and 60 min)"*, which has **no 20-min point**. The stored string
  is a blend of two captions and cannot be found in the source.
* **255 of 2 643 source snippets (9.7%) have empty text** — all of them
  `type: figure_caption` on `sample` (91), `cell_line` (91) and `organism` (73). Every
  record asserts the figure caption as evidence for its cell line while quoting nothing.

For a product whose promise is *auditable* evidence, a source snippet that is not in the
paper is worse than a missing one.

**Fix:** capture the real caption into `figure.caption_text` and enforce that any snippet
carrying a document source type (`figure_caption`, `methods`) is a substring of a captured
source blob; anything the model paraphrases must be typed `model_target` / `model_context`.
Never emit a source with empty text — use MISSING.

---

### M3 — Spurious 20-min candidate on the Fig 3A time course

Records `53817ee52469c12d` (P-ERK 1/2) and `79d1450adc1a89b9` (T-ERK 1/2), crop
`page_005_cand_0036.png`:

```
duration: value=null status=AMBIGUOUS candidates=[0, 5, 10, 20, 30, 60] min
bands   : 0 min, 5 min, 10 min, 30 min, 60 min      ← 5 lanes, no 20
Fig 3A  : "for the indicated times (0, 5, 10, 30 and 60 min)"   ← no 20
```

The record contradicts both its own per-lane data and the source. Traceable to the
paraphrased context in M2.

**Fix:** cross-validate the panel-level candidate series against the union of per-lane
values; a candidate with no lane and no verbatim source support is a hallucinated candidate
— drop it or flag `CANDIDATE_UNSUPPORTED`.

---

### M4 — AMBIGUOUS dose merges different reagents and different units into one unit-less bag, destroying a settled value

`page_005_cand_0034.png` (all 4 records):

```
treatment_name = "IL-6"
dose = null (AMBIGUOUS)   dose_unit = null   candidates = [60.0, 20.0, 10.0]
```

Those three numbers are **CL-E 60 µg/ml, Bis II 20 µM / U0126 20 µM, and IL-6 10 ng/ml** —
three reagents in three unit systems, presented as competing values for the dose of IL-6,
**with the unit dropped**. IL-6's dose is not ambiguous at all; the paper states 10 ng/ml.
The AMBIGUOUS fallback here actively replaces a settled fact with a meaningless list.

`page_004_cand_0028.png` / `page_005_cand_0035.png` (Fig 2B / 3B):

```
dose     candidates = [10.0, 30.0, 60.0, 10.0]   ← duplicate 10 (CL-E 10 µg/ml + IL-6 10 ng/ml), unit null
duration candidates = [1.0, 30.0]                ← 1 h pre-treatment + 30 min stimulation, unit null
```

1 h pre-treat and 30 min stimulation are two *different quantities of two different steps*,
not competing readings of one quantity.

**Fix:** scope dose/duration extraction to the named treatment agent (nearest-agent
binding), keep the unit attached to every candidate, never merge candidates whose units
differ, and model "pretreatment" vs "stimulation" as distinct slots rather than one
`duration`.

---

### M5 — `lane_dose` is null on 452/452 band rows; the per-lane half of the M1 fix has zero coverage

```
total band rows: 452 | lane_dose non-null: 0 | lane_duration non-null: 29
```

The two genuine dose-response panels in the corpus (Fig 2B `page_004_cand_0028`, Fig 3B
`page_005_cand_0035`) print `CL-E (µg/ml)  −  −  10  30  60`, and the records store lane
conditions `IL-6 + / CL-E 10`, `… / CL-E 30`, `… / CL-E 60` — yet every one carries
`lane_dose = null`. Reproduced directly:

```python
extract_dose_series("IL-6 + / CL-E 10")   # -> []        (no unit in the lane label)
extract_dose_series("CL-E 10 ug/ml")      # -> [10.0 ug/ml]
```

The parser requires the unit inside the lane string; real figures print the unit once in the
row header. So on the only dose-response panels in the dataset the feature contributes
nothing, and the dose survives only as free text.

**Fix:** when a lane label carries a bare number that matches one of the panel-level dose
candidates, inherit that candidate's unit (record the inheritance in provenance). The
time-course path works precisely because "10 min" happens to carry its unit.

---

### M6 — Dose regex misses the micro sign, and fabricates values from digits inside reagent names

`biology._DOSE` / `_DOSE_SERIES` accept only ASCII units (`um`, `ug/ml`, …). Verified against
the co-IP paper's real captions:

```python
extract_dose_series("rapamycin (10 µM) for 4 h")        # -> []      (should be 10 µM)
extract_dose_series("CL-E at 10, 30 and 60 µg/ml")      # -> []      (should be 3 values)
extract_dose_series("LY294002 (10 µM for 24 h)")        # -> []
extract_dose_series("rapamycin (10 uM) for 4 h")        # -> [10 uM] (ASCII works)
```

This is why **every one of the 53 co-IP records has `dose` and `duration` MISSING** although
Fig 1C/2C/3A/3C state "rapamycin (10 µM) for 4 h", Fig 3E states "BafA1, 20 nM ... 4 h", and
Fig 4G states "LY294002 (10 µM for 24 h)". The masking effect is that the Stage-2 observer
happened to type ASCII `ug/ml` for the phospho paper, so the bug never surfaced there.

Separately, `_DOSE_SERIES` has **no leading word boundary**, so a digit glued to a reagent
name becomes a phantom series member:

```python
extract_dose_series("BafA1, 20 nM")   # -> [{'value': 1.0, 'unit': 'nM'}, {'value': 20.0, 'unit': 'nM'}]
```

`BafA**1**, 20 nM` yields a fabricated 1 nM dose. The paper's actual wording is
"bafilomycin A1 (BafA1, 20 nM)". Reagent names full of digits (U0126, LY294002, ATG5,
RHEB Q64L, siBEX2#1) make this a broad class.

**Fix:** add `[µμu]` to every unit alternation; add a leading `\b` plus a guard that no
series member is immediately preceded by a letter.

---

### M7 — Loading-control classification depends on label spelling: `β-actin` counts, `ACTB` does not

`biology.LOADING_CONTROLS` holds `"actin"`, `"tubulin"`, `"gapdh"`, … and
`is_loading_control()` substring-matches the raw label. `"actb"` does not contain `"actin"`;
`"tuba1b"` does not contain `"tubulin"`. Across the 452 rows:

| label | `loading_control` | `experiment_type` | rows |
|---|---|---|---|
| `β-actin` (PMC12856536) | **true** | loading_control | 25 |
| `ACTB` (PMC12706926 + PMC9559174) | **false** | standard_western / co_ip | 81 |
| `GAPDH` | true | loading_control | 31 |
| `TUBA1B` | **false** | standard_western | 31 |

The same protein is a loading control or not depending on how the figure spells it —
**81 of 452 rows (18%) are misclassified**. It is worst in exactly the paper where it
matters most: PMC9559174 is a *loading-control validation* study whose Fig 5 blots ACTB,
TUBA1B, GAPDH and ubiquitin side by side as candidate reference proteins and concludes ACTB
is the best one; HiveBlot flags only GAPDH. In PMC12706926 every quantification is
normalised to ACTB ("ratio of LC3B-II: ACTB", stated in five figure legends) and ACTB is
still not a loading control.

**Fix:** run the loading-control test on the *canonical symbol after UniProt resolution*
(ACTB, ACTG1, GAPDH, TUBA1A/B, TUBB, VCL, LMNB1, H3, PPIA, HSP90AA1 …), not the raw label,
and fall back to raw-label matching only when resolution fails.

---

### M8 — Input and loading-control rows inherit `experiment_type = co_ip` and an `ip_bait_protein`

Crop `page_007_cand_0046.png` (Fig 4D). The figure shows p85 and PIK3CA across
Input+IP, and BEX2 and ACTB **in the input only** — I verified this against the crop.
The records:

```
ACTB : experiment_type=co_ip  ip_bait_protein=PIK3CA   bands = [Input BEX2-, Input BEX2+]
BEX2 : experiment_type=co_ip  ip_bait_protein=PIK3CA   bands = [Input BEX2-, Input BEX2+]
```

A row with no IP and no IgG lane is an input / loading row on a co-IP figure, not a co-IP
measurement. As stored, a *co-IP PIK3CA* search returns an actin input control as a
protein-interaction result.

**Fix:** keep the panel-level `co_ip` flag, but set `experiment_type = co_ip` and
`ip_bait_protein` only on rows that actually have an IP or IgG lane; give the others
`co_ip_context` (the mechanism already exists and is used correctly for methods-only
mentions).

---

### M9 — The new `band_pattern` annotation is applied inconsistently, and one of its two positive targets is doubtful

I opened every crop that contains one of the four annotated targets. Result:

**Confirmed correct (visual):**
* `P-ERK 1/2` and `T-ERK 1/2`, crops `page_005_cand_0035` and `page_005_cand_0036` — two
  clearly separated bands (ERK1/ERK2) in every lane of both rows; β-actin on the same
  panels is a single band and is correctly unannotated. 20 lanes, all justified.
* `LC3B`, crop `page_005_cand_0032` (Fig 2C) — unmistakable LC3B-I / LC3B-II doublet in all
  6 lanes.

**Inconsistent:** LC3B is annotated in **1 of its 9 records**. The doublet is equally
obvious and unannotated in `page_004_cand_0025` (Fig 1C, both H1792 and A549),
`page_009_cand_0055` (Fig 5E), `page_010_cand_0062` (Fig 6A), `page_006_cand_0039/0040`.
The starkest case is `page_010_cand_0062`: in one crop, **LC3B (obvious doublet) is
unannotated while BEX2 in the same crop is annotated**.

**Doubtful:** `BEX2` doublet, `page_010_cand_0062`, 4 lanes. BEX2 is a single ~15–20 kDa
band in every other panel of the same paper (Fig 1C, 4B, 4D, 5E — all inspected). Worse,
**two of the four annotated lanes have `band_state = uncertain`** while carrying
`band_pattern = doublet, band_count = 2` — you cannot count bands in a lane whose presence
you decline to settle. That is an internal contradiction, not just a judgement call.

**Under-applied elsewhere:** T-STAT3 shows a clear upper+lower band pair in Fig 2A, 2B, 3C
and 3D; RPS6KB1 and p-RPS6KB1 show two bands in Fig 5E; MYC shows multiple bands in Fig 5E.
None annotated.

The contract "null = the source didn't say" means most of this is not *false* — but the
HANDOFF's claim that patterns were added "ONLY for the 4 targets visibly resolving as two
bands in the inspected crops" implies coverage the data does not have. As populated, the
feature cannot support cross-panel comparison of the same target, which is the one thing a
descriptive multiplicity field is for.

**Fix:** make observer pattern claims a per-(panel, row) checklist with three states —
`pattern`, `inspected: single`, `not inspected` — instead of one nullable field; forbid a
pattern on any lane whose `band_state` is `uncertain`; and require that a pattern asserted
for target T in one panel of a paper triggers explicit re-inspection of T in that paper's
other panels.

---

### M10 — Two complete Western panels never reached the dataset (PMC12706926 Fig 5A, 5B)

The deterministic CV stage kept 15 of 76 candidates for this paper
(`llm_candidates.json`); from page 9 it kept only `cand_0054` (cv 0.687, an IF/bar-chart
region → correctly 0 records) and `cand_0055` (cv 0.843 = Fig 5E). I rendered page 9:
**Fig 5A (A549) and Fig 5B (H1792) are two full 9-row Western panels** — BEX2, p-AKT (S473),
AKT, p-RPS6KB1 (T389), RPS6KB1, p-EIF4EBP1 (S65), EIF4EBP1, LC3B, ACTB × 2 lanes each —
scored below threshold and never presented to Stage 2. That is roughly 18 records of real
evidence, including three phospho/total pairs, missing.

The demo README states "11 real WB panels", which reads as the paper's total; it is the
number that survived CV filtering.

**Fix:** report CV *recall* against a human panel inventory per paper (not just the count
kept), and treat a below-threshold candidate on a page whose legend contains "western
blot" as a review item. Also record the CV threshold and each candidate's score in the demo
README so recall claims are checkable.

---

### M11 — A tissue is stored in `cell_line`

All 20 PMC9559174 records and all 124 of their DB rows:

```
sample    = "mouse submandibular gland (SMG) tissue"
cell_line = "mouse submandibular gland (SMG) tissue"
tissue    = null
```

`tissue` exists and is empty. Per HANDOFF session 5, `cell_line` is a **load-bearing
grouping key** for search results, so a tissue sample is grouped and filtered as if it were
an immortalised line, and a *tissue:* filter finds nothing.

**Fix:** route non-cell-line samples to `tissue` (and `organism`), leave `cell_line` null,
and group on a `sample_identity` that is whichever of the two is populated.

---

### M12 — Two anti-PIK3CA antibodies in the methods; one is silently chosen, the other vanishes

PMC12706926 methods, verbatim: *"anti-LC3B (2775), **anti-PIK3CA (4249)** … were obtained
from Cell Signaling Technology; … anti-BEX2 (SC-398486), **anti-PIK3CA (SC-293172)** were
obtained from Santa Cruz Biotechnology."*

Every PIK3CA record asserts CST **4249** with `association_confidence = 0.92` and
`candidates = []`. **SC-293172 appears nowhere in the 91 records.** Fig 4B/4D use "the
PIK3CA antibody" without saying which, so nothing in the panel disambiguates.

This is a false-settled association of exactly the kind the evidence contract exists to
prevent (and the prior QA listed SC-293172 as verified — see C3).

**Fix:** when >1 antibody in a paper's methods claims the same target and the panel does not
disambiguate, emit all of them as candidates on `catalog_number` and drop
`association_confidence` accordingly. The `association_confidence` mechanism already exists
(P-ERK 1/2 correctly gets 0.6); it just isn't triggered by intra-paper reagent ambiguity.

---

## Minor

1. **`duration_unit` survives an AMBIGUOUS `duration`.** e.g. `page_004_cand_0029` rows:
   `duration = null`, `duration_unit = "min"` — a unit with no value, both in the record and
   in the DB column.
2. **`sample` duplicates `cell_line` in 91/91 records.** (Carried over from the prior QA;
   still true, still harmless, still redundant in the detail panel.)
3. **P62 records carry an antibody entry the methods never list.** PMC12706926's reagent
   paragraph contains no anti-p62; vendor and catalog correctly abstain, but an antibody row
   `target=P62, role=detection, detection_confidence=0.6` is still asserted. Label it
   explicitly "antibody not listed in methods" rather than showing a half-empty reagent.
4. **`image_crop_ref` stores absolute local paths** (`/Users/niks/hive/…`) in
   `supabase_rows.json`; these would ship to the hosted DB and resolve nowhere.
5. **The M1/M2 fields are not searchable.** `band_pattern`, `band_count`, `band_notes`,
   `lane_dose`, `lane_duration` live only inside the `provenance` JSONB, not as columns, so
   the SQL search path cannot filter on "doublet" or on a per-lane dose.
6. **A stated antibody-specificity caveat is dropped.** PMC9559174 says its anti-TUBA1B
   antibody *"has the same target amino acid sequence as TUBB5; thus, more specific
   antibodies are required to discriminate"*. The record presents `TUBA1B → P05213` at
   confidence 0.96 with no caveat. Nothing is fabricated, but the paper's own warning about
   the identity of the band is exactly the context a reviewer wants surfaced.
7. **Faint-lane band states run conservative.** `P-ERK 1/2` lane 1 (0 min,
   `page_005_cand_0036`) is `uncertain` though a faint doublet is visible; several
   knockdown lanes are `uncertain` where `absent` would be defensible. These are legitimate
   observer calls at crop resolution, listed for completeness rather than as errors.
8. **`compare_records.record_key()` is not unique on multi-cell-line crops.**
   `key = (crop basename, raw_target)`; `page_004_cand_0025` carries H1792 and A549 rows for
   BEX2 / P62 / LC3B / ACTB, so four keys hold two records each. When the automated backend
   is finally run, those pairs may be matched in arbitrary order and score `cell_line` as
   wrong. Add cell line (or lane-condition signature) to the key.

---

## Verified as correct

This is a trust audit, so the passes are enumerated as precisely as the failures. Each item
below was independently re-derived, not taken from the prior QA.

1. **UniProt accessions and expected MW — 16/16 exact, re-resolved live today** against
   `rest.uniprot.org`, organism-correct:
   STAT3 P40763 (88.1) · AKT1 P31749 (55.7) · PIK3CA P42336 (124.3) · RPS6KB1 P23443 (59.1) ·
   EIF4EBP1 Q13541 (12.6) · BEX2 Q9BXY8 (15.3) · ACTB P60709 (41.7) · MYC P01106 (50.6) ·
   mouse Gapdh P16858 (35.8) · mouse Actb P60710 (41.7) · mouse Tuba1b P05213 (50.2).
   Every `expected_kda` in the dataset matches the live sequence mass to the decimal.
   **No accession is guessed anywhere:** LC3B, P62, p85, ATG12-ATG5 and Ubiquitin are left
   `MISSING` rather than resolved (see the note under "Judgement calls" below).
2. **Reported MW is null in 91/91 records — and it should be.** I grepped all three
   full-text extractions: the *only* occurrence of "kDa" in the entire corpus is inside a
   gene name, *"Ribosomal protein S6 kinase, 70 kDa, polypeptide 1"*, in PMC12706926's
   abbreviation list. It is correctly **not** attributed to the RPS6KB1 records, which keep
   `reported = null, expected = 59.1`. This is precisely the page-blob trap session 3 fixed,
   re-verified on the hardest available instance. Ladder marks printed inside the co-IP
   crops (70 / 100 / 20 / 40) are likewise not treated as reported MW — correct per
   AGENTS.md decision #5, and BEX2 (expected 15.3, ladder mark 20) is not conflated.
3. **Antibody ↔ target ↔ catalog ↔ dilution match each paper's own methods verbatim.**
   PMC12856536 6/6 (CST 9145 Tyr705, 9134 Ser727, 4904 t-STAT3, 4370 p-ERK, 4695 t-ERK,
   4967 β-actin; dilutions 1:1,000 / 1:2,000 all exact).
   PMC9559174 4/4 (Yurogen 20200728 @ 1:400, Abcam ab108629 @ 1:100,000, CST 5174s, CST
   8457s — all exact including the `s` suffixes).
   PMC12706926 13/14 catalogs correct (A1978, C3956, 2775, 4249, 12994, 9271, 9272, 9234,
   9202, 9451, 9452, 60225-1-Ig, SC-398486); the one gap is SC-293172, written up as M12.
   HiveBlot asserts the *paper's* claimed pairing, not vendor-site truth — correct scope.
4. **Phosphosites are right and are the canonical sites.** Tyr705 and Ser727 (STAT3),
   Ser473 (AKT1), Thr389 (RPS6KB1), Ser65 (EIF4EBP1) — each matches both the figure row
   label and the antibody name in the methods. The one-letter forms `S473` / `T389` / `S65`
   are correctly expanded to Ser/Thr with position, and `phospho_specific_antibody = true`
   is set only where the methods name a phospho antibody.
5. **Phospho and total are cleanly separated.** P-STAT3 (Tyr705) / P-STAT3 (Ser727) /
   T-STAT3; p-AKT (S473) / AKT; p-RPS6KB1 (T389) / RPS6KB1; p-EIF4EBP1 (S65) / EIF4EBP1 —
   distinct records, distinct antibodies, distinct catalog numbers, and no total record
   carries a residue. No phospho/total cross-contamination anywhere in 91 records.
6. **The P-ERK 1/2 CONFLICTING handling is exemplary and is the behaviour the rest of the
   engine should imitate.** `modification_type.value = null`; both candidates preserved with
   their own evidence (`antibody` rank 1 *"p-ERK (1:1,000; CST #4370)"* vs `model_target`
   rank 4 *"P-ERK 1/2"*); `experiment_type` AMBIGUOUS with `value = null`; canonical target
   the **MAPK1/MAPK3 family with no single accession** (the EPHB2 false-friend does not
   recur); `association_confidence` dropped to 0.6; four anomaly flags
   (MODIFICATION_CONFLICT high, ANTIBODY_TARGET_MISMATCH, EXPERIMENT_TYPE_AMBIGUOUS,
   PROTEIN_AMBIGUOUS) and `needs_review = true`. Its paired `T-ERK 1/2` record correctly
   stays AMBIGUOUS-on-protein-only. This is the only record class in the dataset that
   reaches CONFLICTING, and it earns it.
7. **co-IP representation matches Fig 4B and Fig 4D lane for lane** (both crops opened and
   compared against the legends):
   *Fig 4B* (`page_007_cand_0047`) — H1299, lanes `Input` / `IgG` / `IP:PIK3CA`, rows PIK3CA
   and BEX2, with **`IgG` = `band_state: absent`** on both rows. The negative control is
   represented as a real lane with a real (negative) observation, not dropped.
   *Fig 4D* (`page_007_cand_0046`) — H1792, lanes `Input BEX2-/+` and `IP:PIK3CA BEX2-/+`;
   p85 and PIK3CA across all four lanes, BEX2 and ACTB across the two Input lanes only —
   which is exactly what the figure prints. `ip_bait_protein = PIK3CA` on both panels.
   The paper's methods-only immunoprecipitation wording correctly stays a non-settling
   `co_ip_context` flag on the eight non-co-IP panels rather than reclassifying them.
   (Fig S2 is supplementary and absent from the local PDF; nothing was invented for it.)
8. **Organism handling is correct.** PMC9559174 records carry `organism = mouse` and the
   mouse accessions; the two human papers carry human accessions; `organism` is only set
   from explicit claims (Hep3B records leave it null rather than inferring human from the
   cell line) — conservative and consistent with the documented rule.
9. **Lane inventories match the crops.** Verified lane-by-lane:
   PMC9559174 all 5 panels exact — `E14.5…P0` (6), `P0,P7,P14,P25F,P28M` (5;
   **`P25F` is verbatim in the figure**, confirmed by zoom, even though the caption text
   says P28F), `P28F…P112M` (8), `L5d Ctrl…L7d` (4), `L7d Ctrl…DL28d` (8).
   PMC12856536 Fig 2A (6 timepoints) and Fig 2B / 3B (5-lane `CL-E − − 10 30 60` × `IL-6 − + + + +`)
   exact, including per-lane durations 0/5/10/20/30/60 on the time course.
   PMC12706926 Fig 1C (the H1792 | A549 side-by-side split is handled correctly, two record
   sets with the right cell line each), Fig 2C, Fig 5E — all exact.
10. **Non-Western rejection: 22 of the 43 presented candidates produced zero records** —
    bar charts (qPCR / luciferase / MTT / densitometry), IF micrographs, Venn diagrams, dot
    plots, a legend block and a publisher logo. No blot was fabricated from a chart. I
    confirmed the two page-9 zero-record candidates of the co-IP paper are genuinely IF and
    caption regions.
11. **No invented normalisations.** LC3B → MAP1LC3B, P62 → SQSTM1, p85 → PIK3R1 are all
    resolvable (and PMC12706926's own abbreviation list even spells two of them out), yet
    the resolver abstains rather than guessing. That is the correct default under
    "never guess an accession", though see the judgement call below.
12. **Band presence stays categorical.** `present / absent / uncertain` only; no intensity,
    no ratio, no densitometry — even though all three papers publish quantified
    LC3B-II:ACTB and CV values that would have been easy to scrape. The FUTURE intensity
    columns remain NULL. AGENTS.md decision #6 holds across all 452 rows.

**Judgement call worth a decision, not a defect:** LC3B / P62 / p85 are unresolved even
though the source paper defines them explicitly in its own abbreviation table
(*"LC3B — MAP1LC3B"*, *"p85 — Phosphatidylinositol 3-kinase regulatory subunit alpha"*).
Abstention is safe, but it means the paper's central claim — the PIK3CA–p85 interaction —
is not reachable by a `PIK3R1` search. A paper-scoped alias table harvested from the
article's own abbreviation list would resolve these *without* guessing, and would carry
`source: paper_abbreviation_list` as provenance.

---

## Could not verify

* **Faint-band presence/absence at crop resolution.** Whether a barely-visible lane is
  `absent` or `uncertain` is genuinely observer-dependent at the DPI available here; I
  accepted the stored calls except where they contradict a stated condition.
* **Whether a doublet exists in low-signal lanes** (the BEX2 `uncertain` lanes of M9). I can
  say the annotation is internally contradictory; I cannot say what is physically there.
* **Fig 3C/3D band states** (C1). Because those records do not correspond to the real lanes,
  there is nothing to check them against — they need re-extraction, not re-scoring.
* **Vendor-site truth of catalog numbers.** Out of scope by design; I verified only that the
  dataset reproduces each paper's own claimed pairings, which it does (item 3).
* **Supplementary figures S1 / S2** of PMC12706926 — not present in the local PDF, so their
  co-IP panels could be neither audited nor faulted.
* **Automated-backend behaviour.** No model credentials in this environment; all three
  papers remain agent-in-the-loop Stage 2, which is honestly documented in every README.
  Note that M2/M3/M4 are partly *artifacts of that transport* — an automated Stage 2 fed
  the real captions would fail differently, and would immediately expose M6 (the µ bug).

---

## Recommended order of work before UCSF

1. **C2 and C1** — both produce confidently wrong biology today. C2 is a one-rule change in
   `biology._MODIFICATIONS`; C1 needs the panel-split / lane-geometry invariant.
2. **M7** — 18% of rows carry a wrong loading-control flag, and the fix (match on canonical
   symbol) is small and testable.
3. **M6** — the µ bug and the `_DOSE_SERIES` boundary bug are two regex characters, and
   until they are fixed no real paper's doses will be captured.
4. **M2 / M1** — provenance integrity and record identity. These are the two that make the
   evidence panel trustworthy rather than plausible; a UCSF reviewer clicking "where did
   this come from?" is the beta's entire premise.
5. **M4 / M5 / M3** — finish the M1 feature properly: units on candidates, agent scoping,
   lane-level inheritance.
6. **M9** — either widen the band-pattern pass to every inspected panel with an explicit
   "inspected: single" state, or withdraw the two doubtful/orphan annotations (BEX2
   `page_010_cand_0062`, LC3B `page_005_cand_0032`) until it can be applied uniformly.
   A feature that describes the same protein differently in two panels of one paper is
   worse than no feature.
7. **C3** — replace the self-audit with an assertion script so the next QA claim is
   checkable, and correct the two demo READMEs (ubiquitin status; "11 real WB panels").
