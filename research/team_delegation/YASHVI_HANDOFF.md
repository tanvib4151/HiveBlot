# Yashvi Handoff — Coordination, Feedback Synthesis, Team Communication

## Why you have this role
You are not on the engineering side for this pass. Your value is keeping the beta review organized so technical findings do not get lost, duplicated, or turned into random parallel fixes. You should understand enough of HiveBlot to translate what each workstream found into a clean team picture for Nik.

## Learn this first
Read:
1. `research/team_delegation/MASTER_DELEGATION.md`
2. `research/TEAM_BETA_HANDOFF.md`
3. The opening sections of each teammate handoff so you know what Suhas, Ananya, Srushti, and Tanvi are responsible for.

Current beta truth: **3 reviewed papers · 93 experiments · 475 evidence rows**. This is a reviewed reference corpus, not proof of arbitrary-paper automated extraction accuracy.

## Your tasks
1. **Track workstream status.** Keep a simple table with owner, task, status, blockers, and whether Nik needs to decide something.
2. **Collect findings without rewriting them.** When teammates report issues, preserve their exact evidence, screenshots, queries, and severity. Separate confirmed bugs from questions or product ideas.
3. **Identify overlaps.** If two teammates are touching the same issue, flag it before both start implementation. The most likely overlap is Srushti + Suhas on `needs review`, and Ananya + Tanvi on biology terminology.
4. **Prepare a team recap for Nik.** Once the first pass is complete, summarize: what is scientifically wrong, what is technically wrong, what is confusing UX, what is merely polish, and which items need Nik's decision.
5. **Keep claims honest.** If team-facing or external copy starts implying literature-wide coverage, automated ingestion accuracy, or densitometry, flag it immediately.

## What not to change
- No code changes.
- No deploys.
- No Supabase/Render/Vercel actions.
- Do not reinterpret scientific findings yourself; route them back to Ananya/Tanvi when biology judgment is needed.
- Do not collapse unresolved disagreements into one answer.

## What you should understand before finishing
- HiveBlot's core flow is search → result → Evidence Record → blot crop → provenance → uncertainty/feedback.
- A finding can be one of several things: scientific correctness issue, search/data issue, UX issue, communication issue, or product idea. Those should not all be treated the same.
- The team should observe and understand first, then implement only what Nik approves.

## Definition of done
- One current status tracker covering all four teammate workstreams.
- No duplicated implementation work happening unnoticed.
- A concise first-pass team recap ready for Nik when everyone reports back.
- Clear list of decisions only Nik needs to make.

## Report back to Nik
Send:
- current owner/status for every workstream
- blockers
- overlapping findings
- anything waiting on a Nik decision
- final first-pass recap once everyone is done
