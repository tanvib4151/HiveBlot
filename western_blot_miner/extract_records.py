"""Stage-2 semantic extraction -> Evidence Records.

The model (Bedrock by default) reads a figure crop + caption/methods and REPORTS
what it observes as structured claims -- it deliberately does NOT decide the
modification type or experiment type; those are reconciled deterministically
from the evidence hierarchy in record_builder. This keeps the biologically
sensitive decisions out of the model's hands.

Cascade:
  Stage 1  deterministic pre-signals (biology.py) -- already available
  Stage 2  this module: cheap model emits observed claims
  Stage 3  build_evidence_record reconciles + validates
  Stage 4  if a record is CONFLICTING/AMBIGUOUS, escalate to a stronger model
           to re-report the disputed panel (optional, evidence-gated)
"""
from __future__ import annotations

import json
from typing import Any, Optional

from .evidence_record import AMBIGUOUS, CONFLICTING, EvidenceRecord, ExtractionMeta
from .llm_client import LLMClient, get_client
from .record_builder import build_evidence_record
from .resolve import ProteinResolver, default_resolver

SYSTEM_PROMPT = (
    "You are a meticulous Western blot data extractor. Report ONLY what is "
    "visible in the image or explicitly stated in the provided text. Never "
    "invent antibodies, catalog numbers, doses, or sites. Read target and "
    "antibody names verbatim. Do NOT decide whether something is phospho vs "
    "total or co-IP vs standard -- just report the labels and antibody strings "
    "you actually see, each with the source text that supports it. "
    "Return STRICT JSON only, no prose, no markdown."
)

# The model emits one "row" per (target x panel). record_builder + biology do
# the biological reasoning; the model just observes.
OUTPUT_CONTRACT = """
Return JSON of this exact shape:
{
  "rows": [
    {
      "raw_target": "<target label exactly as printed on the blot row>",
      "sample": "<cell line / tissue / sample if stated, else \\"\\">",
      "organism": "<organism if explicitly stated, else \\"\\">",
      "treatment_name": "<treatment/drug name if stated, else \\"\\">",
      "treatment_context": "<verbatim dose/time/treatment text if stated, else \\"\\">",
      "aliases": ["<other names used for this target in the paper>"],
      "antibodies": [
        {
          "target": "<antibody target string exactly as written, e.g. 'phospho-STAT3 (Tyr705)'>",
          "vendor": "<vendor if stated, else \\"\\">",
          "catalog": "<catalog number if stated, else \\"\\">",
          "clone": "<clone if stated, else \\"\\">",
          "dilution": "<dilution if stated, else \\"\\">",
          "role": "detection | immunoprecipitation",
          "phospho_specific": true,
          "source": {"type": "methods|figure_caption", "rank": 3, "text": "<verbatim snippet>"}
        }
      ],
      "bands": [
        {"lane_index": 1, "lane_condition": "<condition or null>", "band_state": "present|absent|uncertain",
         "confidence": "high|medium|low",
         "band_pattern": "single|doublet|multiple|smear|ladder|uncertain (OMIT unless clearly visible or stated)",
         "band_count": "<integer, ONLY if the bands are clearly countable, else omit>",
         "band_notes": "<verbatim wording supporting the pattern, else omit>"}
      ]
    }
  ]
}
Rules:
- One row per distinct target label shown in the panel.
- band_state must be present, absent, or uncertain -- use uncertain for faint/ambiguous.
- Do not estimate intensity or fold change.
- band_pattern is DESCRIPTIVE only: report it when the panel/text clearly shows or
  states multiple bands, a doublet, a smear, or a ladder. Omit it when in doubt --
  omission means "not reported", which is correct and preferred. NEVER derive it
  from what the protein is known to do (e.g. do not call LC3B a doublet, or
  ubiquitin a ladder, unless THIS blot shows/says so). Do not interpret bands as
  isoforms, cleavage products, dimers or degradation products.
- If a value is not stated, use "" (or null for lane_condition). Never guess.
""".strip()


def extract_records_from_claims(
    panel_context: dict[str, Any],
    model_output: dict[str, Any],
    resolver: ProteinResolver,
    extraction_meta: ExtractionMeta,
) -> list[EvidenceRecord]:
    """Turn a model's `rows` output into Evidence Records (Stage 3)."""
    records: list[EvidenceRecord] = []
    for row in model_output.get("rows", []):
        if not isinstance(row, dict) or not row.get("raw_target"):
            continue
        case = {
            "paper": panel_context.get("paper", {}),
            "figure": panel_context.get("figure", {}),
            "raw_target": row["raw_target"],
            "texts": panel_context.get("texts", {}),
            "model_claims": {
                "sample": row.get("sample") or None,
                "organism": row.get("organism") or None,
                "treatment_name": row.get("treatment_name") or None,
                "treatment_context": row.get("treatment_context") or "",
                "aliases": row.get("aliases", []),
                "antibodies": row.get("antibodies", []),
                "bands": row.get("bands", []),
            },
        }
        records.append(build_evidence_record(case, resolver=resolver, extraction=extraction_meta))
    return records


def extract_panel(
    panel_context: dict[str, Any],
    image_data_url: Optional[str] = None,
    client: Optional[LLMClient] = None,
    resolver: Optional[ProteinResolver] = None,
    escalate_client: Optional[LLMClient] = None,
) -> list[EvidenceRecord]:
    """Full Stage 2->3(->4) for one figure panel.

    ``panel_context`` = {paper, figure, texts:{caption, methods}}.
    Returns Evidence Records (possibly several targets). Requires a live model
    for real papers; pass a MockLLMClient for offline tests.
    """
    client = client or get_client()
    resolver = resolver or default_resolver()
    texts = panel_context.get("texts", {})
    user = (
        f"{OUTPUT_CONTRACT}\n\n--- FIGURE CAPTION ---\n{texts.get('caption','')}\n\n"
        f"--- METHODS (excerpt) ---\n{texts.get('methods','')[:4000]}"
    )
    model_output = client.complete_json(SYSTEM_PROMPT, user, image_data_url=image_data_url)
    meta = ExtractionMeta(stage="deterministic+llm", backend=client.name, model=client.model, escalated=False)
    records = extract_records_from_claims(panel_context, model_output, resolver, meta)

    # Stage 4: escalate ONLY the panels that came back unsettled.
    if escalate_client is not None and any(
        r.validation.record_status in (CONFLICTING, AMBIGUOUS) for r in records
    ):
        strong_user = (
            "A first pass produced conflicting or ambiguous biology for this panel. "
            "Re-read the image and text VERY carefully and re-report the same JSON shape, "
            "paying attention to which antibody detects which row and any phospho-site labels.\n\n"
            + user
        )
        strong_output = escalate_client.complete_json(SYSTEM_PROMPT, strong_user, image_data_url=image_data_url)
        strong_meta = ExtractionMeta(stage="deterministic+llm", backend=escalate_client.name,
                                     model=escalate_client.model, escalated=True)
        records = extract_records_from_claims(panel_context, strong_output, resolver, strong_meta)
    return records


def records_to_supabase_rows(records: list[EvidenceRecord]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rec in records:
        rows.extend(rec.to_supabase_rows())
    return rows
