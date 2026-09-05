# Assignment — Scientific Communication & Honest Positioning (Workstream B)

**For:** a teammate comfortable with both the science and the writing — a
biology person who writes well, or a product person working with Workstream A
for scientific accuracy. Pairs naturally with either.
**Mode:** draft, don't deploy. This workstream owns the two P0 findings, which
means everything it produces goes to Nik for sign-off before anything public
changes.

## Why this matters

The product's entire competitive advantage is that it does not overclaim — and
the marketing page in front of it overclaims by three orders of magnitude.
`/about` says "2.8K+ PAPERS PROCESSED / 12.4K+ BLOTS INDEXED / 520+ PROTEINS
TRACKED" against a real corpus of 3 papers / 93 experiments / 475 rows, and
describes automated CV+LLM ingestion that is future work. A UCSF evaluator who
sees 2.8K papers, searches BRCA1, and gets zero results will conclude the
search is broken — and if they later learn the real number, the honesty that
is this product's main asset is gone. This is the single highest-risk finding
of the walkthrough and the one thing that must change before wider
distribution.

## What to learn first

1. Read `/about` and `/learn` on the live site (https://hiveblot-beta.vercel.app)
   as a skeptical researcher would, then read the source:
   `web/app/about/page.tsx`, `web/app/learn/page.tsx`.
2. Read `research/TEAM_BETA_HANDOFF.md` end to end — it is the honest version
   of the product story, already written for testers, and your primary source
   material.
3. Read the walkthrough's §6–§8 (`/Users/niks/Downloads/HiveBlot-Founder-Walkthrough.md`)
   — especially the terminology list and the "two different companies"
   observation.
4. Get the terminology definitions from Workstream A (Biology QA task 5) — do
   not invent scientific definitions yourself unless you are the biology
   person.

## Your tasks

1. **Draft the honest `/about` replacement (P0).** Kill the fabricated
   numbers and the automated-ingestion narrative. The replacement story:
   3 papers, fully reviewed, 93 experiments, 475 evidence rows, every value
   traceable to the figure and the sentence it came from — here is what that
   rigor looks like, and here is the roadmap (automated extraction is future
   work being evaluated against this reviewed baseline). This is a *better*
   pitch to a researcher than fake scale. Deliver as a draft PR or a copy doc;
   Nik approves and ships.
2. **Fix the `/learn` science mismatch (P0-adjacent, P1).** The page
   currently says you "compare band intensity across lanes" and presents
   **Upregulated / Downregulated** result categories (`web/app/learn/page.tsx`
   ~lines 86–111). The product is explicitly categorical — present / absent /
   uncertain, no densitometry, ever (a "Decision That Must Not Be Reversed").
   Rewrite `/learn` to describe what HiveBlot actually reports: the four
   statuses, band presence as categorical, descriptive-only multiplicity,
   expected vs reported MW.
3. **Write the in-product glossary content (P1).** Using Workstream A's
   definitions: IgG, IP bait, Input, phospho / site (e.g. Tyr705), loading
   control, doublet, kDa, expected vs reported MW. Two sentences each,
   plain-English, biologically correct. Deliver the content; where it surfaces
   (tooltips, `/learn` section, evidence-panel hints) is a Workstream C design
   question you coordinate on.
4. **State who it's for (P2).** One short section, usable on the homepage and
   `/about`: HiveBlot is for wet-lab researchers who want to check an antibody
   against published blots before buying, find whether a protein has been
   blotted in a given context, and see the evidence behind every claim.
5. **Cold-start expectation copy (P2).** One or two sentences, suitable for
   the site and for any message sent to testers: the first search after a
   quiet spell takes ~30 s because the free-tier API is waking up; everything
   after is fast. `research/TEAM_BETA_HANDOFF.md` already has a version —
   reuse it.

## What to test

- Read your `/about` draft against `HANDOFF.md`'s session-14 notes and
  `TEAM_BETA_HANDOFF.md`: every number and capability claim in your draft must
  be traceable to one of those documents. If you cannot cite it, cut it.
- Adversarial read: hand the draft to Workstream A and ask "what would a UCSF
  PI call out as an overclaim?" — iterate until the answer is nothing.
- After any merged copy change: `cd web && npx tsc` clean, pages render, no
  claim regression.

## What NOT to change

- **The zero-result copy** on the search page — already correct, already
  scoped, non-negotiable.
- **Numbers move in one direction only: toward the truth.** Never round 3
  papers up to "several", never imply growth that hasn't happened, never write
  "coming soon" for anything unscheduled.
- **No accuracy claims about unseen papers, anywhere, in any tense.** The 3/3
  harness is a self-consistency check on the reviewed reference set — it says
  nothing about new papers, and no copy may imply otherwise until the
  automated-extraction evaluation actually runs.
- No deploys. Drafts and PRs only; Nik ships `/about` personally.

## What you should understand before finishing

- **The current beta is a reviewed corpus, not an ingestion engine.** The
  three papers went through the real pipeline, but the model-reading step was
  a human-supervised agent because no model credentials exist. What is proven:
  the representation, provenance, search, and feedback machinery on
  trustworthy data. What is unproven: reading any new paper automatically.
  Every sentence you write must survive that distinction.
- **Why honesty is the positioning, not a constraint on it.** Researchers are
  professionally trained to detect overclaiming, and the product's
  differentiators — field-level provenance, visible abstention, "as printed"
  wording, scoped negative results — are all forms of honesty. A marketing
  page that overclaims doesn't just risk embarrassment; it contradicts the
  product's one defensible story.
- **The four statuses and what they're for** (SUPPORTED / AMBIGUOUS /
  CONFLICTING / MISSING — see `BIOLOGY_QA_HANDOFF.md` "What you should
  understand" for the full version), because `/learn` must teach the statuses
  the product actually uses, not generic blot-theory categories.
- **What densitometry is and why HiveBlot refuses it:** measuring band
  intensity to quantify protein amounts. HiveBlot never infers intensity from
  an image — lanes are present/absent/uncertain — so any copy suggesting
  quantification promises something the product deliberately will not do.

## Definition of done

- `/about` replacement draft delivered, every claim citable, adversarially
  reviewed by Workstream A, awaiting Nik's sign-off.
- `/learn` rewrite draft: Upregulated/Downregulated and intensity language
  gone, four statuses and categorical-lanes stance in.
- Glossary content for all eight terms, signed off by the biology reviewer.
- Audience statement + cold-start copy delivered.
- Zero unverifiable claims anywhere in the drafts.

## What to report back to Nik

- **What you found:** any additional overclaims discovered beyond the
  walkthrough's list (check every page, including headers/footers/metadata).
- **What you changed, if authorized:** merged copy PRs; `/about` itself ships
  only via Nik.
- **Unresolved questions:** positioning calls only Nik can make (e.g. how
  prominently to state "3 papers" on the homepage).
- **Before/after screenshots** of every page you touched or drafted.
- **Needs Nik's decision:** final `/about` copy, homepage prominence of the
  corpus size, whether `/learn` keeps any generic blot-education content.
