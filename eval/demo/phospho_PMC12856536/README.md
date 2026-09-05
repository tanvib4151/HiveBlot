# Real-paper demo run — phospho-STAT3 Western (PMC12856536)

First real paper taken **end-to-end** through the HiveBlot Evidence Record engine.

- **Paper:** Jang et al., *Curcuma longa* leaf extract suppresses IL-6-induced STAT3
  activation via ERK signaling in Hep3B cells. *Biomedical Reports* 24:35, 2026.
- **DOI:** 10.3892/br.2026.2108 · **PMCID:** PMC12856536 · open access.
- **Cell line:** Hep3B (human HCC). **Stimulus:** IL-6 10 ng/ml. **Modulator:** CL-E 10/30/60 µg/ml.

## Pipeline exercised
```
PDF → PyMuPDF render → OpenCV panel candidates (55 → 9 above threshold)
    → semantic extraction (see "Model backend" below)
    → Evidence Record build → reconcile → LIVE UniProt resolve → validation
    → evidence_records.json + supabase_rows.json (migration-001 projection)
```
9 CV candidates: **5 real Western panels** extracted, **4 bar charts** (qPCR / luciferase /
viability) correctly returned **zero** records (blot-like non-Western negatives).

## Model backend — honest note
No live model backend (Bedrock / Anthropic / OpenAI) was configured in this
environment, so **Stage-2 semantic extraction was performed agent-in-the-loop**:
the Claude Code agent read each real panel crop + the paper's methods/captions and
produced the observed `rows` JSON (`responses_observed.json`), injected through the
real `LLMClient` interface via `eval/tools/manual_pipeline.py`. **Everything
downstream is the real production path** — deterministic biology, reconciliation,
**live UniProt**, validation. Transport is agent-in-the-loop; the biology is real.
To reproduce with an automated backend, set `WBM_LLM_BACKEND` and run
`pipeline.py … --mode records`.

## Records produced (18 records, 90 Supabase rows)
| raw target | canonical | UniProt | modification | experiment | expected MW | antibody | review |
|---|---|---|---|---|---|---|---|
| P-STAT3 (Tyr705) | STAT3 | P40763 | phospho / Tyr705 | phospho_western | 88.1 kDa | CST #9145 | Supported |
| P-STAT3 (Ser727) | STAT3 | P40763 | phospho / Ser727 | phospho_western | 88.1 kDa | CST #9134 | Supported |
| T-STAT3 | STAT3 | P40763 | — (total) | standard_western | 88.1 kDa | CST #4904 | Supported |
| β-actin | — | — | — | **loading_control** | — | CST #4967 | (loading) |
| P-ERK 1/2 | **MAPK1/MAPK3** | — | CONFLICTING (phospho-ab vs no marker; unsettled, value null) | AMBIGUOUS | — | CST #4370 | **Needs review** |
| T-ERK 1/2 | **MAPK1/MAPK3** | — | — | standard_western | — | CST #4695 | **Needs review** |

Reported MW is **NOT REPORTED** in the source, so it is `null` everywhere — never
conflated with the UniProt-derived expected MW.

## What this run proved (and fixed)
- ✅ phospho vs total separation (P-STAT3 rows phospho; T-STAT3 total), site-level
  residues (Tyr705 / Ser727), loading-control detection, treatment parse, live
  UniProt expected-MW, and non-Western rejection all correct on real data.
- 🐞 Found + fixed a **structural** bug cluster (see commit): `core_symbol` mangled
  `P-ERK 1/2`→`ERK`→**EPHB2** (a UniProt gene-synonym false-friend), and `p53`→`53`,
  `PARP`→`ARP`, and never stripped total-protein `T-`. ERK1/2 now resolves as the
  **ambiguous MAPK1/MAPK3 family** (never a false single accession), and an
  ambiguous family no longer renders as `SUPPORTED`.

## Files
- `evidence_records.json` — full Evidence Records (field envelopes + provenance).
- `supabase_rows.json` — flat migration-001 projection (one row per band).
- `responses_observed.json` — the agent's Stage-2 observations (input to the run).

## Correction (independent QA, C1)
The crop `page_005_cand_0034.png` contains TWO experiments (Fig 3C and 3D).
The original observation collapsed them into one 4-lane panel and wrongly
asserted IL-6 treatment on the Ser727 arm — the paper's legend states Fig 3C
was run in the ABSENCE of IL-6. Fixed 2026-08-13: the arms are now separate
records with the printed 6- and 7-lane condition matrices; band states not
confidently re-verifiable were recorded as `uncertain`, never guessed.
