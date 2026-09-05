# HiveBlot migrations

Additive, idempotent SQL migrations for the Supabase `western_blot_records`
table and related beta tables. **Nothing here drops or retypes an existing
column**, so the deployed `/search` and `/proteins` endpoints and the current
frontend keep working while the new biological Evidence Record fields fill in.

| File | What it does | Reversible |
|------|--------------|------------|
| `001_evidence_record.sql` | Adds all Western Blot Evidence Record columns (protein identity, modification/site, experiment type, treatment, antibody, reported/expected MW, provenance, validation, `needs_review`) + FUTURE (unpopulated) densitometry columns + filter indexes. | `001_evidence_record.down.sql` |
| `002_relational_model.sql` | Optional forward-looking normalized model (`papers`, `figures`, `antibodies`) + a `wbr_evidence` view. The beta does **not** require this; the flat table in 001 powers the demo. | `002_relational_model.down.sql` |
| `003_feedback.sql` | `hiveblot_feedback` table for per-field / missing-field / result / UI / search feedback and human corrections (kept separate from AI extraction). | `003_feedback.down.sql` |

## How to apply

Supabase SQL editor, or:

```bash
psql "$SUPABASE_DB_URL" -f migrations/001_evidence_record.sql
psql "$SUPABASE_DB_URL" -f migrations/003_feedback.sql
# 002 is optional / forward-looking
```

## Notes

- **Backfill:** existing rows get `NULL` in new columns and `needs_review = true`.
  Re-running the ingestion pipeline (`western_blot_miner`) upserts enriched
  values via PostgREST, which auto-exposes the new columns.
- **Idempotency key unchanged:** the existing unique index
  `(paper_id, page, figure_label, target, condition)` is intentionally left
  as-is in this migration. Changing the dedupe key is a separate, reviewed
  decision because it affects how re-ingested rows merge.
- **Densitometry columns are deliberately unpopulated.** They exist only so a
  future deterministic measurement pipeline has somewhere to write. Never
  present a value there as "measured" unless that pipeline actually ran.
