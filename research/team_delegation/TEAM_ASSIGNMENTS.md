# HiveBlot Team Assignments

Current beta: **3 reviewed papers · 93 experiments · 475 evidence rows**.

Use this file as the assignment index for the current internal beta pass.

| Person | Primary role | Handoff |
|---|---|---|
| **Ananya** | Biology QA + search support | `ANANYA_HANDOFF.md` |
| **Suhas** | Search, data integrity, API / infra | `SUHAS_HANDOFF.md` |
| **Srushti** | Product / UX | `SRUSHTI_HANDOFF.md` |
| **Tanvi** | Scientific communication + biology support | `TANVI_HANDOFF.md` |
| **Yashvi** | Coordination, feedback synthesis, team communication | `YASHVI_HANDOFF.md` |
| **Nik** | Product direction, integration, evaluation strategy, final decisions | `NIK_FOUNDER_LEARNING.md` + `MASTER_DELEGATION.md` |

## Shared rules

- Work on `feature/bio-context-beta`, never `main`.
- Observe and understand before fixing.
- Do not touch legacy QIB.
- Do not deploy unless Nik explicitly owns/approves the deploy.
- Do not change the reviewed corpus without Nik's sign-off.
- Preserve raw wording and provenance.
- Never silently resolve scientific conflicts.
- Reviewed beta does not equal arbitrary-paper automated extraction accuracy.
- No model automation in this workstream pass.

## Coordination overlaps

- **Ananya ↔ Tanvi:** biology-checked glossary and scientific wording.
- **Srushti ↔ Suhas:** `needs review` reason display and minimal API support.
- **Ananya ↔ Suhas:** what a safe organism-aware query should mean biologically vs technically.
- **Yashvi:** track these overlaps so no duplicate implementation happens without coordination.

## Founder decisions that stay with Nik

- Final `/about` positioning and any public capability claims.
- Whether/when organism filtering changes search semantics.
- Whether API path sanitation requires a reseed.
- Which next-action UX ideas become roadmap items.
- Confidence display direction.
- Any reviewed corpus correction/reseed.
- Model credentials and automated-extraction evaluation.
- Integration, merge, and deploy decisions.
