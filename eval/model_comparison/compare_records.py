#!/usr/bin/env python3
"""Field-level comparison of automated Evidence Record extraction against the
human-reviewed reference set. Model-independent and credential-independent:
it compares two evidence_records.json files, whoever produced them.

Usage:
    python eval/model_comparison/compare_records.py predicted.json reference.json
    python eval/model_comparison/compare_records.py --self-test

Scoring per field:
    EXACT        identical after trivial normalization
    ACCEPTABLE   semantically equivalent (vendor synonyms, catalog formatting,
                 unit spelling, case) — rules below, per field
    PARTIAL      overlapping but incomplete (e.g. right residue, no position)
    WRONG        reference has a value, prediction has a DIFFERENT value
    MISSING      reference has a value, prediction has none
    HALLUCINATED reference has NO value, prediction asserts one
Unmatched whole records count as MISSING (reference-only) or HALLUCINATED
(prediction-only). Hallucination is weighted MORE severely than omission in
the aggregate trust score: a fabricated value misleads; a gap merely
underinforms. Never quote the aggregate as global model accuracy — it is
3 reviewed papers, not a benchmark.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

# Aggregate penalty weights (trust-weighted, hallucination worst).
WEIGHTS = {"EXACT": 1.0, "ACCEPTABLE": 1.0, "PARTIAL": 0.5,
           "WRONG": 0.0, "MISSING": 0.0, "HALLUCINATED": -1.0}

VENDOR_SYNONYMS = {
    "cst": "cell signaling technology",
    "cell signaling": "cell signaling technology",
    "cell signaling technology, inc.": "cell signaling technology",
    "santa cruz": "santa cruz biotechnology",
    "sigma": "sigma-aldrich",
}


def _norm_str(v) -> str:
    return re.sub(r"\s+", " ", str(v)).strip().lower() if v is not None else ""


def _norm_vendor(v) -> str:
    s = _norm_str(v)
    return VENDOR_SYNONYMS.get(s, s)


def _norm_catalog(v) -> str:
    # '#9145' == '9145' == '9145S' == 'sc-398486' vs 'SC- 398486'
    return re.sub(r"[^a-z0-9]", "", _norm_str(v)).rstrip("s")


def _norm_unit(v) -> str:
    s = _norm_str(v).replace("µ", "u").replace("μ", "u")
    return {"minutes": "min", "minute": "min", "hours": "h", "hour": "h",
            "hr": "h", "seconds": "s"}.get(s, s)


def _fv(record: dict, path: list[str]):
    """Value of an Evidence Field envelope at a path inside a record dict."""
    obj = record
    for k in path:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(k)
    if isinstance(obj, dict) and "value" in obj:
        return obj["value"]
    return obj


def _fstatus(record: dict, path: list[str]):
    obj = record
    for k in path:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(k)
    return obj.get("status") if isinstance(obj, dict) else None


def _first_ab(record: dict, key: str, role: str = "detection"):
    for ab in record.get("antibodies", []) or []:
        if ab.get("role", "detection") == role:
            return _fv(ab, [key])
    return None


# (field name, extractor, normalizer, partial-checker|None)
def _residue_partial(p, r):
    return bool(p) and bool(r) and _norm_str(p)[:3] == _norm_str(r)[:3]


FIELDS: list[tuple] = [
    ("raw_target", lambda r: r.get("target", {}).get("raw_target_name"), _norm_str, None),
    ("canonical_target", lambda r: _fv(r, ["target", "canonical_target"]), _norm_str, None),
    ("uniprot_id", lambda r: _fv(r, ["target", "uniprot_id"]), _norm_str, None),
    ("modification_type", lambda r: _fv(r, ["modification", "modification_type"]), _norm_str, None),
    ("residue", lambda r: _fv(r, ["modification", "residue"]), _norm_str, _residue_partial),
    ("residue_position", lambda r: _fv(r, ["modification", "residue_position"]), _norm_str, None),
    ("experiment_type", lambda r: _fv(r, ["experiment", "experiment_type"]), _norm_str, None),
    ("ip_bait", lambda r: _fv(r, ["experiment", "ip_bait_protein"]), _norm_str, None),
    ("cell_line", lambda r: _fv(r, ["sample", "cell_line"]), _norm_str, None),
    ("organism", lambda r: _fv(r, ["sample", "organism"]), _norm_str, None),
    ("treatment_name", lambda r: _fv(r, ["treatment", "treatment_name"]), _norm_str, None),
    ("dose", lambda r: _fv(r, ["treatment", "dose"]), _norm_str, None),
    ("dose_unit", lambda r: _fv(r, ["treatment", "dose_unit"]), _norm_unit, None),
    ("duration", lambda r: _fv(r, ["treatment", "duration"]), _norm_str, None),
    ("duration_unit", lambda r: _fv(r, ["treatment", "duration_unit"]), _norm_unit, None),
    ("antibody_target", lambda r: _first_ab(r, "antibody_target"), _norm_str, None),
    ("antibody_vendor", lambda r: _first_ab(r, "vendor"), _norm_vendor, None),
    ("antibody_catalog", lambda r: _first_ab(r, "catalog_number"), _norm_catalog, None),
    ("ip_antibody_target", lambda r: _first_ab(r, "antibody_target", role="immunoprecipitation"), _norm_str, None),
    ("reported_mw", lambda r: _fv(r, ["molecular_weight", "reported_kda"]), _norm_str, None),
    ("expected_mw", lambda r: _fv(r, ["molecular_weight", "expected_kda"]), _norm_str, None),
    ("needs_review", lambda r: (r.get("validation") or {}).get("needs_review"), _norm_str, None),
    ("modification_status", lambda r: _fstatus(r, ["modification", "modification_type"]), _norm_str, None),
]


def band_states(record: dict) -> list[tuple]:
    out = []
    for b in record.get("bands", []) or []:
        out.append((_norm_str(_fv(b, ["lane_condition"])), _norm_str(_fv(b, ["band_state"]))))
    return out


def record_key(record: dict) -> tuple:
    crop = record.get("figure", {}).get("image_crop_ref") or ""
    return (Path(str(crop)).name, _norm_str(record.get("target", {}).get("raw_target_name")))


def score_field(pred, ref, norm, partial) -> str:
    p, r = norm(pred), norm(ref)
    if not r and not p:
        return "EXACT"          # both silent — agreement on absence
    if r and not p:
        return "MISSING"
    if not r and p:
        return "HALLUCINATED"
    if p == r:
        return "EXACT" if _norm_str(pred) == _norm_str(ref) else "ACCEPTABLE"
    if partial and partial(pred, ref):
        return "PARTIAL"
    return "WRONG"


def compare(pred_records: list[dict], ref_records: list[dict]) -> dict:
    pred_by, ref_by = {}, {}
    for r in pred_records:
        pred_by.setdefault(record_key(r), []).append(r)
    for r in ref_records:
        ref_by.setdefault(record_key(r), []).append(r)

    per_field: dict[str, Counter] = {name: Counter() for name, *_ in FIELDS}
    per_field["band_state"] = Counter()
    unmatched_ref = 0
    unmatched_pred = 0

    for key, refs in ref_by.items():
        preds = pred_by.get(key, [])
        for i, ref in enumerate(refs):
            if i >= len(preds):
                unmatched_ref += 1
                continue
            pred = preds[i]
            for name, get, norm, partial in FIELDS:
                per_field[name][score_field(get(pred), get(ref), norm, partial)] += 1
            # bands: align by lane_condition
            ref_bands = dict(band_states(ref))
            pred_bands = dict(band_states(pred))
            for cond, state in ref_bands.items():
                p = pred_bands.get(cond)
                per_field["band_state"]["MISSING" if p is None else
                                        "EXACT" if p == state else "WRONG"] += 1
            for cond in pred_bands:
                if cond not in ref_bands:
                    per_field["band_state"]["HALLUCINATED"] += 1
    for key, preds in pred_by.items():
        extra = len(preds) - len(ref_by.get(key, []))
        if extra > 0:
            unmatched_pred += extra

    totals = Counter()
    for c in per_field.values():
        totals.update(c)
    n = sum(totals.values()) or 1
    trust = sum(WEIGHTS[k] * v for k, v in totals.items()) / n
    return {
        "per_field": {k: dict(v) for k, v in per_field.items()},
        "totals": dict(totals),
        "unmatched_reference_records (MISSING records)": unmatched_ref,
        "unmatched_predicted_records (HALLUCINATED records)": unmatched_pred,
        "trust_weighted_score": round(trust, 4),
        "note": "3-paper reviewed reference set — NOT a global accuracy metric",
    }


def print_report(rep: dict) -> None:
    cats = ["EXACT", "ACCEPTABLE", "PARTIAL", "WRONG", "MISSING", "HALLUCINATED"]
    print(f"{'FIELD':26} " + " ".join(f"{c:>12}" for c in cats))
    for field, counts in rep["per_field"].items():
        if not counts:
            continue
        print(f"{field:26} " + " ".join(f"{counts.get(c, 0):>12}" for c in cats))
    print("-" * 105)
    t = rep["totals"]
    print(f"{'TOTAL':26} " + " ".join(f"{t.get(c, 0):>12}" for c in cats))
    print(f"unmatched ref records (MISSING): {rep['unmatched_reference_records (MISSING records)']}"
          f" | unmatched predicted (HALLUCINATED): {rep['unmatched_predicted_records (HALLUCINATED records)']}")
    print(f"trust-weighted score: {rep['trust_weighted_score']}  ({rep['note']})")


def main() -> int:
    args = sys.argv[1:]
    if args == ["--self-test"]:
        base = Path(__file__).resolve().parents[1] / "demo"
        ok = True
        for paper in sorted(p.name for p in base.iterdir() if (p / "evidence_records.json").exists()):
            recs = json.loads((base / paper / "evidence_records.json").read_text())
            rep = compare(recs, recs)
            t = rep["totals"]
            clean = (t.get("WRONG", 0) == t.get("MISSING", 0) ==
                     t.get("HALLUCINATED", 0) == t.get("PARTIAL", 0) == 0)
            print(f"self-test {paper}: {'PASS' if clean else 'FAIL'} "
                  f"({t.get('EXACT', 0)} EXACT, score={rep['trust_weighted_score']})")
            ok = ok and clean
        return 0 if ok else 1
    if len(args) != 2:
        print(__doc__)
        return 1
    pred = json.loads(Path(args[0]).read_text())
    ref = json.loads(Path(args[1]).read_text())
    rep = compare(pred, ref)
    print_report(rep)
    out = Path(args[0]).with_suffix(".comparison.json")
    out.write_text(json.dumps(rep, indent=2))
    print(f"\nreport written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
