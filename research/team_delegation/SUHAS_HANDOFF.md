# Suhas Handoff — Search, Data Integrity, API / Infra

## Why you have this role
You are taking the CS/data side of the current HiveBlot beta. The goal is to make sure search behavior, API output, and researcher-facing data stay honest and predictable without disturbing the reviewed corpus or the identity/feedback guarantees that are already working.

## Learn this first
Before changing anything, understand the live flow:
search → Next.js proxy → FastAPI → biological query parser → SQL guard → read-only Supabase → Evidence Record UI.

Read:
1. `research/TEAM_BETA_HANDOFF.md`
2. `research/team_delegation/SEARCH_DATA_HANDOFF.md`
3. `HANDOFF.md` sections on deployment, stable identity, feedback, and decisions that must not be reversed casually.

Current beta truth: **3 reviewed papers · 93 experiments · 475 evidence rows**. Do not infer automated extraction accuracy from this corpus.

## Your tasks
1. **Investigate `GAPDH mouse`.** Confirm exactly why it works today. Document whether `mouse` is a real organism predicate or just free-text matching. Propose a safe structured-organism approach and list false-positive/false-negative cases. Do not change the parser until Nik approves the behavior.
2. **Plan `image_crop_ref` sanitation.** Map every consumer of the absolute local path currently exposed by the public API. Recommend the least disruptive fix, ideally a relative/public-safe reference or omission from list responses. Do not force a reviewed reseed unless Nik explicitly approves it.
3. **Clean raw-value presentation at the shaping layer.** Root-cause `ambiguous_family`, `{}`, and candidate `none` being rendered like paper quotes. Preserve stored provenance; fix only serialization/presentation after findings are agreed.
4. **Design the `review_reasons` API shape with Srushti.** The UI needs to say why a row needs review. Propose the smallest list-response addition instead of exposing full validation JSONB.
5. **Confirm free-tier cold-start behavior.** Treat the Render wake-up delay as a known constraint, not an infra project. Recommend only cheap handling unless Nik asks otherwise.

## Exact checks
- Flagship searches: `phospho STAT3 Tyr705`, `co-IP PIK3CA`, `CST 9145`, `P-ERK`, `GAPDH mouse`, `needs review`, `BRCA1 MCF7 olaparib`.
- Expected shapes: 3/18, 4/14, 3/18, 2/10, 5/31, 4/20, 0.
- `cd api && pytest`
- `cd web && npx tsc`

## What not to change
- No changes to `sql_guard.py` security semantics.
- No changes to `stable_row_key` / identity hashing.
- No direct edits to stored provenance or reviewed corpus rows.
- No writes to Supabase and no deploys.
- Never touch legacy QIB.
- No model automation.

## What you should understand before finishing
- The deterministic parser only structures terms it can recognize safely; everything else falls back to text search.
- Search should over-return honestly rather than silently apply a wrong structured filter.
- The list API and detail API have different responsibilities: compact result discovery vs full evidence/provenance.
- Stable identity ties search grouping and feedback persistence together; infrastructure changes must not break that contract.

## Definition of done
- Organism-filter investigation with current behavior, proposed behavior, and tradeoffs.
- Complete `image_crop_ref` consumer map + recommended sanitation plan.
- Root-cause notes for the raw-value leaks and, only if authorized, a tested shaping-layer fix.
- `review_reasons` API proposal agreed with Srushti.
- All flagship searches and tests still green after any authorized changes.

## Report back to Nik
Send:
- what you found
- what is a real data/search bug vs a presentation issue
- any code changes you recommend
- exact tests/results
- anything that needs a product decision before implementation
