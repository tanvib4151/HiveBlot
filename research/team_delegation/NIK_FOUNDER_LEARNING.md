# Nik's Founder Learning Doc

Everything you need to own HiveBlot intelligently. Not a biology textbook —
just the level required to run the product, brief the team, and not overclaim
in front of a researcher.

## 1. What HiveBlot actually is

A search engine over Western blot experiments where every answer carries its
evidence. A published blot is a picture plus a caption plus a paragraph buried
in Methods; HiveBlot reassembles that into structured rows — which protein,
modified how, in which cells, under what treatment, detected with which
antibody — and keeps every value attached to the exact wording and image it
came from. The distinguishing move: when its sources disagree, it records the
disagreement instead of picking a winner.

## 2. The architecture, high level

```
paper PDF
  → OpenCV candidate filter        (cheap, deterministic: finds likely blot panels)
  → model reads the panel          (currently a human-supervised agent — no model creds yet)
  → deterministic biology engine   (western_blot_miner/: modification detection,
                                    protein normalization, UniProt lookup,
                                    evidence reconciliation, validation flags)
  → Evidence Records               (structured rows + per-field provenance)
  → Supabase Postgres              (475 reviewed rows, locked-down read-only roles)
  → FastAPI                        (query parser → SQL guard → read-only role;
                                    Render, free tier — hence the ~30 s cold start)
  → Next.js web app                (Vercel: search → cards → evidence panel → feedback)
```

Feedback flows the other way: researcher clicks land in a separate
`hiveblot_feedback` table through an insert-only role that physically cannot
touch the evidence rows.

## 3. What an Evidence Record is

Not an answer — a container for an answer plus its justification. One record
per experiment row, and every important field inside it is an envelope:
**value** (what HiveBlot concluded), **status** (how settled it is),
**sources** (where it came from, with the verbatim quoted sentence), and
**candidates** (the competing options when it isn't settled). The record also
carries the cropped blot image and the DOI. That is why the UI can show "here
is the value, here is the sentence it came from, here is the picture" for
every single field.

## 4. The important biological fields

- **Target** — the protein the blot row is detecting (e.g. STAT3).
- **UniProt ID** — the protein's unique global identifier (STAT3 → P40763),
  so names can't be confused across papers and organisms.
- **Modification / site** — a chemical tag on the protein and where it sits
  (phospho-Tyr705). Changes what the experiment means entirely.
- **Cell line / sample / organism** — what biological material was used
  (Hep3B human liver cancer cells; mouse gland tissue).
- **Treatment, dose, duration** — what was done to the cells. A time course
  legitimately has many durations, which is why that field can read "varies
  by lane".
- **Antibody (vendor, catalog, dilution)** — the exact reagent that produced
  the detection. Reproducibility and purchasing decisions hang on this.
- **Expected vs reported MW** — how heavy the protein should be (reference
  database) vs what the paper stated. Kept separate on purpose; conflating
  them fakes a confirmation.
- **Lanes** — the individual sample columns on the blot, each recorded as
  band **present / absent / uncertain**. Categorical only.

## 5. What provenance means

Every value knows where it came from — not "this record is from paper X" but
*this individual field* came *via caption*, *via antibody list*, *via
deterministic rule*, or *via UniProt*, with the quoted source sentence and the
raw `as printed` wording preserved beside the normalized value. Consequence:
any claim in the UI can be walked back to a sentence and an image in a
published paper. That auditability is the product.

## 6. How uncertainty and conflicts work

Four statuses per field:

- **SUPPORTED** — sources agree; value settled.
- **AMBIGUOUS** — the label maps to more than one possibility; value flagged
  as unsettled (e.g. "ERK 1/2" is two proteins, MAPK1/MAPK3).
- **CONFLICTING** — credible sources actively disagree. The value is **null**
  — never a coin flip — and both competing claims are shown with a
  plain-English "Why unresolved" sentence.
- **MISSING** — the paper never said. Shown as "not reported", never invented.

The rule underneath all four: **abstain instead of guess.** A tool that
always answers confidently is wrong somewhere without telling you; visible
abstention is what makes the Supported badge mean something.

## 7. Co-IP, at the level you need

Co-immunoprecipitation asks *do two proteins physically stick to each other*
(a normal blot only asks *is this protein present*). You use an antibody to
fish one protein — the **bait** — out of the cell mixture, then blot to see
what came along attached to it. Three lanes make the logic: **Input** = the
sample before fishing (proves the protein was there), **IgG** = a non-specific
antibody that should catch nothing (the negative control), **IP** = what the
real bait caught. A band in IP but not in IgG is the evidence of interaction.
HiveBlot models bait and all three lane roles explicitly — that's why it can
represent these experiments at all. If asked more than this: "the biology team
can go deeper — the product models it correctly" is a complete answer.

## 8. Phospho / site, at the level you need

Phosphorylation is a chemical tag a cell attaches to a protein to switch its
activity — often effectively on/off. The **site** says exactly where the tag
sits: Tyr705 = the tyrosine at position 705. Phospho-STAT3-Tyr705 is *active*
STAT3, which is a completely different claim from "STAT3 is present". One
trap you should be able to recite: a lowercase "p-" prefix in a label often
means phospho, but a name starting with P does not (p53 is a protein name,
P-selectin is not phospho-selectin) — which is why HiveBlot demands explicit
evidence and has a hard rule against prefix guessing.

## 9. Why antibody catalog search is useful

Searching `CST 9145` (a vendor + catalog number) returns every experiment in
the corpus that used that exact product — in which cells, at what dilution,
with the actual published blot image. Antibodies are expensive and fail
often; seeing a published blot produced by the exact reagent before buying is
a purchasing decision with real money attached. This is the sharpest single
use case the product currently has.

## 10. What the current beta proves

- The data model handles real experimental complexity: phospho sites, time
  courses, dose series, co-IP with bait/Input/IgG roles, loading controls,
  mouse tissue.
- Provenance works end to end: search → field → quoted sentence → crop → DOI.
- The uncertainty machinery is real, not decorative: conflicts abstain, with
  explanations and competing claims shown.
- Zero-result searches are correctly scoped to the dataset, not the
  literature.
- Feedback is captured per field, beside the extraction, and survives a
  database reseed.
- All of it hosted, free-tier, verified end to end: 3 papers · 93 experiments
  · 475 reviewed evidence rows.

## 11. What it does NOT prove

- **That HiveBlot can read an unseen paper accurately.** The corpus was built
  with a human-supervised agent; the "3/3 EXACT" harness is a
  self-consistency check on the reviewed set, not an accuracy measurement.
- Anything about scale, coverage, or recall — 3 papers support no claim about
  the literature.
- Anything about densitometry or band intensity — deliberately out of scope.
- Anything about the quality of the science in the papers — HiveBlot reports
  what blots show; it does not judge them.

If you internalize one sentence from this document: **the beta proves the
representation and the honesty machinery, not the automated reader.**

## 12. What you should be able to explain, per audience

- **To a teammate:** the flow (search → card → evidence panel → crop → DOI →
  feedback), the four statuses, the coordination rules (observe before fix,
  preserve provenance, no hallucinated biology, reviewed beta ≠ ingestion
  accuracy), and which workstream owns which finding.
- **To a UCSF researcher:** "Every value is traceable to the sentence and the
  figure it came from. When sources disagree we show you both claims instead
  of guessing. It's 3 fully reviewed papers today — small on purpose, so you
  can trust every row — and your corrections are stored beside our extraction,
  never over it."
- **To a professor:** the abstention argument — a system that always returns a
  confident answer is unreliable precisely because it never says "unsettled";
  HiveBlot's Supported badge carries information *because* Conflicting exists.
  Plus the evaluation plan: the reviewed corpus is the gold baseline that
  automated extraction will be measured against.
- **To a technical person:** deterministic CV filter → model extraction
  (human-in-loop today) → deterministic biology engine → per-field evidence
  envelopes in Postgres → guarded query parser over a read-only role →
  Next.js. Identity is a content hash of observation data, so feedback
  survives reseeds. The parser never fabricates a filter it can't support.
- **To a nontechnical person:** "Scientific results about proteins are locked
  inside pictures in PDFs. HiveBlot makes them searchable — and unlike most
  AI tools, it shows exactly where every answer came from and says 'we're not
  sure' when the paper isn't clear."
