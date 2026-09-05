# Real-paper demo run — co-IP + phospho/autophagy Westerns (PMC12706926)

- **Paper:** Wang et al., "BEX2 regulates autophagy by inhibiting PIK3CA-p85
  interaction in NSCLC cells." *Cell Commun Signal* 23:528, 2025.
- **DOI:** 10.1186/s12964-025-02385-8 · **PMCID:** PMC12706926 · open access.
- **Cell lines:** H1299, H1792, A549 (human NSCLC).
- **Panels:** 11 real WB panels (Figs 2-7 incl. reciprocal co-IPs with an IgG
  control lane) + 4 non-WB candidates (IF panels, bar chart, publisher logo)
  correctly produced **zero** records. 53 Evidence Records / 238 Supabase rows.
- **Extraction:** agent-in-the-loop Stage-2 (same method + caveat as
  `../phospho_PMC12856536/README.md`); downstream biology is the real path.
- kDa marks printed beside panels are **ladder positions** and were NOT written
  into reported-MW (only explicit caption/methods MW statements count).

## What this paper exercises (and the bugs it caught)
- **co-IP with explicit bait:** `IP: PIK3CA` panels → `experiment_type=co_ip`,
  **`ip_bait_protein=PIK3CA`**, prey p85 (Proteintech 60225-1-Ig) and BEX2
  (Santa Cruz SC-398486); the IgG-control panel classifies the same way.
- **Caught: page-level co-IP bleed.** The methods' immunoprecipitation wording
  was reclassifying every expression panel on the page as co_ip (ACTB included).
  Fixed: co_ip now requires PANEL-scoped evidence (IP-role antibody, co-IP
  caption wording, or IP:/IgG/input lane labels); a methods-only mention is
  kept as a non-settling `co_ip_context` flag.
- **Caught: one-letter phosphosites.** `p-AKT (S473)`, `p-RPS6KB1 (T389)`,
  `p-EIF4EBP1 (S65)` initially lost their sites (three-letter forms worked).
  Fixed: a one-letter site inside the same phospho-marked label is trusted →
  AKT1/P31749 phospho-**Ser473**, RPS6KB1/P23443 phospho-**Thr389**,
  EIF4EBP1/Q13541 phospho-**Ser65**.
- **Caught: ambient-text fake conflicts.** "PI3K/AKT/mTOR signaling" in page
  text was read as an explicit "AKT is unmodified" claim, manufacturing
  MODIFICATION_CONFLICTs. Fixed: bare mentions assert nothing; only explicit
  "total X"/"T-X"/"pan-X" wording claims total.
- **Caught: page-blob reported MW.** The page's first "kDa" figure was being
  attributed to every row (BEX2 "reported 70" vs expected 15.3). Fixed:
  reported MW must appear near a mention of the target's core symbol.
- **p62 trap held:** `P62` (SQSTM1 alias) is never treated as phospho; its
  antibody has no vendor/catalog in the methods list → fields stay empty
  (never guessed).

## Coverage note (independent QA, M10)
The "11 real WB panels" above is the POST-CV-FILTER count. Two additional
full Western panels in this paper (Fig 5A and 5B — three phospho/total pairs
across two cell lines) scored below the OpenCV candidate threshold and never
reached Stage-2 extraction. Absence from the record set means "not extracted",
not "not in the paper".
