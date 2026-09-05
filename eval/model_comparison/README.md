# Automated-extraction comparison harness

Compares an automated model extraction run against the human-reviewed
reference set (`eval/demo/*/evidence_records.json`), field by field.
Model- and credential-independent (stdlib only).

```bash
# smoke test (each reference vs itself must be 100% EXACT):
.venv/bin/python eval/model_comparison/compare_records.py --self-test

# real comparison, once a model backend exists:
.venv/bin/python eval/model_comparison/compare_records.py \
    western_blot_miner/data/pdf_runs/<run>/evidence_records.json \
    eval/demo/<paper>/evidence_records.json
```

Categories: `EXACT / ACCEPTABLE / PARTIAL / WRONG / MISSING / HALLUCINATED`.
Records align on `(panel crop filename, raw target)`; unmatched reference
records score MISSING, unmatched predictions score HALLUCINATED. The
trust-weighted aggregate penalizes hallucination (−1) more than omission (0):
a fabricated value misleads, a gap underinforms.

**Never quote the aggregate as global model accuracy** — the reference is
3 reviewed papers, a smoke set, not a benchmark. Acceptability rules
(vendor synonyms, catalog formatting, unit spelling) live in the script and
should be extended as real mismatches are adjudicated.
