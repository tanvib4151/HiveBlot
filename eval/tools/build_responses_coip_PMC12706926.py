"""Agent-observed Stage-2 rows for coip_PMC12706926 (Wang et al. 2025,
Cell Commun Signal, DOI 10.1186/s12964-025-02385-8) — BEX2 / PIK3CA-p85 co-IP
+ autophagy/PI3K-AKT-mTOR Westerns in human NSCLC lines (H1299/H1792/A549).

Antibodies (Methods, verbatim list): anti-ACTB (A1978) and anti-MYC (C3956)
Sigma-Aldrich; anti-LC3B (2775), anti-PIK3CA (4249), anti-ATG5 (12994),
anti-p-AKT (9271), anti-AKT (9272), anti-p-RPS6KB1 (9234), anti-RPS6KB1
(9202), anti-p-EIF4EBP1 (9451), anti-EIF4EBP1 (9452) Cell Signaling
Technology; anti-p85 (60225-1-Ig), anti-GST (66001-2-Ig) Proteintech;
anti-BEX2 (SC-398486), anti-PIK3CA (SC-293172) Santa Cruz Biotechnology.
A P62 antibody is NOT in the methods list -> vendor/catalog left empty.
kDa marks printed beside panels are ladder positions — NOT written into any
reported-MW field (only explicit caption/methods MW statements would be).
"""
import json
from pathlib import Path

METHODS_TEXT = ("anti-ACTB (A1978), and anti-MYC (C3956) were obtained from Sigma-Aldrich; "
                "anti-LC3B (2775), anti-PIK3CA (4249), anti-ATG5 (12994), anti-p-AKT (9271), "
                "anti-AKT (9272), anti-p-RPS6KB1 (9234), anti-RPS6KB1 (9202), anti-p-EIF4EBP1 "
                "(9451), anti-EIF4EBP1 (9452) were obtained from Cell Signaling Technology; "
                "anti-p85 (60225-1-Ig), anti-GST (66001-2-Ig) were obtained from Proteintech; "
                "anti-BEX2 (SC-398486), anti-PIK3CA (SC-293172) were obtained from Santa Cruz Biotechnology.")

AB = {
    "BEX2": ("Santa Cruz Biotechnology", "SC-398486", False),
    "PIK3CA": ("Cell Signaling Technology", "4249", False),
    "p-AKT (S473)": ("Cell Signaling Technology", "9271", True),
    "AKT": ("Cell Signaling Technology", "9272", False),
    "LC3B": ("Cell Signaling Technology", "2775", False),
    "ATG12-ATG5": ("Cell Signaling Technology", "12994", False),
    "p-RPS6KB1 (T389)": ("Cell Signaling Technology", "9234", True),
    "RPS6KB1": ("Cell Signaling Technology", "9202", False),
    "p-EIF4EBP1 (S65)": ("Cell Signaling Technology", "9451", True),
    "EIF4EBP1": ("Cell Signaling Technology", "9452", False),
    "ACTB": ("Sigma-Aldrich", "A1978", False),
    "MYC": ("Sigma-Aldrich", "C3956", False),
    "p85": ("Proteintech", "60225-1-Ig", False),
    "P62": ("", "", False),  # not in the methods antibody list — never guess
}


def det_ab(target):
    vendor, cat, phospho = AB[target]
    src_text = METHODS_TEXT if vendor else "P62 blot row label (antibody not listed in methods)"
    return {"target": target, "vendor": vendor, "catalog": cat, "clone": "",
            "dilution": "", "role": "detection", "phospho_specific": phospho,
            "source": {"type": "methods" if vendor else "figure_caption",
                       "rank": 3, "text": src_text}}


IP_PIK3CA = {"target": "PIK3CA", "vendor": "", "catalog": "", "clone": "",
             "dilution": "", "role": "immunoprecipitation", "phospho_specific": False,
             "source": {"type": "figure_caption", "rank": 2,
                        "text": "IP: PIK3CA (panel column header)"}}


def row(target, sample, lanes, states, confs=None, tname="", tctx="", extra_abs=None):
    confs = confs or ["high"] * len(lanes)
    return {
        "raw_target": target, "sample": sample, "organism": "human",
        "treatment_name": tname, "treatment_context": tctx, "aliases": [],
        "antibodies": [det_ab(target)] + (extra_abs or []),
        "bands": [{"lane_index": i + 1, "lane_condition": c, "band_state": s,
                   "confidence": cf}
                  for i, (c, s, cf) in enumerate(zip(lanes, states, confs))],
    }


def uniform(target, sample, lanes, state="present", conf="high", **kw):
    return row(target, sample, lanes, [state] * len(lanes), [conf] * len(lanes), **kw)


# ---- panel lane vocabularies ------------------------------------------------
SI6 = ["DMSO siCTRL", "DMSO siBEX2#1", "DMSO siBEX2#2",
       "LY294002 siCTRL", "LY294002 siBEX2#1", "LY294002 siBEX2#2"]
RAPA6 = ["DMSO siCTRL", "DMSO siBEX2#1", "DMSO siBEX2#2",
         "Rapamycin siCTRL", "Rapamycin siBEX2#1", "Rapamycin siBEX2#2"]
ATG6 = ["ctrl", "BEX2", "BEX2 + siATG5", "Rapamycin", "Rapamycin + BEX2",
        "Rapamycin + BEX2 + siATG5"]
BP4 = ["ctrl", "BEX2", "PIK3CA", "BEX2 + PIK3CA"]
SIP4 = ["siCTRL", "siBEX2", "siPIK3CA", "siBEX2 + siPIK3CA"]
RHEB4 = ["ctrl", "BEX2", "MYC-RHEB Q64L", "BEX2 + MYC-RHEB Q64L"]
BAF4 = ["DMSO ctrl", "DMSO BEX2", "BafA1 ctrl", "BafA1 BEX2"]

KD = ["present", "uncertain", "uncertain"]          # BEX2 knocked down by siRNA
KDC = ["high", "low", "low"]

# [0] p7 Fig G — H1299, siBEX2 x LY294002; BEX2 / p-AKT(S473) / AKT / ACTB
g = [
    row("BEX2", "H1299", SI6, KD + KD, KDC + KDC, "LY294002",
        "H1299 treated with DMSO or the PI3K inhibitor LY294002; siCTRL/siBEX2#1/siBEX2#2"),
    uniform("p-AKT (S473)", "H1299", SI6, conf="medium", tname="LY294002",
            tctx="H1299 treated with DMSO or LY294002; siCTRL/siBEX2#1/siBEX2#2"),
    uniform("AKT", "H1299", SI6, tname="LY294002",
            tctx="H1299 treated with DMSO or LY294002; siCTRL/siBEX2#1/siBEX2#2"),
    uniform("ACTB", "H1299", SI6),
]
# Observer note (panel crops): LC3B in Fig 1C and BEX2 in Fig 7A visibly
# resolve as two closely spaced bands. Recorded as DESCRIPTIVE doublet
# observations only — no LC3B-I/II or isoform assignment is made from the
# image (the paper's own text discusses LC3B-II levels, but the pattern claim
# here is purely what the blot shows).
def _doublet(r):
    for b in r["bands"]:
        # Structure is only claimed for lanes with clear signal; uncertain/
        # absent lanes carry no pattern (contradiction otherwise).
        if b["band_state"] == "present":
            b.update({"band_pattern": "doublet", "band_count": 2,
                      "band_notes": "two closely spaced bands visible in each lane"})
    return r


# [1] p5 Fig C — H1299, siBEX2 x Rapamycin; BEX2 / P62 / LC3B / ACTB
c5 = [
    row("BEX2", "H1299", RAPA6, KD + KD, KDC + KDC, "Rapamycin",
        "H1299 treated with DMSO or Rapamycin; siCTRL/siBEX2#1/siBEX2#2"),
    uniform("P62", "H1299", RAPA6, tname="Rapamycin",
            tctx="H1299 treated with DMSO or Rapamycin"),
    _doublet(uniform("LC3B", "H1299", RAPA6, conf="medium", tname="Rapamycin",
                     tctx="H1299 treated with DMSO or Rapamycin")),
    uniform("ACTB", "H1299", RAPA6),
]
# [2] p7 Fig D — H1792 co-IP: Input(-/+BEX2) | IP:PIK3CA(-/+BEX2)
COIP_D_LANES = ["Input BEX2-", "Input BEX2+", "IP:PIK3CA BEX2-", "IP:PIK3CA BEX2+"]
d7 = [
    row("p85", "H1792", COIP_D_LANES, ["present"] * 4,
        ["high", "high", "high", "medium"], "",
        "H1792 with or without BEX2 overexpression; co-immunoprecipitation with anti-PIK3CA",
        extra_abs=[IP_PIK3CA]),
    row("PIK3CA", "H1792", COIP_D_LANES, ["present"] * 4, None, "",
        "H1792 with or without BEX2 overexpression; co-immunoprecipitation with anti-PIK3CA",
        extra_abs=[IP_PIK3CA]),
    row("BEX2", "H1792", ["Input BEX2-", "Input BEX2+"], ["absent", "present"], None, "",
        "H1792 input lysate with or without BEX2 overexpression", extra_abs=[IP_PIK3CA]),
    row("ACTB", "H1792", ["Input BEX2-", "Input BEX2+"], ["present", "present"],
        None, "", "input loading control", extra_abs=[IP_PIK3CA]),
]
# [3] p6 Fig C — H1792 BEX2/siATG5/Rapamycin; [5] same layout in A549 (Fig A)
def atg_panel(cell):
    return [
        row("BEX2", cell, ATG6, ["absent", "present", "present", "absent", "present", "present"],
            None, "Rapamycin", f"{cell}: BEX2 overexpression ± siATG5 ± Rapamycin"),
        row("ATG12-ATG5", cell, ATG6,
            ["present", "present", "uncertain", "present", "present", "uncertain"],
            ["high", "high", "low", "high", "high", "low"], "Rapamycin",
            f"{cell}: siATG5 knockdown lanes show reduced ATG12-ATG5"),
        uniform("LC3B", cell, ATG6, conf="medium", tname="Rapamycin"),
        uniform("ACTB", cell, ATG6),
    ]
# [4] p7 Fig E — H1299 co-IP with IgG control: Input / IgG / IP:PIK3CA
COIP_E_LANES = ["Input", "IgG", "IP:PIK3CA"]
e7 = [
    row("PIK3CA", "H1299", COIP_E_LANES, ["present", "absent", "present"], None, "",
        "H1299 co-immunoprecipitation: IgG control lane vs anti-PIK3CA IP",
        extra_abs=[IP_PIK3CA]),
    row("BEX2", "H1299", COIP_E_LANES, ["present", "absent", "present"], None, "",
        "H1299 co-immunoprecipitation: BEX2 co-precipitates with PIK3CA, not with IgG",
        extra_abs=[IP_PIK3CA]),
]
# [6] p4 — H1792 + A549, DMSO/Rapamycin x BEX2-/+; BEX2 / P62 / LC3B / ACTB
RAPA4 = ["DMSO ctrl", "DMSO BEX2", "Rapamycin ctrl", "Rapamycin BEX2"]
def rapa_panel(cell):
    return [
        row("BEX2", cell, RAPA4, ["absent", "present", "absent", "present"], None,
            "Rapamycin", f"{cell} treated with DMSO or Rapamycin; ± BEX2 overexpression"),
        uniform("P62", cell, RAPA4, tname="Rapamycin"),
        # LC3B doublet independently confirmed "unmistakable" in this panel
        # (Fig 1C) by the QA re-inspection of the crop.
        _doublet(uniform("LC3B", cell, RAPA4, conf="medium", tname="Rapamycin")),
        uniform("ACTB", cell, RAPA4),
    ]
# [7] p6 Fig E — H1792 DMSO/BafA1 x BEX2-/+; BEX2 / LC3B / ACTB
e6 = [
    row("BEX2", "H1792", BAF4, ["absent", "present", "absent", "present"], None,
        "Bafilomycin A1", "H1792 treated with DMSO or BafA1; ± BEX2 overexpression"),
    uniform("LC3B", "H1792", BAF4, conf="medium", tname="Bafilomycin A1"),
    uniform("ACTB", "H1792", BAF4),
]
# [8] p10 Fig D — H1792 BEX2± / PIK3CA±
d10 = [
    row("BEX2", "H1792", BP4, ["absent", "present", "absent", "present"],
        ["high", "medium", "high", "high"], "", "H1792 transfected with BEX2 and/or PIK3CA"),
    uniform("PIK3CA", "H1792", BP4, conf="medium"),
    uniform("p-AKT (S473)", "H1792", BP4, conf="medium"),
    uniform("AKT", "H1792", BP4),
    uniform("LC3B", "H1792", BP4, conf="medium"),
    uniform("ACTB", "H1792", BP4),
]
# [9] p10 Fig A — H1299 siBEX2 / siPIK3CA
# (BEX2 doublet annotation REMOVED after independent QA: BEX2 runs as a single
# band everywhere else in this paper and the knockdown lanes are too faint to
# support a structure claim — abstention is the safe state.)
a10 = [
    row("BEX2", "H1299", SIP4, ["present", "uncertain", "present", "uncertain"],
        ["high", "low", "high", "low"], "", "H1299 transfected with siBEX2 and/or siPIK3CA"),
    uniform("PIK3CA", "H1299", SIP4, conf="medium"),
    uniform("p-AKT (S473)", "H1299", SIP4, conf="medium"),
    uniform("AKT", "H1299", SIP4),
    uniform("LC3B", "H1299", SIP4, conf="medium"),
    uniform("ACTB", "H1299", SIP4),
]
# [10] p9 Fig E — H1792 BEX2± / MYC-RHEB(Q64L)± ; mTOR pathway readouts
e9 = [
    row("BEX2", "H1792", RHEB4, ["absent", "present", "absent", "present"], None,
        "", "H1792 transfected with BEX2 and/or MYC-RHEB Q64L"),
    uniform("MYC", "H1792", RHEB4, conf="medium"),
    uniform("p-RPS6KB1 (T389)", "H1792", RHEB4, conf="medium"),
    uniform("RPS6KB1", "H1792", RHEB4),
    uniform("p-EIF4EBP1 (S65)", "H1792", RHEB4, conf="medium"),
    uniform("EIF4EBP1", "H1792", RHEB4),
    uniform("LC3B", "H1792", RHEB4, conf="medium"),
    uniform("ACTB", "H1792", RHEB4),
]

CAND_ROWS = {
    "page_007_cand_0045.png": g,
    "page_005_cand_0032.png": c5,
    "page_007_cand_0046.png": d7,
    "page_006_cand_0039.png": atg_panel("H1792"),
    "page_007_cand_0047.png": e7,
    "page_006_cand_0040.png": atg_panel("A549"),
    "page_004_cand_0025.png": rapa_panel("H1792") + rapa_panel("A549"),
    "page_006_cand_0037.png": e6,
    "page_010_cand_0060.png": d10,
    "page_010_cand_0062.png": a10,
    "page_009_cand_0055.png": e9,
    # negatives: cand_0054 (IF + chart), cand_0029 (bar chart),
    #            cand_0001 (BMC logo), cand_0031 (IF panels)
}

REQS = json.loads(Path(
    "/Users/niks/hive/western_blot_miner/data/pdf_runs/10.1186_s12964-025-02385-8/extraction_requests.json"
).read_text())

responses = []
for r in REQS:
    name = r["candidate_path"].split("/")[-1]
    responses.append({"candidate_path": r["candidate_path"],
                      "rows": CAND_ROWS.get(name, [])})

out = Path(__file__).parent.parent / "demo/coip_PMC12706926/responses_observed.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(responses, indent=2, ensure_ascii=False))
print("wrote", out)
print("WB panels:", sum(1 for r in responses if r["rows"]),
      "negatives:", sum(1 for r in responses if not r["rows"]),
      "rows:", sum(len(r["rows"]) for r in responses))
