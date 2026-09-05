"""Stage 2->3 integration via the mock LLM backend (no cloud, no keys).
Run: python3 test_extract_records.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from western_blot_miner.extract_records import extract_panel, records_to_supabase_rows  # noqa: E402
from western_blot_miner.llm_client import MockLLMClient  # noqa: E402
from western_blot_miner.resolve import LocalMapResolver  # noqa: E402

CHECKS = []


def check(n, c):
    CHECKS.append((n, bool(c)))


PANEL = {
    "paper": {"doi": "10.1000/mock", "pmcid": "PMC9"},
    "figure": {"figure_label": "Figure 3", "panel_label": "A", "page": 5},
    "texts": {
        "caption": "phospho-STAT3 (Tyr705) and total STAT3 in HEK293T after IL-6 (20 ng/mL, 30 min).",
        "methods": "anti-phospho-STAT3 (Tyr705) (CST #9145); anti-STAT3 (CST #4904).",
    },
}

# What a well-behaved model would emit for this panel (two rows: phospho + total).
MODEL_OUTPUT = {
    "rows": [
        {
            "raw_target": "phospho-STAT3",
            "sample": "HEK293T",
            "treatment_name": "IL-6",
            "treatment_context": "IL-6 20 ng/mL 30 min",
            "antibodies": [{"target": "phospho-STAT3 (Tyr705)", "vendor": "Cell Signaling",
                            "catalog": "9145", "role": "detection", "phospho_specific": True,
                            "source": {"type": "methods", "rank": 3, "text": "anti-phospho-STAT3 (Tyr705) (CST #9145)"}}],
            "bands": [{"lane_index": 1, "lane_condition": "IL-6", "band_state": "present", "confidence": "high"}],
        },
        {
            "raw_target": "STAT3",
            "sample": "HEK293T",
            "antibodies": [{"target": "STAT3", "vendor": "Cell Signaling", "catalog": "4904",
                            "role": "detection", "phospho_specific": False,
                            "source": {"type": "methods", "rank": 3, "text": "anti-STAT3 (CST #4904)"}}],
            "bands": [{"lane_index": 1, "lane_condition": "IL-6", "band_state": "present", "confidence": "high"}],
        },
    ]
}


def main():
    client = MockLLMClient(MODEL_OUTPUT)
    records = extract_panel(PANEL, image_data_url=None, client=client, resolver=LocalMapResolver())
    check("two records produced", len(records) == 2)

    by_target = {r.target.raw_target_name: r for r in records}
    pstat3 = by_target.get("phospho-STAT3")
    total = by_target.get("STAT3")

    # phospho row: modification supported, total row: NOT contaminated by caption's phospho mention
    check("phospho row -> phosphorylation", pstat3.modification.modification_type.value == "phosphorylation")
    check("phospho row -> Tyr705", pstat3.modification.residue.value == "Tyr"
          and pstat3.modification.residue_position.value == 705)
    check("total row stays total (no caption contamination)",
          total.modification.modification_type.value is None
          and total.modification.modification_type.status == "SUPPORTED")

    # supabase projection: conflicting/missing -> NULL scalars; band_detected preserved
    rows = records_to_supabase_rows(records)
    check("supabase rows produced", len(rows) == 2)
    prow = next(r for r in rows if r["raw_target_name"] == "phospho-STAT3")
    check("row carries canonical + uniprot", prow["canonical_target"] == "STAT3" and prow["uniprot_id"] == "P40763")
    check("row carries modification_label", prow["modification_label"] == "phospho-Tyr705")
    check("row preserves band_detected", prow["band_detected"] is True)
    check("row carries provenance JSON", isinstance(prow["provenance"], dict) and "modification" in prow["provenance"])
    check("extraction backend recorded as mock", prow["extraction_model"] == "mock")

    passed = sum(1 for _, ok in CHECKS if ok)
    failed = [n for n, ok in CHECKS if not ok]
    print(f"\n{passed}/{len(CHECKS)} extraction-integration checks passed")
    for n in failed:
        print("  FAIL:", n)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
