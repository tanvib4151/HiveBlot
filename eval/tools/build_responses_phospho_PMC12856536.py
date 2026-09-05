"""Build the agent-observed `rows` JSON for the 9 CV candidates of
phospho_PMC12856536 (Jang et al., Biomed Rep 2026; DOI 10.3892/br.2026.2108).

These are REAL observations made by the Claude Code agent looking at each panel
crop + the paper's methods/captions. The deterministic biology (phospho/total
split, modification+residue, experiment type, loading control, expected MW via
live UniProt) runs downstream in the real engine.

Candidate order (must match extraction_requests.json / llm_candidates.json):
 0 page3 cand0021  cell-viability bar chart      -> NOT a western blot (empty)
 1 page3 cand0022  luciferase bar chart          -> NOT a western blot (empty)
 2 page4 cand0029  Fig2A P-STAT3 IL-6 time course (0-60min)     -> WB
 3 page6 cand0043  SOCS-3 qPCR bar chart         -> NOT a western blot (empty)
 4 page5 cand0034  Fig3C/D P-STAT3 +PKC/ERK inhibitors          -> WB
 5 page5 cand0036  Fig3A P-ERK1/2 IL-6 time course              -> WB
 6 page4 cand0028  Fig2B P-STAT3 CL-E dose response             -> WB
 7 page5 cand0035  Fig3B P-ERK1/2 CL-E dose response            -> WB
 8 page6 cand0042  CRP qPCR bar chart            -> NOT a western blot (empty)
"""
import json

VENDOR = "Cell Signaling Technology"

# Detection antibodies exactly as reported in Methods.
AB = {
    "P-STAT3 (Tyr705)": dict(catalog="9145", dil="1:1,000", phospho=True,
        text="p-STAT3 (Tyr705; 1:1,000; CST #9145)"),
    "P-STAT3 (Ser727)": dict(catalog="9134", dil="1:1,000", phospho=True,
        text="p-STAT3 (Ser727; 1:1,000; CST #9134)"),
    "T-STAT3": dict(catalog="4904", dil="1:1,000", phospho=False,
        text="t-STAT3 (1:1,000; CST #4904)"),
    "P-ERK 1/2": dict(catalog="4370", dil="1:1,000", phospho=True,
        text="p-ERK (1:1,000; CST #4370)"),
    "T-ERK 1/2": dict(catalog="4695", dil="1:1,000", phospho=False,
        text="t-ERK (1:1,000; CST #4695)"),
    "β-actin": dict(catalog="4967", dil="1:2,000", phospho=False,
        text="β-actin (1:2,000; CST #4967)"),
}


def ab_for(label):
    # Case-insensitive: the paper prints "T-STAT3" in Fig 2 but "T-Stat3" in
    # Fig 3C/D; both map to the same CST #4904 antibody.
    a = AB.get(label) or {k.upper(): v for k, v in AB.items()}[label.upper()]
    return [{
        "target": label,
        "vendor": VENDOR,
        "catalog": a["catalog"],
        "clone": "",
        "dilution": a["dil"],
        "role": "detection",
        "phospho_specific": a["phospho"],
        "source": {"type": "methods", "rank": 3, "text": a["text"]},
    }]


def bands(states):
    """states: list of (lane_index, condition, band_state, confidence)."""
    return [{"lane_index": i, "lane_condition": c, "band_state": s, "confidence": conf}
            for (i, c, s, conf) in states]


def row(label, sample, tname, tctx, band_states):
    return {
        "raw_target": label,
        "sample": sample,
        "organism": "",
        "treatment_name": tname,
        "treatment_context": tctx,
        "aliases": [],
        "antibodies": ab_for(label),
        "bands": bands(band_states),
    }


HEP3B = "Hep3B"

# --- Fig 2A: IL-6 time course (0,5,10,20,30,60 min) ------------------------
tc_ctx = "Hep3B cells treated with IL-6 (10 ng/ml) for the indicated times (0, 5, 10, 20, 30, 60 min)"
tc_lanes = ["0 min", "5 min", "10 min", "20 min", "30 min", "60 min"]
def tc_bands(present_from):  # present starting at a given lane index (1-based)
    out = []
    for i, c in enumerate(tc_lanes, 1):
        st = "present" if i >= present_from else "absent"
        out.append((i, c, st, "high"))
    return out
fig2a = [
    row("P-STAT3 (Tyr705)", HEP3B, "IL-6", tc_ctx,
        [(1, "0 min", "absent", "high"), (2, "5 min", "present", "high"),
         (3, "10 min", "present", "high"), (4, "20 min", "present", "high"),
         (5, "30 min", "present", "high"), (6, "60 min", "present", "medium")]),
    row("P-STAT3 (Ser727)", HEP3B, "IL-6", tc_ctx,
        [(1, "0 min", "uncertain", "low"), (2, "5 min", "present", "medium"),
         (3, "10 min", "present", "medium"), (4, "20 min", "present", "high"),
         (5, "30 min", "present", "high"), (6, "60 min", "present", "high")]),
    row("T-STAT3", HEP3B, "IL-6", tc_ctx, tc_bands(1)),
    row("β-actin", HEP3B, "IL-6", tc_ctx, tc_bands(1)),
]

# --- Fig 2B: CL-E dose response + IL-6 (10 ng/ml) 30 min --------------------
dr_ctx = ("Hep3B cells pretreated with CL-E at 10, 30 and 60 ug/ml for 1 h, "
          "then stimulated with IL-6 (10 ng/ml) for 30 min")
dr_lanes = ["IL-6 - / CL-E -", "IL-6 + / CL-E -", "IL-6 + / CL-E 10",
            "IL-6 + / CL-E 30", "IL-6 + / CL-E 60"]
fig2b = [
    row("P-STAT3 (Tyr705)", HEP3B, "IL-6", dr_ctx,
        [(1, dr_lanes[0], "absent", "high"), (2, dr_lanes[1], "present", "high"),
         (3, dr_lanes[2], "present", "medium"), (4, dr_lanes[3], "present", "medium"),
         (5, dr_lanes[4], "present", "low")]),
    row("P-STAT3 (Ser727)", HEP3B, "IL-6", dr_ctx,
        [(1, dr_lanes[0], "uncertain", "low"), (2, dr_lanes[1], "present", "medium"),
         (3, dr_lanes[2], "present", "medium"), (4, dr_lanes[3], "present", "medium"),
         (5, dr_lanes[4], "present", "medium")]),
    row("T-STAT3", HEP3B, "IL-6", dr_ctx, [(i, c, "present", "high") for i, c in enumerate(dr_lanes, 1)]),
    row("β-actin", HEP3B, "IL-6", dr_ctx, [(i, c, "present", "high") for i, c in enumerate(dr_lanes, 1)]),
]

# --- Fig 3A: P-ERK1/2 IL-6 time course -------------------------------------
# Observer note: both ERK rows visibly resolve as two closely spaced bands
# (the p44/p42 pair) in the panel crop. Recorded as a DESCRIPTIVE doublet
# observation only — no isoform assignment is made from the image.
ERK_DOUBLET = {"band_pattern": "doublet", "band_count": 2,
               "band_notes": "two closely spaced bands visible in each lane"}


def erk_row(label, tctx, band_states):
    r = row(label, HEP3B, "IL-6", tctx, band_states)
    for b in r["bands"]:
        # The doublet was observed on lanes with clear signal; an uncertain/
        # absent lane gets no structure claim (a pattern on an absent band is
        # a contradiction the engine now flags).
        if b["band_state"] == "present":
            b.update(ERK_DOUBLET)
    return r


fig3a = [
    erk_row("P-ERK 1/2", tc_ctx,
        [(1, "0 min", "uncertain", "low"), (2, "5 min", "present", "high"),
         (3, "10 min", "present", "high"), (4, "30 min", "present", "high"),
         (5, "60 min", "present", "high")]),
    erk_row("T-ERK 1/2", tc_ctx, [(i, f"lane{i}", "present", "high") for i in range(1, 6)]),
    row("β-actin", HEP3B, "IL-6", tc_ctx, [(i, f"lane{i}", "present", "high") for i in range(1, 6)]),
]

# --- Fig 3B: P-ERK1/2 CL-E dose response -----------------------------------
fig3b = [
    erk_row("P-ERK 1/2", dr_ctx,
        [(1, dr_lanes[0], "uncertain", "low"), (2, dr_lanes[1], "present", "high"),
         (3, dr_lanes[2], "present", "high"), (4, dr_lanes[3], "present", "high"),
         (5, dr_lanes[4], "present", "high")]),
    erk_row("T-ERK 1/2", dr_ctx, [(i, c, "present", "high") for i, c in enumerate(dr_lanes, 1)]),
    row("β-actin", HEP3B, "IL-6", dr_ctx, [(i, c, "present", "high") for i, c in enumerate(dr_lanes, 1)]),
]

# --- Fig 3C + Fig 3D: TWO experiments sharing one CV crop (cand_0034) --------
# Independent QA finding C1: the original observation collapsed both into one
# 4-lane panel and asserted IL-6 treatment on the Ser727 rows, although the
# paper's legend states Fig 3C was run IN THE ABSENCE of IL-6. Corrected here
# to the printed lane matrices. Band states not confidently re-verifiable from
# the session notes are recorded as `uncertain` (never guessed).
#
# Fig 3C (6 lanes, NO IL-6): Bis II  - - + - + -
#                            U0126   - - - + - +
#                            CL-E    - + + + - -
ctx_3c = ("Fig 3C: Hep3B cells treated with CL-E (60 ug/ml) with or without the "
          "PKC inhibitor Bisindolylmaleimide II (20 uM) or the MEK/ERK inhibitor "
          "U0126 (20 uM), in the absence of IL-6")
LANES_3C = ["ctrl", "CL-E", "CL-E + Bis II", "CL-E + U0126", "Bis II", "U0126"]
# Fig 3D (7 lanes, IL-6 matrix): Bis II - - - + - + -
#                                U0126  - - - - + - +
#                                CL-E   - - + + + - -
#                                IL-6   - + + + + - -
ctx_3d = ("Fig 3D: Hep3B cells stimulated with IL-6 (10 ng/ml) with or without "
          "CL-E (60 ug/ml), Bisindolylmaleimide II (20 uM) or U0126 (20 uM)")
LANES_3D = ["ctrl", "IL-6", "IL-6 + CL-E", "IL-6 + CL-E + Bis II",
            "IL-6 + CL-E + U0126", "Bis II", "U0126"]
fig3cd = [
    # Fig 3C — Ser727 arm, no IL-6. CL-E is the treatment.
    row("P-STAT3 (Ser727)", HEP3B, "CL-E", ctx_3c,
        [(1, LANES_3C[0], "present", "medium"), (2, LANES_3C[1], "present", "medium"),
         (3, LANES_3C[2], "uncertain", "low"), (4, LANES_3C[3], "uncertain", "low"),
         (5, LANES_3C[4], "uncertain", "low"), (6, LANES_3C[5], "uncertain", "low")]),
    row("T-Stat3", HEP3B, "CL-E", ctx_3c,
        [(i, c, "present", "high") for i, c in enumerate(LANES_3C, 1)]),
    row("β-actin", HEP3B, "CL-E", ctx_3c,
        [(i, c, "present", "high") for i, c in enumerate(LANES_3C, 1)]),
    # Fig 3D — Tyr705 arm, IL-6 matrix.
    row("P-STAT3 (Tyr705)", HEP3B, "IL-6", ctx_3d,
        [(1, LANES_3D[0], "absent", "high"), (2, LANES_3D[1], "present", "high"),
         (3, LANES_3D[2], "uncertain", "low"), (4, LANES_3D[3], "uncertain", "low"),
         (5, LANES_3D[4], "present", "medium"), (6, LANES_3D[5], "uncertain", "low"),
         (7, LANES_3D[6], "uncertain", "low")]),
    # Same printed labels as the 3C strips (raw wording preserved); the lane
    # conditions distinguish the two arms.
    row("T-Stat3", HEP3B, "IL-6", ctx_3d,
        [(i, c, "present", "high") for i, c in enumerate(LANES_3D, 1)]),
    row("β-actin", HEP3B, "IL-6", ctx_3d,
        [(i, c, "present", "high") for i, c in enumerate(LANES_3D, 1)]),
]

# Candidate paths in order (from extraction_requests.json).
CAND = [
    "page_003_cand_0021.png",  # 0 neg
    "page_003_cand_0022.png",  # 1 neg
    "page_004_cand_0029.png",  # 2 Fig2A
    "page_006_cand_0043.png",  # 3 neg
    "page_005_cand_0034.png",  # 4 Fig3C/D
    "page_005_cand_0036.png",  # 5 Fig3A
    "page_004_cand_0028.png",  # 6 Fig2B
    "page_005_cand_0035.png",  # 7 Fig3B
    "page_006_cand_0042.png",  # 8 neg
]
ROWS = [[], [], fig2a, [], fig3cd, fig3a, fig2b, fig3b, []]

responses = [{"candidate_path": cp, "rows": rows} for cp, rows in zip(CAND, ROWS)]

out = "/private/tmp/claude-502/-Users-niks-hive/71591061-cb4e-40e7-a99a-8691ae1c32b5/scratchpad/responses.json"
with open(out, "w") as f:
    json.dump(responses, f, indent=2, ensure_ascii=False)
print("wrote", out)
print("WB panels:", sum(1 for r in ROWS if r), " negatives:", sum(1 for r in ROWS if not r))
print("total rows:", sum(len(r) for r in ROWS))
