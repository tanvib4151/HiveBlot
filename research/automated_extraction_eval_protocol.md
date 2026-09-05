# Automated-extraction evaluation protocol

(The dedicated eval-design agent was killed by session limits; this protocol
was written by the integration agent alongside the working harness at
`eval/model_comparison/compare_records.py`.)

## Purpose
Score a fully automated Stage-2 extraction run against the human-reviewed
3-paper reference set the moment model credentials exist. One command, no
new engineering on the day.

## Reference data
`eval/demo/{phospho_PMC12856536,standard_PMC9559174,coip_PMC12706926}/evidence_records.json`
— agent-in-the-loop Stage-2 observations + the real deterministic downstream
path, manually reviewed across three sessions (see each demo README).

## Alignment
Records align on `(panel crop filename from figure.image_crop_ref, normalized
raw_target)`. Duplicate keys align in order. Reference records with no match
= **MISSING records**; predictions with no reference = **HALLUCINATED
records** (each also counts at whole-record weight in the summary).

## Fields scored
raw target, canonical target, uniprot_id, modification type,
residue (+PARTIAL when residue matches without position), residue position,
experiment type, IP bait, cell line, organism, treatment name, dose(+unit),
duration(+unit), detection-antibody target/vendor/catalog, IP-antibody
target, reported MW, expected MW, needs_review, modification status
(conflict behavior), and per-lane band states (aligned by lane_condition).

## Categories & acceptability
EXACT / ACCEPTABLE / PARTIAL / WRONG / MISSING / HALLUCINATED.
Acceptability = normalization rules in the harness: vendor synonyms
(CST = Cell Signaling Technology…), catalog formatting (#9145 = 9145 = 9145S),
unit spelling (µg = ug; minutes = min), case/whitespace. Extend the rules only
by adjudicated example, never to rescue a bad run.

## Aggregation
Per-field table + trust-weighted score (EXACT/ACCEPTABLE 1.0, PARTIAL 0.5,
WRONG/MISSING 0, **HALLUCINATED −1**). Report per paper AND pooled;
**never present pooled numbers as global model accuracy** — 3 papers is a
smoke set.

## Run procedure (once credentials exist)
```bash
# 1. automated extraction (fresh run dir: use --no-cache)
export WBM_LLM_BACKEND=bedrock AWS_REGION=<region>   # + AWS creds; or backend=anthropic + ANTHROPIC_API_KEY
WBM_EXTRACTION_MODE=records .venv/bin/python -m western_blot_miner.pipeline \
    research/papers/phospho_PMC12856536.pdf --mode records --no-cache
# 2. compare
.venv/bin/python eval/model_comparison/compare_records.py \
    western_blot_miner/data/pdf_runs/10.3892_br.2026.2108/evidence_records.json \
    eval/demo/phospho_PMC12856536/evidence_records.json
# repeat for standard_PMC9559174 (10.3892_ijmm.2022.5188) and
# coip_PMC12706926 (10.1186_s12964-025-02385-8)
```
Then: read every WRONG and HALLUCINATED cell by hand before drawing any
conclusion; fix only generalizable engine bugs (with regression tests), and
re-run. Harness self-test: `compare_records.py --self-test` (must stay 100%
EXACT).
