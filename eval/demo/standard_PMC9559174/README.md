# Real-paper demo run — standard total-protein Western, MOUSE (PMC9559174)

- **Paper:** Liu et al., loading-control validation across mouse submandibular
  gland (SMG) development and regeneration. *Int J Mol Med* 2022.
- **DOI:** 10.3892/ijmm.2022.5188 · **PMCID:** PMC9559174 · open access.
- **Sample:** mouse SMG **tissue** (not a cell line). **Organism: mouse — explicit.**
- **Panels:** Figure 5A/B/C (5 CV crops) — ubiquitin / TUBA1B / GAPDH / ACTB
  across E14.5→P112 development and duct ligation/de-ligation. 14 non-WB
  candidates (qPCR dot plots, Venn diagrams, legends, micrographs, a license
  logo) correctly produced **zero** records.
- **Extraction:** agent-in-the-loop Stage-2 (same method + caveat as
  `../phospho_PMC12856536/README.md`); downstream biology is the real path.

## What this paper exercises
- **Organism threading (new this session):** the claimed organism (mouse) scopes
  the UniProt query → **Tuba1b P05213 (50.2 kDa), Gapdh P16858 (35.8), Actb
  P60710 (41.7)** — the mouse accessions, not the human ones.
- Loading-control classification (GAPDH → `loading_control`).
- All-total-protein paper: no modification path is triggered anywhere.
- **Ubiquitin** stays honestly unsettled (canonical MISSING, `needs_review`):
  "ubiquitin" is not a single resolvable gene symbol, and an anti-ubiquitin
  blot legitimately raises a modification-vs-protein-identity question the
  engine flags rather than settles.

20 Evidence Records / 124 Supabase rows (one row per lane).
