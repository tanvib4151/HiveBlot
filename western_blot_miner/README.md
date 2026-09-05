# 🔬 Western Blot Miner

Type a protein name → see every published western blot result for it across the
literature. The tool searches PubMed Central Open Access, pulls figure captions
and methods, uses Claude to decide which figures are western blots and extract
structured facts (protein, cell line, condition, result, antibody…), and serves
it all behind a single search bar.

This is the QBI Hackathon MVP: **one flow working end to end** —
`protein name → results table`.

## Pipeline

```
PMC search (E-utilities)
        │
        ▼
BioC full text  ──►  figure captions + methods   (free, no auth)
        │
        ▼
caption pre-filter  ──►  keeps only WB-looking figures (saves LLM calls)
        │
        ▼
Claude (classify + extract)  ──►  is this a western blot? + structured records
        │                          (caption + methods, plus the image if available)
        ▼
SQLite  ──►  searchable by protein / cell line / organism
        │
        ▼
Web UI (FastAPI)  ──►  search bar + results table + source links
```

## Setup

```bash
cd western_blot_miner/..              # be in the parent of this package
python -m venv .venv && source .venv/bin/activate
pip install -r western_blot_miner/requirements.txt

export ANTHROPIC_API_KEY=sk-ant-...   # required
export NCBI_API_KEY=...               # optional, higher rate limit
```

(See `.env.example` for all variables.)

## 1. Ingest some data

```bash
# Text-only (fast, reliable): captions + methods → Claude
python -m western_blot_miner.pipeline --protein TP53 --limit 30

# With figure images sent to Claude's vision model (slower, richer)
python -m western_blot_miner.pipeline --protein GAPDH --limit 20 --with-images
```

Re-runs are idempotent — already-processed figures are skipped, so you can
build the database incrementally across several proteins.

## Local PDF Pipeline

Put PDFs under `papers/`, then run the pipeline with the PDF path:

```bash
python -m western_blot_miner.pipeline papers/fphar-17-1827794.pdf
```

To force a fresh VLM pass instead of reusing cached extraction JSONL:

```bash
python -m western_blot_miner.pipeline papers/fphar-17-1827794.pdf --no-cache
```

That command does the full flow:

1. Extract the paper DOI and use it as `paper_id`
2. Render PDF pages and extract page text
3. Generate and score candidate crop images
4. Send candidate images plus text context to the configured VLM
5. Flatten positive western blot outputs into band-level rows
6. Stream positive rows to Supabase as each blot is detected

The run directory is derived from the DOI. For example, DOI
`10.3389/fphar.2026.1827794` writes under:

```text
western_blot_miner/data/pdf_runs/10.3389_fphar.2026.1827794/
```

The output directory contains:

- `rendered_pages/` PNG renders of each page
- `panel_candidates/` candidate crop PNGs
- `pages.json`, `candidates.json`, `llm_candidates.json`
- `candidate_contexts.jsonl`
- `summary.json`
- `vlm_extractions.jsonl`, `vlm_extractions.json`
- `vlm_failed_requests.jsonl` request-level VLM failure log
- `vlm_extractions_positive_only.json`
- `supabase_rows_streamed.jsonl`, `supabase_rows.json`
- `vlm_summary.json`

Configuration comes from `.env`; the CLI intentionally only takes a PDF path.

## Supabase upload

Positive VLM figure outputs can be flattened into one row per detected band and
uploaded to Supabase. Configure the project URL and key with environment
variables:

```bash
export SUPABASE_URL=https://<your-project>.supabase.co
export SUPABASE_KEY=...
export SUPABASE_TABLE=western_blot_records
```

Create the base table first with `api/db/schema.sql`, then apply
`migrations/001_evidence_record.sql` to add the biological Evidence Record
columns, in the Supabase SQL editor.

For manual re-export only, convert positive VLM JSON to band-level rows without
uploading:

```bash
python -m western_blot_miner.supabase_loader \
  western_blot_miner/data/pdf_runs/10.3389_fphar.2026.1827794/vlm_extractions_positive_only.json \
  --output western_blot_miner/data/pdf_runs/10.3389_fphar.2026.1827794/supabase_rows.json
```

Manual upload is also available, but the main PDF pipeline streams positive
rows automatically:

```bash
python -m western_blot_miner.supabase_loader \
  western_blot_miner/data/pdf_runs/10.3389_fphar.2026.1827794/vlm_extractions_positive_only.json \
  --output western_blot_miner/data/pdf_runs/10.3389_fphar.2026.1827794/supabase_rows.json \
  --upload
```

The PDF pipeline uploads positive blot rows automatically. For local PDF runs,
`paper_id` is the extracted DOI for the current paper, falling back to the PDF
filename stem only when no DOI can be found.
The flattened rows use these columns: `paper_id`, `page`,
`western_blot_type`, `sample`, `organism`, `target`, `condition`, and
`band_detected`.

## 2. Launch the search interface

```bash
uvicorn western_blot_miner.app:app --reload
# open http://127.0.0.1:8000
```

Type `TP53`, hit Enter, get a table of every mined result with links back to
each source paper.

## Files

| File          | Role                                                        |
|---------------|-------------------------------------------------------------|
| `config.py`   | Paths, model name, API endpoints, keyword filter            |
| `pmc.py`      | PMC search (E-utilities) + structured full text (BioC API)  |
| `images.py`   | Optional figure-image download via the PMC OA package       |
| `extract.py`  | Claude classification + structured extraction (vision + text) |
| `pdf_preprocess.py` | Local PDF rendering, CV crop generation, and context assembly |
| `vlm_extract.py` | OpenAI-compatible VLM extraction for local PDF candidates |
| `supabase_loader.py` | Flatten positive VLM outputs and upload band rows to Supabase |
| `db.py`       | SQLite schema, inserts, search queries                      |
| `pipeline.py` | Orchestrates ingestion; CLI entry point                     |
| `app.py`      | FastAPI backend + single-page search UI                     |

## Notes & accuracy

- The model only reports facts it can justify from the caption / methods /
  image, and flags figures that are *not* western blots (bar charts,
  microscopy, Coomassie gels) so they don't pollute the database.
- Each row carries a confidence score and links back to the source paper, so
  results are auditable — pick well-known proteins (TP53, GAPDH, Actin) to
  spot-check extraction quality, as the project brief recommends.
- Data source: PubMed Central Open Access (free APIs, no auth needed for BioC).
  Restricting the search to `open access[filter]` guarantees figures and full
  text are available.
- Model defaults to `claude-opus-4-8`. For large bulk runs set
  `WBM_MODEL=claude-sonnet-4-6` to cut cost.
