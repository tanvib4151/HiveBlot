"""Wiring test: pipeline.run_records_stage over pre-computed OpenCV candidates,
using the mock model backend. Exercises the new ingestion path without needing
PyMuPDF / OpenCV / Pillow / network / cloud creds.
Run: python3 test_pipeline_records.py
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from western_blot_miner.pipeline import run_records_stage  # noqa: E402
from western_blot_miner.llm_client import MockLLMClient  # noqa: E402
from western_blot_miner.resolve import LocalMapResolver  # noqa: E402

CHECKS = []


def check(n, c):
    CHECKS.append((n, bool(c)))


MODEL_OUTPUT = {
    "rows": [
        {"raw_target": "phospho-STAT3", "sample": "HEK293T", "treatment_name": "IL-6",
         "treatment_context": "IL-6 20 ng/mL 30 min",
         "antibodies": [{"target": "phospho-STAT3 (Tyr705)", "vendor": "Cell Signaling",
                         "catalog": "9145", "role": "detection", "phospho_specific": True,
                         "source": {"type": "methods", "rank": 3, "text": "anti-phospho-STAT3 (Tyr705) (CST #9145)"}}],
         "bands": [{"lane_index": 1, "lane_condition": "IL-6", "band_state": "present", "confidence": "high"}]},
        {"raw_target": "STAT3", "sample": "HEK293T",
         "antibodies": [{"target": "STAT3", "vendor": "Cell Signaling", "catalog": "4904",
                         "role": "detection", "phospho_specific": False,
                         "source": {"type": "methods", "rank": 3, "text": "anti-STAT3 (CST #4904)"}}],
         "bands": [{"lane_index": 1, "lane_condition": "IL-6", "band_state": "present", "confidence": "high"}]},
    ]
}


def main():
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        crop = run_dir / "page_005_cand_0001.png"  # intentionally absent -> image_url=None
        candidates = [{"paper_id": "10.1000/x", "page": 5, "candidate_path": str(crop), "cv_score": 0.82}]
        (run_dir / "llm_candidates.json").write_text(json.dumps(candidates))
        (run_dir / "candidate_contexts.jsonl").write_text(json.dumps({
            "candidate_path": str(crop), "page": 5,
            "text_context": "phospho-STAT3 (Tyr705) and total STAT3 in HEK293T; "
                            "anti-phospho-STAT3 (Tyr705) (CST #9145); anti-STAT3 (CST #4904)."}) + "\n")
        summary = {"out_dir": str(run_dir), "paper_id": "10.1000/x", "extracted_doi": "10.1000/x"}

        result = run_records_stage(summary, use_cache=False,
                                   client=MockLLMClient(MODEL_OUTPUT), resolver=LocalMapResolver())

        check("2 records produced", result["records"] == 2)
        check("0 failures", result["failures"] == 0)
        check("evidence_records.json written", (run_dir / "evidence_records.json").exists())
        check("supabase_rows.json written", (run_dir / "supabase_rows.json").exists())

        recs = json.loads((run_dir / "evidence_records.json").read_text())
        targets = {r["target"]["raw_target_name"] for r in recs}
        check("both targets present", targets == {"phospho-STAT3", "STAT3"})

        rows = json.loads((run_dir / "supabase_rows.json").read_text())
        prow = next(r for r in rows if r["raw_target_name"] == "phospho-STAT3")
        check("row canonical STAT3", prow["canonical_target"] == "STAT3")
        check("row uniprot P40763", prow["uniprot_id"] == "P40763")
        check("row modification_label", prow["modification_label"] == "phospho-Tyr705")
        check("row image_crop_ref set", prow["image_crop_ref"] == str(crop))

        # resume: re-run with cache should query 0 new candidates
        result2 = run_records_stage(summary, use_cache=True,
                                    client=MockLLMClient(MODEL_OUTPUT), resolver=LocalMapResolver())
        check("resume queries 0", result2["queried"] == 0)
        check("resume still 2 records", result2["records"] == 2)

    passed = sum(1 for _, ok in CHECKS if ok)
    failed = [n for n, ok in CHECKS if not ok]
    print(f"\n{passed}/{len(CHECKS)} pipeline-wiring checks passed")
    for n in failed:
        print("  FAIL:", n)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
