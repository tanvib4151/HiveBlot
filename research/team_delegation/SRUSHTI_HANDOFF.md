# Srushti Handoff — Product / UX

## Why you have this role
You are taking the first-time researcher experience. HiveBlot's core evidence flow works, but the founder walkthrough showed that a cold user is not taught what to search, why a result matched, why something needs review, or what to do after finding useful evidence.

## Learn this first
Use the live beta before reading the implementation. Try to understand it as a researcher seeing it for the first time.

Read:
1. `research/TEAM_BETA_HANDOFF.md`
2. `research/team_delegation/PRODUCT_UX_HANDOFF.md`
3. `HANDOFF.md` product-state and scientific-guardrail sections.

Current beta truth: **3 reviewed papers · 93 experiments · 475 evidence rows**. The reviewed-corpus scope must stay visible and honest.

## Your tasks
1. **Homepage first-run proposal.** Design what a first-time researcher should immediately understand: what HiveBlot searches, the honest corpus size, and 3–5 example searches.
2. **`needs review` comprehension.** Design how cards should explain why a record needs review without forcing the user to open every card. Coordinate with Suhas on the minimum API field needed.
3. **Next-action exploration only.** Rank what a researcher should be able to do after finding strong evidence, such as save, export, cite, related experiments, or more from this paper. Do not build these yet.
4. **Presentation fixes.** Propose better treatments for empty `WHY HIVEBLOT SAYS THIS`, the loading dash, the `?` marker being overloaded, and cold-start messaging.
5. **Confidence display recommendation.** Decide whether confidence should be shown numerically, bucketed, or kept hidden, and explain why from a researcher-trust perspective.

## Exact searches to use
- `phospho STAT3 Tyr705`
- `co-IP PIK3CA`
- `CST 9145`
- `P-ERK`
- `GAPDH mouse`
- `needs review`
- `BRCA1 MCF7 olaparib`

## What not to change
- Do not weaken the zero-result copy.
- Do not remove provenance to simplify the UI.
- Do not invent biological placeholder values.
- Keep search explicit-submit; do not switch back to search-as-you-type.
- No deploys.
- No model automation.

## What you should understand before finishing
- The core flow is search → card → Evidence Record → blot crop → provenance → feedback.
- `Conflicting` is a trust feature, not an error state to hide.
- Small-and-reviewed is the honest current product story; the UI should not imply literature-wide coverage.
- Product polish should make the evidence easier to understand without hiding where it came from.

## Definition of done
- Homepage proposal with final draft copy and example searches.
- `needs review` reason-display proposal coordinated with Suhas.
- Ranked next-action recommendation, no implementation yet.
- Concrete treatments for the four known presentation issues.
- One-page confidence-display recommendation.

## Report back to Nik
Send:
- your cold-user notes
- screenshots/mockups
- what is confusing vs merely visually rough
- your ranked recommendations
- anything that needs a founder/product decision
