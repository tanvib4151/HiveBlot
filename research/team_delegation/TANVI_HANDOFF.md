# Tanvi Handoff — Scientific Communication + Biology Support

## Why you have this role
You are taking the job of making HiveBlot's public explanation match the actual science and product. The current beta's strongest story is that every value is reviewable and traceable; the live `/about` and `/learn` pages currently weaken that story by overstating scale and implying capabilities the beta has not proven.

## Learn this first
Read:
1. `research/TEAM_BETA_HANDOFF.md`
2. `research/team_delegation/SCIENTIFIC_COMMUNICATION_HANDOFF.md`
3. `research/team_delegation/BIOLOGY_QA_HANDOFF.md` for the status model and terminology context
4. Current live `/about` and `/learn`

Current beta truth: **3 reviewed papers · 93 experiments · 475 evidence rows**. What is proven: representation, search, provenance, uncertainty, and feedback on a reviewed corpus. What is not proven: automated extraction accuracy on unseen papers.

## Your tasks
1. **Draft the honest `/about` replacement.** Remove unsupported scale numbers and arbitrary-ingestion claims. Reframe the product around the reviewed corpus, traceability, uncertainty, and what is being evaluated next.
2. **Rewrite `/learn` to match the real product.** Remove Upregulated/Downregulated and densitometry/intensity language. Teach the actual four statuses and categorical band-presence behavior.
3. **Build the plain-English glossary.** Coordinate with Ananya on biology-checked definitions for IgG, IP bait, Input, phospho/site, loading control, doublet, kDa, expected vs reported MW.
4. **Write the audience/use-case statement.** Explain who HiveBlot is for and the sharpest current use cases, especially finding published evidence for an antibody or experiment context.
5. **Write cold-start copy.** Give testers a simple explanation that the first search after idle may take ~20–30 seconds because the free Render API is waking up.

## What not to change
- Do not deploy anything.
- Do not invent scale, accuracy, growth, or automation claims.
- Do not weaken the scoped zero-result language.
- Do not present densitometry or arbitrary-paper ingestion as current capability.
- Do not independently invent scientific definitions if Ananya flags uncertainty; keep them pending review.

## What you should understand before finishing
- The reviewed corpus and the future ingestion engine are different things.
- Honest abstention is part of the product's positioning, not something to hide.
- Every public claim should be traceable to the current beta state or clearly labeled as future work.
- Researchers will trust a small, auditable dataset more than inflated scale that collapses under one search.

## Definition of done
- `/about` replacement draft with every capability claim grounded in the current beta.
- `/learn` rewrite aligned with actual statuses and no densitometry implication.
- Biology-reviewed glossary.
- Short audience/use-case statement.
- Tester cold-start copy.

## Report back to Nik
Send:
- before/after copy
- any additional overclaims you find anywhere on the site
- unresolved positioning questions
- anything needing biology sign-off
- the exact parts that require Nik's final approval before shipping
