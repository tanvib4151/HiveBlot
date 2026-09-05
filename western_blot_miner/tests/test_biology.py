"""Runnable with either pytest or `python3 test_biology.py`.

These assert the biological rules that MUST hold -- especially the phospho
heuristic fix. If any of these fail, we are making a scientific error.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from western_blot_miner import biology as bio  # noqa: E402

CHECKS: list[tuple[str, bool]] = []


def check(name: str, condition: bool) -> None:
    CHECKS.append((name, bool(condition)))


# --- The phospho-heuristic bug fix: p<number> proteins are NOT phospho ------
def test_p_number_proteins_are_not_phospho():
    for name in ("p53", "p38", "p21", "p27", "PARP", "p130", "p65"):
        mod = bio.detect_modification(name, caption=f"Immunoblot for {name}", methods="")
        check(f"{name} not phospho", mod["modification_type"] is None)


# --- Explicit phospho WITH site -> supported, site captured -----------------
def test_phospho_with_site():
    mod = bio.detect_modification(
        "phospho-STAT3",
        caption="Immunoblot for phospho-STAT3 (Tyr705)",
        methods="anti-phospho-STAT3 Tyr705, CST #9145",
    )
    check("phospho-STAT3 Tyr705 -> phosphorylation", mod["modification_type"] == "phosphorylation")
    check("phospho-STAT3 Tyr705 -> residue Tyr", mod["residue"] == "Tyr")
    check("phospho-STAT3 Tyr705 -> position 705", mod["residue_position"] == 705)
    check("phospho-STAT3 Tyr705 -> label", mod["normalized_label"] == "phospho-Tyr705")
    check("phospho-STAT3 Tyr705 -> SUPPORTED", mod["status"] == "SUPPORTED")
    check("phospho-STAT3 Tyr705 -> phospho-specific ab", mod["phospho_specific_antibody"] is True)


def test_phospho_akt_ser473():
    mod = bio.detect_modification("p-AKT", caption="p-AKT Ser473 after insulin", methods="")
    check("p-AKT Ser473 -> phospho", mod["modification_type"] == "phosphorylation")
    check("p-AKT Ser473 -> Ser", mod["residue"] == "Ser")
    check("p-AKT Ser473 -> 473", mod["residue_position"] == 473)


def test_pY_one_letter_site():
    # target names the phospho form; caption supplies the site (pY705 -> Tyr705)
    mod = bio.detect_modification("p-STAT3", caption="pY705 signal increased", methods="")
    check("pY705 -> phospho", mod["modification_type"] == "phosphorylation")
    check("pY705 -> Tyr705", mod["residue"] == "Tyr" and mod["residue_position"] == 705)


def test_total_target_not_contaminated_by_sibling_phospho():
    # Shared caption lists BOTH phospho-STAT3 and total STAT3; the total-STAT3
    # row must stay total. This is the core STAT3 != phospho-STAT3 requirement.
    caption = "Immunoblot for phospho-STAT3 (Tyr705) and total STAT3 in HEK293T"
    mod = bio.detect_modification("STAT3", caption=caption, methods="")
    check("total STAT3 stays total", mod["modification_type"] is None)


# --- Phospho WITHOUT a site must NOT invent Tyr705 --------------------------
def test_phospho_without_site_stays_siteless():
    mod = bio.detect_modification("phospho-STAT3", caption="phospho-STAT3 immunoblot", methods="")
    check("phospho no-site -> phospho", mod["modification_type"] == "phosphorylation")
    check("phospho no-site -> residue None", mod["residue"] is None)
    check("phospho no-site -> label 'phospho'", mod["normalized_label"] == "phospho")


# --- Non-phospho modifications only on explicit words -----------------------
def test_cleavage():
    # VLM names the row as shown on the blot ("cleaved PARP")
    mod = bio.detect_modification("cleaved PARP", caption="cleaved PARP", methods="")
    check("cleaved PARP -> cleavage", mod["modification_type"] == "cleavage")


# --- Experiment-type classification -----------------------------------------
def test_co_ip_from_methods_only():
    mod = bio.detect_modification("STAT3", caption="STAT3 blot", methods="")
    exp = bio.classify_experiment(
        "STAT3",
        caption="STAT3 detected after co-immunoprecipitation with EGFR",
        methods="Lysates were immunoprecipitated with anti-EGFR.",
        modification=mod,
    )
    check("co-IP detected", exp["experiment_type"] == "co_ip")
    check("co-IP has evidence", len(exp["evidence"]) >= 1)


def test_co_ip_plus_phospho_non_exclusive():
    mod = bio.detect_modification("phospho-STAT3", caption="phospho-STAT3 (Tyr705)", methods="")
    exp = bio.classify_experiment(
        "phospho-STAT3",
        caption="phospho-STAT3 after co-IP with EGFR",
        methods="immunoprecipitated with EGFR antibody",
        modification=mod,
    )
    check("co_ip primary", exp["experiment_type"] == "co_ip")
    check("phospho_western coexists", "phospho_western" in exp["experiment_flags"])


def test_loading_control():
    exp = bio.classify_experiment("GAPDH", caption="GAPDH loading control", methods="")
    check("GAPDH -> loading_control", exp["experiment_type"] == "loading_control")


def test_standard_western_default():
    mod = bio.detect_modification("STAT3", caption="STAT3 immunoblot", methods="")
    exp = bio.classify_experiment("STAT3", caption="STAT3 immunoblot", methods="", modification=mod)
    check("STAT3 total -> standard_western", exp["experiment_type"] == "standard_western")


def test_never_co_ip_without_text_evidence():
    mod = bio.detect_modification("STAT3", caption="", methods="")
    exp = bio.classify_experiment("STAT3", caption="STAT3 blot", methods="Standard SDS-PAGE.", modification=mod)
    check("no co-IP without evidence", "co_ip" not in exp["experiment_flags"])


# --- Protein normalization ---------------------------------------------------
def test_normalize_protein():
    n = bio.normalize_protein("pSTAT3")
    check("pSTAT3 -> STAT3", n["canonical"] == "STAT3")
    check("pSTAT3 -> UniProt P40763", n["uniprot_id"] == "P40763")
    check("pSTAT3 -> SUPPORTED", n["status"] == "SUPPORTED")

    amb = bio.normalize_protein("ERK")
    check("ERK -> ambiguous (no single UniProt)", amb["status"] == "AMBIGUOUS")

    unknown = bio.normalize_protein("Xyzzy1")
    check("unknown protein -> MISSING, not guessed", unknown["canonical"] is None and unknown["status"] == "MISSING")


def test_deterministic_extractors_exist():
    # site parser handles the canonical notations
    check("Tyr705 parse", bio.parse_phospho_site("Tyr705")["position"] == 705)
    check("Ser 473 parse", bio.parse_phospho_site("Ser 473")["residue"] == "Ser")
    check("pS473 parse", bio.parse_phospho_site("pS473")["residue"] == "Ser")


def test_core_symbol_prefix_and_isoform():
    """core_symbol must strip real modification/total prefixes WITHOUT eating a
    letter that is part of the protein name, and must preserve isoform suffixes.
    Regressions here caused P-ERK 1/2 -> "ERK" -> EPHB2 (a false UniProt friend),
    and p53/p38/PARP -> 53/38/ARP (unresolvable). Surfaced by the first real
    paper (Jang et al., 10.3892/br.2026.2108).
    """
    cs = bio.core_symbol
    # phospho / total prefixes are stripped
    check("p-STAT3 -> STAT3", cs("P-STAT3 (Tyr705)") == "STAT3")
    check("t-STAT3 -> STAT3", cs("T-STAT3") == "STAT3")
    check("pSTAT3 glued -> STAT3", cs("pSTAT3") == "STAT3")
    check("phospho-STAT3 -> STAT3", cs("phospho-STAT3 (Tyr705)") == "STAT3")
    # p<number> and P-initial proteins keep their leading letter
    check("p53 kept", cs("p53") == "p53")
    check("p38 kept", cs("p38") == "p38")
    check("PARP kept", cs("PARP") == "PARP")
    # isoform designation preserved (not collapsed to family false-friend)
    check("P-ERK 1/2 -> ERK1/2", cs("P-ERK 1/2") == "ERK1/2")
    check("T-ERK 1/2 -> ERK1/2", cs("T-ERK 1/2") == "ERK1/2")


def test_one_letter_site_in_phospho_marked_label():
    """'p-AKT (S473)' style labels (extremely common) must yield the site: the
    phospho marker and one-letter site travel in the same short label, which
    satisfies the phospho-context guard. Surfaced by the second real paper
    (PMC12706926) where residue came back empty."""
    for label, res_, pos in [("p-AKT (S473)", "Ser", 473),
                             ("p-RPS6KB1 (T389)", "Thr", 389),
                             ("p-EIF4EBP1 (S65)", "Ser", 65)]:
        m = bio.detect_modification(label)
        check(f"{label} is phospho", m["modification_type"] == "phosphorylation")
        check(f"{label} residue {res_}{pos}",
              m["residue"] == res_ and m["residue_position"] == pos)
    # bare one-letter forms WITHOUT a phospho marker still never claim a site
    m = bio.detect_modification("AKT S473")
    check("no phospho marker -> no phospho from bare S473",
          m["modification_type"] is None)


def test_phospho_specific_antibody_flag_prevents_false_total():
    """Uppercase 'P-' is never a phospho MARKER (P-selectin, P-cadherin are
    protein names) — but an explicit phospho_specific antibody claim is real
    evidence. 'P-ERK 1/2' + phospho-specific CST #4370 must NOT settle as
    total; it stays unsettled (CONFLICTING, value null, needs_review)."""
    from western_blot_miner.record_builder import build_evidence_record
    case = {
        "paper": {"doi": "10.x/t"}, "figure": {"page": 1},
        "raw_target": "P-ERK 1/2", "texts": {"caption": "", "methods": ""},
        "model_claims": {
            "sample": "Hep3B",
            "antibodies": [{"target": "P-ERK 1/2", "vendor": "CST", "catalog": "4370",
                            "role": "detection", "phospho_specific": True,
                            "source": {"type": "methods", "rank": 3,
                                       "text": "p-ERK (1:1,000; CST #4370)"}}],
            "bands": [{"lane_index": 1, "lane_condition": "x",
                       "band_state": "present", "confidence": "high"}],
        },
    }
    rec = build_evidence_record(case)
    mt = rec.modification.modification_type
    check("P-ERK + phospho-ab does not settle as total",
          not (mt.status == "SUPPORTED" and mt.value is None))
    check("P-ERK + phospho-ab unsettled -> value null + review",
          mt.value is None and rec.validation.needs_review)
    # A genuinely total antibody (phospho_specific False) still settles total.
    case2 = dict(case, raw_target="T-ERK 1/2")
    case2["model_claims"] = dict(case["model_claims"])
    case2["model_claims"]["antibodies"] = [{
        "target": "T-ERK 1/2", "vendor": "CST", "catalog": "4695",
        "role": "detection", "phospho_specific": False,
        "source": {"type": "methods", "rank": 3, "text": "t-ERK (CST #4695)"}}]
    rec2 = build_evidence_record(case2)
    mt2 = rec2.modification.modification_type
    check("T-ERK + total-ab settles total",
          mt2.status == "SUPPORTED" and mt2.value is None)


def test_bare_mention_is_not_a_total_claim():
    """A pathway sentence ('PI3K/AKT/mTOR signaling') must not be read as an
    explicit 'AKT is unmodified' claim — that manufactured fake MODIFICATION_
    CONFLICTs against real phospho rows (PMC12706926, page 10). Explicit
    'total X' wording still asserts total; mixed forms still abstain."""
    cm = bio.caption_modification_for_core
    check("bare pathway mention -> abstain",
          cm("AKT", "BEX2 impairs PI3K/AKT/mTOR signaling in NSCLC.") is None)
    check("explicit total -> none-claim",
          cm("STAT3", "Total STAT3 levels remained constant.")["modification_type"] is None)
    check("T- prefix -> none-claim",
          cm("STAT3", "T-STAT3 was blotted.")["modification_type"] is None)
    check("phospho-only mention -> phospho claim",
          cm("STAT3", "pSTAT3 blot.")["modification_type"] == "phosphorylation")
    check("mixed phospho + bare forms -> abstain",
          cm("STAT3", "pSTAT3 and STAT3 were blotted.") is None)


def test_co_ip_requires_panel_scoped_evidence():
    """A methods paragraph about immunoprecipitation must not reclassify every
    panel on the page as co_ip; panel-scoped evidence (IP-role antibody, co-IP
    caption, or IP:/IgG lane labels) is required. Surfaced by PMC12706926 where
    autophagy/mTOR expression panels all came back co_ip."""
    from western_blot_miner.record_builder import build_evidence_record
    methods_blob = ("Cells were lysed... For co-immunoprecipitation, lysates were "
                    "immunoprecipitated with anti-PIK3CA... antibodies: anti-LC3B (2775)...")
    base = {
        "paper": {"doi": "10.x/test"},
        "figure": {"page": 1},
        "texts": {"caption": "", "methods": methods_blob},
    }
    # Expression panel: NO panel-scoped IP evidence -> NOT co_ip.
    case = dict(base, raw_target="LC3B", model_claims={
        "sample": "H1299",
        "antibodies": [{"target": "LC3B", "vendor": "CST", "catalog": "2775",
                        "role": "detection", "phospho_specific": False,
                        "source": {"type": "methods", "rank": 3, "text": "anti-LC3B (2775)"}}],
        "bands": [{"lane_index": 1, "lane_condition": "DMSO", "band_state": "present",
                   "confidence": "high"}],
    })
    rec = build_evidence_record(case)
    check("methods-only co-IP mention does not settle co_ip",
          rec.experiment.experiment_type.value != "co_ip")
    check("methods mention preserved as co_ip_context flag",
          "co_ip_context" in (rec.experiment.experiment_flags.value or []))
    # Same page, but the panel's lanes say IP:/IgG -> IS co_ip.
    case2 = dict(base, raw_target="BEX2", model_claims={
        "sample": "H1299",
        "antibodies": [{"target": "BEX2", "vendor": "Santa Cruz", "catalog": "SC-398486",
                        "role": "detection", "phospho_specific": False,
                        "source": {"type": "methods", "rank": 3, "text": "anti-BEX2"}}],
        "bands": [{"lane_index": 1, "lane_condition": "Input", "band_state": "present", "confidence": "high"},
                  {"lane_index": 2, "lane_condition": "IgG", "band_state": "absent", "confidence": "high"},
                  {"lane_index": 3, "lane_condition": "IP:PIK3CA", "band_state": "present", "confidence": "high"}],
    })
    rec2 = build_evidence_record(case2)
    check("IP:/IgG lane labels settle co_ip", rec2.experiment.experiment_type.value == "co_ip")


def test_dose_duration_series_expansion():
    """Enumerated series sharing one unit must expand, not collapse to the last
    value. Real contexts from PMC12856536."""
    from western_blot_miner.supabase_loader import extract_dose_series, extract_duration_series
    tc = ("Hep3B cells treated with IL-6 (10 ng/ml) for the indicated times "
          "(0, 5, 10, 20, 30, 60 min)")
    durs = [d["value"] for d in extract_duration_series(tc)]
    check("time course expands to 6 timepoints", durs == [0.0, 5.0, 10.0, 20.0, 30.0, 60.0])
    check("time course keeps single stimulus dose",
          [d["value"] for d in extract_dose_series(tc)] == [10.0])
    dr = ("Hep3B cells pretreated with CL-E at 10, 30 and 60 ug/ml for 1 h, "
          "then stimulated with IL-6 (10 ng/ml) for 30 min")
    doses = extract_dose_series(dr)
    check("dose response expands to 10/30/60 ug/ml",
          [d["value"] for d in doses if d["unit"].lower() == "ug/ml"] == [10.0, 30.0, 60.0])
    check("dose response still sees the second agent's ng/ml dose",
          any(d["unit"].lower() == "ng/ml" for d in doses))
    # single-value text is unchanged
    single = extract_dose_series("IL-6 (10 ng/ml) for 30 min")
    check("single dose unchanged", len(single) == 1 and single[0]["value"] == 10.0)


def test_multi_condition_scalar_is_never_settled():
    """A dose-response / time-course panel must NOT report one lane's value as
    THE dose/duration. Before this fix the CL-E dose (60 ug/ml) was reported as
    the IL-6 dose, and 60 min as THE duration of a 0-60 min course. Scalars go
    null+AMBIGUOUS with every stated value preserved as a candidate; per-lane
    values live on the bands."""
    from western_blot_miner.record_builder import build_evidence_record

    def rec(ctx, lanes):
        return build_evidence_record({
            "paper": {"doi": "10.x/t"}, "figure": {"page": 1},
            "raw_target": "P-STAT3 (Tyr705)", "texts": {"caption": "", "methods": ""},
            "model_claims": {
                "sample": "Hep3B", "treatment_name": "IL-6", "treatment_context": ctx,
                "antibodies": [{"target": "p-STAT3 (Tyr705)", "vendor": "CST", "catalog": "9145",
                                "role": "detection", "phospho_specific": True,
                                "source": {"type": "methods", "rank": 3, "text": "CST #9145"}}],
                "bands": [{"lane_index": i + 1, "lane_condition": c, "band_state": "present",
                           "confidence": "high"} for i, c in enumerate(lanes)],
            },
        })

    tc = rec("Hep3B cells treated with IL-6 (10 ng/ml) for the indicated times "
             "(0, 5, 10, 20, 30, 60 min)",
             ["0 min", "5 min", "10 min", "20 min", "30 min", "60 min"])
    check("time course duration not settled",
          tc.treatment.duration.value is None and tc.treatment.duration.status == "AMBIGUOUS")
    check("time course keeps all 6 timepoints as candidates",
          [c.value for c in tc.treatment.duration.candidates] == [0.0, 5.0, 10.0, 20.0, 30.0, 60.0])
    check("time course stimulus dose stays SETTLED (kind-specific marker)",
          tc.treatment.dose.value == 10.0 and tc.treatment.dose.status == "SUPPORTED")
    check("lane-level durations preserved",
          [b.lane_duration.value for b in tc.bands] == [0.0, 5.0, 10.0, 20.0, 30.0, 60.0])

    dr = rec("Hep3B cells pretreated with CL-E at 10, 30 and 60 ug/ml for 1 h, "
             "then stimulated with IL-6 (10 ng/ml) for 30 min",
             ["IL-6 - / CL-E -", "IL-6 + / CL-E 10", "IL-6 + / CL-E 30"])
    check("dose-response dose not settled (no cross-treatment misattribution)",
          dr.treatment.dose.value is None and dr.treatment.dose.status == "AMBIGUOUS")
    check("dose-response never reports 60 ug/ml as THE IL-6 dose",
          dr.treatment.dose.value != 60.0)
    check("dose-response candidates preserved",
          {c.value for c in dr.treatment.dose.candidates} >= {10.0, 30.0, 60.0})
    check("two different duration claims stay unsettled",
          dr.treatment.duration.value is None)

    single = rec("Hep3B cells stimulated with IL-6 (10 ng/ml) for 30 min",
                 ["untreated", "IL-6 30 min"])
    check("single-condition dose still settled",
          single.treatment.dose.value == 10.0 and single.treatment.dose.status == "SUPPORTED")
    check("single-condition duration still settled",
          single.treatment.duration.value == 30.0)
    check("lane parses its own duration", single.bands[1].lane_duration.value == 30.0)
    check("lane with no stated value stays MISSING",
          single.bands[0].lane_duration.value is None)


def _band_case(raw_target, caption, lanes, **band_extra):
    """Build a record and return its first band (band-pattern test helper)."""
    from western_blot_miner.record_builder import build_evidence_record
    rec = build_evidence_record({
        "paper": {"doi": "10.x/t"}, "figure": {"page": 1},
        "raw_target": raw_target, "texts": {"caption": caption, "methods": ""},
        "model_claims": {
            "sample": "H1792",
            "antibodies": [{"target": raw_target, "vendor": "CST", "catalog": "2775",
                            "role": "detection", "phospho_specific": False,
                            "source": {"type": "methods", "rank": 3, "text": "anti-LC3B (2775)"}}],
            "bands": [dict({"lane_index": i + 1, "lane_condition": c,
                            "band_state": "present", "confidence": "high"}, **band_extra)
                      for i, c in enumerate(lanes)],
        },
    })
    return rec.bands[0]


def test_band_pattern_from_explicit_wording():
    """Descriptive multiplicity is read ONLY from explicit wording. band_state
    stays independent: a smeared or doublet band is still `present`."""
    d = bio.detect_band_pattern
    check("doublet wording", d("LC3B resolved as a doublet")["pattern"] == "doublet")
    check("doublet implies count 2", d("resolved as a doublet")["count"] == 2)
    check("'two bands' -> doublet/2", d("two distinct bands were detected")["count"] == 2)
    check("'three bands' -> multiple", d("three bands were observed")["pattern"] == "multiple")
    check("smear wording", d("the signal appeared as a smear")["pattern"] == "smear")
    check("smeared wording", d("a smeared high background")["pattern"] == "smear")
    check("polyubiquitin ladder", d("a polyubiquitin ladder was detected")["pattern"] == "ladder")
    check("high-MW species", d("higher-molecular-weight species accumulated")["pattern"] == "ladder")
    check("multiple bands", d("multiple bands were present")["pattern"] == "multiple")
    check("non-specific extra band", d("an additional band was seen")["pattern"] == "multiple")
    check("single band", d("a single band was detected")["pattern"] == "single")
    # band_state is untouched by pattern
    b = _band_case("LC3B", "LC3B was detected as a doublet in H1792 cells.", ["DMSO"])
    check("doublet band is still present", b.band_state.value == "present")
    check("doublet pattern recorded", b.band_pattern.value == "doublet")
    check("doublet count recorded", b.band_count.value == 2)
    check("doublet keeps verbatim wording", "doublet" in (b.band_notes.value or ""))


def test_band_pattern_absent_means_missing_not_single():
    """No multiplicity wording => MISSING. Never guess 'single', and never
    infer a pattern from protein identity (LC3B does not imply a doublet;
    ubiquitin does not imply a ladder)."""
    b = _band_case("LC3B", "LC3B levels were analyzed by western blotting.", ["DMSO", "Rapamycin"])
    check("no wording -> pattern MISSING", b.band_pattern.status == "MISSING"
          and b.band_pattern.value is None)
    check("no wording -> count MISSING", b.band_count.value is None)
    ub = _band_case("Ubiquitin", "Ubiquitin was analyzed by western blotting.", ["E14.5"])
    check("ubiquitin identity alone implies no ladder", ub.band_pattern.value is None)


def test_antibody_antigen_name_is_not_a_modification_claim():
    """An anti-ubiquitin blot detects the PROTEIN ubiquitin; it does not
    establish that some target is ubiquitinated. Asserting a modification from
    the antibody's own antigen name is the same failure class as the banned
    startswith('p') rule (independent QA, C2). A real modified-target label
    keeps the claim."""
    check("'Ubiquitin' target -> no modification claim",
          bio.detect_modification("Ubiquitin")["modification_type"] is None)
    check("'ubiquitin' antibody -> no modification claim",
          bio.antibody_modification("ubiquitin")["modification_type"] is None)
    check("'SUMO' target -> no modification claim",
          bio.detect_modification("SUMO")["modification_type"] is None)
    check("'ubiquitinated EGFR' keeps the claim",
          bio.detect_modification("ubiquitinated EGFR")["modification_type"] == "ubiquitination")
    check("'cleaved PARP' keeps the claim",
          bio.detect_modification("cleaved PARP")["modification_type"] == "cleavage")


def test_loading_control_gene_symbols():
    """'β-actin' matched but 'ACTB' did not (QA M7 — 81 rows misclassified)."""
    check("ACTB is a loading control", bio.is_loading_control("ACTB"))
    check("TUBA1B is a loading control", bio.is_loading_control("TUBA1B"))
    check("β-actin still matches", bio.is_loading_control("β-actin"))
    check("STAT3 is not", not bio.is_loading_control("STAT3"))


def test_greek_beta_normalizes_in_core_symbol():
    check("β-actin core -> beta-actin", bio.core_symbol("β-actin") == "beta-actin")


def test_figure_references_are_not_durations():
    """Manual-test issue 3 ('IL-6 · 3D'): 'Fig 3D' was parsed as a 3-day
    duration and rendered as a treatment. Figure/panel references and glued
    UPPERCASE single-letter units ('3D culture', 'Fig. 3H') are never
    durations; real lowercase durations still parse."""
    from western_blot_miner.supabase_loader import extract_duration, extract_duration_series
    check("'Fig 3D:' yields no duration",
          extract_duration("Fig 3D: Hep3B cells stimulated with IL-6") == [])
    check("'Fig. 3H' yields no duration",
          extract_duration("as shown in Fig. 3H for this blot") == [])
    check("'3D culture' yields no duration",
          extract_duration("grown in a 3D culture model") == [])
    check("'panel 4h' figure ref guarded",
          extract_duration("quantified in panel 4h") == [])
    check("'Figs. 2, 3 and 4' is not a series",
          extract_duration_series("see Figs. 2, 3 and 4 d") == [])
    check("real '3 d' still parses",
          extract_duration("treated for 3 d")[0]["value"] == 3.0)
    check("real '24h' glued lowercase still parses",
          extract_duration("stimulated for 24h")[0]["value"] == 24.0)
    check("real '30 min' unaffected",
          extract_duration("IL-6 for 30 min")[0]["value"] == 30.0)
    check("'Figure 2, 4 h exposure' keeps the real 4 h",
          extract_duration("Figure 2, 4 h exposure")[0]["value"] == 4.0)
    check("time-course series still expands",
          len(extract_duration_series("times (0, 5, 10, 20, 30, 60 min)")) == 6)


def test_dose_micro_sign_and_identifier_guard():
    """QA M6: 'µ' doses were silently dropped, and the series regex matched
    INSIDE identifiers — 'BafA1, 20 nM' fabricated a 1 nM candidate from the
    trailing digit of the drug name."""
    from western_blot_miner.supabase_loader import extract_dose
    d = extract_dose("cells treated with 10 µM LY294002")
    check("µM dose captured", any(x["value"] == 10.0 for x in d))
    d = extract_dose("CL-E at 60 µg/ml")
    check("µg/ml dose captured", any(x["value"] == 60.0 for x in d))
    d = extract_dose("incubated with BafA1, 20 nM, for 4 h")
    check("BafA1 does not fabricate a 1 nM dose",
          all(x["value"] != 1.0 for x in d))
    check("real 20 nM dose kept", any(x["value"] == 20.0 for x in d))


def test_band_pattern_negation_abstains():
    """Negated multiplicity is antibody-specificity boilerplate; asserting the
    pattern from it would INVERT the paper's claim (review finding B1). We
    abstain — a negated mention is not evidence of 'single' either."""
    d = bio.detect_band_pattern
    check("'no smearing' abstains", d("No smearing was observed.") is None)
    check("'without smearing' abstains", d("clean transfer without smearing") is None)
    check("'no additional bands' abstains",
          d("The antibody detected no additional bands.") is None)
    check("'did not detect a doublet' abstains",
          d("we did not detect a doublet") is None)
    check("un-negated smear still fires", d("the lane showed a smear")["pattern"] == "smear")


def test_band_pattern_high_mw_singular_is_not_ladder():
    """'a higher molecular weight band' (singular) is the standard phrasing for
    ONE upshifted band (phospho/SUMO/mono-Ub) — never a ladder claim (B2)."""
    d = bio.detect_band_pattern
    check("singular high-MW band -> no pattern",
          d("STAT3 migrated as a higher molecular weight band upon modification") is None)
    check("plural high-MW species still ladder",
          d("higher-molecular-weight species accumulated")["pattern"] == "ladder")


def test_band_pattern_polyubiquitin_smear_is_ladder_not_conflict():
    """'a polyubiquitin smear' matches the smear AND ladder regexes on the same
    substring — that is ONE statement, not two conflicting descriptions; the
    longer/more specific match wins (containment pruning)."""
    got = bio.detect_band_pattern("a polyubiquitin smear was detected")
    check("polyubiquitin smear -> ladder", got is not None and got["pattern"] == "ladder")


def test_band_pattern_count_context_guard():
    d = bio.detect_band_pattern
    check("'Fig. 3 bands' does not fire", d("as shown in Fig. 3 bands were compared") is None)
    check("'n = 3 bands' does not fire", d("quantified (n = 3 bands per group)") is None)
    check("'1-2 bands' range does not fire", d("we expected 1-2 bands typically") is None)
    check("plain 'three bands' still fires", d("three bands were observed")["pattern"] == "multiple")


def test_band_pattern_caption_cannot_settle_multilane_panel():
    """A caption describes the PANEL; on a multi-lane panel it cannot settle any
    single lane's pattern as SUPPORTED (B3 — same panel-vs-lane discipline as
    the dose/duration scalars). Single-lane panels may settle."""
    multi = _band_case("LC3B", "LC3B appeared as a doublet after rapamycin treatment.",
                       ["DMSO", "Rapamycin"])
    check("multi-lane caption pattern is AMBIGUOUS", multi.band_pattern.status == "AMBIGUOUS")
    check("multi-lane caption pattern value kept for review",
          multi.band_pattern.value == "doublet")
    single = _band_case("LC3B", "LC3B appeared as a doublet.", ["Rapamycin"])
    check("single-lane caption pattern may settle", single.band_pattern.status == "SUPPORTED")


def test_band_pattern_parenthetical_does_not_leak_across_and():
    """'probed for LC3B (doublet) and ACTB' must not hand ACTB the doublet."""
    caption = "Blots were probed for LC3B (doublet) and ACTB."
    actb = _band_case("ACTB", caption, ["DMSO"])
    check("parenthetical doublet does not leak to ACTB", actb.band_pattern.value is None)


def test_absent_band_with_pattern_is_flagged():
    """band_state=absent + a visible-structure pattern is a contradiction and
    must surface as an anomaly + needs_review (B4)."""
    from western_blot_miner.record_builder import build_evidence_record
    rec = build_evidence_record({
        "paper": {"doi": "10.x/t"}, "figure": {"page": 1},
        "raw_target": "LC3B", "texts": {"caption": "", "methods": ""},
        "model_claims": {
            "sample": "H1792",
            "antibodies": [{"target": "LC3B", "vendor": "CST", "catalog": "2775",
                            "role": "detection", "phospho_specific": False,
                            "source": {"type": "methods", "rank": 3, "text": "anti-LC3B"}}],
            "bands": [{"lane_index": 1, "lane_condition": "ctrl", "band_state": "absent",
                       "confidence": "high", "band_pattern": "doublet", "band_count": 2}],
        },
    })
    codes = [a.code for a in rec.validation.anomaly_flags]
    check("absent+doublet raises BAND_PATTERN_STATE_MISMATCH",
          "BAND_PATTERN_STATE_MISMATCH" in codes)


def test_band_pattern_hedged_and_conflicting_stay_uncertain():
    d = bio.detect_band_pattern
    check("hedged doublet -> uncertain",
          d("the signal may represent a doublet")["pattern"] == "uncertain")
    check("hedged doublet drops the count",
          d("this could be a doublet")["count"] is None)
    check("two competing descriptions -> uncertain",
          d("a doublet or possibly a smear was observed")["pattern"] == "uncertain")
    b = _band_case("LC3B", "LC3B may appear as a doublet here.", ["DMSO"])
    check("hedged pattern is AMBIGUOUS, not settled", b.band_pattern.status == "AMBIGUOUS")


def test_band_pattern_is_target_scoped():
    """A sibling target's doublet must not leak onto this row (same scoping
    discipline as reported-MW and co-IP classification)."""
    caption = "LC3B resolved as a doublet, while ACTB was used as a loading control."
    actb = _band_case("ACTB", caption, ["DMSO"])
    check("sibling doublet does not leak to ACTB", actb.band_pattern.value is None)
    lc3b = _band_case("LC3B", caption, ["DMSO"])
    check("scoped doublet still found for LC3B", lc3b.band_pattern.value == "doublet")


def test_band_pattern_explicit_observer_claim():
    """An extractor may REPORT an observed pattern (like band_state); it is
    recorded as a claim with image provenance. Unknown vocabulary is ignored."""
    b = _band_case("LC3B", "", ["DMSO"], band_pattern="doublet", band_count=2,
                   band_notes="two closely spaced bands")
    check("observer doublet recorded", b.band_pattern.value == "doublet")
    check("observer count recorded", b.band_count.value == 2)
    bad = _band_case("LC3B", "", ["DMSO"], band_pattern="isoform-resolved")
    check("unknown pattern vocabulary ignored", bad.band_pattern.value is None)


def test_multiple_rows_are_not_multiplicity():
    """Multiplicity belongs to ONE band observation. A panel with several
    target rows (phospho + total + loading control) is not a 'doublet'."""
    caption = "P-STAT3 (Tyr705), total STAT3 and beta-actin were blotted."
    for tgt in ("P-STAT3 (Tyr705)", "T-STAT3", "β-actin"):
        b = _band_case(tgt, caption, ["IL-6 -", "IL-6 +"])
        check(f"{tgt}: multiple rows != multiplicity", b.band_pattern.value is None)


def test_organism_taxon_mapping():
    """Explicit organism wording scopes the UniProt query; anything else keeps
    the previous human default. The map must never invent an organism."""
    check("human -> 9606", bio.organism_taxon_id("human") == 9606)
    check("Mouse -> 10090", bio.organism_taxon_id("Mouse") == 10090)
    check("Mus musculus -> 10090", bio.organism_taxon_id("Mus musculus") == 10090)
    check("rat -> 10116", bio.organism_taxon_id("rat") == 10116)
    check("None -> default 9606", bio.organism_taxon_id(None) == 9606)
    check("unknown wording -> default 9606", bio.organism_taxon_id("zebrafish-ish") == 9606)


def test_erk_family_not_a_false_friend_offline():
    """The curated map must mark ERK-family shorthand ambiguous (ERK1/ERK2), so
    it is never collapsed to a single accession -- offline resolver check."""
    from western_blot_miner import resolve
    r = resolve.LocalMapResolver()
    for label in ("P-ERK 1/2", "T-ERK 1/2", "ERK", "p44/42 MAPK"):
        res = r.resolve(label)
        check(f"{label} ambiguous ERK1/2", res.status == "AMBIGUOUS"
              and res.canonical == "MAPK1/MAPK3" and res.uniprot_id is None)
    # p53 / PARP must resolve to the right protein via the curated map
    check("p53 -> TP53 offline", r.resolve("p53").uniprot_id == "P04637")
    check("PARP -> PARP1 offline", r.resolve("PARP").uniprot_id == "P09874")


def run() -> int:
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
    passed = sum(1 for _, ok in CHECKS if ok)
    failed = [name for name, ok in CHECKS if not ok]
    print(f"\n{passed}/{len(CHECKS)} biological checks passed")
    if failed:
        print("FAILED:")
        for name in failed:
            print(f"  - {name}")
        return 1
    print("All biological rules hold.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
