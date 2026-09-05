"""Agent-observed Stage-2 rows for standard_PMC9559174 (Liu et al. 2022,
IJMM, DOI 10.3892/ijmm.2022.5188) — mouse SMG loading-control validation.

Figure 5: Western blots of ubiquitin / TUBA1B / GAPDH / ACTB across SMG
development (A: E14.5..P0; B: P0..P112) and duct ligation/de-ligation (C).
All targets are TOTAL protein (no modification). Organism: mouse (explicit).
Antibodies (Methods, verbatim): anti-ubiquitin 1:400 cat 20200728 Yurogen
Biosystems; anti-TUBA1B 1:100,000 ab108629 Abcam; anti-GAPDH 1:1,000 5174s
CST; anti-ACTB 1:1,000 8457s CST.

Candidate order (extraction_requests.json):
 0 p11 cand_0057  Fig5C-left  ligation (L5d Ctrl, L5d, L7d Ctrl, L7d)     WB
 1 p11 cand_0063  Fig5A       embryonic E14.5..P0 (6 lanes)              WB
 2 p11 cand_0060  Fig5B-late  P28F..P112M (8 lanes)                      WB
 3 p11 cand_0062  Fig5B-early P0..P28M (5 lanes)                         WB
 4 p11 cand_0058  Fig5C-right deligation L7dCtrl..DL28d (8 lanes)        WB
 5-18 legends / bar charts / qPCR dot plots / venns / micrographs / logo  NOT WB
"""
import json
from pathlib import Path

AB = {
    "Ubiquitin": dict(vendor="Yurogen Biosystems", catalog="20200728", dil="1:400",
        text="anti-ubiquitin (1:400 dilution; cat. no. 20200728, Yurogen Biosystems LLC)"),
    "TUBA1B": dict(vendor="Abcam", catalog="ab108629", dil="1:100,000",
        text="rabbit anti-TUBA1B (1:100,000 dilution; cat. no. ab108629, Abcam)"),
    "GAPDH": dict(vendor="Cell Signaling Technology", catalog="5174s", dil="1:1,000",
        text="rabbit anti-GAPDH (1:1,000 dilution; cat. no. 5174s, Cell Signaling Technology, Inc.)"),
    "ACTB": dict(vendor="Cell Signaling Technology", catalog="8457s", dil="1:1,000",
        text="rabbit anti-ACTB (1:1,000 dilution; cat. no. 8457s, Cell Signaling Technology, Inc.)"),
}

SAMPLE = "mouse submandibular gland (SMG) tissue"


def row(target, lanes, states=None, confs=None):
    a = AB[target]
    n = len(lanes)
    states = states or ["present"] * n
    confs = confs or ["high"] * n
    return {
        "raw_target": target,
        "sample": SAMPLE,
        "organism": "mouse",
        "treatment_name": "",
        "treatment_context": "",
        "aliases": [],
        "antibodies": [{
            "target": target, "vendor": a["vendor"], "catalog": a["catalog"],
            "clone": "", "dilution": a["dil"], "role": "detection",
            "phospho_specific": False,
            "source": {"type": "methods", "rank": 3, "text": a["text"]},
        }],
        "bands": [{"lane_index": i + 1, "lane_condition": c, "band_state": s,
                   "confidence": cf}
                  for i, (c, s, cf) in enumerate(zip(lanes, states, confs))],
    }


L_5C = ["L5d Ctrl", "L5d", "L7d Ctrl", "L7d"]
L_5A = ["E14.5", "E15.5", "E16.5", "E17.5", "E18.5", "P0"]
L_5B_LATE = ["P28F", "P28M", "P56F", "P56M", "P84F", "P84M", "P112F", "P112M"]
L_5B_EARLY = ["P0", "P7", "P14", "P25F", "P28M"]
L_5C_R = ["L7d Ctrl", "L7d", "DL7d Ctrl", "DL7d", "DL14d Ctrl", "DL14d", "DL28d Ctrl", "DL28d"]

fig5c_left = [
    # Ubiquitin strong in Ctrl lanes, faint in ligated lanes.
    row("Ubiquitin", L_5C, ["present", "uncertain", "present", "uncertain"],
        ["high", "low", "high", "low"]),
    row("TUBA1B", L_5C),
    row("GAPDH", L_5C),
    row("ACTB", L_5C),
]
fig5a = [
    row("Ubiquitin", L_5A),
    row("TUBA1B", L_5A),
    row("GAPDH", L_5A),
    row("ACTB", L_5A),
]
fig5b_late = [
    # Ubiquitin/TUBA1B visibly variable across P56M/P84M/P112M (faint) —
    # exactly why the paper concludes they are poor loading controls here.
    row("Ubiquitin", L_5B_LATE,
        ["present", "present", "present", "uncertain", "uncertain", "uncertain", "present", "absent"],
        ["high", "high", "high", "low", "low", "low", "medium", "medium"]),
    row("TUBA1B", L_5B_LATE,
        ["present", "present", "present", "uncertain", "present", "uncertain", "present", "uncertain"],
        ["high", "high", "high", "low", "high", "low", "high", "low"]),
    row("GAPDH", L_5B_LATE),
    row("ACTB", L_5B_LATE),
]
fig5b_early = [
    row("Ubiquitin", L_5B_EARLY, confs=["medium"] * 5),
    row("TUBA1B", L_5B_EARLY),
    row("GAPDH", L_5B_EARLY),
    row("ACTB", L_5B_EARLY),
]
fig5c_right = [
    row("Ubiquitin", L_5C_R),
    row("TUBA1B", L_5C_R),
    row("GAPDH", L_5C_R),
    row("ACTB", L_5C_R),
]

CAND_ROWS = {
    "page_011_cand_0057.png": fig5c_left,
    "page_011_cand_0063.png": fig5a,
    "page_011_cand_0060.png": fig5b_late,
    "page_011_cand_0062.png": fig5b_early,
    "page_011_cand_0058.png": fig5c_right,
}

REQS = json.loads(Path(
    "/Users/niks/hive/western_blot_miner/data/pdf_runs/10.3892_ijmm.2022.5188/extraction_requests.json"
).read_text())

responses = []
for r in REQS:
    name = r["candidate_path"].split("/")[-1]
    responses.append({"candidate_path": r["candidate_path"],
                      "rows": CAND_ROWS.get(name, [])})

out = Path(__file__).parent.parent / "demo/standard_PMC9559174/responses_observed.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(responses, indent=2, ensure_ascii=False))
print("wrote", out)
print("WB panels:", sum(1 for r in responses if r["rows"]),
      "negatives:", sum(1 for r in responses if not r["rows"]),
      "rows:", sum(len(r["rows"]) for r in responses))
