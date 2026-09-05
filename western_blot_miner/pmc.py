"""PubMed Central access layer.

Two free NCBI services are used, no auth required:
  * E-utilities (esearch)      -> find open-access PMC articles for a query
  * BioC API (PMC OA)          -> structured full text: figure captions + methods

Everything returned here is plain dicts so the pipeline stays decoupled
from NCBI's JSON shapes.
"""
import time
from dataclasses import dataclass, field
from typing import Optional

import requests

from . import config


@dataclass
class Figure:
    figure_id: str
    caption: str
    image_filename: Optional[str] = None  # graphic file referenced by BioC, if any


@dataclass
class Article:
    pmcid: str
    pmid: Optional[str] = None
    doi: Optional[str] = None
    title: Optional[str] = None
    methods: str = ""
    figures: list[Figure] = field(default_factory=list)


def _params(extra: dict) -> dict:
    base = {"tool": config.NCBI_TOOL, "email": config.NCBI_EMAIL}
    if config.NCBI_API_KEY:
        base["api_key"] = config.NCBI_API_KEY
    base.update(extra)
    return base


def search_pmc(protein: str, limit: int = 50) -> list[str]:
    """Return a list of PMCIDs (e.g. 'PMC1234567') for open-access articles
    mentioning the protein and a western blot."""
    term = f'{protein} AND "western blot" AND open access[filter]'
    resp = requests.get(
        f"{config.EUTILS}/esearch.fcgi",
        params=_params(
            {
                "db": "pmc",
                "term": term,
                "retmax": limit,
                "retmode": "json",
                # Relevance beats date here: the newest articles often aren't
                # indexed in the BioC full-text service yet.
                "sort": "relevance",
            }
        ),
        timeout=30,
    )
    resp.raise_for_status()
    idlist = resp.json().get("esearchresult", {}).get("idlist", [])
    # esearch on db=pmc returns the numeric part of the PMCID.
    return [f"PMC{uid}" for uid in idlist]


def _passage_section(infons: dict) -> str:
    return (infons.get("section_type") or infons.get("type") or "").upper()


def fetch_article(pmcid: str, retries: int = 2) -> Optional[Article]:
    """Pull the structured BioC document for one PMC article and reduce it to
    the figures + methods text we care about."""
    url = f"{config.BIOC}/{pmcid}/unicode"
    data = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, timeout=60)
            body = resp.text.strip()
            # Not-yet-indexed articles return HTTP 200 with a "[Error]" page,
            # not JSON. No point retrying those.
            if resp.status_code == 200 and body.startswith("[Error]"):
                return None
            if resp.status_code == 200 and body:
                data = resp.json()
                break
        except (requests.RequestException, ValueError):
            pass
        time.sleep(1.5 * (attempt + 1))
    if not data:
        return None

    # BioC returns a list of collections; each has documents -> passages.
    collection = data[0] if isinstance(data, list) else data
    documents = collection.get("documents", [])
    if not documents:
        return None
    doc = documents[0]
    article = Article(pmcid=pmcid)

    # Group figure passages by figure id; collect methods text.
    figs: dict[str, Figure] = {}
    methods_chunks: list[str] = []
    for passage in doc.get("passages", []):
        infons = passage.get("infons", {})
        text = (passage.get("text") or "").strip()

        # Article IDs (pmid/doi) live in passage infons, usually on the front
        # passage — grab them wherever they first appear.
        if article.pmid is None and "article-id_pmid" in infons:
            article.pmid = infons.get("article-id_pmid")
        if article.doi is None and "article-id_doi" in infons:
            article.doi = infons.get("article-id_doi")

        if not text:
            continue
        section = _passage_section(infons)

        if section in ("TITLE", "FRONT") and not article.title:
            article.title = text

        if section == "METHODS":
            methods_chunks.append(text)

        # Figure captions live in passages with section_type == FIG.
        if section == "FIG" or infons.get("type", "").startswith("fig"):
            fid = infons.get("id") or f"fig{len(figs) + 1}"
            fig = figs.get(fid)
            if fig is None:
                fig = Figure(figure_id=fid, caption="")
                figs[fid] = fig
            fig.caption = (fig.caption + " " + text).strip()
            # Some BioC outputs name the graphic file directly.
            if not fig.image_filename:
                fig.image_filename = infons.get("file")

    article.methods = "\n".join(methods_chunks)[:8000]  # keep prompt bounded
    article.figures = list(figs.values())
    return article


def is_western_blot_caption(caption: str) -> bool:
    low = f" {caption.lower()} "
    return any(kw in low for kw in config.WB_KEYWORDS)
