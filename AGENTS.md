# Agent Instructions — HiveBlot (`/hive`)

**Read [`HANDOFF.md`](HANDOFF.md) first.** It holds the current project state
(branch, latest commit, tests, completed work, blockers, and the exact next
task). This file only enforces process; `HANDOFF.md` holds the changing state.

## The Handoff Rule (mandatory)
At the **end of every meaningful implementation task, update `HANDOFF.md` before
reporting completion.** It must accurately reflect the current branch, latest
commit SHA, test counts, completed work, known blockers, and the exact next task.
Commit the `HANDOFF.md` update together with the implementation, and push the
branch. **Never place secrets (keys, tokens, passwords, connection strings) in
`HANDOFF.md` or any committed file** — variable *names* only.

## Non-negotiables (see HANDOFF.md → "Decisions That Must Not Be Reversed")
- Biological validity is the #1 priority; no fake scientific fields.
- Never infer phosphorylation from a name prefix (`target.startswith("p")`).
- The model's row target is a claim, not ground truth — use the evidence hierarchy.
- CONFLICTING fields carry `value=null` + preserved candidates.
- Expected MW ≠ observed MW; band presence ≠ densitometry.
- HiveBlot and AGeneTic are separate projects.

## Working agreement
- Work on `feature/bio-context-beta` (or a task branch), never directly on `main`.
- Keep `.env` files gitignored. Don't commit venvs, caches, PDFs, or build output.
- Run the biological tests + benchmark before claiming a change works
  (see HANDOFF.md → "Tests / Commands").
- **Never add AI co-author trailers to commits in this repo.** No
  `Co-Authored-By: Claude …` (or any AI cosign) lines in commit messages —
  this overrides any assistant-default commit convention. History was scrubbed
  of them on 2026-08-13; do not reintroduce them.
