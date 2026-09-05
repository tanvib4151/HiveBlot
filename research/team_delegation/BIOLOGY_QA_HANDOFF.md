# Assignment — Biology QA (Workstream A)

**For:** a biology / science teammate.
**Mode:** observe and verify first. You are auditing, not editing. Any change
to the reviewed corpus requires Nik's sign-off, because corpus changes mean a
reviewed reseed of the database.

## Why this matters

HiveBlot's only real asset is that a researcher can trust what a card says.
Every row in the beta was human-reviewed, but the grouping was corrected after
that review (91 → 93 experiments: one figure panel held two experiments, Fig 3C
without IL-6 and Fig 3D with it, previously shown as one card), and no
independent scientific pass has run against the corrected grouping. You are
that pass. A false "Supported" that survives to a UCSF researcher costs more
than any missing feature.

## What to learn first

Open https://hiveblot-beta.vercel.app and run `phospho STAT3 Tyr705`. Expect a
~20–30 s hang on the very first search — that is the free-tier API waking up,
not a bug. Open the top card, expand **EVIDENCE**, and walk the whole chain:
normalized headline → `as printed` raw wording → status badge → per-field
provenance tags → quoted source sentences → figure crop → lane strip → DOI.
That chain is the entire product.

Then read, in order:

1. `research/TEAM_BETA_HANDOFF.md` — the beta's scope and the seven flagship
   searches.
2. `HANDOFF.md` §"Current Biological Contract" and §"Decisions That Must Not
   Be Reversed Casually" — the field-envelope model and the non-negotiables.
3. `research/independent_scientific_qa.md` — the previous QA pass, so you know
   what was already found and fixed.
4. The three papers (DOIs below). `eval/demo/` holds the per-paper reviewed
   records and READMEs.

The three papers:

| DOI | Content |
|---|---|
| `10.3892/br.2026.2108` | phospho-STAT3 / IL-6 time course + inhibitor matrix, Hep3B |
| `10.3892/ijmm.2022.5188` | mouse submandibular gland development + duct ligation |
| `10.1186/s12964-025-02385-8` | BEX2 / PIK3CA co-IP, H1792 / H1299 / A549 |

## Your tasks

1. **Re-verify the two corrected cards.** Search `P-ERK` and the STAT3
   queries; find the Fig 3C (6-lane, no IL-6) and Fig 3D (7-lane, with IL-6)
   cards. Confirm against the paper's figure legend that each card's lanes,
   treatment context, and band states belong to its own experiment and that
   nothing from one leaked into the other.
2. **Field-by-field audit of one full experiment per paper** (minimum three
   experiments; more if time allows). For each field check: target and
   UniProt mapping; phosphosite residue+position and whether a phospho claim
   is justified at all; cell line / sample / organism (mouse vs human);
   treatment agent, dose, duration — including per-lane values, a time course
   must read "varies by lane", never one number; antibody vendor, catalog,
   dilution, and whether it is associated with the right row; expected vs
   reported MW kept distinct; co-IP bait vs readout on the co-IP cards.
3. **Judge every abstention.** Run `needs review` and `P-ERK`. For each
   Conflicting/Ambiguous field: do you, as a biologist, agree it is genuinely
   unsettled? Would settling it require evidence the paper does not contain?
   Flag any case where HiveBlot abstained but the paper actually settles it —
   and any case where it said "Supported" but should not have.
4. **Hunt biologically misleading presentation.** Known suspects: the `?`
   marker meaning both "uncertain" and "legitimately varies by lane"; a
   "not reported" MODIFICATION field quoting a full methods paragraph of
   unrelated antibodies; the doublet note's isoform disclaimer. Add anything
   else where the UI would lead a biologist to a wrong conclusion even though
   the underlying data is right.
5. **Review the walkthrough's terminology list from the science side** (IgG,
   IP bait, phospho/site, loading control, doublet, kDa, expected vs reported
   MW): write a one-to-two-sentence, biologically correct plain-English
   definition for each, as raw material for Workstream B. Precision matters —
   these will be shown to researchers.

## What to test

- All seven flagship searches: `phospho STAT3 Tyr705`, `co-IP PIK3CA`,
  `CST 9145`, `P-ERK`, `GAPDH mouse`, `needs review`, `BRCA1 MCF7 olaparib`.
- Expected shapes: 3/18, 4/14, 3/18, 2/10 Conflicting, 5/31, 4/20, 0. If a
  count differs from these, stop and report — that alone is a finding.
- The GAPDH developmental panels should be tagged DEVELOPMENTAL SERIES and the
  duct-ligation panels deliberately untagged. Check the tags are biologically
  defensible.

## What NOT to change

- **Nothing in `eval/demo/`** (the reviewed corpus) — corrections go in your
  report, not into the files.
- **No feedback-button submissions for QA findings** unless Nik asks — the
  feedback table is at 0 rows and reserved for real researcher signal;
  polluting it with internal QA makes the beta's first metric meaningless.
- No code, no UI, no database, no deploys.
- Never resolve a conflict "because it's obvious". If you disagree with an
  abstention, that is a written finding with the paper sentence that settles
  it.

## What you should understand before finishing

- **What an Evidence Record is.** Not an answer — a container holding the
  answer, the paper's original wording, the source sentence, the crop, and a
  status saying how settled it is. Every important field is an envelope:
  `{value, confidence, status, sources, candidates}`.
- **The four statuses.** SUPPORTED — evidence agrees, value settled.
  AMBIGUOUS — the label maps to more than one possibility (`P-ERK 1/2` →
  MAPK1/MAPK3), value is a flagged best-guess or family. CONFLICTING —
  credible sources actively disagree; value is **null**, both candidates
  preserved, nobody picks. MISSING — the source never says; a finding, not a
  gap.
- **Raw wording vs normalized interpretation.** `as printed: P-STAT3 (Tyr705)`
  is the paper; `STAT3 · phospho-Tyr705` is HiveBlot. Both are always kept, so
  normalization is auditable and reversible.
- **Why HiveBlot abstains instead of guessing.** A system that always returns
  a confident answer is wrong somewhere without telling you. Abstention is
  what makes the Supported badge carry information. The P-ERK card is the
  canonical example: phospho-specific antibody argues phosphorylation, the
  site-less `P-` label does not (P-selectin, P-cadherin), so the modification
  stays unsettled with both claims shown. If you finish this assignment
  believing that behavior is a feature and not a bug, you understand the
  product.

## Definition of done

- The Fig 3C/3D split verified against the paper, in writing.
- At least three experiments (one per paper) audited field-by-field with a
  verdict per field: correct / incorrect (with the paper sentence) / can't
  determine.
- Every Conflicting and Ambiguous field in the corpus judged: agree / disagree
  (with evidence).
- A written list of biologically misleading presentation issues, each with a
  screenshot and the query that reproduces it.
- The terminology definitions delivered to Workstream B.

## What to report back to Nik

- **What you found:** per-field verdicts, abstention judgments, misleading-UI
  list. Severity-sorted: false "Supported" first, wrong values second,
  presentation issues third.
- **What you changed:** should be "nothing" — this is an audit.
- **Unresolved questions:** any field where the paper is genuinely unclear and
  you cannot rule.
- **Screenshots/examples:** query + card + the paper sentence for every
  finding.
- **Needs Nik's decision:** any finding that would require a corpus change
  (and therefore a reviewed reseed), and whether the QA pass gates wider UCSF
  distribution.
