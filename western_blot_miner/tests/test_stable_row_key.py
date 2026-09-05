"""Regression tests for the stable per-lane identity (`stable_row_key`).

Reproduces the P0 identity collision fixed in session 14 and pins the
properties the identity has to keep.

The defect: `_record_id` hashed paper + figure/panel + crop + raw target +
treatment context, but NOT the biological system. Crop
`page_004_cand_0025.png` in PMC12706926 prints H1792 and A549 side by side, so
P62, LC3B and ACTB each collapsed TWO biologically distinct experiments into
ONE id — 12 duplicate stable keys over 24 rows in the reviewed corpus.
Researcher feedback keys on `stable_row_key`, so a correction left on the
H1792 arm could rehydrate onto the A549 arm.

Run: python3 test_stable_row_key.py
"""
import copy
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from western_blot_miner.record_builder import _record_id, identity_sample  # noqa: E402

CHECKS = []


def check(n, c):
    CHECKS.append((n, bool(c)))


# The real collision, reduced to its inputs: one crop, one target, one
# treatment context, two cell lines.
COIP_CASE = {
    "paper": {"doi": "10.1186/s12964-025-02385-8", "pmcid": "PMC12706926"},
    "figure": {
        "figure_label": None,
        "panel_label": None,
        "image_crop_ref": ("/Users/niks/hive/western_blot_miner/data/pdf_runs/"
                           "10.1186_s12964-025-02385-8/panel_candidates/page_004_cand_0025.png"),
    },
    "model_claims": {
        "sample": "H1792",
        "cell_line": "H1792",
        "treatment_context": "DMSO or rapamycin, control vs BEX2 overexpression",
    },
}


def with_sample(case, sample):
    c = copy.deepcopy(case)
    c["model_claims"]["sample"] = sample
    c["model_claims"]["cell_line"] = sample
    return c


def stable_key(case, raw_target, lane_index):
    """Mirror of EvidenceRecord.to_supabase_rows()'s key construction."""
    return f"{_record_id(case, raw_target)}:{lane_index}"


def main():
    # --- A. biologically distinct twins get DIFFERENT keys -------------------
    # Same paper, same crop, same target, same treatment; different cell line.
    for target in ("P62", "LC3B", "ACTB"):
        a = with_sample(COIP_CASE, "H1792")
        b = with_sample(COIP_CASE, "A549")
        keys_a = {stable_key(a, target, i) for i in range(1, 5)}
        keys_b = {stable_key(b, target, i) for i in range(1, 5)}
        check(f"A: {target} H1792 vs A549 -> disjoint stable keys",
              keys_a.isdisjoint(keys_b) and len(keys_a) == 4 and len(keys_b) == 4)

    # A record's own lanes must still be distinct from each other.
    a = with_sample(COIP_CASE, "H1792")
    check("A: four lanes of one experiment -> four distinct keys",
          len({stable_key(a, "P62", i) for i in range(1, 5)}) == 4)

    # ...and every lane of one experiment shares ONE experiment hash, which is
    # what the search UI groups a card by.
    check("A: lanes of one experiment share one experiment hash",
          len({stable_key(a, "P62", i).split(":")[0] for i in range(1, 5)}) == 1)

    # --- B. regeneration is deterministic ------------------------------------
    check("B: same inputs -> same key (reseed-stable)",
          stable_key(with_sample(COIP_CASE, "H1792"), "P62", 2)
          == stable_key(with_sample(COIP_CASE, "H1792"), "P62", 2))

    # A fresh dict built from scratch (as a re-run would) must agree.
    rebuilt = json.loads(json.dumps(with_sample(COIP_CASE, "H1792")))
    check("B: round-tripped case dict -> same key",
          stable_key(rebuilt, "P62", 2) == stable_key(with_sample(COIP_CASE, "H1792"), "P62", 2))

    # --- E. harmless display/formatting changes must NOT move the key --------
    spaced = with_sample(COIP_CASE, "  H1792  ")
    check("E: whitespace around the sample does not move the key",
          stable_key(spaced, "P62", 1) == stable_key(with_sample(COIP_CASE, "H1792"), "P62", 1))
    check("E: sample letter case does not move the key",
          stable_key(with_sample(COIP_CASE, "h1792"), "P62", 1)
          == stable_key(with_sample(COIP_CASE, "H1792"), "P62", 1))

    # Lane identity is the reviewed panel's index, never the printed condition
    # text — so the display-only lane formatter ("IL-6: + · CL-E: −") cannot
    # move a key. Changing lane_condition is not even an input here.
    reformatted = copy.deepcopy(with_sample(COIP_CASE, "H1792"))
    reformatted["model_claims"]["rows"] = [{"lane_condition": "IL-6: + · CL-E: −"}]
    check("E: lane-label reformatting does not move the key",
          stable_key(reformatted, "P62", 1) == stable_key(with_sample(COIP_CASE, "H1792"), "P62", 1))

    # Reconciliation OUTPUTS must not feed identity: if they did, every engine
    # improvement would orphan stored feedback.
    for field in ("modification_type", "modification_label", "experiment_type",
                  "ip_bait", "protein_status", "confidence", "needs_review"):
        mutated = copy.deepcopy(with_sample(COIP_CASE, "H1792"))
        mutated["model_claims"][field] = "CHANGED-BY-RECONCILIATION"
        check(f"E: reconciliation output `{field}` does not move the key",
              stable_key(mutated, "P62", 1) == stable_key(with_sample(COIP_CASE, "H1792"), "P62", 1))

    # DB serial ids are not an input at all (nothing to mutate) — assert the
    # identity function never reads one.
    serialed = copy.deepcopy(with_sample(COIP_CASE, "H1792"))
    serialed["model_claims"]["id"] = 4019
    check("E: a DB serial id does not move the key",
          stable_key(serialed, "P62", 1) == stable_key(with_sample(COIP_CASE, "H1792"), "P62", 1))

    # --- genuinely distinct evidence must still separate ---------------------
    other_target = stable_key(with_sample(COIP_CASE, "H1792"), "LC3B", 1)
    check("distinct target -> distinct key",
          other_target != stable_key(with_sample(COIP_CASE, "H1792"), "P62", 1))

    other_crop = copy.deepcopy(with_sample(COIP_CASE, "H1792"))
    other_crop["figure"]["image_crop_ref"] = other_crop["figure"]["image_crop_ref"].replace(
        "page_004_cand_0025", "page_005_cand_0032")
    check("distinct crop -> distinct key",
          stable_key(other_crop, "P62", 1) != stable_key(with_sample(COIP_CASE, "H1792"), "P62", 1))

    other_tx = copy.deepcopy(with_sample(COIP_CASE, "H1792"))
    other_tx["model_claims"]["treatment_context"] = "serum starvation, 24 h"
    check("distinct treatment context -> distinct key",
          stable_key(other_tx, "P62", 1) != stable_key(with_sample(COIP_CASE, "H1792"), "P62", 1))

    other_paper = copy.deepcopy(with_sample(COIP_CASE, "H1792"))
    other_paper["paper"]["doi"] = "10.3892/br.2026.2108"
    check("distinct paper -> distinct key",
          stable_key(other_paper, "P62", 1) != stable_key(with_sample(COIP_CASE, "H1792"), "P62", 1))

    # sample falls back to cell_line, matching _sample_info's precedence
    fallback = copy.deepcopy(COIP_CASE)
    fallback["model_claims"].pop("sample")
    fallback["model_claims"]["cell_line"] = "H1792"
    check("sample precedence matches _sample_info (sample or cell_line)",
          identity_sample(fallback["model_claims"]) == "h1792")
    check("absent sample normalizes to empty, not to a crash",
          identity_sample({}) == "")

    # --- corpus-wide: the reviewed reference set is collision-free -----------
    rows = []
    for f in sorted((REPO / "eval" / "demo").glob("*/supabase_rows.json")):
        rows += json.loads(f.read_text())
    keys = [r.get("stable_row_key") for r in rows]
    check("corpus: every reviewed row carries a stable key", all(keys))
    check(f"corpus: {len(keys)} rows -> {len(set(keys))} distinct keys (no collisions)",
          len(keys) == len(set(keys)))

    # the historically colliding trio, proven separated in the shipped corpus
    coip = json.loads((REPO / "eval" / "demo" / "coip_PMC12706926" / "supabase_rows.json").read_text())
    for target in ("P62", "LC3B", "ACTB"):
        twins = [r for r in coip if r.get("target") == target
                 and "page_004_cand_0025" in str(r.get("image_crop_ref"))]
        by_cell = {}
        for r in twins:
            by_cell.setdefault(r.get("cell_line"), set()).add(r["stable_row_key"].split(":")[0])
        hashes = [h for hs in by_cell.values() for h in hs]
        check(f"corpus: {target} H1792/A549 twins have distinct experiment hashes",
              len(by_cell) == 2 and len(set(hashes)) == 2)

    # --- collision class 2: the SAME flaw pointing the other way -------------
    # The old search-grouping key (paper|crop|target|experiment_type|cell_line|
    # modification_label) carried no treatment context, so on crop
    # page_005_cand_0034 — which holds TWO experiments, Fig 3C and Fig 3D — it
    # concatenated the 6-lane Fig 3C strip (no IL-6) and the 7-lane Fig 3D strip
    # (with IL-6) into ONE 13-lane card under a single identity line. That is
    # the conflation session 7's C1 finding was about. The identity hash always
    # separated them via treatment_context; grouping now reads that hash, so
    # the card boundary and the feedback boundary are the same thing.
    phospho = json.loads((REPO / "eval" / "demo" / "phospho_PMC12856536" / "supabase_rows.json").read_text())
    for target in ("T-Stat3", "\u03b2-actin"):
        strip = [r for r in phospho if r.get("target") == target
                 and "page_005_cand_0034" in str(r.get("image_crop_ref"))]
        hashes = {r["stable_row_key"].split(":")[0] for r in strip}
        by_hash = {}
        for r in strip:
            by_hash.setdefault(r["stable_row_key"].split(":")[0], []).append(r)
        sizes = sorted(len(v) for v in by_hash.values())
        check(f"corpus: {target} Fig 3C/3D on one crop -> 2 experiments, not 1",
              len(hashes) == 2 and sizes == [6, 7])
        # The scientific point of the split: Fig 3C ran WITHOUT IL-6 and Fig 3D
        # WITH it. One experiment must therefore have no IL-6 lane at all while
        # the other does. (A control lane inside the IL-6 experiment is normal
        # and is not mixing — the 3C experiment containing an IL-6 lane would
        # be.) This is the C1 finding from session 7 held in place by a test.
        arms = {h: any("IL-6" in str(r.get("lane_condition")) for r in rs)
                for h, rs in by_hash.items()}
        no_il6 = [h for h, has in arms.items() if not has]
        with_il6 = [h for h, has in arms.items() if has]
        check(f"corpus: {target} Fig 3C arm carries NO IL-6 lane, Fig 3D arm does",
              len(no_il6) == 1 and len(with_il6) == 1
              and len(by_hash[no_il6[0]]) == 6 and len(by_hash[with_il6[0]]) == 7)

    # identity and search grouping must agree on how many experiments exist
    all_hashes = {k.split(":")[0] for k in keys}
    check(f"corpus: {len(all_hashes)} experiment hashes (search groups by this exact hash)",
          len(all_hashes) == 93)

    passed = sum(1 for _, ok in CHECKS if ok)
    failed = [n for n, ok in CHECKS if not ok]
    print(f"\n{passed}/{len(CHECKS)} stable-row-key checks passed")
    for n in failed:
        print("  FAIL:", n)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
