"""End-to-end check: a VLM extraction -> enriched Evidence Record rows.

Runs with `python3 test_loader_enrichment.py` (no network / no requests needed;
the requests import in supabase_loader is lazy).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from western_blot_miner import supabase_loader as sl  # noqa: E402

CHECKS: list[tuple[str, bool]] = []


def check(name, cond):
    CHECKS.append((name, bool(cond)))


# A realistic positive VLM extraction (shape matches vlm_extract.run_vlm_extraction).
VLM_OUTPUT = [
    {
        "paper_id": "10.1000/demo",
        "page": 5,
        "extraction": {
            "is_western_blot": True,
            "figure_label": "Figure 3",
            "figure_caption": "Immunoblot for phospho-STAT3 (Tyr705) and total STAT3 in "
            "HEK293T cells after IL-6 (20 ng/mL, 30 min). GAPDH loading control.",
            "cell_line_tissue": "HEK293T",
            "organism": "human",
            "treatment_context": "IL-6 20 ng/mL 30 min",
            "panels": [
                {
                    "panel_label": "A",
                    "targets_top_to_bottom": [
                        {"row_index": 1, "target": "phospho-STAT3", "is_loading_control": False, "confidence": "high"},
                        {"row_index": 2, "target": "STAT3", "is_loading_control": False, "confidence": "high"},
                        {"row_index": 3, "target": "GAPDH", "is_loading_control": True, "confidence": "high"},
                    ],
                    "lanes_left_to_right": [
                        {"lane_index": 1, "condition": "untreated", "confidence": "high"},
                        {"lane_index": 2, "condition": "IL-6 20 ng/mL 30 min", "confidence": "high"},
                    ],
                    "bands": [
                        {"row_index": 1, "target": "phospho-STAT3", "lane_index": 2, "band_state": "present", "confidence": "high"},
                        {"row_index": 1, "target": "phospho-STAT3", "lane_index": 1, "band_state": "absent", "confidence": "medium"},
                        {"row_index": 2, "target": "STAT3", "lane_index": 1, "band_state": "present", "confidence": "high"},
                        {"row_index": 3, "target": "GAPDH", "lane_index": 1, "band_state": "present", "confidence": "high"},
                    ],
                }
            ],
        },
    },
    {
        "paper_id": "10.1000/demo2",
        "page": 2,
        "extraction": {
            "is_western_blot": True,
            "figure_label": "Figure 1",
            "figure_caption": "STAT3 co-immunoprecipitated with EGFR. Input and IP blots shown.",
            "cell_line_tissue": "A549",
            "treatment_context": "",
            "targets_top_to_bottom": [{"row_index": 1, "target": "STAT3", "is_loading_control": False, "confidence": "medium"}],
            "lanes_left_to_right": [{"lane_index": 1, "condition": "IP: EGFR", "confidence": "medium"}],
            "bands": [{"row_index": 1, "target": "STAT3", "lane_index": 1, "band_state": "present", "confidence": "medium"}],
        },
    },
]


def find(rows, target, mod=None):
    for r in rows:
        if r["target"] == target and (mod is None or r["modification_type"] == mod):
            return r
    return None


def main():
    rows = sl.flatten_json(VLM_OUTPUT)
    check("produced rows", len(rows) == 5)

    pstat3 = find(rows, "phospho-STAT3")
    check("pSTAT3 -> phosphorylation", pstat3 and pstat3["modification_type"] == "phosphorylation")
    check("pSTAT3 -> Tyr705", pstat3 and pstat3["residue"] == "Tyr" and pstat3["residue_position"] == 705)
    check("pSTAT3 -> label phospho-Tyr705", pstat3 and pstat3["modification_label"] == "phospho-Tyr705")
    check("pSTAT3 -> canonical STAT3", pstat3 and pstat3["canonical_target"] == "STAT3")
    check("pSTAT3 -> UniProt P40763", pstat3 and pstat3["uniprot_id"] == "P40763")
    check("pSTAT3 -> experiment phospho_western", pstat3 and pstat3["experiment_type"] == "phospho_western")
    check("pSTAT3 -> legacy phospho_signaling", pstat3 and pstat3["western_blot_type"] == "phospho_signaling")
    check("pSTAT3 -> dose 20 ng/mL parsed", pstat3 and pstat3["dose"] == 20.0 and pstat3["dose_unit"].lower() == "ng/ml")
    check("pSTAT3 -> duration 30 min parsed", pstat3 and pstat3["duration"] == 30.0)

    total_stat3 = find(rows, "STAT3", mod=None)
    check("total STAT3 -> NOT phospho", total_stat3 and total_stat3["modification_type"] is None)
    check("total STAT3 -> standard_western", total_stat3 and total_stat3["experiment_type"] == "standard_western")

    gapdh = find(rows, "GAPDH")
    check("GAPDH -> loading_control experiment", gapdh and gapdh["experiment_type"] == "loading_control")
    check("GAPDH -> loading_control flag", gapdh and gapdh["loading_control"] is True)

    coip = find(rows, "STAT3")  # from paper 2 (co-IP), may also match paper1 total; check any co_ip row
    coip_rows = [r for r in rows if r["experiment_type"] == "co_ip"]
    check("co-IP row detected from text", len(coip_rows) == 1)
    check("co-IP row has needs_review or evidence", coip_rows and "provenance" in coip_rows[0])

    # Nothing invented: reported MW absent here -> None, not fabricated
    check("no fabricated MW", all(r["reported_molecular_weight_kda"] is None for r in rows))
    # band_detected preserved for legacy frontend
    check("band_detected preserved", find(rows, "GAPDH")["band_detected"] is True)

    passed = sum(1 for _, ok in CHECKS if ok)
    failed = [n for n, ok in CHECKS if not ok]
    print(f"\n{passed}/{len(CHECKS)} enrichment checks passed")
    if failed:
        print("FAILED:")
        for n in failed:
            print("  -", n)
        # dump a sample row for debugging
        import json
        print("\nSample pSTAT3 row:")
        print(json.dumps(pstat3, indent=2, default=str))
        return 1
    print("Enrichment pipeline works end-to-end.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
