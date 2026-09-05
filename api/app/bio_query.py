"""Deterministic biological query -> SQL generator.

Used by /search when OPENAI_KEY is not configured (and as a way to serve the
structured biological queries UCSF researchers actually type without any LLM):

    phospho STAT3 Tyr705      -> modification + residue/position + target term
    co-IP EGFR                -> experiment_type co_ip + target term
    CST 9145                  -> antibody vendor + catalog number
    A549 STAT3                -> two AND'd terms, each OR'd across bio columns
    phospho AKT Ser473        -> modification + residue Ser/473 + target term

Design constraints:
  * Output is a SINGLE `SELECT * FROM western_blot_records ...` string that
    still goes through sql_guard.guard_and_limit_sql and executes under the
    scoped read-only role — this generator gets no special trust.
  * Deterministic and transparent: the generated SQL is returned to the client
    in the response (same as the LLM path), so a researcher can see exactly
    what was searched. No model, no guessing.
  * Unrecognized tokens degrade to broad ILIKE term matching — never an error.
"""
from __future__ import annotations

import re

from .config import settings

# Columns a free-text term is matched against (OR within a term, AND between
# terms). Covers protein identity, sample, treatment and antibody target.
TERM_COLUMNS = (
    "target",
    "raw_target_name",
    "canonical_target",
    "uniprot_id",
    "cell_line",
    "sample",
    "treatment_name",
    "treatment_context",
    "antibody_target",
    "modification_label",
)

RESIDUE_NAMES = {"y": "Tyr", "s": "Ser", "t": "Thr",
                 "tyr": "Tyr", "ser": "Ser", "thr": "Thr"}

# Vendor vocabulary -> the string matched against antibody_vendor.
VENDORS = {
    "cst": "cell signaling",
    "cell signaling": "cell signaling",
    "cell signaling technology": "cell signaling",
    "santa cruz": "santa cruz",
    "abcam": "abcam",
    "sigma": "sigma",
    "sigma-aldrich": "sigma",
    "millipore": "millipore",
    "thermo": "thermo",
    "invitrogen": "invitrogen",
    "proteintech": "proteintech",
    "bd biosciences": "bd biosciences",
}

STOPWORDS = {
    "western", "blot", "blots", "westerns", "in", "of", "for", "with", "the",
    "a", "an", "and", "show", "me", "find", "papers", "paper", "evidence",
    "cells", "cell", "detect", "detected", "detection", "antibody",
    "antibodies", "data", "records", "record", "results", "human",
}

_SITE_RE = re.compile(r"\b(tyr|ser|thr|y|s|t)\s?-?(\d{2,4})\b", re.IGNORECASE)
# Only the explicit WORD "phospho" adds a modification filter. A "p-" prefix
# ("P-ERK", "p-AKT") stays a plain term: the printed row label matches it
# directly, and adding a phospho filter would EXCLUDE rows whose modification
# is honestly CONFLICTING (value null) — hiding exactly the records that most
# need review.
_PHOSPHO_RE = re.compile(r"\bphospho\w*", re.IGNORECASE)
_COIP_RE = re.compile(r"\bco-?ip\b|\bimmunoprecipitat\w*", re.IGNORECASE)
_LOADING_RE = re.compile(r"\bloading[\s-]?controls?\b", re.IGNORECASE)
_NEEDS_REVIEW_RE = re.compile(r"\bneeds?[\s-]?review\b", re.IGNORECASE)
_CATALOG_RE = re.compile(r"#\s?(\d{3,7})\b")
_BARE_NUM_RE = re.compile(r"\b(\d{3,7})\b")


def _esc(term: str) -> str:
    """Sanitize a term for embedding in an ILIKE literal. Defense-in-depth:
    the output still passes through sql_guard AST validation + the read-only
    role, but we never build a literal from raw user text anyway."""
    term = re.sub(r"[^A-Za-z0-9µβ/+.\- ]", "", term)
    return term.replace("'", "''").strip()


def _term_clause(term: str) -> str:
    t = _esc(term)
    ors = " OR ".join(f"{c} ILIKE '%{t}%'" for c in TERM_COLUMNS)
    return f"({ors})"


def generate_bio_sql(question: str) -> str:
    q = " " + question.strip() + " "
    clauses: list[str] = []

    # Phospho-site notation (Tyr705 / Y705 / Ser 473) -> residue + position.
    site = _SITE_RE.search(q)
    if site:
        residue = RESIDUE_NAMES[site.group(1).lower()]
        position = int(site.group(2))
        clauses.append(f"(residue ILIKE '{residue}' AND residue_position = {position})")
        q = _SITE_RE.sub(" ", q)

    # Modification / experiment-type keywords.
    if _PHOSPHO_RE.search(q):
        # Unsettled modifications (CONFLICTING/AMBIGUOUS) stay INCLUDED: a
        # phospho search must surface a disputed phospho-vs-total row for
        # review, not silently hide it (its scalar modification_type is null
        # by design). Settled rows rank first via ORDER BY needs_review.
        clauses.append("(modification_type ILIKE '%phospho%' OR "
                       "modification_status ILIKE 'CONFLICTING' OR "
                       "modification_status ILIKE 'AMBIGUOUS')")
        q = re.sub(r"\bphospho\w*", " ", q, flags=re.IGNORECASE)
    if _COIP_RE.search(q):
        clauses.append("experiment_type ILIKE 'co_ip'")
        q = _COIP_RE.sub(" ", q)
    if _LOADING_RE.search(q):
        clauses.append("experiment_type ILIKE 'loading_control'")
        q = _LOADING_RE.sub(" ", q)
    if _NEEDS_REVIEW_RE.search(q):
        clauses.append("needs_review = true")
        q = _NEEDS_REVIEW_RE.sub(" ", q)

    # Antibody vendor + catalog number.
    vendor_hit = None
    for alias in sorted(VENDORS, key=len, reverse=True):
        m = re.search(rf"\b{re.escape(alias)}\b", q, re.IGNORECASE)
        if m:
            vendor_hit = VENDORS[alias]
            clauses.append(f"antibody_vendor ILIKE '%{_esc(vendor_hit)}%'")
            q = q[: m.start()] + " " + q[m.end():]
            break
    cat = _CATALOG_RE.search(q)
    if not cat and vendor_hit:
        cat = _BARE_NUM_RE.search(q)  # "CST 9145" — number only trusted next to a vendor
    if cat:
        clauses.append(f"antibody_catalog_number ILIKE '%{_esc(cat.group(1))}%'")
        q = q.replace(cat.group(0), " ")

    # Remaining free-text terms: AND between terms, OR across bio columns.
    for token in re.split(r"[\s,;]+", q):
        token = token.strip(" .?!()[]{}\"'")
        if len(token) < 2 or token.lower() in STOPWORDS:
            continue
        if not _esc(token):
            continue
        clauses.append(_term_clause(token))

    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    # Settled evidence first (needs_review=false), stable order within.
    return (
        f"SELECT * FROM {settings.table_name}{where} "
        f"ORDER BY needs_review ASC, id ASC"
    )
