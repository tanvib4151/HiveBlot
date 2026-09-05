# HiveBlot Beta — UX Review from the UCSF Wet-Lab Researcher's Seat

> **Scope:** review only. No code was changed by this document.
> **Reviewed:** `web/app/page.tsx`, `web/app/search/page.tsx`,
> `web/components/DatabaseResultCard.tsx`, `ResultsTable.tsx`, `ResultsCard.tsx`,
> `SearchInput.tsx`, `web/app/api/search/route.ts`, `api/app/schemas.py`,
> and the real data the UI actually renders
> (`eval/demo/phospho_PMC12856536/supabase_rows.json`, 90 rows).
> **Lens:** the biologist verification loop from `biologist_western_workflow.md` §1 —
> *is this my protein → can I trust this band → is the biology real → can I buy/reproduce it*.

---

## 0. Executive summary

The result card is **directionally right**. The biological headline
(`STAT3 · phospho-Tyr705`) + review badge is exactly the first thing a bench
scientist wants, and keeping reported-vs-expected MW distinct is the kind of
detail that earns trust from this audience on first contact.

But measured against a real researcher session on real data, the beta has
**four blocking problems** and one structural one:

| # | Problem | Severity |
|---|---|---|
| B1 | **The landing page never shows the Evidence Record at all.** `web/app/page.tsx:251` renders `ResultsTable`, a 6-column legacy table (target / sample / condition / type / detected / paper). Most beta users will search from `/`, see the *old* product, and never reach `DatabaseResultCard` (only wired at `search/page.tsx:127`). | **Blocker** |
| B2 | **90 near-identical rows per paper.** One row per lane. A `phospho STAT3 Tyr705` search returns 15 cards whose headline, sample, antibody, and MW are byte-identical and which differ only in `lane_condition` and `band_state`. The researcher cannot see the *experiment*; they see its shrapnel. | **Blocker** |
| B3 | **There is no way to correct anything.** No feedback affordance exists anywhere in `web/` or `api/` (grep: zero hits for feedback/thumb/correct). For a beta whose *stated purpose* is collecting researcher feedback (HANDOFF, Product North Star), this is the single largest gap. | **Blocker** |
| B4 | **The evidence panel is empty on real data.** In all three demo papers `figure_label`, `panel_label`, `figure_caption`, `title`, `pmid`, `pmcid` are `null`. So the "Figure:" footer line and the `CAPTION` block — the two things that let a researcher *verify against the paper* — never render. "WHY HIVEBLOT SAYS THIS" currently resolves to UniProt ID + antibody + treatment + a bare DOI string. That is not why HiveBlot says this; it is a restatement of the card. | **Blocker** |
| S1 | **Provenance is claimed but not shown.** The engine stores per-field `{value, confidence, status, sources, candidates}`, and `provenance` is deliberately excluded from list responses (correctly — ~1.7 MB/90 rows). But no detail endpoint exists, so the field-level evidence that is HiveBlot's whole differentiator is **unreachable from the UI**. | Structural |

Everything below is concrete and per-element.

---

## 1. Can a researcher answer the ten questions? (audit)

Tested against the live card with a real row (STAT3 pTyr705, Hep3B, IL-6).

| Question | Answerable today? | Where / why not |
|---|---|---|
| What protein? | **Yes** | Headline `canonical_target`; `as printed:` line preserves raw wording. Good. |
| Total or phospho? | **Yes** | `modification_label` in the headline. Best element on the card. |
| Which site? | **Yes** | `phospho-Tyr705` in the headline. |
| What cell line? | **Yes** | `SAMPLE` prefers `cell_line`. |
| What treatment? | **Partly** | `IL-6 · 10ng/ml · 60min` renders, but this is the *record-level* treatment while the lane the row describes may be `0 min` or `IL-6 -`. The card shows a treatment that contradicts its own lane (see §3, `CONDITION` is not rendered at all in the collapsed card). **This is a biological-accuracy bug surfaced by the UI, not just a UX nit.** |
| Which antibody / catalog? | **Yes** | `Cell Signaling Technology · #9145`, dilution in the expanded panel. Strong. |
| What experiment type? | **Yes** | `EXPERIMENT — Phospho Western`. |
| Which paper / figure? | **No** | DOI + page only. `figure_label` is null in all real data (B4). A researcher cannot find the blot in the PDF. |
| Why does HiveBlot believe this? | **No** | The expanded panel repeats card fields. No sources, no locators, no per-field status (S1). |
| What is uncertain? | **Weakly** | One record-level badge only. It says *that* something is unsettled, never *which field*. `anomaly_flags` is `[]` on every real row so the FLAGS block never renders. |
| How do I correct it? | **No** | Nothing exists (B3). |
| What is missing? | **No** | MISSING fields silently vanish (`{x && <Field…/>}`). The researcher cannot distinguish *"the paper didn't say"* from *"HiveBlot didn't look."* `biologist_western_workflow.md` §1 explicitly calls MISSING "a legitimate, useful answer" — the UI currently throws it away. |

**Score: 6 of 12 answerable.** The six failures cluster on exactly the two
axes this audience judges a tool by: **verifiability** and **correctability**.

---

## 2. Information density

Collapsed card renders ~7 values in a 2×3 grid at 24/28px padding inside a
1000px container. Vertical cost per card is roughly 230–260px.

- **Under-dense for a list.** 15 cards for one query = ~3,800px of scroll to
  read what is really one experiment with 15 lanes. A researcher scanning
  "which papers used CST #9145 in a liver line" is paying card-sized rent for
  table-sized information.
- **Over-dense for the evidence panel.** 300px fixed rail, vertical-text
  "EVIDENCE" tab, `overflowY: auto`. Caption text (when it exists — a real
  Western caption is 400–800 characters) will be a tiny scroll well in a
  300px column at 12px serif. Captions are the *primary* verification artifact;
  they deserve full card width, not a sidebar.
- **The expand affordance is a whole clickable column.** The vertical
  `EVIDENCE` tab is stylish but the entire 56px rail is a click target with no
  hover state, no `role="button"`, no keyboard access, and no `aria-expanded`.
  It is invisible as an affordance to anyone who doesn't already know.

**Recommendation:** two densities, one card component.
`compact` (default in result lists, ~110px: headline + badge + sample +
antibody + lane summary + paper) and `full` (on click/expand, full width,
evidence *below* the card, not beside it). Kill the side rail; move the
evidence panel to a full-width accordion under the card body. This alone makes
captions readable and frees the horizontal budget for the lane strip (§3).

---

## 3. The 90-rows-per-paper problem (the most important UX decision here)

**Measured on real data** (`phospho_PMC12856536`, 90 rows):

| Group (target · modification) | Rows |
|---|---|
| STAT3 · phospho-Tyr705 | 15 |
| STAT3 · phospho-Ser727 | 15 |
| STAT3 · total | 15 |
| β-actin · total (`canonical_target` null, `protein_status` MISSING) | 25 |
| MAPK1/MAPK3 (mod CONFLICTING → null) | 10 |
| MAPK1/MAPK3 · total | 10 |

Within the 15 STAT3-pTyr705 rows, the **only** fields that vary are:
`condition`/`lane_condition`, `band_state`/`band_detected`, `confidence`,
`page`, and `treatment_context`/`dose`/`duration` (because the 15 rows actually
span **three different panels** across pages 4–5 — a time course, a CL-E dose
series, and a U0126 inhibitor panel).

### 3.1 The grouping key

Do **not** group on `(target, modification)` alone — that would fuse three
biologically distinct experiments into one card and would be a correctness
error, not just a display one. The correct grouping key is the **panel**:

```
(paper_id, page, figure_label ?? panel_label ?? treatment_context, canonical_target ?? target, modification_label)
```

`treatment_context` is the honest fallback while `figure_label`/`panel_label`
are null (B4) — the three STAT3-pTyr705 panels have three distinct
`treatment_context` strings, so this key separates them correctly *today*, and
degrades gracefully to the real figure label once ingestion populates it.

Group **client-side for the beta** (`web/app/search/page.tsx` before the
`.map`), so no API/SQL change is on the critical path. Move it server-side
later.

### 3.2 What a grouped card looks like

```
STAT3 · phospho-Tyr705                                   [Supported]
as printed: P-STAT3 (Tyr705)
Hep3B · Phospho Western · CST #9145 (1:1,000) · expected 88.1 kDa

LANES   0min  5min  10min  20min  30min  60min
        ✗     ✓     ✓      ✓      ✓      ✓
        IL-6 (10 ng/ml) time course

Fig ? · p.4 · 10.3892/br.2026.2108              [evidence ▾] [⚑]
```

The **lane strip** is the key move: it turns 15 rows of noise into the one
thing a biologist actually reads off a blot — *the band pattern across the
condition series*. Six lanes, one line, `band_state` colored (present teal /
absent red / uncertain gold), `lane_condition` as the label. It is more
informative than the 15 cards *and* ~20× denser.

Rules:
- Show a lane count badge (`6 lanes`) so nothing feels hidden.
- Clicking a lane pins it and shows that lane's row-level detail (its own
  dose/duration/confidence) — the per-lane record is still addressable.
- If a group has exactly 1 lane, render it as a plain card with no strip.
- Never merge rows with differing `protein_status`/`modification_status` into
  one badge; if lanes disagree, the group badge takes the **worst** status and
  the disagreeing lanes are marked.

### 3.3 Result-count honesty

`Found 90 results` is technically true and experientially false. Show
**`14 experiments · 90 lanes across 3 papers`**. Researchers count experiments,
not database rows.

---

## 4. Per-element recommendations

**Legend:** **KEEP** = prominent in the collapsed card · **EXPAND** = hide until
expanded · **DE-EMPH** = remove or demote · **ADD** = missing, should exist.

### 4.1 Headline block

| Element | Verdict | Note |
|---|---|---|
| `canonical_target` + `modification_label` | **KEEP** | The single best decision in the current card. Do not touch. |
| `as printed: <raw target>` | **KEEP**, restyle | Correct per invariant #10, but at `marginTop: -12px` it collides with the flex `gap: 20px` and reads as a layout bug. Make it a proper subtitle line under the headline. |
| Review badge (Supported / Needs review / Conflicting) | **KEEP**, but **fix the derivation** | `reviewState()` only inspects `protein_status` and `modification_status` (`DatabaseResultCard.tsx:68`). A CONFLICTING antibody, treatment, or MW never reaches the badge. It should consider every surfaced field's status. |
| "Supported" as a word | **RENAME** | To a biologist "supported" sounds like *the biology is supported*. It means *the extraction is settled*. Use **`Evidence: settled / unsettled / conflicting`** or `Extraction: settled`. Getting this wrong on a beta with UCSF is a credibility own-goal. |
| Uniqueness of the group (lane count, panel) | **ADD** | `6 lanes · Fig 3B` next to the headline. |

### 4.2 Body fields

| Element | Verdict | Note |
|---|---|---|
| `SAMPLE` (cell_line ?? sample) | **KEEP** | |
| `EXPERIMENT` (experiment_type) | **KEEP** | But render `experiment_flags` too — `co_ip` + `phospho_western` co-occur and only one shows today. |
| `ANTIBODY` (vendor · #cat) | **KEEP** — promote further | This is the wedge (`RESEARCH_SYNTHESIS.md` §7). Pull `antibody_dilution` and `antibody_clone` up into the collapsed card; they are currently expanded-only. A researcher deciding what to buy should never have to expand. |
| `TREATMENT` | **KEEP**, but **scope it correctly** | At group level show the *series* ("IL-6 10 ng/ml, 0–60 min"), not one lane's value. Today the card shows a record-level treatment that can contradict its own lane. |
| `BAND` (band_state) | **REPLACE** with the lane strip | A single `Present` on a card that represents one lane of a six-lane series is the least useful true statement on the card. |
| `CONDITION` / `lane_condition` | **ADD** | It is in the interface and in the data and is **never rendered** in the collapsed card. It is the *only* field distinguishing 15 otherwise-identical cards. Its absence is why B2 feels so bad. In grouped mode it becomes the lane strip labels. |
| `MOLECULAR WEIGHT` (reported vs expected) | **KEEP** | Labeling is correct. But when `reported` is null, say **`reported: not stated in paper`** rather than silently showing only `expected 88.1 kDa` — the absence is information (see §5). |
| `confidence` (0–1 float) | **DE-EMPH / do not render** | Currently unrendered in this card and rendered as `confidence * 100`% in the unused `ResultsCard`. **Keep it unrendered.** See §8. |
| `organism` | **DE-EMPH** | Already correctly suppressed when `cell_line` exists. Keep. |
| Footer `Paper / Page / Figure` | **KEEP**, needs data | Fine as designed, starved of data (B4). |
| `paper_id` as a bare DOI string | **UPGRADE** | Make it `<a href="https://doi.org/…">` + the paper `title` when present. Right now the researcher cannot click through to the source — for a literature-evidence tool that is close to disqualifying. |
| Densitometry / intensity columns | **KEEP OFF** | Correct today. Never surface them until a real measurement pipeline writes them (invariant #6). |

### 4.3 Evidence panel ("WHY HIVEBLOT SAYS THIS")

| Element | Verdict | Note |
|---|---|---|
| Panel as a 300px right rail | **REPLACE** | Full-width accordion below the card. |
| `UNIPROT` id | **KEEP in panel**, link it | Link to `uniprot.org/uniprotkb/{id}`. A researcher will absolutely click it to check the accession — and letting them check it is the point. |
| MW explanation line | **KEEP** | Good copy. |
| Antibody / Treatment restatement | **DE-EMPH** | These duplicate the card. Replace with their **provenance** ("antibody — from Methods p.3, `association_confidence 0.7`"). |
| `CAPTION` | **KEEP**, needs data + width | The highest-value verification artifact. Full width, with the matched span highlighted if possible. |
| `FLAGS` (`anomaly_flags`) | **KEEP**, promote on non-empty | Currently panel-only and empty on all real rows. When non-empty it should raise a marker on the *collapsed* card. Also render `a.message` preferentially over `a.code` — `MODIFICATION_CONFLICT` is jargon; the message is for humans. |
| Per-field sources / locators | **ADD** (this is S1) | The panel is named "why HiveBlot says this" and contains no *why*. Needs a detail endpoint serving `provenance`. |
| `extraction_model` / `extraction_version` | **ADD**, small | Auditability line. Researchers reporting a bug need to say *which version* was wrong. |
| Legacy fallback copy ("No structured evidence on this legacy record yet") | **KEEP** | Honest. Good. |

### 4.4 Missing Tier-1 biology (from `biologist_western_workflow.md` §7.2)

Not UI bugs — but the UI should be **designed with slots** for these now, so
adding them later is data plumbing rather than a redesign:

- **Antibody trust triad** (host species, clonality, species reactivity) → a
  second line under `ANTIBODY`.
- **Validation status / KO-validated / validated-for-WB** → a small chip beside
  the catalog number. This is the #1 ask from both research tracks.
- **Controls block** (positive / negative / vehicle / KO-KD / IgG / input) →
  a `CONTROLS` row of present/absent chips. `were the controls appropriate?` is
  a top-3 trust question and is currently unanswerable.
- **Loading-control linkage + normalization method** → a line on the phospho
  card: `normalized to: β-actin (same panel)`.
- **Replicates** (`n`, biological vs technical) → footer chip; its **absence**
  is signal and should read `replicates: not stated`.
- **Band multiplicity / qualifier** (single / doublet / smear / nonspecific) →
  next to the lane strip.

---

## 5. Recommendation 2 — the "missing information?" affordance

**Principle: MISSING must be visible, not absent.** Today a null field renders
nothing, so "the paper never reported the catalog number" is
indistinguishable from "HiveBlot doesn't extract catalog numbers." The first is
a *valuable finding*. The second is a *product failure*. Conflating them costs
HiveBlot credit for its best behavior.

Concrete design:

1. **A `NOT REPORTED` line in the expanded panel**, always present, listing the
   Tier-1 fields that are MISSING for this record, in a muted color:
   `Not reported in this paper: antibody clone · replicates · reported MW · controls`
   Derive from the field status (MISSING) — never from "the column is null,"
   so a CONFLICTING null is not mislabeled as unreported.
2. **Distinguish three nulls explicitly** in copy:
   - `not reported` — paper is silent (MISSING).
   - `conflicting — see candidates` — sources disagree (CONFLICTING, value null).
   - `not extracted yet` — HiveBlot doesn't parse this field at all (legacy rows,
     un-migrated fields). Be honest about this one; researchers respect it.
3. **The ask button lives on that line**: `[ Is something missing? ]` — opens a
   short form pre-filled with `record_id` + `paper_id` + the current field list,
   with one free-text box: *"What should HiveBlot have captured from this
   figure?"* Two optional checkboxes for the most common answers (a field we
   don't have; a lane/panel we missed).
4. **Zero-result and low-result states** get the same affordance:
   `No results for "co-IP MYC in HEK293" — [ tell us what you expected to find ]`.
   Zero-result queries are the highest-signal feedback in the entire beta and
   are currently discarded silently (`search/page.tsx:133-139`).

---

## 6. Recommendation 1 — per-field feedback controls (👍 / 👎 / correct value)

**The failure mode to avoid:** 12 fields × 3 controls = 36 icons per card,
repeated across 15 cards. That destroys the card and, worse, makes the tool
look like a labeling task rather than a research instrument. Researchers will
stop reading.

**Design: progressive disclosure, one gesture, three levels.**

**Level 0 — card level, always visible, one control.**
A single `⚑` (flag) icon in the card footer, right-aligned next to the DOI,
same visual weight as the existing `EVIDENCE` label. Tooltip: *"Something wrong
here?"* This is the only feedback affordance visible at rest. One icon per
card, not 36.

**Level 1 — hover / focus reveals per-field controls, inline, zero-layout-shift.**
When the pointer is over a `Field` (or it receives keyboard focus), a small
`✓ ✗` pair fades in **in the field's label row**, right-aligned — the label row
is currently a 10px mono line with a large amount of empty horizontal space, so
this consumes **no new vertical space and shifts nothing**. Absolutely do not
reserve permanent space for these.

```
ANTIBODY                        ✓ ✗       ← appears on hover/focus only
Cell Signaling Technology · #9145
```

- `✓` posts instantly (optimistic, no dialog) → the label turns teal for 1.5s.
  Confirmation must be **one click, no modal**, or nobody will ever confirm
  anything and you will only collect complaints.
- `✗` opens Level 2.

**Level 2 — correction popover, anchored to the field, not a modal.**
~280px popover containing:
- the current value (read-only, so the correction is unambiguous),
- one input for the corrected value (typed to the field: free text for
  antibody, a `phospho / total / cleaved / none` select for modification, a
  number+unit for MW),
- an optional "where did you see this?" line (page / figure / "vendor
  datasheet" / "I ran this blot"),
- `Submit` / `Cancel`.

Never block the page. Never require login for the beta (attribute by an opaque
session id; ask for an optional email once, at the end of a session).

**Which fields get controls (beta):** target, modification+site, cell line,
treatment, antibody (vendor/catalog), experiment type, band state per lane, MW.
That is 8, and only the hovered one is ever visible. Do **not** put controls on
derived/expected values (`expected_molecular_weight_kda` comes from UniProt —
a correction there is a UniProt issue, not a HiveBlot one; instead let them
flag *"wrong protein identity"* on the headline, which is the real error).

**Where the feedback goes:** a new `POST /feedback` on the internal router,
writing to a `record_feedback` table keyed by
`(record_id, field_name, verdict, corrected_value, source_note, session_id,
extraction_version)`. Store `extraction_version` — otherwise corrections
against a superseded extraction are unattributable. **Feedback must never
mutate `western_blot_records`.** It is a separate evidence stream to be
reconciled by the same evidence hierarchy the engine already has; silently
overwriting an extracted value with a user's typed value would violate the
provenance contract.

---

## 7. Recommendation 3 — result-level and search-level feedback prompts

**Three tiers, decreasing frequency, so the beta never feels like a survey.**

1. **Field level** (§6) — always available, invisible until hover. Frequency:
   unlimited.
2. **Result level** — one line at the *bottom of the expanded panel* only
   (i.e. the user has already chosen to read the evidence):
   *"Does this record match the paper? `Yes` · `No — what's wrong?`"*
   Rationale: expansion is the moment the researcher has actually verified
   against the source, so it is the only moment their yes/no is meaningful. A
   yes/no on a collapsed card is noise.
3. **Search level** — a single row **below the last result**, never a popup,
   never mid-list:
   *"Did this answer your question? `Yes` · `Partly` · `No` — [tell us more]"*
   plus the zero-result variant from §5.4. Post the *query text* and
   `generated_sql` with it — both are already returned by the API and both are
   currently discarded (`search/page.tsx:60-61` reads only `results`). Search
   feedback paired with the generated SQL is the fastest way to debug the
   NL→SQL / `bio_query` path.
   Show at most **once per session**, after the third search, and never again
   once answered.

**Also add a session-level exit prompt** (once, ever, dismissible): *"You're
using the HiveBlot beta. What's the one thing that would make this useful in
your lab tomorrow?"* One box. That question is worth more than the sum of the
per-field clicks for a beta of this size.

---

## 8. Recommendation 4 — field-level confidence without a meaningless global score

**Do not show a global confidence percentage. Ever.** The existing `confidence`
float (rendered as `confidence * 100`% in the unused `ResultsCard`) is a
per-row extraction-stage number that varies 0.3–0.9 across lanes of the *same
panel* for no biologically meaningful reason. A biologist reading "60%
confident" will ask "60% confident of *what?*" and there is no honest answer.
A number that cannot be interpreted is worse than no number — it invites
false precision, which is the exact failure this project's invariants exist to
prevent.

**Instead: status, not score. Per field. Categorical. In the type system, not
the color system alone.**

Render each field's `status` as a **glyph in the field's label row**, in the
same slot the hover controls use, at 10px mono:

| Status | Glyph | Color | Label copy on hover |
|---|---|---|---|
| SUPPORTED | *(nothing)* | — | settled — the default, silent |
| AMBIGUOUS | `?` | gold `#e0a458` | "under-supported — best available reading" |
| CONFLICTING | `⚠` | red `#ff6b6b` | "sources disagree — see candidates" |
| MISSING | `—` | subtle `#6f857d` | "not reported in this paper" |

Key properties:
- **Silence means settled.** Only unsettled fields carry a mark, so a clean
  record looks clean and an unsettled one is instantly scannable. This is the
  opposite of a score badge on every field, which trains people to ignore all
  of them.
- **The mark is a link**, opening that field's provenance in the evidence panel
  (which sources, which locator, which rank in the evidence hierarchy).
- **The record badge becomes a roll-up** of the field marks, not an independent
  judgment: worst field status wins. This also fixes the `reviewState()` bug in
  §4.1.
- Where a numeric confidence genuinely helps a specialist —
  `association_confidence` on the antibody↔panel link, `experiment_type_confidence` —
  show it **only inside the provenance detail**, always with its name attached
  (`association_confidence 0.7`), never as a bare percentage on the card.
- The DB currently returns only `protein_status` and `modification_status` as
  status columns. Either widen the flat projection with per-field status
  columns for the surfaced set, or (better) serve them from the record-detail
  endpoint on expand.

---

## 9. Recommendation 5 — conflicts and candidates

CONFLICTING fields have `value = null` with candidates preserved
(invariant #3). Today, `null` means the field **silently disappears** from the
card. So HiveBlot's most intellectually honest behavior is currently rendered
as *nothing at all* — and the researcher sees a card that just looks
incomplete. Observed live: 10 real MAPK1/MAPK3 rows have `modification_label`
null from a genuine conflict, and the card shows a bare `MAPK1/MAPK3` headline
with no hint that a conflict is the reason.

**Design:**

1. **Never hide a conflicting field.** Render the label with the value slot
   occupied by the conflict marker, not by emptiness:
   ```
   MODIFICATION  ⚠
   contested — 2 readings
   ```
2. **Show candidates side by side, with their evidence, and do not pick a
   winner.** In the expanded panel, a two-column comparison — not a ranked
   list, because ranking is picking a winner by layout:
   ```
   MODIFICATION — sources disagree

   phospho (unspecified site)        total
   ├ antibody: CST #4370             ├ row label: "P-ERK 1/2"
   │  phospho-specific = true        │  uppercase P- is not a
   └ rank 1 (antibody)               └  phospho marker · rank 3
   ```
   Equal visual weight, each with its source type and hierarchy rank. Order by
   evidence rank but never style one as selected.
3. **Conflict is where feedback is most valuable** — put an explicit
   `Which is right? [phospho] [total] [neither]` control directly under the
   candidate pair. This is the highest-yield feedback in the product: an expert
   resolving a conflict the engine correctly refused to resolve. It is also the
   most satisfying interaction you can offer this audience, because it says
   *we didn't guess, and we trust you more than our model*.
4. **AMBIGUOUS candidates get the same treatment, softer.** For the resolver
   family case, show `MAPK1 (P28482) · MAPK3 (P27361) — family, not resolved to
   one accession`. Do **not** show one accession with a caveat.
5. **In grouped cards (§3), a conflict on any lane raises to the group badge**
   and the offending lanes are marked in the strip. Never let grouping hide a
   conflict.

---

## 10. Prioritized punch list

**P0 — before any UCSF researcher sees this**
1. Wire `DatabaseResultCard` into `web/app/page.tsx` (replace `ResultsTable`), or
   redirect `/` search to `/search`. Two different result UIs is disqualifying. (B1)
2. Group by panel + lane strip; change the count copy to experiments/lanes. (B2)
3. Render `lane_condition` — it is the only field distinguishing the duplicates. (§4.2)
4. Make DOI/paper clickable. (§4.2)
5. Ship the card-level `⚑` + a `POST /feedback` endpoint, even if Level 1/2 land
   later. Some correction path must exist on day one. (B3)

**P1 — makes the beta actually collect what it exists to collect**
6. Per-field hover `✓ ✗` + correction popover. (§6)
7. Field-status glyphs; fix `reviewState()` to roll up all fields; rename
   "Supported". (§8, §4.1)
8. Conflict/candidate rendering. (§9)
9. `NOT REPORTED` line + "is something missing?" + zero-result prompt. (§5)
10. Move the evidence panel from a 300px rail to a full-width accordion; add
    `role="button"`/`aria-expanded`/keyboard access. (§2)

**P2 — the differentiator**
11. Record-detail endpoint serving `provenance`; render real per-field sources
    and locators in "WHY HIVEBLOT SAYS THIS". (S1)
12. Populate `figure_label` / `panel_label` / `figure_caption` / `title` /
    `pmcid` in ingestion — without them the card cannot be verified against
    the paper. (B4)
13. Search-level + session-level prompts. (§7)
14. Design slots for the Tier-1 gaps: antibody trust triad, validation status,
    controls block, normalization, replicates, band qualifier. (§4.4)

---

## 11. What must not change

- The biological headline (`canonical_target · modification_label`) as the
  first thing on the card.
- Reported MW and expected MW kept visually and verbally distinct.
- Raw source wording (`as printed:`) preserved next to the canonical value.
- CONFLICTING never rendered as a settled scalar — and now, never rendered as
  *nothing* either.
- No densitometry, no fabricated fields, no global confidence percentage.
- Feedback as a separate evidence stream that never silently overwrites an
  extracted value.
