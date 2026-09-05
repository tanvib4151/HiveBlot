# How Experienced Biologists Actually Read a Western Blot

**Purpose:** Drive HiveBlot beta priorities from how real wet-lab and biopharma
scientists inspect Western blots, their figures, and their Methods. Ends with an
explicit gap analysis against the current Evidence Record schema
(`western_blot_miner/evidence_record.py`, `biology.py`, `record_builder.py`,
`migrations/001_evidence_record.sql`), naming the **Tier-1 biological fields that
are missing**.

**Tiering used throughout:**
- **Tier 1** — required for the HiveBlot beta (a UCSF researcher cannot trust the
  record without it).
- **Tier 2** — important next (materially improves trust / purchasing decisions).
- **Tier 3** — future quantitative / image-analysis work.

Each finding is also tagged **EASY** (usually in the caption or main text) or
**HARD** (buried in Methods / Supplementary / reagent tables, or not reported at
all) to find in a paper — because "hard to find" is exactly the researcher pain
HiveBlot exists to remove.

---

## 1. The biologist's mental model (what they are actually doing)

When an experienced scientist looks at a blot, they are silently running a
verification loop, roughly in this order:

1. **"Is this really my protein?"** — Does the band sit at the expected apparent
   molecular weight? Is there *one* clean band or a mess of bands? Is the
   antibody specific and validated?
2. **"Can I trust this band?"** — Is the exposure reasonable (not saturated, not
   blank)? Is the loading even? Is there a loading / total-protein control? Are
   there replicates?
3. **"Is the biology real?"** — Did the right controls move the right way?
   Positive control up, negative/KO control gone, treatment produced the claimed
   change, the phospho signal tracks the stimulus.
4. **"Can I reproduce / buy this?"** — Exactly which antibody (vendor, catalog,
   clone, lot, dilution), in which cell line, at which dilution, validated how?

HiveBlot's job is to make each of these answerable **from structured, provenance-
tagged evidence**, and to be honest when the paper simply does not report it
(MISSING is a legitimate, useful answer — biologists spend hours discovering a
paper *never stated* the catalog number).

---

## 2. The real questions scientists ask (mapped to what must be captured)

| Question they ask | What HiveBlot must expose | Where it lives in a paper | Find difficulty |
|---|---|---|---|
| Is this really my protein? | apparent MW vs expected MW, band count, specificity/validation | caption + Methods + antibody datasheet | HARD |
| Can I trust this band? | loading/total-protein control, replicates, exposure/saturation, single vs multiple bands | caption + Methods + Supp | HARD |
| Is the MW plausible? | reported (apparent) kDa vs UniProt expected kDa, known anomalous migration | figure ladder + caption | MEDIUM (apparent), HARD (justification) |
| Which antibody should I buy? | vendor, catalog #, clone, **host species**, **clonality**, **species reactivity**, RRID, dilution | Methods / reagents table / Key Resources Table | HARD |
| Has this antibody worked in *this* cell line? | antibody + cell line + band success in that context | Methods + figure | HARD |
| Is this the specific phosphosite? | residue + position, phospho-specific antibody, matched total | caption + antibody name | MEDIUM |
| Total vs phospho? | modification state, and whether a matched total-protein blot exists | caption (p-X vs X panels) | MEDIUM |
| Is this co-IP evidence? | assay type, IP bait, input lane, IgG control | Methods + caption | HARD (design), MEDIUM (word "co-IP") |
| What treatment caused the response? | agent, dose, duration, stimulus, vehicle control | caption + Methods | MEDIUM |
| Were the controls appropriate? | positive / negative / KO-KD / vehicle / IgG / input controls present | caption + Methods + Supp | HARD |
| Was normalization appropriate? | loading control identity, total-protein stain, phospho-to-total | Methods + caption | HARD |

The recurring pattern: **the answer is almost always split between the caption
(easy) and the Methods / Supplementary / Key Resources Table (hard).** The
antibody catalog number, host species, and validation status — the things a
biologist most needs before spending money — are the *hardest* to find and the
highest-value thing HiveBlot can surface.

---

## 3. What biologists inspect IN THE BLOT itself

### 3.1 Molecular weight & band identity
- **Expected MW vs apparent (observed) MW.** The first sanity check. Note: the
  UniProt sequence mass is *expected*; the gel shows *apparent* migration, which
  legitimately differs due to PTMs, glycosylation, SDS binding, and charge. A
  20–30% discrepancy is common and not automatically wrong. **EASY** to read the
  ladder position from the figure; **HARD** to know whether the authors
  addressed anomalous migration. **Tier 1** (keep reported vs expected distinct —
  already a core HiveBlot decision).
- **Single band vs multiple bands / nonspecific bands.** A clean single band at
  the right MW is the ideal. Extra bands = possible nonspecificity, isoforms,
  degradation, or cross-reactivity. **EASY** if the caption/text mentions it or
  the figure clearly shows it; **HARD** to get authors to comment. **Tier 1** to
  at least capture *reported* multiplicity / nonspecific-band mentions from text;
  **Tier 3** to detect it from the image.
- **Doublets.** Two closely spaced bands — often a real signal (e.g.
  phospho-shift, two isoforms, modified vs unmodified). Biologists specifically
  look for these. **MEDIUM/HARD** (usually only in text if noteworthy).
  **Tier 2** from text; **Tier 3** from image.
- **Cleavage products / fragments.** e.g. cleaved caspase-3 (17/19 kDa) vs
  full-length (35 kDa); cleaved PARP (89 kDa) vs full-length (116 kDa). The
  *relationship* between full-length and fragment MW is the evidence.
  **MEDIUM** (named in caption). **Tier 2**.
- **Isoforms.** Multiple gene products / splice variants running at different MW
  (e.g. ERK1 44 kDa vs ERK2 42 kDa; lamin A vs C). **HARD**. **Tier 2**.
- **Smearing.** Degradation, overloading, or aggregation. **HARD** (rarely
  described). **Tier 3** (image).
- **Saturation / over-exposure.** Saturated bands invalidate any quantification
  and hide the real signal. Biologists distrust pure-black, blown-out bands.
  **HARD** (almost never stated). **Tier 3** (image).
- **Background / nonspecific smudging.** Signals dirty membrane, bad blocking,
  too-high antibody. **HARD**. **Tier 3** (image).

### 3.2 Loading, normalization & controls on the blot
- **Loading control** (β-actin, GAPDH, tubulin, vinculin, lamin, histone H3 for
  nuclear, etc.). Biologists check that it is (a) present, (b) even across lanes,
  (c) *appropriate* (nuclear vs cytoplasmic vs whole-cell; a housekeeping gene
  that is itself changed by the treatment is a bad control). **EASY** to see a
  loading-control panel; **MEDIUM** to know which target it normalizes.
  **Tier 1** (identity + presence + which target/panel it belongs to).
- **Total-protein normalization** (Ponceau, stain-free, REVERT). Increasingly
  the journal-preferred normalizer over a single housekeeping protein. **MEDIUM**.
  **Tier 1** to record *as a normalization method*, not just a target.
- **Phospho-vs-total normalization.** For phospho blots, the correct denominator
  is the **total** protein, not (only) a housekeeping gene. Biologists check that
  a matched total blot exists and that the same membrane/samples were used.
  **MEDIUM**. **Tier 2** (linkage between the phospho record and its total).
- **Lane consistency / even loading.** Visual evenness of the loading control.
  **Tier 3** (image).

### 3.3 Exposure, replicates, quantification
- **Replicates — biological vs technical, and n.** "Representative of 3
  independent experiments" is the phrase they hunt for. A single blot with no
  replicate statement is treated with suspicion. Biological replicates (separate
  cultures/animals) >> technical replicates (same lysate re-run). **MEDIUM/HARD**
  (caption or Methods, often vague). **Tier 1** to capture the statement + n +
  biological/technical distinction.
- **Quantification / densitometry & normalization method.** Bar graphs beside
  blots, mean ± SD/SEM, statistical test. **MEDIUM** for the graph; **HARD** for
  the exact normalization math. **Tier 3** for measured intensities (correctly
  NULL until a real pipeline runs — this is already an explicit HiveBlot rule).

---

## 4. What biologists inspect in the EXPERIMENTAL CONTEXT

- **Cell line / primary cells / tissue / organism.** Grounds every other
  interpretation (an antibody validated in human HeLa may fail in mouse tissue;
  expected MW differs by species). **EASY** in caption; organism often implicit
  (inferred from cell line). **Tier 1**.
- **Genotype / KO / KD status of the sample.** WT vs knockout vs knockdown vs
  overexpression. This is both experimental context *and* a specificity control.
  **MEDIUM/HARD**. **Tier 1** (field exists but is under-populated — see §6).
- **Treatment: agent, dose, duration, route.** The independent variable. "EGF
  50 ng/mL, 15 min" — biologists check the dose/time is physiologically sensible
  and matches the claim. **MEDIUM**. **Tier 1** (dose/duration already parsed).
- **Stimulation vs steady state; vehicle control.** Was there a proper
  vehicle/untreated control lane? **MEDIUM/HARD**. **Tier 1** (control presence).
- **Positive & negative controls.** Positive: a sample known to express/respond.
  Negative: a sample known not to. Their presence is a top trust signal.
  **HARD**. **Tier 1**.
- **KO / KD specificity control.** The gold standard for antibody specificity: a
  lane where the target is genetically removed and the band disappears.
  **HARD**. **Tier 1** (both as antibody validation and as experiment control).
- **Co-IP specifics — bait, input, IgG control.** For co-IP: which protein was
  pulled (bait), was an **input** (lysate) lane shown, was a **control IgG** IP
  run? Without input + IgG, a co-IP is weak evidence. **MEDIUM** (word "co-IP");
  **HARD** (input/IgG lanes). **Tier 1**.
- **Biological vs technical replicate design** — see §3.3. **Tier 1/2**.

---

## 5. Antibody details — the highest-value, hardest-to-find information

Biologists (especially in biopharma, where reagent traceability is audited)
scrutinize antibodies more than almost anything else, because a blot is only as
trustworthy as the antibody, and because they may need to **buy the exact same
one**. Ranked by how much they care and how hard it is to find:

| Field | Why it matters | Find difficulty | Tier |
|---|---|---|---|
| **Target (+ modification/site)** | what it claims to detect | EASY (caption/name) | 1 |
| **Vendor** | who sells it | MEDIUM (Methods) | 1 |
| **Catalog number** | the *only* unambiguous way to buy it | HARD (Methods/KRT) | 1 |
| **Clone** (e.g. D3A7, EP2154Y) | pins the exact reagent within a vendor | HARD | 1 |
| **Host species** (rabbit/mouse/goat) | dictates the secondary antibody and whether two primaries can be co-run; needed to buy/plan | HARD | **1 (missing)** |
| **Clonality** (monoclonal / polyclonal) | reproducibility (mono = defined; poly = lot-variable) | HARD | **1 (missing)** |
| **Species reactivity** (human/mouse/rat/…) | "will it work in *my* organism/cell line?" | HARD | **1 (missing)** |
| **Phospho-specificity** | does it detect only the phosphorylated form | MEDIUM (name) | 1 (present) |
| **Validation status** (KO-validated? validated *for WB*?) | the core trust signal; MIQE/vendor validation, KO/KD, peptide block | HARD | **1 (missing)** |
| **Dilution** | reproduce the protocol | HARD (Methods) | 1 (present) |
| **RRID** | globally unique antibody ID; journal-mandated in many venues | HARD | 2 (missing) |
| **Lot number** | poly-clonals vary lot-to-lot; biopharma tracks this | VERY HARD | 3 |
| **Epitope / immunogen** | predict cross-reactivity & which isoforms/species | VERY HARD | 2/3 |
| **Amount/concentration (µg/mL)** | alternative to dilution | HARD | 3 |
| **Secondary antibody** (host, conjugate, vendor) | completes the protocol | HARD | 3 |
| **Application validation** (validated for WB vs only IHC/IF) | an antibody great for IHC may fail WB | HARD | **1/2 (missing)** |

**Key antibody insight for the product:** the *identity* triple (vendor +
catalog + clone) answers "which antibody should I buy," but **host species,
clonality, species reactivity, and validation status** answer "*should* I buy it
and will it work for me." The current schema nails identity and is weak on
trust/fit. Those are the differentiators UCSF researchers will feel immediately.

**Antibody validation literature the product should encode (as flags):**
- KO/KD-validated (band lost in knockout/knockdown) — the strongest.
- Genetic/orthogonal (overexpression, siRNA), peptide-competition/blocking.
- Independent-antibody concordance (two antibodies, same band).
- Validated *for the application* (WB) and *for the species* used.
- Recombinant monoclonal (most reproducible).
These map onto the MIQE / "antibody validation five pillars" (Uhlen et al.) /
CST & Abcam validation framings that experienced users implicitly apply.

---

## 6. Painful information commonly buried (the HiveBlot value proposition)

These are the exact items that waste researcher time; each is a place HiveBlot
wins by surfacing structured evidence with a clear MISSING when absent:

- **Catalog number & clone** — scattered between a reagents paragraph, a
  Supplementary table, and a "Key Resources Table." **Tier 1.**
- **Host species / clonality / reactivity** — usually only on the datasheet, not
  the paper. **Tier 1.**
- **Antibody dilution** — one line deep in Methods. **Tier 1.**
- **Which loading control goes with which panel** — implied by figure layout,
  never stated. **Tier 1.**
- **Replicate number & biological-vs-technical** — a single vague clause
  ("representative experiment"). **Tier 1/2.**
- **Positive/negative/KO/IgG/input controls** — often only in Supplementary.
  **Tier 1.**
- **Dose & duration when multiple are used** — a lane matrix where each lane has
  its own dose/time; the current engine captures only the first per row.
  **Tier 2.**
- **Whether a phospho blot has a matched total blot** — requires cross-panel
  reasoning. **Tier 2.**
- **Anomalous-migration justification** — why the band is not at the sequence
  MW. **Tier 3.**

---

## 7. Gap analysis vs the current Evidence Record schema

Reviewed: `evidence_record.py` (envelopes + `to_supabase_rows`), `biology.py`
(deterministic biology), `record_builder.py` (assembly/validation), and
`migrations/001_evidence_record.sql` (flat columns).

### 7.1 What the schema already does well (keep)
- Field-level `EvidenceField` envelope (value/confidence/status/sources/
  candidates) with SUPPORTED/AMBIGUOUS/CONFLICTING/MISSING — the right backbone.
- **reported vs expected MW kept distinct** (`molecular_weight.reported_kda`
  vs `expected_kda` + `reconciliation`) with a discrepancy anomaly flag.
- **Modification** from evidence, not name prefix; residue + position;
  `phospho_specific_antibody`.
- **Antibody** identity: `antibody_target`, `vendor`, `catalog_number`, `clone`,
  `dilution`, `role` (detection vs immunoprecipitation), plus
  `detection_confidence` and `association_confidence`.
- **Experiment**: `experiment_type` + non-exclusive `experiment_flags` +
  `ip_bait_protein`; co-IP / purified-protein / loading-control detection.
- **Sample**: `cell_line`, `organism` (with cell-line→organism inference),
  `tissue`, `genotype`.
- **Treatment**: `treatment_name`, `dose`/`dose_unit`, `duration`/
  `duration_unit`, raw `treatment_context`.
- **Bands** per lane with categorical `band_state` (present/absent/uncertain) —
  correctly *not* densitometry; quantitative columns exist but stay NULL.
- Validation/anomaly flags + `needs_review`; full provenance JSONB.

### 7.2 MISSING Tier-1 biological fields (specific, named)

These are biological facts a UCSF researcher needs to trust or reproduce a blot,
that the current record cannot represent. **Named by proposed field / location.**

1. **Antibody host species** — `AntibodyInfo.host_species`
   (e.g. rabbit/mouse/goat). Column: `antibody_host_species`.
   *Why Tier 1:* determines the secondary antibody and whether two primaries can
   be co-detected; a standard "which antibody / can I combine these" question.

2. **Antibody clonality** — `AntibodyInfo.clonality`
   (monoclonal | polyclonal | recombinant_monoclonal). Column:
   `antibody_clonality`. *Why Tier 1:* first-order reproducibility signal;
   polyclonals vary lot-to-lot.

3. **Antibody species reactivity** — `AntibodyInfo.species_reactivity`
   (list: human/mouse/rat/…). Column: `antibody_reactivity`.
   *Why Tier 1:* directly answers "will this work in my organism/cell line."

4. **Antibody validation status** — `AntibodyInfo.validation_status` +
   `validated_applications` (list incl. "WB"). Columns:
   `antibody_validation_status`, `antibody_validated_applications`,
   `antibody_ko_validated` (bool). *Why Tier 1:* the central antibody-trust
   signal ("is this really my protein?"); KO/KD/peptide-block validation and
   WB-application validation are exactly what experienced users check.

5. **Controls block** — a first-class controls representation. There is
   currently **no** structured control field except `ip_bait_protein`
   (co-IP only). Proposed `ExperimentInfo.controls` /
   `ControlInfo` with booleans + evidence + lane linkage:
   - `positive_control`
   - `negative_control`
   - `vehicle_untreated_control`
   - `knockout_knockdown_control` (specificity control)
   - `igg_control` (for IP)
   - `input_control` (for IP — note: `biology._INPUT_BLOT` regex already exists
     but is **not surfaced into any field**)
   - `loading_control_present`
   Columns: `positive_control`, `negative_control`, `vehicle_control`,
   `ko_kd_control`, `igg_control`, `input_control` (JSONB or booleans).
   *Why Tier 1:* "were the controls appropriate?" is a core trust question and
   currently unanswerable from the record.

6. **Loading-control linkage & normalization method** — the schema flags a row
   *as* a loading control (`experiment_flags` contains `loading_control`,
   column `loading_control BOOLEAN`) but cannot say **which loading/total-protein
   control normalizes which target**, nor capture **total-protein normalization**
   (Ponceau / stain-free) as a *method*. Proposed:
   `ExperimentInfo.loading_control_target` (e.g. "GAPDH") and
   `ExperimentInfo.normalization_method`
   (housekeeping_protein | total_protein_stain | phospho_to_total | none).
   Columns: `loading_control_target`, `normalization_method`.
   *Why Tier 1:* "was normalization appropriate?"; phospho blots specifically
   require total-protein normalization, and a nuclear target needs a nuclear
   loading control.

7. **Replicates** — `Provenance/ExperimentInfo.replicates`:
   `replicate_n` (int) + `replicate_type` (biological | technical | unspecified)
   + `representative_of_n` evidence. Columns: `replicate_n`, `replicate_type`.
   *Why Tier 1:* "representative of 3 independent experiments" is a primary
   trust cue; its **absence** is itself signal.

8. **Per-band apparent MW & band multiplicity / quality** — `BandObservation`
   holds only `lane_index`, `lane_condition`, `band_state`. It cannot record
   **the apparent MW of an individual band**, **more than one band in a lane**,
   or a **reported doublet / nonspecific / smear** note. Proposed on
   `BandObservation`: `apparent_kda` (EvidenceField),
   `band_qualifier` (single | doublet | multiple | smear | nonspecific), plus a
   record-level `reported_band_count`. Columns: `band_apparent_kda`,
   `band_qualifier`. *Why Tier 1 (text-derived only):* "single clean band?" and
   "is this really my protein?" hinge on band multiplicity; capture what the
   **text/caption reports** now (image-based detection stays Tier 3).

### 7.3 MISSING Tier-2 fields (important next)
- **Antibody RRID** — `AntibodyInfo.rrid`; column `antibody_rrid`. Journal-
  mandated unique reagent ID; strong dedupe/lookup key.
- **Antibody epitope / immunogen** — `AntibodyInfo.epitope`. Predicts
  cross-reactivity, isoform/species coverage.
- **Antibody lot number** — `AntibodyInfo.lot_number` (VERY HARD to find, but
  biopharma tracks it; column `antibody_lot`).
- **Phospho↔total linkage** — `ModificationInfo.matched_total_record_id` linking
  a phospho record to its total-protein counterpart.
- **Isoform / cleavage-product representation** — link full-length vs fragment
  MW (e.g. cleaved vs full PARP); `MolecularWeightInfo.fragment_of` /
  `isoform_label`.
- **Multi-dose / multi-timepoint per lane** — extend `BandObservation` to carry
  its own dose/duration (current engine captures only the first per row —
  documented gap in HANDOFF).
- **Secondary antibody** — host + conjugate (HRP/fluor) + vendor.

### 7.4 MISSING Tier-3 fields (future quantitative / image analysis)
- Measured densitometry: `raw_intensity`, `background_corrected_intensity`,
  `normalized_intensity`, band geometry, `smearing_score`, `saturation_flag`,
  `densitometry_source` — **columns already reserved and correctly NULL**; keep
  them NULL until a real lane-detection + ladder-calibration + IOD pipeline runs.
- Image-derived exposure/saturation/background quality.
- Gel %, membrane type (PVDF/nitrocellulose), reducing/denaturing conditions,
  µg protein loaded, blocking agent, transfer method — protocol reproducibility
  detail; nice-to-have, low trust-per-field.

### 7.5 Population gaps (schema exists, builder never fills it)
Not missing *fields*, but Tier-1 fields the builder leaves empty — worth a note
for the implementation backlog:
- `sample.tissue` and `sample.genotype` are **hard-coded to
  `EvidenceField.missing()`** in `record_builder._sample_info` — genotype (WT/KO)
  is Tier 1 and should be extracted, not stubbed.
- `biology._INPUT_BLOT` is defined but unused — wire it into an input-control
  field (see gap #5).
- `experiment.experiment_flags` can contain `loading_control` but nothing links
  that control to the target(s) it normalizes (see gap #6).

---

## 8. Recommended Tier-1 additions, in priority order

If the beta ships only a handful of new fields, this is the order that most
improves a UCSF researcher's trust-per-record:

1. **Antibody trust triad** — `host_species`, `clonality`, `species_reactivity`
   (turns "which antibody" into "*the right* antibody for me").
2. **Antibody `validation_status` / `ko_validated` / `validated_applications`**
   (answers "can I trust this band," "validated for WB?").
3. **Controls block** — positive / negative / vehicle / KO-KD / IgG / input /
   loading-present (answers "were the controls appropriate?"; wire the existing
   `_INPUT_BLOT`).
4. **Loading-control linkage + `normalization_method`** (answers "was
   normalization appropriate?"; total-protein & phospho-to-total).
5. **Replicates** (`replicate_n`, `replicate_type`).
6. **Per-band apparent MW + band multiplicity/qualifier** from text (answers
   "single clean band / is this really my protein?").
7. **Populate `genotype`/`tissue`** rather than stubbing them.

Every one of these should follow HiveBlot's existing invariants: preserve raw
wording, carry provenance, and use **MISSING** honestly when the paper is
silent — because "the paper never says" is itself one of the most valuable
answers HiveBlot can give a bench scientist.
