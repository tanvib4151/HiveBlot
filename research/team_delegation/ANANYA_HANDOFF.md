# Ananya Handoff — Biology QA + Search Support

## Why you have this role
You can handle both biology-facing reasoning and solid CS work, so your assignment sits at the boundary where HiveBlot needs the most judgment: does the structured evidence make biological sense, and does the search system retrieve it honestly?

## Learn this first
Before changing anything, use the live beta and understand the full chain:
search → result card → Evidence Record → figure crop → provenance → uncertainty/status.

Read:
1. `research/TEAM_BETA_HANDOFF.md`
2. `research/team_delegation/BIOLOGY_QA_HANDOFF.md`
3. `research/team_delegation/SEARCH_DATA_HANDOFF.md`
4. `HANDOFF.md` sections on the biological contract, stable identity, and decisions that must not be reversed casually.

Current beta truth: **3 reviewed papers · 93 experiments · 475 evidence rows**. This proves the representation/search/provenance/review experience on a reviewed corpus. It does **not** prove arbitrary-paper automated extraction accuracy.

## Your tasks
1. **Biology QA pass.** Re-check the corrected Fig 3C/3D grouping and audit at least one full experiment per paper. Verify target, modification/site, cell line/sample, organism, treatment, antibody details, expected vs reported MW, and co-IP bait/readout where relevant.
2. **Abstention review.** Run `P-ERK` and `needs review`. Judge whether each Ambiguous/Conflicting case really should remain unresolved. Flag any case where HiveBlot says Supported but should not, or abstains when the paper clearly settles it.
3. **Search sanity support.** Pair with Suhas on the `GAPDH mouse` finding. Help define what an organism-aware query should mean biologically before any parser change is made.
4. **Misleading-presentation hunt.** Log anything where the underlying data may be correct but the UI could lead a scientist to the wrong conclusion. Known examples: `?` meaning both uncertainty and varies-by-lane, raw internal values rendered like paper quotes, and overly broad methods text shown for missing fields.
5. **Science definitions.** Provide precise plain-English definitions for IgG, IP bait, Input, phospho/site, loading control, doublet, kDa, and expected vs reported MW. Tanvi will use these in product copy.

## Exact searches to run
- `phospho STAT3 Tyr705`
- `co-IP PIK3CA`
- `CST 9145`
- `P-ERK`
- `GAPDH mouse`
- `needs review`
- `BRCA1 MCF7 olaparib`

Expected shapes: 3/18, 4/14, 3/18, 2/10, 5/31, 4/20, 0.

## What not to change
- Do not edit the reviewed corpus directly.
- Do not resolve scientific conflicts because something seems obvious.
- Do not touch `stable_row_key` identity logic.
- Do not deploy or write to Supabase.
- Do not start model automation.

## What you should understand before finishing
- An Evidence Record is not just an answer. It stores a normalized value, raw wording, status, provenance, candidates, and the evidence that supports or challenges it.
- SUPPORTED means the evidence agrees. AMBIGUOUS means more than one interpretation remains plausible. CONFLICTING means credible sources disagree and HiveBlot keeps the canonical value null. MISSING means the source simply does not provide the value.
- HiveBlot's trust story depends on refusing to invent or silently settle evidence.
- Search must distinguish true structured filters from broad text matching. A broad result set is preferable to a confidently wrong hidden filter.

## Definition of done
- Written Fig 3C/3D verification.
- At least one full experiment audited per paper.
- Every Ambiguous/Conflicting case you encounter gets an agree/disagree judgment with evidence.
- A short organism-query recommendation shared with Suhas.
- A severity-ranked misleading-UI list with screenshots/examples.
- Final glossary definitions sent to Tanvi.

## Report back to Nik
Send:
- what you found
- what is scientifically wrong vs just confusing
- any suggested code changes, without making unapproved corpus changes
- screenshots + paper evidence for major findings
- anything that needs a founder/product decision
