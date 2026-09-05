# Assignment — Product / UX (Workstream C)

**For:** a product / design teammate.
**Mode:** explore and propose first. Homepage copy and small presentation fixes
can become PRs after Nik approves the direction; the next-action work is
explicitly exploration, not building.

## Why this matters

The founder walkthrough's blunt verdict: "a real UCSF researcher would
bounce." The product behind the homepage is genuinely good — full provenance,
honest abstention, real figure crops — but a first-time user is given a bare
search box with no idea what is inside, gets no reason shown on the one query
built for triage, and hits a dead end after their best result. The gap between
product quality and first-run experience is currently the cheapest place to
create value.

## What to learn first

Do the first-run experience yourself, cold, before reading anything:

1. Open https://hiveblot-beta.vercel.app and try to decide what to type with
   no help. Notice how that feels — that is the bug. (Expect a ~20–30 s hang
   on the very first search: the free-tier API waking up, not a bug.)
2. Then run the good queries: `phospho STAT3 Tyr705`, `CST 9145`, `P-ERK`,
   `needs review`. Open cards, expand **EVIDENCE**, follow a DOI, look at a
   crop.
3. Read `research/TEAM_BETA_HANDOFF.md` (what the beta is and is not), then
   the walkthrough's §6 "Things that confused me"
   (`/Users/niks/Downloads/HiveBlot-Founder-Walkthrough.md`).
4. Skim the code you will be proposing changes to: `web/app/page.tsx`
   (homepage), `web/app/search/page.tsx`, `web/components/DatabaseResultCard.tsx`,
   `web/components/EvidencePanel.tsx`.

## Your tasks

1. **Homepage first-run proposal.** Design what a first-time researcher sees:
   what HiveBlot searches (Western blot experiments from a reviewed corpus),
   the honest corpus size (3 papers · 93 experiments · 475 evidence rows), and
   3–5 clickable example searches (draw from the flagship seven). Constraint:
   the honesty IS the brand — no "coming soon" inflation, no implied scale.
2. **`needs review` comprehension.** Propose how a result card shows WHY a row
   needs review without opening it. Note the constraint from the API side:
   the machine-readable flags (e.g. `MODIFICATION_CONFLICT`) live in a
   `validation` JSONB blob deliberately excluded from list responses, so any
   reason-on-the-card design needs a small API addition — coordinate with
   Workstream D rather than designing around fake data.
3. **Next-action exploration (do NOT build).** After a researcher finds a
   useful record, what should they be able to do? Candidates from the
   walkthrough: save, export, cite, related experiments, "more from this
   paper". Interview-style thinking, not features: which of these serves the
   actual wedge use cases (antibody-before-buying; "has anyone blotted X in Y
   under Z"; "can I trust this row")? Deliver a ranked recommendation with
   rationale, mockups optional. Nik decides what gets built.
4. **Presentation bug list, designed.** Propose treatments for: the empty
   `WHY HIVEBLOT SAYS THIS` section when protein identity is MISSING (an
   explicit "no normalization chain — protein identity could not be
   established" state beats a bare heading); the `RESULTS -` loading dash; the
   `?` marker doing double duty for "uncertain" and "varies by lane"; the
   cold-start wait having no explanation beyond "Querying database…".
5. **Confidence display question.** Per-field confidence is stored but never
   shown as a number; two fields at 0.3 and 0.9 look identical. Recommend:
   show it, bucket it, or keep it hidden — with reasoning about researcher
   trust. This is input to a Nik decision, not a change.

## What to test

- Live site: https://hiveblot-beta.vercel.app — all seven flagship searches
  (`phospho STAT3 Tyr705`, `co-IP PIK3CA`, `CST 9145`, `P-ERK`, `GAPDH mouse`,
  `needs review`, `BRCA1 MCF7 olaparib`).
- The zero-result search (`BRCA1 MCF7 olaparib`) — read its copy carefully.
  It is deliberate, correct, and non-negotiable product language.
- The `p85` co-IP card (via `co-IP PIK3CA`) for the empty-WHY state.
- Reload `/search?q=needs%20review` after ~15 min idle to feel the cold start.

## What NOT to change

- **The zero-result copy.** "No matching evidence in the current HiveBlot beta
  dataset… does not mean no such evidence exists in the literature" — the
  scoping is a scientific-integrity feature. Restyle if needed; never weaken.
- **Never remove provenance to declutter.** `as printed`, quoted sentences,
  provenance tags, and the crop stay. Density problems get solved by layout,
  not deletion.
- **No invented UI values.** No placeholder biology, no "example" records, no
  synthetic confidence numbers in mockups presented as real.
- **The search stays explicit-submit** (Enter or SEARCH button, never
  search-as-you-type) — that was a deliberate session-8 decision.
- No deploys; PRs only after Nik approves direction.

## What you should understand before finishing

- **The full flow:** search → result card (normalized answer + `as printed` +
  status badge) → EVIDENCE panel (normalization chain → figure crop →
  per-field provenance + quoted sentences → lanes) → DOI → paper. Every hop
  clickable. That chain is the product; every UX decision either strengthens
  or breaks a link in it.
- **The researcher value proposition,** sharpest first: (1) "which published
  experiments used this exact antibody, and what did the blot look like?" — a
  purchasing decision with real money attached; (2) "has anyone blotted this
  protein in this cell line under this treatment?"; (3) "can I trust this
  row?" — because the tool says when it can't decide.
- **Why the beta scope must be stated honestly.** The corpus is 3 reviewed
  papers. A researcher who expects thousands, searches BRCA1, and gets zero
  results concludes the search is broken; when they learn the real number,
  the honesty that is the product's main asset is gone. Small-and-auditable
  is the pitch, not a limitation to hide.
- **Why "Conflicting" is a feature.** The Supported badge only means something
  because the system visibly refuses to settle what the evidence doesn't
  settle. Any design that makes conflicts look like errors damages the core
  differentiator.

## Definition of done

- A homepage proposal (annotated mockup or written spec) with final copy that
  states corpus size and example searches, honestly.
- A `needs review` reason-display proposal, including the exact field(s) it
  needs from the API (agreed with Workstream D).
- A ranked next-action recommendation document — explicitly not code.
- Concrete treatments for the four presentation bugs in task 4.
- A one-page confidence-display recommendation.

## What to report back to Nik

- **What you found:** your own cold first-run notes plus anything the
  walkthrough missed.
- **What you changed, if authorized:** list any merged PRs; everything else is
  proposals.
- **Unresolved questions:** especially where honesty and polish pull against
  each other.
- **Screenshots/mockups** for every proposal.
- **Needs Nik's decision:** homepage direction, next-action priorities,
  confidence display, and anything touching the API contract.
