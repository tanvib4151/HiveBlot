"""HiveBlot biological benchmark scorer.

Runs the deterministic + reconciliation pipeline (build_evidence_record) over
the curated cases, serializes each EvidenceRecord to eval/out/, and scores
important fields against the gold labels. Uses the offline LocalMapResolver so
it runs with no network and no model keys.

    python3 eval/score.py            # score + write serialized records
    python3 eval/score.py --dump A   # print full serialized record for a case id prefix

This is a SEED harness: the 4 gold cases are the Phase-3 worked examples,
reviewed by the implementer only. Do NOT quote these numbers as validated
accuracy until wet-lab annotation expands the gold set (target 10-20 cases).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from western_blot_miner.record_builder import build_evidence_record  # noqa: E402
from western_blot_miner.resolve import LocalMapResolver  # noqa: E402

EVAL = Path(__file__).resolve().parent
OUT = EVAL / "out"

IMPORTANT_FIELDS = [
    "canonical_target", "uniprot_id", "modification_type", "residue", "residue_position",
    "experiment_type", "ip_bait_protein", "cell_line", "treatment_name",
    "antibody_vendor", "antibody_catalog_number", "reported_kda", "band_state",
]


def detection_ab(rec):
    for a in rec.antibodies:
        if a.role == "detection":
            return a
    return rec.antibodies[0] if rec.antibodies else None


def field_view(rec, name):
    """Return (value, status) for an important field name."""
    ab = detection_ab(rec)
    m = {
        "canonical_target": (rec.target.canonical_target.value, rec.target.canonical_target.status),
        "uniprot_id": (rec.target.uniprot_id.value, rec.target.uniprot_id.status),
        "modification_type": (rec.modification.modification_type.value, rec.modification.modification_type.status),
        "residue": (rec.modification.residue.value, rec.modification.residue.status),
        "residue_position": (rec.modification.residue_position.value, rec.modification.residue_position.status),
        "experiment_type": (rec.experiment.experiment_type.value, rec.experiment.experiment_type.status),
        "ip_bait_protein": (rec.experiment.ip_bait_protein.value, rec.experiment.ip_bait_protein.status),
        "cell_line": (rec.sample.cell_line.value, rec.sample.cell_line.status),
        "treatment_name": (rec.treatment.treatment_name.value, rec.treatment.treatment_name.status),
        "antibody_vendor": (ab.vendor.value if ab else None, ab.vendor.status if ab else "MISSING"),
        "antibody_catalog_number": (ab.catalog_number.value if ab else None,
                                    ab.catalog_number.status if ab else "MISSING"),
        "reported_kda": (rec.molecular_weight.reported_kda.value, rec.molecular_weight.reported_kda.status),
        "band_state": (rec.bands[0].band_state.value if rec.bands else None,
                       rec.bands[0].band_state.status if rec.bands else "MISSING"),
    }
    return m.get(name, (None, "MISSING"))


def norm(v):
    return v.strip().lower() if isinstance(v, str) else v


def match(got, gold):
    gv, gs = got
    ok_val = True
    ok_status = True
    if "value" in gold:
        ok_val = norm(gv) == norm(gold["value"])
    if "status" in gold:
        ok_status = gs == gold["status"]
    return ok_val and ok_status


def main():
    dump_prefix = None
    if "--dump" in sys.argv:
        i = sys.argv.index("--dump")
        dump_prefix = sys.argv[i + 1] if i + 1 < len(sys.argv) else ""

    cases = json.loads((EVAL / "cases.json").read_text())
    gold = json.loads((EVAL / "gold.json").read_text())
    OUT.mkdir(exist_ok=True)
    resolver = LocalMapResolver()

    total_fields = 0
    total_ok = 0
    case_status_ok = 0
    print("=" * 78)
    print("HiveBlot biological benchmark (SEED — awaiting wet-lab annotation)")
    print("=" * 78)

    for case in cases:
        cid = case["id"]
        rec = build_evidence_record(case, resolver=resolver)
        serialized = rec.model_dump(mode="json")
        (OUT / f"{cid}.json").write_text(json.dumps(serialized, indent=2))

        if dump_prefix is not None and cid.startswith(dump_prefix):
            print(json.dumps(serialized, indent=2))
            continue

        g = gold.get(cid, {})
        print(f"\n[{cid}]  record_status={rec.validation.record_status}  "
              f"needs_review={rec.validation.needs_review}")
        anomalies = [a.code for a in rec.validation.anomaly_flags]
        if anomalies:
            print(f"   anomalies: {', '.join(anomalies)}")

        for fname in IMPORTANT_FIELDS:
            if fname not in g:
                continue
            got = field_view(rec, fname)
            ok = match(got, g[fname])
            total_fields += 1
            total_ok += int(ok)
            mark = "OK " if ok else "XX "
            print(f"   {mark} {fname:24s} got={_fmt(got)}  gold={g[fname]}")

        # record status + expected anomaly
        if "record_status" in g:
            rs_ok = rec.validation.record_status == g["record_status"]
            case_status_ok += int(rs_ok)
            print(f"   {'OK ' if rs_ok else 'XX '} record_status            "
                  f"got={rec.validation.record_status}  gold={g['record_status']}")
        if "expect_anomaly" in g:
            a_ok = g["expect_anomaly"] in anomalies
            print(f"   {'OK ' if a_ok else 'XX '} expect_anomaly           "
                  f"got={anomalies}  gold={g['expect_anomaly']}")

    if dump_prefix is not None:
        return 0

    print("\n" + "-" * 78)
    print(f"Field-level accuracy: {total_ok}/{total_fields} "
          f"({100 * total_ok / max(total_fields, 1):.0f}%)  across {len(cases)} seed cases")
    print(f"Serialized records written to: {OUT}")
    print("NOTE: seed benchmark. Expand gold set with wet-lab review before quoting accuracy.")
    return 0 if total_ok == total_fields else 1


def _fmt(got):
    v, s = got
    return f"({v!r}, {s})"


if __name__ == "__main__":
    raise SystemExit(main())
