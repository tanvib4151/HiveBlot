from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=100, ge=1, le=500)


class WesternBlotRecord(BaseModel):
    # NOTE: fields are strictly ADDITIVE and every new one is Optional with a
    # default of None. The DB returns every column via `SELECT *`; anything not
    # declared here is silently dropped by Pydantic (that is exactly why the
    # Evidence Record columns from migration 001 never reached the browser).
    # Legacy rows have NULLs in all the new columns + needs_review=true by
    # design, so they must render as "not reported", never as fabricated data.
    id: int
    paper_id: str
    page: int | None = None
    western_blot_type: str | None = None
    sample: str | None = None
    organism: str | None = None
    treatment_context: str | None = None
    figure_label: str | None = None
    target: str | None = None
    condition: str | None = None
    band_detected: bool | None = None
    # Settled: confidence is a 0-1 score everywhere - `real` in
    # db/schema.sql, REAL in the nlp.py prompt schema, `number` in the
    # frontend (which renders it as `confidence * 100`%). An extraction
    # pipeline that produces "high"/"medium"/"low" must map to a score
    # before insert; don't reintroduce a text column on one side only.
    confidence: float | None = None

    # --- Evidence Record fields (migration 001, additive) -------------------
    # Paper provenance
    pmid: str | None = None
    pmcid: str | None = None
    doi: str | None = None
    title: str | None = None
    authors: str | None = None
    source_url: str | None = None
    # Figure
    panel_label: str | None = None
    figure_caption: str | None = None
    image_crop_ref: str | None = None
    # Protein identity
    raw_target_name: str | None = None
    canonical_target: str | None = None
    uniprot_id: str | None = None
    protein_status: str | None = None  # SUPPORTED / AMBIGUOUS / CONFLICTING / MISSING
    # Modification (phospho, cleavage, ...). value is NULL when CONFLICTING.
    modification_type: str | None = None
    residue: str | None = None
    residue_position: int | None = None
    modification_label: str | None = None  # e.g. "phospho-Tyr705"
    modification_status: str | None = None
    phospho_specific_antibody: bool | None = None
    # Experiment. experiment_flags is non-exclusive (co_ip + phospho can coexist).
    experiment_type: str | None = None
    experiment_flags: list[str] | None = None
    experiment_type_confidence: float | None = None
    # Sample extras
    cell_line: str | None = None
    tissue: str | None = None
    genotype: str | None = None
    # Treatment (deterministic parse; never invented)
    treatment_name: str | None = None
    dose: float | None = None
    dose_unit: str | None = None
    duration: float | None = None
    duration_unit: str | None = None
    # Antibody (UCSF researchers care about this a lot)
    antibody_target: str | None = None
    antibody_vendor: str | None = None
    antibody_catalog_number: str | None = None
    antibody_clone: str | None = None
    antibody_dilution: str | None = None
    # Band / MW. Keep expected != reported (never conflate); band_state is
    # categorical present/absent/uncertain, NOT densitometry.
    band_state: str | None = None
    lane_condition: str | None = None
    loading_control: bool | None = None
    reported_molecular_weight_kda: float | None = None
    expected_molecular_weight_kda: float | None = None
    molecular_weight_source: str | None = None
    # Validation / review. The full per-field `provenance` and `validation`
    # JSONB envelopes are intentionally NOT surfaced here (they are the entire
    # record dump); a dedicated record-detail endpoint serves them so list
    # responses stay small ("avoid giant internal blobs by default").
    anomaly_flags: list[dict] | None = None
    needs_review: bool | None = None
    extraction_stage: str | None = None
    extraction_model: str | None = None

    # Reseed-proof identity: `<experiment hash>:<lane index>` (migration 003).
    # Surfaced on list rows too — not only on RecordDetail — so the search UI
    # groups lanes into cards by the SAME experiment identity that researcher
    # feedback keys to. Deriving the card boundary from a separate composite
    # key is what let grouping and identity disagree (the H1792/A549 co-IP
    # collision); one source of truth removes that whole failure class.
    stable_row_key: str | None = None


class SearchResponse(BaseModel):
    question: str
    generated_sql: str
    count: int
    results: list[WesternBlotRecord]


# --- record detail ("Why does HiveBlot say this?") --------------------------

class FieldEvidence(BaseModel):
    """One biological field with its evidence envelope. This is the unit of
    the trust story: value + status + the actual source snippets, plus the
    competing candidates whenever the field is AMBIGUOUS/CONFLICTING (a
    disputed field keeps value=null and shows both claims — disagreement is
    never hidden)."""
    value: object = None
    confidence: float | None = None
    status: str | None = None       # SUPPORTED / AMBIGUOUS / CONFLICTING / MISSING
    sources: list[dict] = []        # [{type, text}] — provenance snippets
    candidates: list[dict] = []     # [{value, source_type, confidence}] when unsettled


class RecordAntibody(BaseModel):
    target: str | None = None
    vendor: str | None = None
    catalog_number: str | None = None
    clone: str | None = None
    dilution: str | None = None
    role: str | None = None          # detection | immunoprecipitation
    phospho_specific: bool | None = None
    detection_confidence: float | None = None
    association_confidence: float | None = None
    source_text: str | None = None


class RecordBand(BaseModel):
    lane_index: int | None = None
    lane_condition: str | None = None
    band_state: str | None = None    # present / absent / uncertain — categorical, not densitometry
    confidence: float | None = None
    # Lane-specific design, parsed only from this lane's own printed condition.
    # A dose-response / time course keeps its real per-lane values here while
    # the panel-level scalar stays AMBIGUOUS (never collapsed to one value).
    lane_dose: str | None = None
    lane_duration: str | None = None
    # Descriptive multiplicity, additive to band_state (a smeared band is still
    # `present`). Null = the source did not say, NOT "single band".
    band_pattern: str | None = None
    band_pattern_status: str | None = None
    band_count: int | None = None
    band_notes: str | None = None


class RecordDetail(BaseModel):
    """Full provenance view of ONE record. List responses stay lean; this is
    where the complete evidence story lives."""
    id: int
    stable_row_key: str | None = None  # reseed-proof identity for feedback
    # source identity
    paper_id: str | None = None
    title: str | None = None
    doi: str | None = None
    pmcid: str | None = None
    pmid: str | None = None
    figure_label: str | None = None
    panel_label: str | None = None
    page: int | None = None
    figure_caption: str | None = None
    image_crop_ref: str | None = None
    # biological scalars (settled values; null when disputed/missing)
    raw_target_name: str | None = None
    canonical_target: str | None = None
    uniprot_id: str | None = None
    modification_label: str | None = None
    experiment_type: str | None = None
    cell_line: str | None = None
    organism: str | None = None
    sample: str | None = None
    band_state: str | None = None
    lane_condition: str | None = None
    reported_molecular_weight_kda: float | None = None
    expected_molecular_weight_kda: float | None = None
    molecular_weight_source: str | None = None
    # field-level evidence envelopes for the important fields
    fields: dict[str, FieldEvidence] = {}
    antibodies: list[RecordAntibody] = []
    bands: list[RecordBand] = []
    # validation
    record_status: str | None = None
    needs_review: bool | None = None
    anomaly_flags: list[dict] = []


# --- researcher feedback -----------------------------------------------------

FEEDBACK_SCOPES = {"field", "record", "missing_field", "search", "ui"}
FIELD_FEEDBACK_TYPES = {"correct", "incorrect", "not_useful", "missing_context"}
RECORD_FEEDBACK_TYPES = {
    "wrong_interpretation", "wrong_experiment_type", "wrong_target_modification",
    "wrong_phosphosite", "wrong_antibody_association", "wrong_figure_association",
    "missing_methods_context", "irrelevant_result", "other",
}
SEARCH_FEEDBACK_TYPES = {"understood_yes", "understood_partially", "understood_no"}


class FeedbackSubmission(BaseModel):
    """One piece of researcher feedback. Stored in hiveblot_feedback (migration
    002) beside — never over — the AI extraction. suggested_value is a human
    CORRECTION CLAIM for audit + future eval; it is never auto-applied."""
    feedback_scope: str
    record_id: int | None = None
    # Reseed-proof identity (migration 003): survives DB reloads where the
    # serial record_id does not. Sent by the evidence panel when available.
    stable_row_key: str | None = Field(default=None, max_length=100)
    paper_id: str | None = Field(default=None, max_length=200)
    figure_label: str | None = Field(default=None, max_length=100)
    search_query: str | None = Field(default=None, max_length=500)
    field_name: str | None = Field(default=None, max_length=100)
    model_value: str | None = Field(default=None, max_length=1000)
    feedback_type: str | None = Field(default=None, max_length=50)
    suggested_value: str | None = Field(default=None, max_length=1000)
    comment: str | None = Field(default=None, max_length=4000)
    ui_location: str | None = Field(default=None, max_length=200)
    session_id: str | None = Field(default=None, max_length=64)

    def validate_scope(self) -> str | None:
        """Scope-specific requirements; returns an error string or None."""
        s = self.feedback_scope
        if s not in FEEDBACK_SCOPES:
            return f"feedback_scope must be one of {sorted(FEEDBACK_SCOPES)}"
        if s == "field":
            if self.record_id is None or not self.field_name:
                return "field feedback requires record_id and field_name"
            if self.feedback_type not in FIELD_FEEDBACK_TYPES:
                return f"field feedback_type must be one of {sorted(FIELD_FEEDBACK_TYPES)}"
        elif s == "record":
            if self.record_id is None:
                return "record feedback requires record_id"
            if self.feedback_type not in RECORD_FEEDBACK_TYPES:
                return f"record feedback_type must be one of {sorted(RECORD_FEEDBACK_TYPES)}"
        elif s == "missing_field":
            if not self.field_name:
                return "missing_field feedback requires field_name (the requested field)"
        elif s == "search":
            if not self.search_query:
                return "search feedback requires search_query"
            if self.feedback_type not in SEARCH_FEEDBACK_TYPES:
                return f"search feedback_type must be one of {sorted(SEARCH_FEEDBACK_TYPES)}"
        elif s == "ui":
            if not self.comment:
                return "ui feedback requires a comment"
        return None


class FeedbackResponse(BaseModel):
    feedback_id: int
    stored: bool = True


class FeedbackItem(BaseModel):
    """One prior researcher-feedback row, for rehydration in the evidence
    panel. Rendered clearly as RESEARCHER FEEDBACK, never mixed into the
    HiveBlot extraction."""
    feedback_id: int
    created_at: str
    feedback_scope: str
    stable_row_key: str | None = None
    field_name: str | None = None
    model_value: str | None = None
    feedback_type: str | None = None
    suggested_value: str | None = None
    comment: str | None = None
    session_id: str | None = None


class RecordFeedbackResponse(BaseModel):
    record_id: int
    items: list[FeedbackItem]


class ProteinSearchResponse(BaseModel):
    protein: str
    count: int
    results: list[WesternBlotRecord]
