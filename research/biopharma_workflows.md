# HiveBlot in Biopharma R&D — Workflow Time-Savings & Wedge Analysis

> Research memo. Author: research sub-agent (Claude Code, Opus 4.8), 2026-08-12.
> Scope: where a biologically-accurate, auditable Western blot evidence engine
> saves *real* time in preclinical/drug-discovery workflows, and its single
> strongest wedge. Grounded in HiveBlot's actual contract (Evidence Field
> envelopes, evidence hierarchy, provenance, "band presence ≠ densitometry",
> "image MW needs a ladder", "model output is a claim not truth").

---

## 0. Framing: what HiveBlot actually is (and isn't), for this analysis

HiveBlot turns Western blot figures + captions + methods + paper context into
**structured, auditable evidence rows**. The unit of value is a normalized,
provenance-tagged tuple roughly of the form:

`(target, canonical accession, modification, residue, experiment type, sample/cell line,
treatment, dose, duration, antibody, vendor, catalog#, reported MW, expected MW,
band state {present/absent/uncertain}, validation status, provenance, confidence)`

Two things follow immediately and shape every workflow below:

1. **HiveBlot's edge is not "read one blot better than a human."** A trained
   scientist reads a single blot fine. HiveBlot's edge is **aggregation at scale
   with structure and provenance** — answering "across N papers, what does the
   Western literature *collectively* say about this target/antibody/condition,
   and can I click through to each source?" That is a task humans do slowly,
   incompletely, and non-reproducibly today.

2. **HiveBlot reports claims-with-provenance, never verdicts.** It says "Paper X's
   Fig 3B, using antibody cat# ab12345, reports a band at ~88 kDa for STAT3 in
   HeLa" — it does **not** say "this antibody is validated" or "this band is
   real." That distinction is the whole product's integrity, and it maps cleanly
   onto the workflows where trust is the bottleneck.

The recurring integrity constraints ("must NOT claim") are nearly identical
across workflows, so they are stated once here and only specialized per workflow:

- **No fabricated densitometry / quantification.** Band state is categorical
  (present/absent/uncertain). Never emit a fold-change, %-change, or intensity
  number unless the source text explicitly reports one (and then it is *the
  source's* number, quoted with provenance — not HiveBlot's measurement).
- **No molecular weight invented from pixels.** A reported MW is only valid
  against an actual ladder/reference in that figure. Otherwise MW is "reported by
  authors as X" or unknown — never HiveBlot-estimated from image geometry.
- **The model's row target is a claim, not ground truth** (evidence hierarchy:
  antibody/catalog → caption → methods → model → image).
- **No inferred phosphorylation from naming** (p53/p38/PARP are not phospho).
- **Conflicting evidence stays unsettled** (`value=null`, candidates preserved) —
  HiveBlot must not manufacture false consensus.
- **Absence of evidence ≠ evidence of absence.** "No blot found" means HiveBlot
  didn't extract one, not that the biology is false.

Provenance required for trust is also largely shared: **source paper ID + figure/
panel label + exact source wording (caption/methods span) + which field-source
produced each value + field-level confidence/status + a click-through to the
original figure.** Per-workflow notes below only add specializations.

---

## 1. Target validation

**1. Manual today:** Before committing a program to a target, teams assemble the
evidence that modulating it changes disease-relevant biology: knockdown/knockout
phenotypes, pathway consequences, expression in relevant tissues/models. Analysts
read dozens–hundreds of papers, screenshot blots into slide decks, and hand-curate
"evidence tables" for target-assessment / portfolio-review meetings.

**2. Information sought:** Does perturbing the target actually reduce the protein
(KD/KO efficiency)? What downstream nodes move? In which disease-relevant cell
lines/models? Is protein expression present in the indication's tissue at all?

**3. Time wasted:** Rebuilding the same evidence table each program; re-reading
figures to transcribe "which lane, which condition"; no memory across analysts;
citation lists that don't tell you *what the blot showed*.

**4. HiveBlot automates:** A structured first-pass evidence table for a target —
every extracted blot where the target appears, with condition/cell-line/modification
and band state, each row click-through to source. Turns "read 80 papers" into
"review 80 pre-structured rows and spot-check the ones that matter."

**5. Must NOT claim:** No "target is validated" scoring. No aggregate effect sizes.
No implying causality from co-occurrence. Expression present in a blot ≠ expression
in patient tissue.

**6. Provenance:** Per-row source + figure panel + the methods/caption span that
established the condition. Target validation feeds go/no-go money decisions — every
number must be traceable to a figure a human can open.

---

## 2. Pathway activation / inhibition

**1. Manual today:** Reading the signaling literature to map which stimuli/drugs
turn a pathway node on/off, largely evidenced by phospho-Westerns (p-ERK, p-AKT,
p-STAT3, etc.) against total protein.

**2. Information sought:** Under stimulus/drug X, does p-<site> go up or down, in
which cell line, at what dose/time, relative to total protein and loading control?

**3. Time wasted:** Phospho-site notation is inconsistent (pY705 vs "phospho-Tyr705"
vs "activated STAT3"); analysts manually reconcile site + direction + condition
across papers.

**4. HiveBlot automates:** Structured retrieval of phospho-evidence rows keyed on
target + residue + modification + treatment + direction-of-change *as reported* —
exactly the fields the engine already models, and exactly where its
"never infer phospho from a name prefix" discipline pays off.

**5. Must NOT claim:** Band present ≠ "pathway activated." Direction of change only
if the source states it (or a paired ± lane makes it explicit); never inferred from
a single band. No cross-paper "activation score."

**6. Provenance:** Residue-level source (antibody catalog is often the strongest
evidence for which phospho-site); the ± comparison lane pairing must be preserved,
not just the positive lane.

---

## 3. Mechanism of action (MoA)

**1. Manual today:** Building the causal story for how a compound works —
target engagement → proximal signaling → downstream markers — heavily supported by
blots at each step. Assembled by hand into MoA figures/dossiers.

**2. Information sought:** The chain of protein-level readouts that a compound moves,
and prior literature blots supporting each link.

**3. Time wasted:** Stitching disparate blots (different papers, cell lines, doses)
into one coherent chain; re-finding the paper that showed a given link.

**4. HiveBlot automates:** Fast retrieval of candidate evidence for each proposed
link (node + modification + direction + context), so an MoA hypothesis can be
"evidence-backed by prior blots" in minutes, with sources attached.

**5. Must NOT claim:** HiveBlot does not assert mechanism. It surfaces prior blots
consistent with a link; it must not chain them into a claimed causal pathway or
imply the links were shown together.

**6. Provenance:** Because MoA claims travel into regulatory/IP documents, each
supporting blot needs full source + figure + condition provenance and an explicit
"context differs" flag when cell line/dose/species don't match the program's.

---

## 4. Drug-response experiments

**1. Manual today:** Designing and contextualizing dose/time-response experiments;
checking what doses/timepoints others used for the same target+drug+cell line, and
what the protein-level response looked like.

**2. Information sought:** Dose, duration, cell line, and the resulting band change
for a given drug × target.

**3. Time wasted:** Manually mining methods sections for concentrations/timepoints;
these live in prose, not tables. (HANDOFF notes only the *first* dose/duration per
row is captured deterministically today — a known gap to close for this workflow.)

**4. HiveBlot automates:** A structured "who dosed what, how long, and what the blot
did" view — strong for experiment planning and for sanity-checking one's own dose
range against the literature.

**5. Must NOT claim:** No dose-response curves or IC50/EC50 fabrication from
categorical band states. Report the reported dose/time; do not interpolate.

**6. Provenance:** Methods-span provenance for dose/duration specifically (these are
easy to mis-transcribe); multi-dose extraction completeness should be surfaced as a
confidence/coverage flag.

---

## 5. Biomarkers / pharmacodynamic (PD) markers

**1. Manual today:** Choosing PD markers (often a phospho-protein) to show target
engagement in vivo/ex vivo; surveying which markers others used and whether they
moved by Western.

**2. Information sought:** Candidate PD markers for a pathway, prior evidence they
respond to modulation, and the antibodies/conditions used to detect them.

**3. Time wasted:** Marker discovery is a literature slog; connecting "marker →
antibody → assay conditions" is manual.

**4. HiveBlot automates:** From a pathway/target, enumerate protein/phospho readouts
that appear in blots as responsive, with the reagent + condition context needed to
actually run the assay.

**5. Must NOT claim:** No "validated biomarker" designation; no clinical/predictive
claims. PD context (preclinical model) must not be conflated with patient biomarkers.

**6. Provenance:** Marker–response evidence must carry the perturbation that produced
it; a marker "appearing in blots" is not a responsive marker.

---

## 6. Antibody selection  ★ (core wedge — see §15)

**1. Manual today:** Before blotting target T, a scientist must pick an antibody.
They search vendor sites, CiteAb/antibody registries, and papers; skim figures to
see if the antibody "looks clean" (single band at expected MW); check the vendor,
catalog#, and whether it worked in their species/application. Then they order 1–3
candidates and burn weeks empirically testing them.

**2. Information sought:** For target T, application = Western: which antibodies
(vendor + catalog#) have produced a **specific band at the expected MW**, in which
species/cell lines, ideally with a **specificity control** (KO/KD loss of signal,
blocking peptide)? Which have citations that actually *show a working blot* vs.
citations that merely list the reagent?

**3. Time wasted:** Citation counts (CiteAb et al.) tell you an antibody was *used*,
not that it *worked*. Scientists open PDF after PDF to see the actual band. Ordering
and testing a bad antibody costs 2–6 weeks and hundreds of dollars per failure —
and antibody failure is the single largest documented driver of irreproducibility
in the field.

**4. HiveBlot automates:** This is the **tightest fit between what HiveBlot extracts
and what the workflow needs.** For target T it can return, per antibody
(vendor+catalog#): the set of blots where it was used, the reported vs expected MW,
band state, species/cell-line context, and whether a specificity control was present
in that figure — each row click-through to the figure. It converts "open 40 PDFs"
into "scan a structured, sourced antibody-evidence table."

**5. Must NOT claim:** **HiveBlot must never label an antibody "validated" or rank
antibodies by a manufactured score.** It reports *evidence instances* — "cat# X
produced a band at reported ~88 kDa (expected ~88) with a KO-control lane in Paper Y,
Fig 3B." Whether that constitutes validation is the scientist's judgment. No fake
densitometry of band cleanliness; "single clean band" only if the source shows/states
it. Catalog# and vendor must be extracted, never guessed — a wrong catalog# is worse
than none.

**6. Provenance:** Antibody identity (vendor + catalog# + lot if present) with the
exact methods-span it came from; figure panel for the band; explicit presence/absence
of a specificity control as its own provenance-tagged field. This is the highest-bar
provenance in the product because a wrong reagent recommendation directly wastes
bench time and money.

---

## 7. Reagent validation (beyond antibodies)

**1. Manual today:** Confirming that a reagent (antibody, and by extension the
cell line / construct / inhibitor) behaves as expected, per journal/funder RRID and
reproducibility requirements.

**2. Information sought:** Documented evidence that the specific reagent lot/catalog
performs (specific band, expected MW, controls) in a comparable context.

**3. Time wasted:** Reconstructing a reagent's track record from scattered methods
sections; RRIDs are inconsistently reported.

**4. HiveBlot automates:** A reagent-centric evidence view (see §6) plus flagging
when catalog#/RRID is *missing* from a paper — itself a useful reproducibility signal.

**5. Must NOT claim:** No "reagent qualified" status. Missing catalog# must be shown
as missing, not inferred.

**6. Provenance:** Catalog#/RRID provenance + the figure demonstrating performance.

---

## 8. Preclinical studies (in vivo / ex vivo protein readouts)

**1. Manual today:** In efficacy/tox and PK/PD studies, Westerns confirm target
engagement and pathway modulation in tissue. Teams survey prior in-vivo blot
evidence for a target/pathway in a given tissue/species.

**2. Information sought:** Species, tissue, dosing, and the protein/phospho readout —
crucially, whether prior evidence is in the *right species/tissue*.

**3. Time wasted:** Species/tissue filtering is manual and error-prone; human vs
mouse expected-MW differences trip people up.

**4. HiveBlot automates:** Species/tissue-scoped retrieval of in-vivo blot evidence.
(Note the HANDOFF gap: resolver defaults to human `organism_id=9606`; mouse/rat
expected-MW can resolve wrong until organism is threaded in — this workflow *requires*
fixing that.)

**5. Must NOT claim:** No cross-species equivalence claims; expected MW must be
organism-correct or flagged. In-vivo target engagement is a reported result, not a
HiveBlot inference.

**6. Provenance:** Species + tissue as first-class provenance-tagged fields; the
organism source (cell line/tissue mention) preserved.

---

## 9. Protein-expression confirmation

**1. Manual today:** Checking whether a protein is expressed (and at what apparent
size) in a given cell line/tissue before using that model — often the very first
blot anyone runs.

**2. Information sought:** Is target T detectable by Western in model M, at roughly
the expected MW?

**3. Time wasted:** Hunting for a prior figure showing T in M; re-deriving expected
MW.

**4. HiveBlot automates:** Direct lookup "target × model → prior blots + reported vs
expected MW + band state," with the canonical accession's expected MW from the
UniProt resolver as a reference point.

**5. Must NOT claim:** Expression in a blot ≠ functional/abundant expression; band
present is categorical. Expected MW (from UniProt) is a reference, not a measurement
of the pictured band.

**6. Provenance:** Expected MW sourced to UniProt accession; reported MW sourced to
the figure/caption; the two kept explicitly distinct (a core HiveBlot invariant).

---

## 10. Phosphorylation / signaling

Covered functionally by §2 (pathway) and overlapping §5 (PD markers); the
distinctive HiveBlot value is the **residue-level, modification-aware, provenance-
tagged** representation and the discipline of never inferring phospho from a name.
This is the area of highest scientific value **and** highest integrity risk
(direction-of-change, site identity, total-vs-phospho pairing). It is where the
"claim not truth" and "conflicting stays unsettled" rules do the most work.
**Must NOT:** assert activation/inhibition from a lone band; collapse distinct sites;
lose the phospho/total pairing. **Provenance:** residue evidence source (often the
antibody), and the total-protein/loading-control comparators.

---

## 11. Knockdown / knockout validation  ★ (core adjacency — see §15)

**1. Manual today:** Validating that a shRNA/siRNA/CRISPR perturbation actually
reduced the target protein — the canonical control being a Western showing band loss
in KD/KO vs control. Also used to validate antibody specificity (signal disappears
when target is gone). Scientists hunt prior papers for "does knocking down X reduce
protein X, and by how much (categorically)?"

**2. Information sought:** For target T, prior blots with a KD/KO vs control lane
pairing showing reduced/absent band; the reagent (shRNA/guide) and cell line.

**3. Time wasted:** Finding the specific control figure; confirming the pairing
(which lane is control vs perturbed) from prose.

**4. HiveBlot automates:** Retrieval of KD/KO-vs-control blot evidence — the same
**specificity-control logic** as antibody validation (§6). This is where HiveBlot's
"antibody detection vs association" and co-IP role modeling generalize: it can flag
figures that contain the control lane pairing at all, which is what makes the
evidence trustworthy.

**5. Must NOT claim:** No knockdown efficiency % (that is densitometry — categorical
band state only, unless the source states a number). "Band reduced" only if a paired
comparison supports it.

**6. Provenance:** The control/perturbed lane pairing must be preserved as structured
evidence, plus the perturbation reagent from methods. A KD/KO claim without the
paired control is not usable.

---

## 12. Co-IP / interaction confirmation

**1. Manual today:** Confirming protein–protein interactions via co-immunoprecipitation
Westerns (pull down bait, blot for prey). Surveying prior evidence that A interacts
with B, and with what bait/prey roles and IP antibody.

**2. Information sought:** Bait, prey, IP antibody, input/IP/IgG-control lanes, and
whether prey was detected in the bait pulldown.

**3. Time wasted:** Parsing co-IP designs from dense methods; assigning bait vs prey
roles correctly.

**4. HiveBlot automates:** Structured interaction-evidence rows (bait/prey roles are
already modeled in the engine), with IP reagent and control context.

**5. Must NOT claim:** Detection in a pulldown ≠ direct interaction (could be indirect/
complex). No interaction "confidence" beyond what controls in the figure support.
Bait/prey role assignment is flagged, not assumed, when methods are ambiguous.

**6. Provenance:** IP antibody + input/IgG-control lane presence as provenance-tagged
fields; the bait/prey role source.

---

## 13. Reproducibility

**1. Manual today:** Asking "how many independent groups have reproduced this
protein-level finding, and under what conditions?" — done ad hoc, rarely
systematically.

**2. Information sought:** Count and context-spread of independent blots supporting a
given target/modification/condition claim; and where results *conflict*.

**3. Time wasted:** There is no structured way to do this today; it's manual
meta-analysis. Conflicts are especially costly to discover late.

**4. HiveBlot automates:** Because evidence is structured with provenance, HiveBlot
can group independent blots by (target, modification, condition) and — critically —
**surface conflicts explicitly** (its CONFLICTING status with preserved candidates is
purpose-built for this). This is a differentiated capability no citation database has.

**5. Must NOT claim:** No p-values, no manufactured consensus, no "N papers therefore
true." Independent-replication count is a descriptive tally with sources, not a
statistical verdict. Conflicts must be shown as conflicts, never averaged away.

**6. Provenance:** Every counted instance is click-through-able; conflicting instances
keep both sides' evidence. Group-independence is itself uncertain (same lab, reused
figure) and should be flagged, not asserted.

---

## 14. Literature diligence

**1. Manual today:** For BD/licensing, IP, or program-entry diligence, teams verify
that a target/asset's claimed protein-level evidence actually exists and holds up —
opening figures, checking controls, looking for contradicting reports.

**2. Information sought:** Does the underlying blot evidence for a claim exist, is it
controlled, is it reproduced, and is anything contradicting it?

**3. Time wasted:** Manual figure-by-figure verification under time pressure; easy to
miss a contradicting paper.

**4. HiveBlot automates:** A "show me the blot evidence + its controls + conflicts,
with sources" view over a target/claim — turning diligence from spot-checking into
structured review.

**5. Must NOT claim:** No credibility scoring of papers; no "claim verified." HiveBlot
provides the evidence trail; the human makes the judgment.

**6. Provenance:** Maximal — this workflow's entire value is the audit trail. Every
field click-through to source; conflicts and missing-control flags prominent.

---

## 15. The strongest wedge (direct, opinionated answer)

**Wedge: an antibody / reagent-validation evidence engine — "for the target I'm
about to blot, show me every antibody (vendor + catalog#) that has produced a
specific band at the expected MW, in which context, with what specificity controls,
each row traceable to the source figure." Enter through antibody selection (§6),
extend immediately into KD/KO specificity validation (§11).**

### Why this wedge, concretely

1. **Perfect fit between what HiveBlot extracts and what the workflow needs.** The
   engine's native fields — target, canonical accession, **antibody, vendor,
   catalog#**, reported-vs-expected MW, band state, cell line/species, and the
   presence of a **specificity control** — *are literally the antibody-validation
   record*. No other workflow lines up this cleanly with the existing schema. You
   are not building new extraction; you are pointing the extraction you have at the
   question that needs exactly those fields.

2. **The pain is universal, frequent, and expensive.** Antibody choice precedes
   nearly every Western. Antibody failure is the most-cited driver of biological
   irreproducibility, and each failed antibody costs weeks of bench time plus
   reagent spend. This is a recurring, pre-experiment decision every wet-lab
   scientist makes — including the UCSF beta users in HANDOFF — not a rare
   portfolio-level event.

3. **Incumbents miss the actual question.** CiteAb, vendor citation lists, and
   antibody registries count *usage*; they do not tell you whether the blot in each
   citation *worked* — right MW, clean band, proper controls. That verification is
   exactly the manual PDF-opening slog HiveBlot removes. The gap is real and
   specifically Western-blot-shaped, which is where general AI literature tools are
   weakest (they read text, not figure-anchored reagent performance).

4. **It is defensible on integrity — it fits the "claim not truth" rule natively.**
   HiveBlot reports *evidence instances with provenance*, not verdicts: "cat# X gave a
   band at reported ~88 kDa (expected ~88) with a KO-control lane in Paper Y Fig 3B."
   The scientist decides if that is "validated." No densitometry, no invented MW, no
   scoring required — the wedge lives entirely inside the allowed claim space. Many
   flashier wedges (e.g. cross-paper phospho "activation scores") require exactly the
   claims HiveBlot must not make; this one does not.

5. **Provenance is naturally satisfiable and is the whole value.** Vendor/catalog
   from methods, band from the figure, control-lane presence as its own field — all
   auditable, all click-through. Trust is the product here, and this wedge's data is
   the most trust-shaped.

6. **Clean expansion path.** Antibody validation (§6) → KD/KO specificity validation
   (§11) is the *same specificity-control logic* (does signal disappear when the
   target is removed?), so the wedge widens without new machinery. From there,
   reagent/RRID reproducibility (§7), protein-expression confirmation (§9), and
   reproducibility conflict-surfacing (§13) are adjacent with the same schema. The
   higher-value-but-higher-risk phospho/pathway/PD territory (§2/§5/§10 — where the
   biopharma money ultimately is) becomes the *later* expansion, entered only after
   the antibody wedge has earned trust, precisely because it demands the harder
   claims.

### Sharpest one-line framing
Sell it as **"the antibody your experiment needs, with the blots that prove it —
sourced, MW-checked, and control-aware,"** not as "AI that reads blots." The former
is a daily decision with expensive failure and no good tool; the latter is a demo.

### Honest caveats (so the wedge isn't oversold)
- Requires **catalog#/vendor extraction to be reliable** — a wrong catalog# is worse
  than none; keep it in the "never guess, provenance-or-abstain" discipline.
- Requires **specificity-control detection** (KO/KD lane, blocking peptide) to be at
  least *flagged*; without it the engine reports "used" not "validated," which is
  honest but less differentiated — so control detection is the key capability to
  push.
- Requires the **organism/expected-MW fix** (HANDOFF known gap) so mouse/rat expected
  MW is right; antibody validation is species-specific.
- Coverage is bounded by open-access/figure-accessible literature; "no evidence
  found" must read as coverage-limited, never as "antibody is bad."

---

## Appendix: cross-workflow "must NOT claim" — the shared integrity floor

| Temptation | Rule |
|---|---|
| Emit fold-change / %-knockdown / intensity | Categorical band state only; a number must be the *source's* quoted number with provenance. Never HiveBlot-measured. |
| Estimate MW from image | Only reported-vs-expected; reported MW needs an actual ladder; expected MW is UniProt reference, distinct field. |
| Infer phospho from name / activation from one band | Explicit modification evidence only; direction only if paired ± lanes / stated. |
| Score an antibody/reagent/paper as "validated"/"credible" | Report evidence instances + controls + conflicts; the human judges. |
| Average away disagreement | CONFLICTING → value null, both candidates preserved. |
| Treat "no blot found" as "biology is false" | Absence = coverage limit, flagged as such. |
| Assume species/tissue equivalence | Species/tissue are first-class provenance fields; expected MW organism-correct or flagged. |

Every workflow above ultimately sells the same thing: **structured, sourced,
control-aware blot evidence that a scientist can audit** — and the antibody/reagent
validation wedge is the one where that offering is most needed, most frequent, best-
matched to the existing schema, and safest to make.
