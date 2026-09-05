"""Locks in the reconciliation contract, especially adjustment 1:
CONFLICTING fields store NO settled value and preserve competing candidates.
Run: python3 test_reconcile.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from western_blot_miner.evidence_record import CONFLICTING, SUPPORTED, MISSING, AMBIGUOUS  # noqa: E402
from western_blot_miner.reconcile import (  # noqa: E402
    Claim,
    ModClaim,
    reconcile_field,
    reconcile_modification,
)

CHECKS = []


def check(name, cond):
    CHECKS.append((name, bool(cond)))


def test_agreement_supported():
    f = reconcile_field([
        Claim("HEK293T", "figure_caption", 2, 0.9, "HEK293T cells"),
        Claim("hek293t", "methods", 3, 0.7, "HEK293T lysate"),
    ])
    check("agreement -> SUPPORTED", f.status == SUPPORTED)
    check("agreement keeps value", f.value == "HEK293T")
    check("agreement merges sources", len(f.sources) == 2)


def test_missing():
    f = reconcile_field([Claim(None, "model_target", 4, 0.5)])
    check("no value -> MISSING", f.status == MISSING and f.value is None)


def test_conflict_has_no_settled_value():
    f = reconcile_field([
        Claim("HeLa", "figure_caption", 2, 0.8, "HeLa"),
        Claim("A549", "model_target", 4, 0.6, "A549"),
    ])
    check("conflict -> CONFLICTING", f.status == CONFLICTING)
    check("conflict value is None (adjustment 1)", f.value is None)
    check("conflict preserves both candidates", len(f.candidates) == 2)
    check("candidates carry evidence", all(c.evidence for c in f.candidates))


def test_modification_phospho_vs_total_conflicts():
    # antibody + caption say phospho Tyr705; model row says total -> CONFLICT
    fields = reconcile_modification([
        ModClaim("phosphorylation", "Tyr", 705, "antibody", 1, 0.9, "anti-phospho-STAT3 (Tyr705)"),
        ModClaim("phosphorylation", None, None, "figure_caption", 2, 0.7, "pSTAT3"),
        ModClaim(None, None, None, "model_target", 4, 0.5, "STAT3"),
    ])
    mt = fields["modification_type"]
    check("mod conflict -> CONFLICTING", mt.status == CONFLICTING)
    check("mod conflict value None", mt.value is None)
    vals = sorted(str(c.value) for c in mt.candidates)
    check("candidates are phospho + none", "none" in vals and any("phospho" in v for v in vals))
    check("residue not asserted as settled while disputed", fields["residue"].status != SUPPORTED)


def test_modification_all_phospho_merges_site():
    fields = reconcile_modification([
        ModClaim("phosphorylation", "Tyr", 705, "antibody", 1, 0.9, "anti-phospho-STAT3 (Tyr705)"),
        ModClaim("phosphorylation", None, None, "model_target", 4, 0.5, "phospho-STAT3"),
    ])
    check("all phospho -> SUPPORTED", fields["modification_type"].status == SUPPORTED)
    check("site merged Tyr", fields["residue"].value == "Tyr")
    check("site merged 705", fields["residue_position"].value == 705)


def test_modification_all_total():
    fields = reconcile_modification([
        ModClaim(None, None, None, "antibody", 1, 0.9, "anti-STAT3"),
        ModClaim(None, None, None, "model_target", 4, 0.5, "STAT3"),
    ])
    mt = fields["modification_type"]
    check("all total -> SUPPORTED", mt.status == SUPPORTED)
    check("total value is None(=total)", mt.value is None)
    check("total label", fields["normalized_label"].value == "total")


def test_different_sites_conflict():
    fields = reconcile_modification([
        ModClaim("phosphorylation", "Tyr", 705, "antibody", 1, 0.9, "Tyr705"),
        ModClaim("phosphorylation", "Ser", 727, "figure_caption", 2, 0.7, "Ser727"),
    ])
    check("phospho type still supported", fields["modification_type"].status == SUPPORTED)
    check("different sites -> residue CONFLICTING", fields["residue"].status == CONFLICTING)
    check("residue conflict value None", fields["residue"].value is None)


def run():
    for k, v in sorted(globals().items()):
        if k.startswith("test_") and callable(v):
            v()
    passed = sum(1 for _, ok in CHECKS if ok)
    failed = [n for n, ok in CHECKS if not ok]
    print(f"\n{passed}/{len(CHECKS)} reconciliation checks passed")
    for n in failed:
        print("  FAIL:", n)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(run())
