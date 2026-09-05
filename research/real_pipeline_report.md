# Real Pipeline Paper Set — Research Report

Prepared by the HiveBlot research sub-agent for an end-to-end `records`-mode pipeline run.

All three papers are **real, open-access (PMC OA subset)** articles. All three PDFs were
**downloaded successfully** as genuine, non-empty PDF files from the PMC OA distribution
(current path: `https://ftp.ncbi.nlm.nih.gov/pub/pmc/deprecated/oa_pdf/...` — the legacy
`oa_pdf`/`oa_package` trees were moved under `deprecated/` in 2026 and are scheduled for
removal; the FTP `oa.fcgi` service still advertises them).

| # | Category | PMCID | Local file | Format |
|---|----------|-------|------------|--------|
| 1 | STANDARD total-protein Western | PMC9559174 | `research/papers/standard_PMC9559174.pdf` | PDF (3.1 MB) |
| 2 | PHOSPHO Western (explicit site) | PMC12856536 | `research/papers/phospho_PMC12856536.pdf` | PDF (2.9 MB) |
| 3 | co-IP Western (explicit bait) | PMC12706926 | `research/papers/coip_PMC12706926.pdf` | PDF (8.3 MB) |

Field extraction below is read directly from each paper's caption + methods (via the PMC
article HTML). Anything the source does not state is marked `NOT REPORTED`. Expected MW
values are the well-known canonical masses for the human/mouse protein and are labeled as
`expected` (not read from the paper) to keep them distinct from any reported/observed MW,
per the HiveBlot invariant "Expected MW ≠ observed/reported MW."

---

## 1. STANDARD total-protein Western — PMC9559174

- **Title:** Reference-gene / loading-control validation for Western blot analysis across
  mouse submandibular gland development and regeneration.
- **Authors:** Liu et al.
- **Journal / year:** *International Journal of Molecular Medicine*, 2022.
- **DOI:** 10.3892/ijmm.2022.5188
- **PMCID:** PMC9559174
- **WB figure/panel:** **Figure 5A–E** — immunoblots of candidate loading-control /
  total-protein targets (ubiquitin, TUBA1B, GAPDH, ACTB) across developmental stages
  (E14.5–P112) and a duct ligation / de-ligation model. Caption theme: "Validation of
  loading controls for Western blot analysis throughout SMG development and regeneration."
- **PDF obtained?** YES — `research/papers/standard_PMC9559174.pdf` (3,104,472 bytes, PDF v1.x).

**Why this is the STANDARD case:** all targets are **total protein** (no phospho / no
modification), and every antibody carries an explicit vendor + catalog number — good
exercise for the antibody-detection and loading-control logic without any modification path.

### Human-expected Evidence Record fields
| Field | Value |
|-------|-------|
| raw target(s) | "ubiquitin", "TUBA1B", "GAPDH", "ACTB (β-actin)" |
| canonical target | UBB/ubiquitin; TUBA1B; GAPDH; ACTB |
| likely UniProt (mouse — this is *Mus musculus* tissue) | UBB P0CG49; TUBA1B P05213 (Tuba1b); GAPDH P16858; ACTB P60710 |
| modification | none (total protein) |
| residue | N/A |
| experiment type | standard Western blot (loading-control validation) |
| sample / cell line | mouse **submandibular gland (SMG) tissue** — NOT a cell line; NOT REPORTED as a cell line |
| treatment + dose + duration | NOT REPORTED as pharmacologic treatment; conditions are developmental stages E14.5–P112 and duct ligation/de-ligation model |
| antibody vendor + catalog | anti-ubiquitin rabbit, Yurogen Biosystems cat. 20200728 (1:400); anti-TUBA1B rabbit, Abcam ab108629 (1:100,000); anti-GAPDH rabbit, Cell Signaling Technology 5174s (1:1,000); anti-ACTB rabbit, Cell Signaling Technology 8457s (1:1,000) |
| reported MW | NOT REPORTED |
| expected MW | ubiquitin ~8.5 kDa (poly-Ub ladder higher); TUBA1B ~50 kDa; GAPDH ~36 kDa; ACTB ~42 kDa |
| band state | present (categorical) across stages; NOT densitometry |
| provenance | antibody + methods + Fig. 5 caption |

**Caveats:** mouse tissue, not a human cell line; resolver defaults to organism 9606 and will
need the mouse organism threaded in (a known gap in HANDOFF) or GAPDH/ACTB expected-MW is fine
but accessions will be human unless organism is set. No treatment/dose to exercise.

---

## 2. PHOSPHO Western (explicit phosphosite) — PMC12856536

- **Title:** "Ethyl acetate fraction of *Curcuma longa* leaves suppresses IL-6-induced STAT3
  activation via ERK signaling in Hep3B cells."
- **Authors:** Jang et al.
- **Journal / year:** *Biomedical Reports*, 2026.
- **DOI:** 10.3892/br.2026.2108
- **PMCID:** PMC12856536
- **WB figure/panel:** phospho-Western blots in **Figures 2B, 3B, 3C, 3D** — p-STAT3 (Tyr705),
  p-STAT3 (Ser727), and p-ERK1/2 under IL-6 stimulation ± *C. longa* leaf extract (CL-E) and
  ± MEK/PKC inhibitors.
- **PDF obtained?** YES — `research/papers/phospho_PMC12856536.pdf` (2,922,096 bytes, PDF v1.x).

**Why this is the PHOSPHO case:** it names an **explicit phosphosite (STAT3 Tyr705)** exactly
as requested, plus a second site (STAT3 Ser727) and p-ERK1/2, in a **human cell line** with a
**dose + duration treatment** and **full antibody vendor + catalog** — strongly exercises the
modification / residue detection, treatment extraction, and antibody logic. This dual-site
STAT3 (Tyr705 vs Ser727 moving in opposite directions) is also a useful stress test for the
"dual/competing modification on one target" edge case noted in HANDOFF.

### Human-expected Evidence Record fields (primary target: phospho-STAT3 Tyr705)
| Field | Value |
|-------|-------|
| raw target | "p-STAT3 (Tyr705)" / "phospho-STAT3 Tyr705" |
| canonical target | STAT3 |
| likely UniProt | **P40763** (human STAT3) |
| modification | phosphorylation |
| residue | **Tyr705** (Y705); paper also reports **Ser727** on the same protein (opposite direction) |
| experiment type | phospho-Western blot |
| sample / cell line | **Hep3B** (human hepatoma / hepatocellular carcinoma) |
| treatment + dose + duration | **IL-6 10 ng/ml for 30 min** (stimulus); CL-E pretreatment 10/30/60 µg/ml for 1 h before IL-6; U0126 (MEK inhibitor) 20 µM; bisindolylmaleimide II (PKC inhibitor) 20 µM |
| antibody vendor + catalog | p-STAT3 Tyr705 = Cell Signaling Technology **#9145**; p-STAT3 Ser727 = CST **#9134**; p-ERK1/2 = CST **#4370**; loading control β-actin = CST **#4967** |
| reported MW | NOT REPORTED |
| expected MW | STAT3 ~86–88 kDa (isoform α ~88 kDa / β ~83 kDa); ERK1/2 ~44/42 kDa; β-actin ~42 kDa |
| band state | phospho band present under IL-6, reduced by CL-E (categorical; NOT densitometry) |
| provenance | antibody (CST #9145 is a phospho-specific detection reagent) + caption + methods |

**Note for the pipeline:** CST #9145 is a *phospho-specific* antibody → the modification +
Tyr705 residue should resolve from the **antibody** source even if the caption text is terse,
which is exactly the antibody→modification association path the engine should confirm.

---

## 3. co-IP Western (explicit bait) — PMC12706926

- **Title:** "BEX2 regulates autophagy by inhibiting PIK3CA-p85 interaction in non-small-cell
  lung cancer cells."
- **Authors:** Wang et al.
- **Journal / year:** *Cell Communication and Signaling*, 2025.
- **DOI:** 10.1186/s12964-025-02385-8
- **PMCID:** PMC12706926
- **WB figure/panel:** **Figure 4B–D** (+ **Supplementary Fig. S2A–C**) — co-immunoprecipitation
  blots. Panel caption: "BEX2 hampers the interaction between PIK3CA and p85." Reciprocal IPs
  (anti-PIK3CA, anti-FLAG M2, anti-BEX2) with the partner protein probed on the blot.
- **PDF obtained?** YES — `research/papers/coip_PMC12706926.pdf` (8,294,277 bytes, PDF v1.x).

**Why this is the co-IP case:** it has **explicit IP baits** and **reciprocal
co-immunoprecipitation** with tagged constructs (FLAG, GST) and a complete antibody
vendor+catalog list — the strongest of the three for the co-IP role / IP-bait heuristic
(`_first_gene_after`) and antibody-detection-vs-association logic.

### Human-expected Evidence Record fields (co-IP)
| Field | Value |
|-------|-------|
| raw target(s) | "PIK3CA", "p85", "BEX2" (interaction: PIK3CA–p85 disrupted by BEX2) |
| canonical target | PIK3CA (p110α); PIK3R1 (p85α regulatory subunit); BEX2 |
| likely UniProt | PIK3CA **P42336**; PIK3R1/p85α **P27986**; BEX2 **Q9BXN6** |
| modification | none (protein–protein interaction assay, not a PTM blot) |
| residue | N/A |
| experiment type | **co-immunoprecipitation (co-IP) Western blot** |
| IP bait / prey | bait = **anti-PIK3CA** (also **anti-FLAG M2** on PIK3CA-FLAG, and **anti-BEX2** reciprocally); prey detected = p85 (PIK3R1) and BEX2 |
| sample / cell line | **HEK293FT**, **H1299**, **H1792** (human NSCLC + HEK) |
| treatment + dose + duration | NOT REPORTED as a pharmacologic dose/duration; manipulation is BEX2 over-expression / knockdown via plasmids (PIK3CA-FLAG, GST-BEX2, BEX2, pcDNA3.1) |
| antibody vendor + catalog | anti-BEX2 Santa Cruz **SC-398486**; anti-PIK3CA Cell Signaling **4249** and Santa Cruz **SC-293172**; anti-p85 Proteintech **60225-1-Ig**; anti-GST Proteintech **66001-2-Ig**; anti-FLAG Sigma-Aldrich **A2220** (M2 affinity gel) |
| reported MW | NOT REPORTED |
| expected MW | PIK3CA/p110α ~110 kDa; p85α ~85 kDa; BEX2 ~14 kDa; GST tag ~26 kDa (GST-BEX2 fusion higher) |
| band state | interaction present in control, reduced/absent with BEX2 (categorical; NOT densitometry) |
| provenance | IP antibody (bait) + co-IP blot antibody (prey) + Fig. 4 caption + methods |

**Note for the pipeline:** anti-FLAG M2 (Sigma A2220) is an **affinity/IP reagent**, not a
detection antibody for an endogenous target — a good test of the antibody
**detection-vs-association** distinction and the co-IP role assignment.

---

## Download provenance / verification
- OA availability confirmed per-article via the NCBI OA service:
  `https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id=PMCxxxx` (each returned an OA `link`).
- PDFs pulled from `https://ftp.ncbi.nlm.nih.gov/pub/pmc/deprecated/oa_pdf/<a>/<b>/<file>.PMCxxxx.pdf`.
  (The classic `/pub/pmc/oa_pdf/...` and `ftp://` paths now 404 / are blocked; the working
  route is the `deprecated/` subtree over HTTPS. This tree is slated for removal — re-fetch
  soon if the files are needed again, or switch to the AWS PMC OA cloud mirror.)
- Each file verified with `file` (all report "PDF document") and `stat` size (all > 2 MB,
  well above the 50 KB floor). No fabricated successes: all three are real downloaded PDFs.

## Suggested pipeline order
1. **PMC12856536** (phospho) — richest single-paper exercise of modification + residue +
   treatment/dose/duration + phospho-specific antibody.
2. **PMC12706926** (co-IP) — exercises IP-bait heuristic + antibody association + interaction roles.
3. **PMC9559174** (standard) — clean total-protein baseline; also exercises the mouse-organism
   resolver gap (set organism to *Mus musculus* before UniProt resolution).
