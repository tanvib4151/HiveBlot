"""The HiveBlot Evidence Record: structured biological claims with provenance.

Every important biological field is an :class:`EvidenceField` carrying its own
value, confidence, status and evidence sources (correction 4: field-level, not
record-level, confidence). A CONFLICTING field deliberately stores ``value=None``
and preserves the competing candidates, so downstream search never treats a
disputed value as settled (correction 1 from the Phase-3 review).

This module is pure pydantic + stdlib; it has no model/network dependencies and
serializes cleanly via ``model_dump()``.
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel

# --- statuses (plain strings so JSON stays readable) ------------------------
SUPPORTED = "SUPPORTED"
AMBIGUOUS = "AMBIGUOUS"
CONFLICTING = "CONFLICTING"
MISSING = "MISSING"

# --- evidence-hierarchy ranks (lower = stronger) ----------------------------
RANK_ANTIBODY = 1        # explicit antibody target / phospho-specific antibody
RANK_CAPTION = 2         # explicit figure caption
RANK_METHODS = 3         # figure-associated methods
RANK_MODEL_TARGET = 4    # model's structured row target
RANK_IMAGE = 5           # image-only inference
RANK_DETERMINISTIC = 2   # regex over a specific text counts as that text's rank; default caption-ish
RANK_REFERENCE = 1       # external DB (UniProt) for identity/expected-MW


class Source(BaseModel):
    type: str                       # antibody | figure_caption | methods | model_target | image | deterministic | uniprot_reference
    rank: int = RANK_MODEL_TARGET
    text: str = ""                  # verbatim snippet
    locator: Optional[str] = None   # e.g. fig3A_caption / methods_p3


class Candidate(BaseModel):
    """A competing value kept when a field is AMBIGUOUS or CONFLICTING."""
    value: Any = None
    source_type: str = ""
    rank: int = RANK_MODEL_TARGET
    confidence: float = 0.0
    evidence: list[Source] = []


class EvidenceField(BaseModel):
    """The Field envelope. Use the classmethod constructors, not the raw ctor."""
    value: Any = None
    confidence: float = 0.0
    status: str = MISSING
    sources: list[Source] = []
    candidates: list[Candidate] = []

    # -- constructors --------------------------------------------------------
    @classmethod
    def supported(cls, value: Any, confidence: float, sources: list[Source]) -> "EvidenceField":
        return cls(value=value, confidence=confidence, status=SUPPORTED, sources=sources)

    @classmethod
    def missing(cls) -> "EvidenceField":
        return cls(value=None, confidence=0.0, status=MISSING)

    @classmethod
    def ambiguous(cls, candidates: list[Candidate], sources: Optional[list[Source]] = None) -> "EvidenceField":
        # AMBIGUOUS keeps a best-guess value (the top-ranked candidate) but marks it unsettled.
        best = _best_candidate(candidates)
        return cls(
            value=best.value if best else None,
            confidence=best.confidence if best else 0.0,
            status=AMBIGUOUS,
            sources=sources or (best.evidence if best else []),
            candidates=candidates,
        )

    @classmethod
    def conflicting(cls, candidates: list[Candidate]) -> "EvidenceField":
        # CONFLICTING stores NO settled value (correction 1). Candidates + evidence preserved.
        return cls(value=None, confidence=0.0, status=CONFLICTING, sources=[], candidates=candidates)


def _best_candidate(candidates: list[Candidate]) -> Optional[Candidate]:
    if not candidates:
        return None
    return sorted(candidates, key=lambda c: (c.rank, -c.confidence))[0]


# --------------------------------------------------------------------------- #
# Grouped sub-objects
# --------------------------------------------------------------------------- #

class PaperRef(BaseModel):
    pmid: EvidenceField = EvidenceField.missing()
    pmcid: EvidenceField = EvidenceField.missing()
    doi: EvidenceField = EvidenceField.missing()
    title: EvidenceField = EvidenceField.missing()
    authors: EvidenceField = EvidenceField.missing()
    source_url: EvidenceField = EvidenceField.missing()


class FigureRef(BaseModel):
    figure_label: EvidenceField = EvidenceField.missing()
    panel_label: EvidenceField = EvidenceField.missing()
    page: Optional[int] = None
    caption_text: str = ""
    image_crop_ref: Optional[str] = None


class TargetInfo(BaseModel):
    raw_target_name: str                       # verbatim, ALWAYS preserved
    canonical_target: EvidenceField = EvidenceField.missing()
    uniprot_id: EvidenceField = EvidenceField.missing()
    aliases_used_in_paper: list[str] = []


class ModificationInfo(BaseModel):
    modification_type: EvidenceField = EvidenceField.missing()
    residue: EvidenceField = EvidenceField.missing()
    residue_position: EvidenceField = EvidenceField.missing()
    normalized_label: EvidenceField = EvidenceField.missing()
    phospho_specific_antibody: EvidenceField = EvidenceField.missing()


class ExperimentInfo(BaseModel):
    experiment_type: EvidenceField = EvidenceField.missing()
    experiment_flags: EvidenceField = EvidenceField.missing()
    ip_bait_protein: EvidenceField = EvidenceField.missing()


class SampleInfo(BaseModel):
    sample: EvidenceField = EvidenceField.missing()
    cell_line: EvidenceField = EvidenceField.missing()
    organism: EvidenceField = EvidenceField.missing()
    tissue: EvidenceField = EvidenceField.missing()
    genotype: EvidenceField = EvidenceField.missing()


class TreatmentInfo(BaseModel):
    treatment_name: EvidenceField = EvidenceField.missing()
    dose: EvidenceField = EvidenceField.missing()
    dose_unit: EvidenceField = EvidenceField.missing()
    duration: EvidenceField = EvidenceField.missing()
    duration_unit: EvidenceField = EvidenceField.missing()
    treatment_context: EvidenceField = EvidenceField.missing()


class AntibodyInfo(BaseModel):
    role: str = "detection"                    # detection | immunoprecipitation
    antibody_target: EvidenceField = EvidenceField.missing()
    vendor: EvidenceField = EvidenceField.missing()
    catalog_number: EvidenceField = EvidenceField.missing()
    clone: EvidenceField = EvidenceField.missing()
    dilution: EvidenceField = EvidenceField.missing()
    phospho_specific: EvidenceField = EvidenceField.missing()
    detection_confidence: float = 0.0          # was the string found
    association_confidence: float = 0.0         # does it belong to THIS target (correction 3)


class MolecularWeightInfo(BaseModel):
    reported_kda: EvidenceField = EvidenceField.missing()      # observed/reported in text
    expected_kda: EvidenceField = EvidenceField.missing()      # UniProt reference (labeled expected)
    reconciliation: str = "not_comparable"                     # match | discrepancy | not_comparable


class BandObservation(BaseModel):
    lane_index: int
    lane_condition: EvidenceField = EvidenceField.missing()
    band_state: EvidenceField = EvidenceField.missing()        # present | absent | uncertain
    # Lane-specific design, parsed ONLY from this lane's own printed condition
    # text (never inferred from the panel blob). A dose-response or time course
    # keeps its per-lane values here while the panel-level scalar stays
    # AMBIGUOUS/null -- multiple conditions are never collapsed into one scalar.
    lane_dose: EvidenceField = EvidenceField.missing()
    lane_dose_unit: EvidenceField = EvidenceField.missing()
    lane_duration: EvidenceField = EvidenceField.missing()
    lane_duration_unit: EvidenceField = EvidenceField.missing()
    # DESCRIPTIVE band multiplicity -- additive to band_state, never a
    # replacement for it (a smeared band is still `present`). Populated only
    # from explicit source wording or an explicit observer claim; MISSING means
    # "the source did not say", NOT "single band". Deliberately carries no
    # isoform / cleavage / dimer interpretation and no intensity: this is what
    # the blot is reported to SHOW, not what it biochemically means.
    # `band_count` is filled only when a count is literally stated; the
    # EvidenceField envelope supplies status + candidates for both fields.
    band_pattern: EvidenceField = EvidenceField.missing()   # single|doublet|multiple|smear|ladder|uncertain
    band_count: EvidenceField = EvidenceField.missing()     # int, only when explicitly stated
    band_notes: EvidenceField = EvidenceField.missing()     # verbatim supporting wording


class AnomalyFlag(BaseModel):
    code: str
    severity: str = "med"                                       # high | med | low
    detail: str = ""
    evidence: list[Source] = []


class ValidationInfo(BaseModel):
    record_status: str = MISSING              # SUPPORTED | AMBIGUOUS | CONFLICTING | NEEDS_REVIEW
    anomaly_flags: list[AnomalyFlag] = []
    needs_review: bool = True


class ExtractionMeta(BaseModel):
    stage: str = "deterministic+llm"
    backend: str = "unknown"
    model: str = "unknown"
    version: str = "0.3.0"
    escalated: bool = False


class EvidenceRecord(BaseModel):
    record_id: str
    paper: PaperRef = PaperRef()
    figure: FigureRef = FigureRef()
    target: TargetInfo
    modification: ModificationInfo = ModificationInfo()
    experiment: ExperimentInfo = ExperimentInfo()
    sample: SampleInfo = SampleInfo()
    treatment: TreatmentInfo = TreatmentInfo()
    antibodies: list[AntibodyInfo] = []
    molecular_weight: MolecularWeightInfo = MolecularWeightInfo()
    bands: list[BandObservation] = []
    validation: ValidationInfo = ValidationInfo()
    extraction: ExtractionMeta = ExtractionMeta()

    # -- projection to the flat Supabase row (migration 001) -----------------
    def to_supabase_rows(self) -> list[dict[str, Any]]:
        """One flat row per band. Scalar columns take the SETTLED value only:
        CONFLICTING/MISSING fields become NULL so filters never match a disputed
        value. The full field envelopes live in the provenance/validation JSONB.
        """
        det = self.antibodies[0] if self.antibodies else None
        base = {
            "paper_id": _v(self.paper.doi) or _v(self.paper.pmcid),
            "pmid": _v(self.paper.pmid),
            "pmcid": _v(self.paper.pmcid),
            "doi": _v(self.paper.doi),
            "title": _v(self.paper.title),
            "figure_label": _v(self.figure.figure_label),
            "panel_label": _v(self.figure.panel_label),
            "page": self.figure.page,
            "figure_caption": self.figure.caption_text or None,
            "image_crop_ref": self.figure.image_crop_ref,
            "raw_target_name": self.target.raw_target_name,
            "target": self.target.raw_target_name,
            "canonical_target": _v(self.target.canonical_target),
            "uniprot_id": _v(self.target.uniprot_id),
            "protein_status": self.target.canonical_target.status,
            "modification_type": _v(self.modification.modification_type),
            "residue": _v(self.modification.residue),
            "residue_position": _v(self.modification.residue_position),
            "modification_label": _v(self.modification.normalized_label),
            "modification_status": self.modification.modification_type.status,
            "phospho_specific_antibody": _v(self.modification.phospho_specific_antibody),
            "experiment_type": _v(self.experiment.experiment_type),
            "experiment_flags": _v(self.experiment.experiment_flags),
            "experiment_type_confidence": self.experiment.experiment_type.confidence,
            "sample": _v(self.sample.sample),
            "cell_line": _v(self.sample.cell_line),
            "organism": _v(self.sample.organism),
            "tissue": _v(self.sample.tissue),
            "genotype": _v(self.sample.genotype),
            "treatment_name": _v(self.treatment.treatment_name),
            "dose": _v(self.treatment.dose),
            "dose_unit": _v(self.treatment.dose_unit),
            "duration": _v(self.treatment.duration),
            "duration_unit": _v(self.treatment.duration_unit),
            "treatment_context": _v(self.treatment.treatment_context),
            "antibody_target": _v(det.antibody_target) if det else None,
            "antibody_vendor": _v(det.vendor) if det else None,
            "antibody_catalog_number": _v(det.catalog_number) if det else None,
            "antibody_clone": _v(det.clone) if det else None,
            "antibody_dilution": _v(det.dilution) if det else None,
            "reported_molecular_weight_kda": _v(self.molecular_weight.reported_kda),
            "expected_molecular_weight_kda": _v(self.molecular_weight.expected_kda),
            "molecular_weight_source": (
                "uniprot_reference" if _v(self.molecular_weight.expected_kda) is not None else None
            ),
            "provenance": self.model_dump(mode="json"),   # full envelopes for "why did HiveBlot say this?"
            "validation": self.validation.model_dump(mode="json"),
            "anomaly_flags": [a.model_dump(mode="json") for a in self.validation.anomaly_flags],
            "needs_review": self.validation.needs_review,
            "extraction_stage": self.extraction.stage,
            "extraction_model": self.extraction.model,
            "extraction_version": self.extraction.version,
        }
        rows = []
        for band in self.bands or [BandObservation(lane_index=1)]:
            row = dict(base)
            # Stable per-lane identity (record hash + lane index): survives
            # DB reseeds, unlike the serial `id`. Researcher feedback keys on
            # this so corrections rehydrate after any reload (migration 003).
            row["stable_row_key"] = f"{self.record_id}:{band.lane_index}"
            row["lane_condition"] = _v(band.lane_condition)
            row["condition"] = _v(band.lane_condition)
            row["band_state"] = _v(band.band_state)
            row["band_detected"] = _v(band.band_state) == "present"
            row["confidence"] = band.band_state.confidence
            row["loading_control"] = _v(self.experiment.experiment_type) == "loading_control"
            rows.append(row)
        return rows


def _v(field: EvidenceField) -> Any:
    """Settled scalar value, or None if the field is unsettled/absent."""
    if field is None:
        return None
    if field.status in (CONFLICTING, MISSING):
        return None
    return field.value
