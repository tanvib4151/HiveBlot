# HiveBlot Benchmark Candidates — Diverse Western Blot Validation Set

> **Purpose.** A biologically diverse set of **real, open-access** papers to stress the
> HiveBlot Evidence Record extractor across the capabilities in the beta brief. This is a
> **candidate pool for human annotation**, not a gold set. Every entry was found via web
> search and **verified to resolve on PMC via WebFetch**. Fields not explicitly stated in
> the source are marked `NOT REPORTED`. **No gold labels were invented.**
>
> - Machine-readable companion: `eval/candidates.json` (26 objects; do NOT confuse with the
>   seed `eval/cases.json` / `eval/gold.json`, which were left untouched).
> - Generated 2026-08-12. Caption excerpts are quoted as extracted from each PMC page and
>   **should be spot-checked verbatim by the annotator** before final gold labeling.

## How to use this file
1. Pull each PMC article, open the named figure/panel, and read the caption + Methods pointer.
2. Fill the `annotation_fields` with values you can justify **from the source**. Leave
   `NOT REPORTED` where the paper is silent — that silence is itself a test case.
3. For the **negatives** (`is_western: false`), the correct behavior is to **reject the
   figure as non-Western**; do not manufacture protein fields.
4. Watch the flagged **adversarial** cases (GAPDH-as-target, p53-is-not-phospho,
   non-specific bands, ambiguous phospho/total, retracted figure).

## Verification status
- **8** candidates were **personally verified** by me via direct WebFetch of the PMC page.
- **18** came from three parallel research sub-agents, each of which WebFetch-verified its
  own set; I additionally **spot-checked 4** of those (PMC8332585, PMC7333534, PMC2542845,
  PMC9283986) and all matched exactly (PMCID resolves, caption + catalog numbers correct).
- Where a license string could not be confirmed on the page, it is marked honestly rather
  than assumed CC-BY. One negative (PMC1867154, zymography) is **publisher-copyright** and is
  included as a **pointer-only** negative — do not reproduce its image.

## Diversity coverage matrix

| Capability in brief | Covered by (PMCID) |
|---|---|
| Total / standard Western | PMC3139001, PMC5328321 |
| Phospho-Western | PMC5225179, PMC2820294, PMC8332585 |
| Co-IP | PMC7842739, PMC8632698, PMC7250321 |
| IP / Input / IgG lanes | PMC8784402, PMC7250321, PMC8632698 |
| Loading control (incl. as subject) | PMC12022650, PMC3631761 |
| Dose-response | PMC5778823 |
| Time course | PMC4393234, PMC2820294 |
| Explicit antibody catalog number | PMC5328321, PMC5225179, PMC2820294, PMC8332585, PMC5778823, PMC4393234, PMC9283986, PMC3941594 |
| Explicit phosphosite | PMC5225179 (Tyr705), PMC2820294 (S473/T308), PMC8332585 (T202/Y204), PMC9283986 (tau T231/T181/S404/S396), PMC7757890 (Ser2448) |
| Multiple targets in one figure | PMC3139001, PMC6406374, PMC6242874, PMC7948984 |
| Reported molecular weight (kDa) | PMC7333534 (CFTR 170/130), PMC7948984 (89), PMC8632698 (14/58), PMC1867154 (88/70/62) |
| Multiple / unexpected bands | PMC7948984 (cleavage), PMC5225179 (isoforms), PMC6794468 (non-specific), PMC7333534 (glycoforms) |
| Ambiguous experiment | PMC7757890 (phospho vs total, legend-only) |
| Blot-like NON-Western (negative) | PMC4087434 (Northern), PMC5472695 (silver SDS-PAGE), PMC1867154 (zymography) |
| Poor-quality / difficult | PMC6360618 (saturation/ghosting), PMC2542845 (retracted, figure duplication) |
| Different cell lines / samples | PMC3139001 (isogenic KO), PMC5225179 (mouse hepatocytes), PMC4393234 (rat spinal cord), PMC9283986 (patient fibroblasts), PMC3941594 (rat lung), PMC12022650 (mouse lung) |
| Multiple blot rows stacked | PMC6242874 (8 rows) |
| Antibody catalog in reagent table | PMC9283986 (Table 2) |

---

## Candidate list

Each entry: **citation** · DOI · PMCID · license · figure/panel · caption excerpt · methods
pointer · capabilities stressed · key annotation pointers. Full structured
`annotation_fields` are in `eval/candidates.json`.

### 1. `total-multitarget-p53-isogenic-01` — PMC3139001 *(personally verified)*
- **Qiu P, et al. Mol Nutr Food Res. 2011;55(4):613-622.** DOI 10.1002/mnfr.201000269 · license: PMC public access
- Fig 3 (p53) / Fig 8 (p21). Caption: *"Effects of 5OH-PMFs on the expression levels of p53 in three isogenic human colon cancer cells, namely HCT116 (p53 +/+), HCT116 (p53 -/-), and HCT116 (p21 -/-) cells."*
- Methods: primary antibodies from Cell Signaling; catalog numbers not itemized.
- Stresses: total Western, multi-target, isogenic KO cell-line diversity, beta-actin loading control. **Adversarial:** `p53`/`p21` must NOT be read as phospho.

### 2. `total-knockdown-overexpr-ctnnb1-01` — PMC5328321
- **Yang CM, et al. Onco Targets Ther. 2017;10:711-724.** DOI 10.2147/OTT.S117933 · CC BY-NC 3.0
- Fig 2. Caption: *"expression of CTNNB1 assay was analyzed by real-time PCR and Western blot."*
- Methods: anti-beta-catenin **ab6302** (Abcam, 1:4000); anti-GAPDH **5174** (CST, 1:1500).
- Stresses: knockdown AND overexpression, canonical gene **CTNNB1** (source-supported), explicit catalog, GAPDH loading control.

### 3. `phospho-stat3-tyr705-liver-01` — PMC5225179 *(personally verified)*
- **Svinka J, et al. J Mol Med (Berl). 2016;95(1):109-117.** DOI 10.1007/s00109-016-1462-8 · CC BY 4.0
- Fig 2f. Caption: *"Western blot analysis for tyrosine-705 phosphorylated pY-STAT3 (upper images) in STAT3flox/flox p19ARF-/- and STAT3dhc p19ARF-/- hepatocytes after IL-6 treatment."*
- Methods: **P-STAT3 (CST 9145)**; beta-actin (Sigma A5316).
- Stresses: phospho-Western, phosphosite **Tyr705**, catalog, **mouse primary hepatocytes with genetic KO**, **two isoform bands (STAT3-alpha/beta)**.

### 4. `phospho-akt-s473-t308-timecourse-01` — PMC2820294 *(personally verified; also found by sub-agent)*
- **Kumar N, et al. Biochem Biophys Res Commun. 2007;354(1):14-20.** DOI 10.1016/j.bbrc.2006.12.188 · NIHPA author manuscript
- Fig 1B (EGF) / Fig 3B (insulin). Caption: *"Representative blots for T308 and S473 from the three biological replicates."*
- Methods: anti-pAkt **Ser473 (CST #9271)**; **Thr308 (CST #4056)**.
- Stresses: phospho-Western, **time course**, two phosphosites of one target, catalog. Akt isoform not stated → canonical gene `NOT REPORTED`.

### 5. `phospho-erk-thr202-tyr204-01` — PMC8332585 *(spot-verified)*
- **Liu H, Lee S-M, Joung H. J Muscle Res Cell Motil. 2021.** DOI 10.1007/s10974-021-09605-x · CC BY 4.0
- Fig 6a. Caption: *"...analyzed using western blots with the respective antibodies against phosopho-Erk1/2 (Thr202/Tyr204), Erk1/2, phospho-Akt (Ser473), and Akt."*
- Methods (CST): pErk1/2 (T202/Y204) **9106**, Erk1/2 **4695**, pAkt (S473) **9271S**, Akt **9272S**, beta-Actin **4967S**.
- Stresses: phosphosite + catalog, ERK1/2 inherent p44/p42 **dual band**, phospho/total pairing.

### 6. `dose-response-actein-a549-01` — PMC5778823
- **Zhang Y, Lian J, Wang X. Oncol Lett. 2017.** DOI 10.3892/ol.2017.7668 · Spandidos OA (CC string not confirmed → `NOT REPORTED`)
- Fig 5. Caption: *"A549 cells were treated with different doses of actein (0, 20 and 40 uM) and total proteins in each group were subjected to western blot analysis."*
- Methods: Bcl-2 **ab32124**, Bax **ab32503** (Abcam); caspase-9 **sc4704**, caspase-3 **sc1224**, cytochrome c **sc8385**, GAPDH **sc365062** (Santa Cruz).
- Stresses: **dose gradient** (0/20/40 uM), multi-target apoptosis panel, catalog, GAPDH loading control.

### 7. `timecourse-arc-spinal-cord-01` — PMC4393234
- **Bojovic O, et al. PLoS ONE. 2015;10(4):e0123604.** DOI 10.1371/journal.pone.0123604 · CC BY 4.0
- Fig 3. Caption: *"Arc protein immunoblot analysis 2 h post CS ... stimulated side dorsal horn (SD), non-stimulated side dorsal horn (NSD)."*
- Methods: Arc C7 (**Santa Cruz sc-17839**); GAPDH (**sc-32233**).
- Stresses: **time course** (2 h/3 h), stimulated-vs-non-stimulated pairing, catalog, **rat spinal cord tissue**, loading control.

### 8. `loading-control-housekeeping-subject-01` — PMC12022650
- **Patterson AR, et al. Biochem Biophys Rep. 2025;42:102018.** DOI 10.1016/j.bbrep.2025.102018 · CC BY-NC-ND 4.0
- Fig 2 (Ponceau / alpha-tubulin / GAPDH / beta-actin); Fig 1 = 1-30 ug load titration. Caption: *"Ponceau S staining is a reliable loading control in asthmatic lung samples."*
- Stresses: loading-control identification incl. **Ponceau total-protein stain**. **Adversarial:** the housekeeping proteins ARE the study subject, not normalizers. Mouse lung tissue.

### 9. `loading-control-gapdh-knockdown-adversarial-01` — PMC3631761
- **Liang W, Mason AJ, Lam JKW. Methods Mol Biol. 2013;986:73-87.** DOI 10.1007/978-1-62703-311-4_5 · author manuscript (license `NOT REPORTED`)
- Fig 4. Caption: *"GAPDH expression in A549 cells at 72h post-transfection ... GAPDH protein band decreases as the amount of siRNA per well increases."*
- Stresses: **GAPDH is the knockdown TARGET here**, beta-actin is the loading control — breaks the "GAPDH == loading control" assumption. siRNA dose vs band intensity.

### 10. `coip-top1-native-01` — PMC7842739 *(personally verified)*
- **Husain A, et al. Bio Protoc. 2020;10(23):e3837.** DOI 10.21769/BioProtoc.3837 · Bio-protocol OA
- Fig 1C. Caption: *"Co-immunoprecipitation of SMARCA4, subunits of histone chaperone FACT (SSRP1 and SUPT16H), and H3K4me3 with TOP1."*
- Capture reagent: **GFP-Trap (Chromotek gta-20)**. Bait = GFP-TOP1; prey = SMARCA4/SSRP1/SUPT16H/H3K4me3.
- Stresses: co-IP, bait/prey, **separating capture reagent from detection antibody**.

### 11. `coip-pfn3-trim27-reciprocal-01` — PMC8632698
- **Umer N, et al. Front Cell Dev Biol. 2021;9:749559.** DOI 10.3389/fcell.2021.749559 · CC BY
- Fig 9. Caption: *"Co-immunoprecipitation using anti-PFN3 and anti-TRIM27 antibody on testis lysates."*
- Stresses: **reciprocal co-IP**, Input + negative-control lanes, **reported MW in caption** (PFN3 ~14 kDa; TRIM27 ~58 kDa). Mouse testis lysate.

### 12. `ip-input-hcf1-oglcnac-01` — PMC8784402
- **Ahmed O, et al. STAR Protoc. 2022;3(1):101108.** DOI 10.1016/j.xpro.2021.101108 · CC BY-NC-ND
- Fig 7. Caption: *"Immunoprecipitation of native HCF-1 using an anti-HCF-1 antibody... As a control, the immunoprecipitation was also done using an anti-GAL4 antibody."*
- Stresses: IP/input design with **anti-GAL4 as the negative control** (in place of IgG), PTM **O-GlcNAcylation** (RL2, Abcam ab2739). HeLa/HEK293T.

### 13. `ip-input-flag-ha-acox1-01` — PMC7250321
- **You L, et al. Virulence. 2020;11(1):537-553.** DOI 10.1080/21505594.2020.1766790 · license `NOT REPORTED`
- Fig 1. Reciprocal tagged co-IP: whole-cell-lysate **Input**, control **IgG**, and **anti-Flag / anti-HA IP** lanes. Bait = Flag-ACOX1 / HA-EV71-3D. HEK293T.
- Stresses: explicit Input/IgG/IP lane labeling, epitope tags, reciprocal design.

### 14. `multitarget-emt-2d-3d-01` — PMC6406374
- **Fontana F, et al. Cells. 2019;8(2):143.** DOI 10.3390/cells8020143 · CC BY 4.0
- Fig 7. Caption: *"Representative Western blot analysis showing Snail, Slug, Twist, and Zeb1 protein levels in whole cell lysates obtained from PC3 and DU145 cells cultured in 2D-monolayers and 3D cell cultures."*
- Stresses: **four targets in one figure** across two cell lines and 2D/3D conditions; alpha-tubulin loading control.

### 15. `reported-mw-cftr-glycoforms-01` — PMC7333534 *(spot-verified)*
- **Heda GD, et al. BioTechniques. 2020;68(6):318-324.** DOI 10.2144/btn-2019-0124 · CC BY-NC-ND 4.0
- Fig 1. Caption: *"Arrows on the left indicate the fully glycosylated, mature CFTR (band C, MW ~170 kDa) and core glycosylated CFTR (band B, MW ~130 kDa)."*
- Stresses: **explicit reported MW per band**, two glycoforms (doublet). CFBE-wt cells. Clean reported-MW gold source.

### 16. `bands-parp-caspase-cleavage-01` — PMC7948984 *(personally verified)*
- **Mashimo M, et al. J Biol Chem. 2021;296:100046.** DOI 10.1074/jbc.RA120.014479 · CC BY 4.0
- Fig 2A. Caption: *"Cleavage of PARP1 and caspase-3 (c-caspase-3) after staurosporine exposure."*
- Methods: anti-PARP1 recognizes **full-length + 89-kDa fragment**; GAPDH loading control.
- Stresses: **multiple bands** (full-length + 89 kDa), reported MW, **cleavage (not phosphorylation)**, two markers in one panel. HeLa + staurosporine.

### 17. `bands-app-nonspecific-01` — PMC6794468
- **Haytural H, et al. Front Aging Neurosci. 2019;11:273.** DOI 10.3389/fnagi.2019.00273 · CC BY
- Fig 1G. Caption: *"Equal amounts of homogenates of human AD and adult rat brain were loaded ... primary antibody Y188 together with a total protein stain."*
- Stresses: **unexpected / non-specific band** (~20 kDa) detected by many APP antibodies + total-protein stain. **Adversarial:** a band does not prove the target is present. Human AD + rat brain.

### 18. `unusual-sample-patient-fibroblasts-tau-01` — PMC9283986 *(spot-verified)*
- **Lopez-Toledo G, et al. Front Aging Neurosci. 2022;14:921573.** DOI 10.3389/fnagi.2022.921573 · CC BY
- Fig 4 (+ reagents **Table 2**). Caption (4B): *"Analysis of ABPP, p-tau-Thr231, p-tau-Thr181, p-tau Ser396-Ser404 and total tau levels."*
- Methods/Table 2: e.g. p-tau Thr231 **MBS9600919** (Biosource) + more catalog numbers.
- Stresses: **patient-derived fibroblasts (PSEN1 M146L/A246E)**, multiple tau phosphosites (incl. compound `Ser396-Ser404` notation), **catalog table**.

### 19. `unusual-sample-rat-lung-nrf2-01` — PMC3941594
- **Yao W, et al. Oxid Med Cell Longev. 2014;2014:258567.** DOI 10.1155/2014/258567 · CC BY
- Fig 4/5. Caption: *"Keap1 and nuclear Nrf2 expression in lung tissue after OALT."*
- Methods: Nrf2 **sc-722** (Santa Cruz); Keap1 **ABS97** (Millipore).
- Stresses: **rat lung tissue**, nuclear-vs-whole-fraction subtlety, multi-target, catalog.

### 20. `ambiguous-mtor-phospho-vs-total-01` — PMC7757890
- **Bortolami M, et al. PLoS ONE. 2020;15(12):e0244356.** DOI 10.1371/journal.pone.0244356 · CC BY 4.0
- Fig 3. Caption: *"p-mTOR(Ser2448), mTOR and beta-actin protein expression of patients with primary liver cancer."*
- Stresses: **ambiguous total-vs-phospho** — the gel strips are visually indistinguishable and only the legend disambiguates `p-mTOR(Ser2448)` from total mTOR. Human patient tissue (HCC / CRLM / normal).

### 21. `stacked-rows-autophagy-phospho-total-01` — PMC6242874
- **Liang P, et al. Cell Death Dis. 2018;9(12):1152.** DOI 10.1038/s41419-018-1194-5 · CC BY 4.0
- Fig 9d. Caption: *"Western-blot analysis of LC3, P62, AMPK, p-AMPK, Akt, p-Akt, mTOR and p-mTOR in heat-denatured dermis at 5d after heat injury."*
- Stresses: **8 stacked immunoblot rows** in one panel; each phospho row pairs with a total row — tests row-to-antibody association. HUVEC + dermis tissue.

### 22. `negative-northern-blot-01` — PMC4087434 *(personally verified)* — **NON-WESTERN NEGATIVE**
- **Splinter PL, et al. World J Gastroenterol. 2006;12(42):6797-6805.** DOI 10.3748/wjg.v12.i42.6797 · OA (Baishideng)
- Fig 4. Caption: *"Northern blot analysis of SLC10A4 mRNA expression in human tissues ... hybridized with a 32P-labeled SLC10A4 specific probe ... 32P-labeled beta-actin specific probe to confirm equal loading of mRNA."*
- **Correct behavior: reject.** Blot-like lanes but detects **mRNA**, not protein.

### 23. `negative-silver-sdspage-01` — PMC5472695 *(personally verified)* — **NON-WESTERN NEGATIVE**
- **Gabe CM, Brookes SJ, Kirkham J. Front Physiol. 2017;8:424.** DOI 10.3389/fphys.2017.00424 · CC BY
- Fig 7. Caption: *"Preparative SDS PAGE purified cleaved recombinant amelogenin to single band purity on silver stained SDS PAGE analytical gels."*
- **Correct behavior: reject.** Silver-stained SDS-PAGE of purified protein (24 kDa) — no antibody / no immunodetection.

### 24. `negative-gelatin-zymography-01` — PMC1867154 — **NON-WESTERN NEGATIVE (pointer only)**
- **Bendeck MP, et al. Am J Pathol. 2002;160(3):1089-1095.** DOI 10.1016/S0002-9440(10)64929-2 · **ASIP copyright (NOT CC-BY)** — pointer only, do not reproduce image
- Fig 2. Caption: *"Gelatin zymogram showing activity of MMP-9 (88 kd active) and MMP-2 (70 kd latent and 62 kd active)."*
- **Correct behavior: reject.** Bands are substrate-clearing **activity** signals, not antibody staining. Rat vascular SMC.

### 25. `difficult-densitometry-quality-01` — PMC6360618
- **Butler TAJ, et al. Biomed Res Int. 2019;2019:5214821.** DOI 10.1155/2019/5214821 · CC BY
- Fig 1. Caption: *"O.D. data were calculated from band area and background-subtracted intensity for (b) nitrocellulose membranes detected by chemiluminescence."*
- Stresses: **poor-quality bands on purpose** — saturation, fading ("ghosting"), high background. Tests graceful degradation and quantitation caveats.

### 26. `difficult-retracted-figure-duplication-01` — PMC2542845 *(spot-verified; retraction banner confirmed)*
- **He Q, et al. PPAR Res. 2008;2008:649808.** DOI 10.1155/2008/649808 · CC BY — **RETRACTED** (PPAR Res. 2020;2020:9469261)
- Fig 3 (PPARgamma / MMP-2 / VEGF / beta-actin). Caption: *"RGZ (1-20 uM) inhibited the mRNA and (c) protein expression levels of MMP-2 in a dose-dependent manner."*
- Retraction: Figure 3C "was not the authors' experimental result" (figure duplication).
- Stresses: **integrity / retraction handling** — the original article still resolves with a retraction banner. Tests whether the system surfaces retraction status rather than treating the blot as trustworthy evidence. SGC-7901 gastric cancer cells.

---

## Notes, caveats, and honest weak spots
- **Dose-response and time-course gradients are shallow** in some entries (2-3 doses / 2 time
  points rather than 5+): PMC5778823 (0/20/40 uM), PMC4393234 (2 h/3 h). Fine for lane parsing,
  but not deep kinetics.
- **Several strong biology cases lack antibody catalog numbers** (PMC3941594 gives some;
  PMC6242874, PMC6360618 do not). Marked `NOT REPORTED`, which is itself a useful test.
- **License honesty:** PMC5778823 (Spandidos), PMC7250321 (Virulence), PMC3631761 (author MS)
  could not be confirmed CC-BY on the page → `NOT REPORTED`. PMC1867154 is publisher-copyright
  and included **pointer-only**.
- **`p53`, `p21`, `p62`, `p-AMPK` naming:** entries 1, 16, 21 deliberately include `p`-prefixed
  names that are NOT phospho — direct regression guards for the removed `startswith("p")` heuristic.
- These are **candidates, not gold.** Do not treat any `annotation_fields` value as an answer key;
  the annotator sets the gold. Caption excerpts should be re-checked verbatim against the source.
