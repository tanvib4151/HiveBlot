"""Claude-powered figure classification + structured extraction.

A single API call per figure does both jobs:
  1. Classify: is this figure actually a western blot?
  2. Extract: pull structured records (protein, cell line, result, ...).

Caption + methods text is always sent. When a figure image is available it is
attached too, so the vision model can read band presence/intensity directly.
We use structured outputs (a Pydantic schema) so the response is guaranteed to
parse — no brittle string parsing.
"""
import base64
import mimetypes
from pathlib import Path
from typing import Optional

import anthropic
from pydantic import BaseModel, Field

from . import config

_client: Optional[anthropic.Anthropic] = None


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        # Resolves ANTHROPIC_API_KEY from the environment.
        _client = anthropic.Anthropic()
    return _client


# --- Output schema -------------------------------------------------------
class WBRecord(BaseModel):
    protein: str = Field(description="Protein/target detected, e.g. 'p53'")
    cell_line: Optional[str] = Field(
        None, description="Cell line or tissue, e.g. 'HeLa', 'liver'"
    )
    organism: Optional[str] = Field(None, description="Organism, e.g. 'human', 'mouse'")
    mol_weight_kda: Optional[str] = Field(
        None, description="Molecular weight in kDa if stated, e.g. '53'"
    )
    antibody: Optional[str] = Field(
        None, description="Antibody name / catalog number if stated"
    )
    condition: Optional[str] = Field(
        None, description="Experimental condition, e.g. 'doxorubicin treatment', 'siRNA knockdown'"
    )
    result: str = Field(
        description="One of: expressed, not expressed, upregulated, downregulated, unclear"
    )


class FigureExtraction(BaseModel):
    is_western_blot: bool = Field(
        description="True only if this figure (or a panel of it) is a western/immunoblot"
    )
    confidence: float = Field(description="Confidence 0.0-1.0 that this is a western blot")
    records: list[WBRecord] = Field(
        default_factory=list,
        description="One record per protein/condition combination shown in the blot",
    )


SYSTEM_PROMPT = (
    "You are a proteomics data extraction assistant. You read western blot "
    "figures from biology papers and extract structured facts. Be precise and "
    "conservative: only report a protein/cell-line/result you can justify from "
    "the caption, methods, or image. If a field is not stated, leave it null. "
    "If the figure is NOT a western/immunoblot (e.g. a bar chart, microscopy "
    "image, Coomassie/silver-stained gel without antibody detection), set "
    "is_western_blot to false and return no records."
)


def _image_block(image_path: Path) -> Optional[dict]:
    try:
        data = image_path.read_bytes()
    except OSError:
        return None
    media_type = mimetypes.guess_type(str(image_path))[0] or "image/jpeg"
    if media_type not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
        # Claude vision accepts these four; skip TIFFs etc.
        return None
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": base64.standard_b64encode(data).decode("utf-8"),
        },
    }


def extract_figure(
    caption: str,
    methods: str,
    image_path: Optional[Path] = None,
) -> Optional[FigureExtraction]:
    """Run one classification+extraction call. Returns None on API failure."""
    prompt_text = (
        "Analyze this figure and decide whether it is a western blot. If it is, "
        "extract one record per protein/condition shown.\n\n"
        f"FIGURE CAPTION:\n{caption.strip()}\n\n"
        f"METHODS (excerpt, may be empty):\n{methods.strip()[:4000]}"
    )
    content: list[dict] = []
    if image_path is not None:
        block = _image_block(image_path)
        if block:
            content.append(block)
    content.append({"type": "text", "text": prompt_text})

    try:
        response = client().messages.parse(
            model=config.MODEL,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
            output_format=FigureExtraction,
        )
    except anthropic.APIError as exc:
        print(f"    [warn] Claude API error: {exc}")
        return None

    return response.parsed_output
