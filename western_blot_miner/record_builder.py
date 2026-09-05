"""Assemble an EvidenceRecord from model claims + deterministic biology.

This is the Stage-2/Stage-3 join point. The LLM (Bedrock, via llm_client)
produces structured *claims* about a panel -- target label, antibodies with
their targets, sample, treatment, bands. The deterministic layer (biology.py)
independently derives modification, dose/duration, catalog/vendor and protein
identity. :func:`build_evidence_record` reconciles all sources through the
evidence hierarchy (reconcile.py), resolves the protein (resolve.py), computes
antibody association confidence, and runs validation -- producing the fully
provenanced EvidenceRecord.

Deliberately model-free at this layer: give it the model's claims (or a fixture)
and it runs offline, which is how the benchmark exercises the biology.
"""
from __future__ import annotations

import hashlib
from typing import Any, Optional

from . import biology
from .evidence_record import (
    AMBIGUOUS,
    CONFLICTING,
    MISSING,
    SUPPORTED,
    AntibodyInfo,
    AnomalyFlag,
    BandObservation,
    Candidate,
    EvidenceField,
    EvidenceRecord,
    ExtractionMeta,
    ExperimentInfo,
    FigureRef,
    MolecularWeightInfo,
    ModificationInfo,
    PaperRef,
    RANK_ANTIBODY,
    RANK_CAPTION,
    RANK_DETERMINISTIC,
    RANK_METHODS,
    RANK_MODEL_TARGET,
    RANK_REFERENCE,
    SampleInfo,
    Source,
    TargetInfo,
    TreatmentInfo,
    ValidationInfo,
)
from .reconcile import Claim, ModClaim, reconcile_field, reconcile_modification
from .resolve import ProteinResolver, LocalMapResolver
from .supabase_loader import (
    extract_dose,
    extract_dose_series,
    extract_duration,
    extract_duration_series,
    extract_kda,
)

CELL_LINE_ORGANISM = {
    "hek293": "human", "hek293t": "human", "hela": "human", "a549": "human",
    "mcf7": "human", "mcf-7": "human", "hepg2": "human", "u2os": "human",
    "jurkat": "human", "3t3": "mouse", "nih3t3": "mouse", "raw264.7": "mouse", "cho": "hamster",
}


def build_evidence_record(
    case: dict[str, Any],
    resolver: Optional[ProteinResolver] = None,
    extraction: Optional[ExtractionMeta] = None,
) -> EvidenceRecord:
    resolver = resolver or LocalMapResolver()
    mc = case.get("model_claims", {})
    texts = case.get("texts", {})
    caption = texts.get("caption", "") or case.get("figure", {}).get("caption_text", "")
    methods = texts.get("methods", "")
    raw_target = case["raw_target"]
    core = biology.core_symbol(raw_target)

    antibodies_in = mc.get("antibodies", [])
    detection_abs = [a for a in antibodies_in if a.get("role", "detection") == "detection"]
    ip_abs = [a for a in antibodies_in if a.get("role") == "immunoprecipitation"]

    # ---- protein identity (real resolver; never guessed) -------------------
    # Scope the UniProt query to the paper's claimed organism (default human,
    # the previous unconditional behavior) so e.g. mouse Stat3 resolves to the
    # mouse accession and expected MW, not the human one.
    organism_id = biology.organism_taxon_id(mc.get("organism"))
    res = resolver.resolve(core, organism_id=organism_id)
    target_info = _target_info(raw_target, core, res, mc)

    # ---- modification: gather claims from every source, then reconcile -----
    mod_claims: list[ModClaim] = []
    for ab in detection_abs:
        m = biology.antibody_modification(ab.get("target", ""))
        conf = 0.9
        if m["modification_type"] is None and ab.get("phospho_specific"):
            # The extractor explicitly claimed this antibody is phospho-specific
            # even though its target string carries no parseable marker — e.g.
            # uppercase "P-ERK 1/2" (uppercase P- must NEVER be read as a
            # phospho marker by itself: P-selectin / P-cadherin are protein
            # names). The explicit flag is real evidence; without it the row
            # would falsely SETTLE as total against a phospho-specific
            # antibody. No site is invented; reconciliation decides.
            m = {"modification_type": "phosphorylation", "residue": None,
                 "residue_position": None}
            conf = 0.6
        mod_claims.append(ModClaim(m["modification_type"], m["residue"], m["residue_position"],
                                   "antibody", RANK_ANTIBODY, conf,
                                   ab.get("source", {}).get("text", ab.get("target", ""))))
    cap_m = biology.caption_modification_for_core(core, caption)
    if cap_m is not None:
        mod_claims.append(ModClaim(cap_m["modification_type"], cap_m["residue"], cap_m["residue_position"],
                                   "figure_caption", RANK_CAPTION, 0.7, _snippet(caption, core)))
    meth_m = biology.caption_modification_for_core(core, methods)
    if meth_m is not None:
        mod_claims.append(ModClaim(meth_m["modification_type"], meth_m["residue"], meth_m["residue_position"],
                                   "methods", RANK_METHODS, 0.6, _snippet(methods, core)))
    row_m = biology.detect_modification(raw_target)
    mod_claims.append(ModClaim(row_m["modification_type"], row_m["residue"], row_m["residue_position"],
                               "model_target", RANK_MODEL_TARGET, 0.5, raw_target))

    mod_fields = reconcile_modification(mod_claims)
    phospho_specific = _phospho_specific_field(detection_abs, mod_fields)
    modification = ModificationInfo(
        modification_type=mod_fields["modification_type"],
        residue=mod_fields["residue"],
        residue_position=mod_fields["residue_position"],
        normalized_label=mod_fields["normalized_label"],
        phospho_specific_antibody=phospho_specific,
    )

    # ---- experiment type ---------------------------------------------------
    lane_text = " | ".join(
        str(b.get("lane_condition") or "") for b in mc.get("bands", []))
    experiment = _experiment_info(core, caption, methods, mod_fields, ip_abs, lane_text=lane_text)

    # ---- sample ------------------------------------------------------------
    sample = _sample_info(mc, caption)

    # ---- treatment (deterministic dose/duration; never invented) -----------
    treatment = _treatment_info(mc)

    # ---- antibodies with detection vs association confidence ---------------
    antibodies = [_antibody_info(ab, core, mod_fields) for ab in antibodies_in]

    # ---- molecular weight: reported (text) vs expected (UniProt) -----------
    molecular_weight = _mw_info(caption, methods, res, core=core)

    # ---- bands -------------------------------------------------------------
    # `core` + `caption` let band-pattern wording be scoped to THIS target so a
    # sibling row's doublet never leaks onto this one.
    bands = _bands(mc, core=core, caption=caption)

    record = EvidenceRecord(
        record_id=_record_id(case, raw_target),
        paper=_paper_ref(case.get("paper", {})),
        figure=_figure_ref(case.get("figure", {}), caption),
        target=target_info,
        modification=modification,
        experiment=experiment,
        sample=sample,
        treatment=treatment,
        antibodies=antibodies,
        molecular_weight=molecular_weight,
        bands=bands,
        extraction=extraction or ExtractionMeta(stage="deterministic+llm", backend="mock", model="fixture"),
    )
    record.validation = _validate(record, detection_abs, mod_fields)
    return record


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #

def _target_info(raw_target, core, res, mc) -> TargetInfo:
    aliases = mc.get("aliases", [])
    if res.status == SUPPORTED and res.uniprot_id:
        canonical = EvidenceField.supported(
            res.canonical, 0.96, [Source(type="uniprot_reference", rank=RANK_REFERENCE, text=res.uniprot_id)])
        uniprot = EvidenceField.supported(
            res.uniprot_id, 0.96, [Source(type="uniprot_reference", rank=RANK_REFERENCE, text=res.uniprot_id)])
    elif res.status == AMBIGUOUS:
        cands = [Candidate(value=c.get("uniprot_id"), source_type="uniprot_reference", rank=RANK_REFERENCE,
                           confidence=0.5, evidence=[Source(type="uniprot_reference", rank=RANK_REFERENCE,
                                                            text=str(c))]) for c in (res.candidates or [{}])]
        # An ambiguous resolution keeps a best-effort family LABEL (e.g.
        # "MAPK1/MAPK3" for ERK1/2) as the value, but MUST stay AMBIGUOUS -- a
        # multi-gene family is not a settled canonical value (invariant #3), so
        # it never renders as SUPPORTED and surfaces for review.
        canonical = EvidenceField(
            value=res.canonical, confidence=0.5, status=AMBIGUOUS,
            sources=[Source(type="uniprot_reference", rank=RANK_REFERENCE, text="ambiguous_family")],
            candidates=cands,
        ) if res.canonical else EvidenceField.ambiguous(cands)
        uniprot = EvidenceField.ambiguous(cands)   # accession NOT chosen
    else:
        canonical = EvidenceField.missing()
        uniprot = EvidenceField.missing()
    return TargetInfo(raw_target_name=raw_target, canonical_target=canonical, uniprot_id=uniprot,
                      aliases_used_in_paper=aliases)


def _phospho_specific_field(detection_abs, mod_fields) -> EvidenceField:
    for ab in detection_abs:
        if ab.get("phospho_specific") is True:
            return EvidenceField.supported(True, 0.9, [Source(
                type="antibody", rank=RANK_ANTIBODY, text=ab.get("source", {}).get("text", ""))])
        m = biology.antibody_modification(ab.get("target", ""))
        if m["modification_type"] == "phosphorylation":
            return EvidenceField.supported(True, 0.85, [Source(
                type="antibody", rank=RANK_ANTIBODY, text=ab.get("target", ""))])
    return EvidenceField.missing()


def _experiment_info(core, caption, methods, mod_fields, ip_abs, lane_text: str = "") -> ExperimentInfo:
    text_blob = f"{caption}\n{methods}"
    flags: list[str] = []
    sources: list[Source] = []

    # co-IP requires PANEL-SCOPED evidence: an IP-role antibody claim, co-IP
    # wording in this panel's caption, or IP:/IgG/input markers printed on the
    # panel's own lanes. A methods paragraph mentioning immunoprecipitation is
    # page-level context — real papers discuss their co-IP next to unrelated
    # expression blots, and that wording must NOT reclassify every panel on the
    # page (it mislabeled whole autophagy/mTOR panels as co_ip). Methods-only
    # mentions are preserved as a non-settling "co_ip_context" flag.
    panel_scoped = f"{caption}\n{lane_text}"
    if ip_abs:
        flags.append("co_ip")
        ab0 = ip_abs[0]
        sources.append(Source(type="antibody", rank=RANK_ANTIBODY,
                              text=ab0.get("source", {}).get("text", ab0.get("target", "IP antibody"))))
    elif biology._CO_IP.search(panel_scoped):
        m = biology._CO_IP.search(panel_scoped)
        flags.append("co_ip")
        sources.append(Source(type="figure_caption", rank=RANK_CAPTION,
                              text=_around(panel_scoped, m.start())))
    elif biology._IP_LANE.search(lane_text):
        m = biology._IP_LANE.search(lane_text)
        flags.append("co_ip")
        sources.append(Source(type="figure_caption", rank=RANK_CAPTION,
                              text=_around(lane_text, m.start())))
    elif biology._CO_IP.search(methods):
        m = biology._CO_IP.search(methods)
        flags.append("co_ip_context")
        sources.append(Source(type="methods", rank=RANK_METHODS, text=_around(methods, m.start())))
    if biology._PURIFIED.search(text_blob):
        flags.append("purified_protein")
    if biology.is_loading_control(core):
        flags.append("loading_control")

    mtype = mod_fields["modification_type"]
    mod_conflicted = mtype.status in (CONFLICTING, AMBIGUOUS)
    is_phospho = (mtype.status == SUPPORTED and mtype.value == "phosphorylation")
    if is_phospho:
        flags.append("phospho_western")

    # Primary label + confidence, degraded when the modification is unsettled.
    if "co_ip" in flags:
        primary, conf, status = "co_ip", 0.9, SUPPORTED
    elif "purified_protein" in flags:
        primary, conf, status = "purified_protein", 0.85, SUPPORTED
    elif "loading_control" in flags:
        primary, conf, status = "loading_control", 0.9, SUPPORTED
    elif mod_conflicted:
        # modification dispute propagates: don't assert phospho vs standard.
        primary, conf, status = None, 0.4, AMBIGUOUS
    elif is_phospho:
        primary, conf, status = "phospho_western", 0.9, SUPPORTED
    elif biology._looks_like_western(caption, methods):
        primary, conf, status = "standard_western", 0.55, SUPPORTED
        flags.append("standard_western")
    else:
        primary, conf, status = None, 0.2, MISSING

    exp_type = EvidenceField(value=primary, confidence=conf, status=status, sources=sources)
    exp_flags = EvidenceField.supported(sorted(set(flags)), conf, sources) if flags else EvidenceField.missing()

    ip_bait = EvidenceField.missing()
    if "co_ip" in flags:
        bait = None
        bait_src = None
        panel_co_ip = biology._CO_IP.search(panel_scoped)
        if ip_abs:
            bait = biology.core_symbol(ip_abs[0].get("target", ""))
            bait_src = Source(type="antibody", rank=RANK_ANTIBODY,
                              text=ip_abs[0].get("source", {}).get("text", ip_abs[0].get("target", "")))
        elif panel_co_ip:
            # best-effort bait from the panel-scoped text only (same scoping
            # rule as the classification itself).
            bait = _first_gene_after(panel_scoped, panel_co_ip.end())
            bait_src = Source(type="figure_caption", rank=RANK_CAPTION,
                              text=_around(panel_scoped, panel_co_ip.start()))
        if bait:
            ip_bait = EvidenceField.supported(bait, 0.75, [bait_src])
    return ExperimentInfo(experiment_type=exp_type, experiment_flags=exp_flags, ip_bait_protein=ip_bait)


def _sample_info(mc, caption) -> SampleInfo:
    sample_val = mc.get("sample") or mc.get("cell_line")
    cell_line = mc.get("cell_line") or mc.get("sample")
    org = mc.get("organism")
    src_sample = [Source(type="figure_caption", rank=RANK_CAPTION, text=_snippet(caption, str(sample_val or "")))]
    sample_f = EvidenceField.supported(sample_val, 0.9, src_sample) if sample_val else EvidenceField.missing()
    cell_f = EvidenceField.supported(cell_line, 0.9, src_sample) if cell_line else EvidenceField.missing()
    if not org and cell_line:
        org = CELL_LINE_ORGANISM.get(str(cell_line).lower())
        if org:
            organism_f = EvidenceField.supported(
                org, 0.8, [Source(type="deterministic", rank=RANK_DETERMINISTIC,
                                  text=f"{cell_line} -> {org} (cell-line table)")])
        else:
            organism_f = EvidenceField.missing()
    elif org:
        organism_f = EvidenceField.supported(org, 0.85, src_sample)
    else:
        organism_f = EvidenceField.missing()
    return SampleInfo(sample=sample_f, cell_line=cell_f, organism=organism_f,
                      tissue=EvidenceField.missing(), genotype=EvidenceField.missing())


def _series_fields(values: list[dict], ctx: str, det: list[Source],
                   multi_marker: bool) -> tuple[EvidenceField, EvidenceField]:
    """(value_field, unit_field) for a dose or duration series.

    ONE stated value -> SUPPORTED scalar, as before.
    MORE THAN ONE (a dose-response / time course, or two agents at different
    units) -> the panel-level scalar is NOT attributable to any single lane, so
    it becomes **value=None, status=AMBIGUOUS** with every stated value kept as
    a candidate. Taking values[0] used to report the CL-E dose (60 ug/ml) as the
    IL-6 dose, and 60 min as THE duration of a 0-60 min time course. The
    lane-level values live on each BandObservation; the DB scalar goes NULL
    rather than asserting a wrong one (null > misleading value).
    """
    if not values:
        return EvidenceField.missing(), EvidenceField.missing()
    distinct = {(v["value"], v["unit"].lower()) for v in values}
    if len(distinct) == 1 and not multi_marker:
        return (EvidenceField.supported(values[0]["value"], 0.85, det),
                EvidenceField.supported(values[0]["unit"], 0.85, det))
    # source_type "lane_series": these are per-lane values of a varied design
    # (time course / dose series), NOT mutually competing claims about one
    # scalar. Consumers must render them as "varies by lane", never as a
    # pick-a-winner candidate list (manual-beta P0 finding).
    cands = [
        Candidate(value=v["value"], source_type="lane_series", rank=RANK_DETERMINISTIC,
                  confidence=0.5,
                  evidence=[Source(type="deterministic", rank=RANK_DETERMINISTIC,
                                   text=f'{v["value"]} {v["unit"]} — {ctx[:160]}')])
        for v in values
    ]
    units = {v["unit"] for v in values}
    value_f = EvidenceField(value=None, confidence=0.0, status=AMBIGUOUS,
                            sources=det, candidates=cands)
    unit_f = (EvidenceField.supported(next(iter(units)), 0.85, det) if len(units) == 1
              else EvidenceField(value=None, confidence=0.0, status=AMBIGUOUS,
                                 sources=det,
                                 candidates=[Candidate(value=u, source_type="deterministic",
                                                       rank=RANK_DETERMINISTIC, confidence=0.5)
                                             for u in sorted(units)]))
    return value_f, unit_f


def _treatment_info(mc) -> TreatmentInfo:
    ctx = mc.get("treatment_context") or ""
    name = mc.get("treatment_name")
    # Series-aware: enumerations ("10, 30 and 60 ug/ml", "0, 5, 10, 30, 60 min")
    # are expanded so multiplicity is visible instead of silently collapsed.
    doses = extract_dose_series(ctx)
    durs = extract_duration_series(ctx)
    # "for the indicated times/doses" says the panel varies THAT quantity per
    # lane even when only one value is parseable -> never settle that scalar.
    # Kind-specific: a time course's single stimulus concentration stays settled.
    src = [Source(type="figure_caption", rank=RANK_CAPTION, text=ctx)] if ctx else []
    det = [Source(type="deterministic", rank=RANK_DETERMINISTIC, text=ctx)] if ctx else []
    dose_f, dose_unit_f = _series_fields(
        doses, ctx, det, bool(biology._INDICATED_DOSE.search(ctx)))
    dur_f, dur_unit_f = _series_fields(
        durs, ctx, det, bool(biology._INDICATED_TIME.search(ctx)))
    return TreatmentInfo(
        treatment_name=EvidenceField.supported(name, 0.8, src) if name else EvidenceField.missing(),
        dose=dose_f,
        dose_unit=dose_unit_f,
        duration=dur_f,
        duration_unit=dur_unit_f,
        treatment_context=EvidenceField.supported(ctx, 0.8, src) if ctx else EvidenceField.missing(),
    )


def _antibody_info(ab, row_core, mod_fields) -> AntibodyInfo:
    text = ab.get("source", {}).get("text", "")
    vendor = ab.get("vendor")
    if vendor:
        for key, label in biology.VENDORS.items():
            if key in vendor.lower():
                vendor = label
                break
    catalog = ab.get("catalog")
    detection_conf = 0.6
    if catalog:
        detection_conf += 0.2
    if vendor:
        detection_conf += 0.15
    detection_conf = min(detection_conf, 0.98)

    assoc = _association_confidence(ab, row_core, mod_fields)
    src = [Source(type="methods", rank=RANK_METHODS, text=text)] if text else []
    mk = lambda v, c=0.9: EvidenceField.supported(v, c, src) if v else EvidenceField.missing()
    ab_mod = biology.antibody_modification(ab.get("target", ""))
    phospho_specific = ab.get("phospho_specific")
    if phospho_specific is None:
        phospho_specific = ab_mod["modification_type"] == "phosphorylation"
    return AntibodyInfo(
        role=ab.get("role", "detection"),
        antibody_target=mk(ab.get("target")),
        vendor=mk(vendor),
        catalog_number=mk(catalog, detection_conf),
        clone=mk(ab.get("clone")),
        dilution=mk(ab.get("dilution")),
        phospho_specific=EvidenceField.supported(bool(phospho_specific), 0.85, src)
        if ab.get("target") else EvidenceField.missing(),
        detection_confidence=round(detection_conf, 2),
        association_confidence=round(assoc, 2),
    )


def _association_confidence(ab, row_core, mod_fields) -> float:
    ab_core = biology.core_symbol(ab.get("target", ""))
    if not ab_core:
        return 0.2
    if ab_core.lower() != row_core.lower():
        return 0.3                       # antibody is for a different protein
    ab_mod = biology.antibody_modification(ab.get("target", ""))["modification_type"]
    mtype = mod_fields["modification_type"]
    if mtype.status == CONFLICTING:
        return 0.6                       # can't confirm association while modification disputed
    row_mod = mtype.value if mtype.status == SUPPORTED else None
    if ab_mod == row_mod:
        return 0.92                      # same protein + same modification state
    return 0.5                           # same protein, modification mismatch


def _kda_near_core(core: str, text: str) -> float | None:
    """A kDa figure counts as REPORTED for this target only when it appears
    near a mention of the target's core symbol. A page blob's first kDa number
    (ladder descriptions, other rows' masses) must never be attributed to every
    row on the page — that fabricated e.g. 'BEX2 reported 70 kDa' (vs expected
    15.3) and flagged false MW discrepancies on the co-IP paper."""
    if not core or not text:
        return None
    low, core_low = text.lower(), core.lower()
    idx = low.find(core_low)
    while idx != -1:
        window = text[max(0, idx - 30): idx + len(core) + 60]
        val = extract_kda(window)
        if val is not None:
            return val
        idx = low.find(core_low, idx + 1)
    return None


def _mw_info(caption, methods, res, core: str = "") -> MolecularWeightInfo:
    reported = _kda_near_core(core, caption)
    if reported is None:
        reported = _kda_near_core(core, methods)
    if reported is None and caption and core and core.lower() not in caption.lower():
        # Core absent from a short caption -> the caption is plausibly about
        # this single target row anyway (same fallback rule as _scoped_site).
        # Applies to the CAPTION only, never the page-level methods blob.
        reported = extract_kda(caption)
    reported_f = EvidenceField.supported(
        reported, 0.8, [Source(type="figure_caption", rank=RANK_CAPTION, text=f"{reported} kDa")]) \
        if reported is not None else EvidenceField.missing()
    expected = res.expected_mass_kda
    expected_f = EvidenceField.supported(
        expected, 0.9, [Source(type="uniprot_reference", rank=RANK_REFERENCE,
                               text=f"{res.uniprot_id} {expected} kDa (expected)")]) \
        if expected is not None else EvidenceField.missing()
    recon = "not_comparable"
    if reported is not None and expected is not None:
        recon = "match" if abs(reported - expected) / expected <= 0.2 else "discrepancy"
    return MolecularWeightInfo(reported_kda=reported_f, expected_kda=expected_f, reconciliation=recon)


def _pattern_near_core(core: str, text: str) -> Optional[dict]:
    """Band-pattern wording that belongs to THIS target, not to the page.

    Same scoping discipline as reported-MW and co-IP classification: a caption
    sentence like "LC3B resolved as a doublet" must not mark the ACTB row on the
    same panel as a doublet. Only wording within a window around a mention of
    this target's core symbol counts; if the core is never mentioned, no
    page-level pattern is adopted at all.
    """
    if not core or not text:
        return None
    # Clause-scoped, not window-scoped: a sliding character window bleeds across
    # "LC3B resolved as a doublet, while ACTB was the loading control" and marks
    # ACTB a doublet. Captions delimit targets with clause punctuation and
    # contrastive conjunctions, so only the clause naming THIS target counts.
    import re as _re
    core_low = core.lower()
    # Parentheses and "and" also delimit per-target phrasing: "probed for LC3B
    # (doublet) and ACTB" must not hand ACTB the doublet (review finding).
    for clause in _re.split(r"[;.()]|,|\bwhile\b|\bwhereas\b|\band\b", text):
        if clause and core_low in clause.lower():
            hit = biology.detect_band_pattern(clause)
            if hit:
                return hit
    return None


def _band_pattern_fields(b: dict, core: str, caption: str, lane_text: str,
                         n_lanes: int = 1):
    """(pattern, count, notes) EvidenceFields for one band observation.

    Precedence: an explicit observer claim on the row, then this lane's own
    printed text, then target-scoped caption wording. Nothing is inferred from
    the protein's identity or from the number of rows in the panel.
    """
    claim = b.get("band_pattern")
    caption_derived = False
    if claim and str(claim).lower() in biology.BAND_PATTERNS:
        pattern = str(claim).lower()
        raw = str(b.get("band_notes") or claim)
        count = b.get("band_count")
        src = [Source(type="image", rank=5, text=raw)]
        conf = 0.75
        hedged = pattern == "uncertain"
    else:
        lane_hit = biology.detect_band_pattern(lane_text)
        hit = lane_hit or _pattern_near_core(core, caption)
        if not hit:
            return (EvidenceField.missing(), EvidenceField.missing(), EvidenceField.missing())
        caption_derived = lane_hit is None
        pattern, count, raw = hit["pattern"], hit["count"], hit["raw"]
        hedged = hit["hedged"]
        src = [Source(type="figure_caption", rank=RANK_CAPTION, text=raw)]
        conf = 0.6 if hedged else 0.8
    # A caption describes the PANEL; on a multi-lane panel it cannot settle any
    # single lane's pattern ("a doublet appeared after rapamycin" must not
    # stamp the DMSO lane as SUPPORTED doublet — review finding B3). Same
    # panel-vs-lane discipline as the dose/duration scalars.
    if caption_derived and n_lanes > 1:
        hedged = True
        conf = min(conf, 0.5)
    pattern_f = (EvidenceField(value=pattern, confidence=conf, status=AMBIGUOUS, sources=src)
                 if hedged or pattern == "uncertain"
                 else EvidenceField.supported(pattern, conf, src))
    count_f = (EvidenceField.supported(int(count), conf, src)
               if isinstance(count, int) else EvidenceField.missing())
    notes_f = EvidenceField.supported(raw, conf, src) if raw else EvidenceField.missing()
    return pattern_f, count_f, notes_f


def _bands(mc, core: str = "", caption: str = "") -> list[BandObservation]:
    out = []
    for b in mc.get("bands", []):
        cond = b.get("lane_condition")
        cond_text = str(cond or "")
        # Lane-specific dose/duration, read ONLY from this lane's own printed
        # condition ("30 min", "IL-6 + / CL-E 30"). Ambiguous within one lane
        # (>1 value) -> leave MISSING rather than pick one. Never inferred from
        # the panel-level blob.
        lane_src = [Source(type="figure_caption", rank=RANK_CAPTION, text=cond_text)]
        lane_doses = extract_dose_series(cond_text)
        lane_durs = extract_duration_series(cond_text)
        lane_dose_f = lane_dose_unit_f = EvidenceField.missing()
        lane_dur_f = lane_dur_unit_f = EvidenceField.missing()
        if len(lane_doses) == 1:
            lane_dose_f = EvidenceField.supported(lane_doses[0]["value"], 0.8, lane_src)
            lane_dose_unit_f = EvidenceField.supported(lane_doses[0]["unit"], 0.8, lane_src)
        if len(lane_durs) == 1:
            lane_dur_f = EvidenceField.supported(lane_durs[0]["value"], 0.8, lane_src)
            lane_dur_unit_f = EvidenceField.supported(lane_durs[0]["unit"], 0.8, lane_src)
        pattern_f, count_f, notes_f = _band_pattern_fields(
            b, core, caption, cond_text, n_lanes=len(mc.get("bands", [])))
        out.append(BandObservation(
            lane_index=b.get("lane_index", 1),
            lane_condition=EvidenceField.supported(cond, 0.8, lane_src)
            if cond else EvidenceField.missing(),
            band_state=EvidenceField.supported(
                b.get("band_state"), _band_conf(b.get("confidence")),
                [Source(type="image", rank=5, text="image")]) if b.get("band_state") else EvidenceField.missing(),
            lane_dose=lane_dose_f,
            lane_dose_unit=lane_dose_unit_f,
            lane_duration=lane_dur_f,
            lane_duration_unit=lane_dur_unit_f,
            band_pattern=pattern_f,
            band_count=count_f,
            band_notes=notes_f,
        ))
    return out


# --------------------------------------------------------------------------- #
# Validation / anomaly flags
# --------------------------------------------------------------------------- #

def _validate(record: EvidenceRecord, detection_abs, mod_fields) -> ValidationInfo:
    flags: list[AnomalyFlag] = []
    mtype = record.modification.modification_type

    if mtype.status == CONFLICTING:
        flags.append(AnomalyFlag(code="MODIFICATION_CONFLICT", severity="high",
                                 detail="Sources disagree on whether this is a modified or total protein.",
                                 evidence=[s for c in mtype.candidates for s in c.evidence][:4]))
    if record.modification.residue.status == CONFLICTING:
        flags.append(AnomalyFlag(code="RESIDUE_CONFLICT", severity="high",
                                 detail="Different phospho-sites are claimed for this target."))

    # antibody target vs reconciled modification mismatch
    row_mod = mtype.value if mtype.status == SUPPORTED else "disputed"
    for ab in detection_abs:
        ab_mod = biology.antibody_modification(ab.get("target", ""))["modification_type"]
        if mtype.status == SUPPORTED and ab_mod != mtype.value:
            flags.append(AnomalyFlag(code="ANTIBODY_TARGET_MISMATCH", severity="med",
                                     detail=f"Detection antibody implies {ab_mod or 'total'} but record "
                                            f"modification is {mtype.value or 'total'}."))
            break
        if mtype.status == CONFLICTING:
            flags.append(AnomalyFlag(code="ANTIBODY_TARGET_MISMATCH", severity="med",
                                     detail="Antibody indicates a modification that conflicts with the row label."))
            break

    # A band reported ABSENT cannot simultaneously show a visible structure
    # pattern (doublet/multiple/ladder/smear/single) — flag the contradiction
    # instead of shipping it silently (review finding B4).
    for band in record.bands:
        pat = band.band_pattern.value
        if pat and pat != "uncertain" and band.band_state.value == "absent":
            flags.append(AnomalyFlag(
                code="BAND_PATTERN_STATE_MISMATCH", severity="med",
                detail=f"Lane '{band.lane_condition.value or band.lane_index}' is "
                       f"absent yet carries band_pattern '{pat}'."))
            break

    if record.experiment.experiment_type.status == AMBIGUOUS:
        flags.append(AnomalyFlag(code="EXPERIMENT_TYPE_AMBIGUOUS", severity="med",
                                 detail="Experiment type is unsettled (often downstream of a modification conflict)."))
    if record.target.canonical_target.status == AMBIGUOUS:
        flags.append(AnomalyFlag(code="PROTEIN_AMBIGUOUS", severity="med",
                                 detail="Protein name maps to more than one reviewed UniProt entry."))
    if record.molecular_weight.reconciliation == "discrepancy":
        flags.append(AnomalyFlag(code="MW_DISCREPANCY", severity="med",
                                 detail="Reported migration differs from the expected (UniProt) mass."))

    severities = {f.severity for f in flags}
    if any(f.code in ("MODIFICATION_CONFLICT", "RESIDUE_CONFLICT") for f in flags):
        status = CONFLICTING
    elif "med" in severities or record.experiment.experiment_type.status == AMBIGUOUS:
        status = AMBIGUOUS
    else:
        status = SUPPORTED
    return ValidationInfo(record_status=status, anomaly_flags=flags, needs_review=status != SUPPORTED)


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #

def _paper_ref(p: dict) -> PaperRef:
    def f(key):
        v = p.get(key)
        return EvidenceField.supported(v, 0.99, [Source(type="deterministic", rank=RANK_DETERMINISTIC, text=str(v))]) \
            if v else EvidenceField.missing()
    return PaperRef(pmid=f("pmid"), pmcid=f("pmcid"), doi=f("doi"), title=f("title"),
                    authors=f("authors"), source_url=f("source_url"))


def _figure_ref(fig: dict, caption: str) -> FigureRef:
    def f(key):
        v = fig.get(key)
        return EvidenceField.supported(v, 0.95, [Source(type="figure_caption", rank=RANK_CAPTION, text=str(v))]) \
            if v else EvidenceField.missing()
    return FigureRef(figure_label=f("figure_label"), panel_label=f("panel_label"),
                     page=fig.get("page"), caption_text=caption or fig.get("caption_text", ""),
                     image_crop_ref=fig.get("image_crop_ref"))


def _band_conf(c) -> float:
    if isinstance(c, (int, float)):
        return float(c)
    return {"high": 0.9, "medium": 0.6, "low": 0.3}.get(str(c).lower(), 0.6)


def _snippet(text: str, needle: str, width: int = 70) -> str:
    if not text:
        return ""
    if needle:
        i = text.lower().find(needle.lower())
        if i != -1:
            return text[max(0, i - 20): i + len(needle) + width].strip()
    return text[:width].strip()


def _around(text: str, pos: int, width: int = 60) -> str:
    return text[max(0, pos - 10): pos + width].strip()


def _first_gene_after(text: str, pos: int) -> Optional[str]:
    import re
    m = re.search(r"anti-?([A-Z][A-Za-z0-9]{1,7})", text[pos: pos + 60])
    if m:
        return biology.core_symbol(m.group(1))
    m = re.search(r"\b([A-Z]{2,}[0-9]?)\b", text[pos: pos + 40])
    return m.group(1) if m else None


def identity_sample(mc: dict) -> str:
    """The biological system this evidence came from, normalized for identity.

    Same precedence as `_sample_info`, so the experiment identity and the
    SAMPLE the UI prints can never disagree about which system a row belongs
    to. Case- and whitespace-folded because `H1792`, `h1792` and ` H1792 ` are
    the same cell line and a reviewer re-typing one must not orphan feedback.

    Deliberately NOT applied to target labels: in this codebase case is
    semantic there (uppercase `P-` is not a phospho marker, lowercase `p-`
    is), so folding a target would merge biologically distinct rows.
    """
    val = mc.get("sample") or mc.get("cell_line") or ""
    return " ".join(str(val).split()).casefold()


def _record_id(case: dict, raw_target: str) -> str:
    """Deterministic experiment identity — the unit researcher feedback keys to.

    Every input is reviewed OBSERVATION data (what the paper printed), never a
    DB serial and never a reconciliation OUTPUT. That is the whole design:
    reconciliation results (modification_label, experiment_type, ip_bait,
    protein_status, confidence) legitimately change when the engine improves,
    and if they fed the identity every stored correction would orphan itself on
    the next fix. Display-layer text never reaches here either, so reformatting
    a lane label cannot move a key.

    Components, and why each earns its place:
      * paper (doi/pmcid/pmid) — which source
      * figure_label, panel_label, crop filename — which blot in that source
      * raw_target — which row of that blot, as printed
      * treatment_context — separates two experiments sharing one crop and one
        target label (Fig 3C vs 3D total-STAT3 in PMC12856536)
      * sample/cell line — separates two experiments sharing crop, target AND
        treatment but run in different biological systems

    The sample component fixes a P0 identity collision: crop
    `page_004_cand_0025.png` in PMC12706926 prints H1792 and A549 side by side,
    so P62, LC3B and ACTB each produced ONE id for TWO biologically distinct
    experiments (12 duplicate stable keys over 24 rows). Search grouping had
    always split those two cards on cell line while the identity did not —
    two disagreeing notions of "one experiment" was the underlying flaw, and
    feedback left on the H1792 arm could surface on the A549 arm.

    Lane identity lives OUTSIDE this hash: `stable_row_key` is
    `<record_id>:<lane_index>`. Lane index is the reviewed panel's own left-to-
    right order — stable across reseeds and immune to lane-label reformatting,
    which the printed condition text is not.
    """
    paper = case.get("paper", {})
    fig = case.get("figure", {})
    mc = case.get("model_claims", {})
    crop = fig.get("image_crop_ref")
    crop_name = str(crop).rsplit("/", 1)[-1] if crop else None
    key = "|".join(str(x) for x in [
        paper.get("doi") or paper.get("pmcid") or paper.get("pmid"),
        fig.get("figure_label"), fig.get("panel_label"), crop_name,
        raw_target, mc.get("treatment_context") or "",
        identity_sample(mc),
    ])
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
