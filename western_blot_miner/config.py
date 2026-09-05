"""Central configuration for Western Blot Miner.

Everything tunable lives here so the rest of the pipeline stays clean.
Values can be overridden via environment variables.
"""
import os
from pathlib import Path

# --- Paths ---------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
IMAGE_DIR = DATA_DIR / "figures"
DB_PATH = DATA_DIR / "western_blots.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

# --- Claude / Anthropic --------------------------------------------------
# Default to the most capable model. The figure caption + methods text is
# small, so cost per call is modest; for very large bulk runs you can set
# WBM_MODEL=claude-sonnet-4-6 (cheaper) or claude-haiku-4-5 (cheapest).
MODEL = os.environ.get("WBM_MODEL", "claude-opus-4-8")

# --- NCBI E-utilities ----------------------------------------------------
# An API key (free, from https://www.ncbi.nlm.nih.gov/account/settings/)
# raises the rate limit from 3 to 10 requests/sec. Optional but recommended.
NCBI_API_KEY = os.environ.get("NCBI_API_KEY", "")
# NCBI asks that bulk users identify themselves.
NCBI_EMAIL = os.environ.get("NCBI_EMAIL", "western-blot-miner@example.com")
NCBI_TOOL = "western-blot-miner"

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
BIOC = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json"
OA_SERVICE = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"

# Caption keywords used to pre-filter figures before spending an LLM call.
# A figure whose caption mentions any of these is a western-blot candidate.
WB_KEYWORDS = (
    "western blot",
    "immunoblot",
    "western blotting",
    " wb ",
    "blotting",
)
