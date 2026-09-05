# HiveBlot Research Synthesis

Integration owner's synthesis of the five parallel research tracks + the first
real end-to-end paper run. Sources:
- `biologist_western_workflow.md` (what biologists inspect; Tier 1/2/3 + schema gaps)
- `biopharma_workflows.md` (where HiveBlot saves time; the wedge)
- `frontend_integration_plan.md` (fastest safe path to display Evidence Records)
- `benchmark_candidates.md` + `../eval/candidates.json` (26 verified diverse papers)
- `real_pipeline_report.md` + `../eval/demo/phospho_PMC12856536/` (real run)

This is a decision document, not a backlog. Not every suggestion is adopted.

---

## 1. Are any Tier-1 biological fields missing?
**Yes — the schema is strong on identity/modification/MW but thin on trust & controls.**
The current Evidence Record nails: field-level envelopes, reported-vs-expected MW,
evidence-based phospho vs total, antibody *identity* (vendor/catalog/clone/dilution),
co-IP roles, provenance. Confirmed correct on the real STAT3 run.

Highest-value **missing** Tier-1 fields (from `biologist_western_workflow.md`, in
priority order for the beta):
1. **Antibody validation trust** — `validation_status`, `ko_validated`,
   `validated_applications` (WB?), `host_species`, `clonality`, `species_reactivity`.
   This is the biologists' *and* biopharma's #1 ask ("which antibody actually worked?").
2. **Controls block** — positive / negative / vehicle / KO-KD / IgG / **input**
   controls. Only `ip_bait_protein` exists today. `biology._INPUT_BLOT` regex already
   exists but is never surfaced — quick win.
3. **Loading-control → target linkage + `normalization_method`** (housekeeping vs
   total-protein stain vs phospho-to-total). We flag a row *as* a loading control but
   can't say what it normalizes.
4. **Per-band apparent MW + band multiplicity** (doublet / multiple / smear /
   nonspecific). `BandObservation` is only present/absent/uncertain.
5. **Replicates** (`replicate_n`, biological vs technical).

Also **populate existing-but-stubbed** fields: `sample.tissue` and `sample.genotype`
are hard-coded to `missing()` in `record_builder._sample_info` (genotype/KO is Tier 1).

## 2. Which current fields should be de-emphasized?
- The **FUTURE densitometry columns** (raw/normalized intensity, band geometry,
  smearing/saturation) must stay NULL and off the default card — do not imply
  quantitation we don't have.
- **organism** should defer to **cell_line** when known (more useful; the real run
  showed Hep3B carries the signal, organism is redundant). Keep organism only when no
  cell line. *Caveat:* organism still matters for the UniProt query (see §6).
- The full **`provenance` JSONB** must NOT ride in list responses (it is the whole
  record dump; ~1.7 MB across 90 rows in the real run). Already excluded from the API
  list model; serve it from a dedicated detail endpoint.

## 3. Which advanced search filters matter most?
Ranked for the beta (all map to indexed migration-001 columns):
1. `canonical_target` + `modification_type` + `residue`/`residue_position`
   ("phospho-STAT3 Tyr705").
2. `antibody_catalog_number` / `antibody_vendor` (the reagent-selection query).
3. `experiment_type` (phospho_western / co_ip / loading_control / …).
4. `cell_line`.
5. `needs_review=false` (trust filter — hide unsettled rows).

## 4. What should appear first on a result?
The **biological headline**: `canonical_target · modification_label`
(e.g. **STAT3 · phospho-Tyr705**) + a **review badge** (Supported / Needs review /
Conflicting). Then experiment, sample/cell line, treatment, antibody (vendor·catalog),
band state, MW (reported vs expected kept distinct). Expanded = "Why HiveBlot says
this": UniProt, MW source, antibody, treatment, caption, flags, citation.
**This is now implemented** in `web/components/DatabaseResultCard.tsx`.

## 5. What blot types should be in the demo set?
Prioritize diversity that stresses the biology (from `benchmark_candidates.md`):
phospho-Western **with explicit site** (✅ have STAT3 Tyr705/Ser727), co-IP with
explicit bait, standard total Western, a **loading-control-as-subject** adversarial
case, a **p-prefixed non-phospho** guard (p53/p21/p62), and ≥1 **blot-like
non-Western negative** (✅ the run's 4 bar charts). The two other downloaded papers
(standard PMC9559174, co-IP PMC12706926) are the next two demo records.

## 6. What biological errors would most damage trust? (ranked)
1. **Confident wrong protein identity** — exactly the `P-ERK 1/2 → EPHB2` false-friend
   this run hit and we **fixed**. UniProt gene-synonym collisions (ERK, PERK, …) are
   the sharpest edge; ambiguity must resolve to a family (MAPK1/MAPK3), never a single
   wrong accession.
2. **Calling total protein "phospho"** (or vice-versa) — the p53/p38/PARP prefix trap;
   guarded and regression-tested.
3. **Conflating expected vs reported vs image MW** — kept strictly separate; reported
   stays null when the paper doesn't state it.
4. **Presenting an ambiguous/conflicting field as settled** — fixed this run
   (ambiguous ERK family no longer renders SUPPORTED; flips `needs_review`).
5. **Wrong organism → wrong expected MW** — resolver defaults to human (9606); a
   mouse/rat paper (e.g. the standard demo PMC9559174) can mis-resolve. Thread
   cell-line/organism into the query next.
6. Fabricated antibody↔panel association in dense methods (flagged, not solved).

## 7. HiveBlot's strongest biopharma wedge
From `biopharma_workflows.md`, adopted: **an antibody / reagent-validation evidence
engine.** Enter via **antibody selection**, extend into **KD/KO specificity
validation**. Rationale: it is the tightest fit to the existing schema (target,
vendor, catalog#, expected-vs-reported MW, band state, cell line, control presence
*are* the validation record), a universal/frequent/expensive pain, and an incumbent
gap (CiteAb counts *usage*, not whether the blot *worked*). It is integrity-safe —
pure claims-with-provenance ("cat# X gave a band at expected ~88 kDa with a
KO-control lane in Paper Y Fig 3B"), no densitometry, no invented values. Sell
"the antibody your experiment needs, with the blots that prove it," not "AI that
reads blots." This directly reinforces the Tier-1 gaps in §1 (validation + controls).

## 8. Which future image-analysis features matter most?
Deferred to post-beta and gated behind ladder calibration (never fabricate):
1. Lane/band detection + **MW estimation from a ladder** (only defensible image MW).
2. Doublet / multiplicity / saturation / smear QC flags (categorical, not intensity).
3. Densitometry / normalization — last, and only with a real measurement pipeline
   writing the reserved columns.

---

## Adopted implementation deltas (this session)
- **Fixed** the `core_symbol` prefix/isoform bug cluster + ERK false-friend
  (biology.py, resolve.py, record_builder.py) with regression tests.
- **Widened the API** model (additive Optional Evidence Record fields;
  `provenance` blob deliberately excluded from list responses).
- **Rebuilt the result card** around the biological headline + review badge +
  evidence panel.

## Session-4 delta (scientist-review sprint — what materially changed)
1. **Most valuable feedback fields** (per the UX review + what we instrumented):
   per-field ✓/✗ with suggested correction on canonical_target, experiment_type,
   cell_line, phosphosite, antibody catalog; the **conflict "Which is right?"
   candidate picker** is the single highest-yield signal and is now built.
2. **Evidence that must be prominent:** the normalization chain
   (raw → canonical → UniProt), per-field source snippets, and CONFLICTING
   candidates rendered equal-weight. All shipped in the evidence accordion.
   A CONFLICTING field must never render as silent emptiness (UX finding #4).
3. **Fields researchers care about most** (unchanged from Tier-1): antibody
   catalog/vendor, phosphosite, cell line, experiment type — now each
   individually correctable.
4. **Remaining trust-critical failure modes** (open, ranked):
   scalar dose/duration on time-course/dose-response panels (QA finding M1 →
   should become AMBIGUOUS-with-candidates); band multiplicity/smear not
   representable (M2, LC3B doublet / poly-Ub); antibody↔panel association
   still heuristic; automated Stage-2 completely unvalidated.
5. **Before UCSF beta:** independent scientific QA re-run (this session's QA
   was a self-audit); the automated-model comparison (blocked on creds);
   figure-crop serving so researchers see the blot; lane-grouping in the
   results list (15 near-identical cards per panel today).

## Deferred (next, in priority order)
1. Organism threading into UniProt (unblocks the mouse standard-Western demo).
2. Tier-1 schema additions: antibody validation trust + controls block (+ surface
   the dead `_INPUT_BLOT` regex; populate stubbed tissue/genotype).
3. Record-detail/provenance endpoint (serve the full envelope out of list payloads).
4. Load a Supabase beta project + apply migration 001 → get these records live in
   the frontend (the one remaining gap to the full success condition).
