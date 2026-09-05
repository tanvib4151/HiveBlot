"""Deterministic biological interpretation for Western blot evidence.

This module is intentionally dependency-free (standard library only) so it can
run and be unit-tested anywhere -- no anthropic, no opencv, no network. It holds
the *rules* that must not be delegated to an LLM because getting them wrong is a
scientific error, not a style choice:

  * modification detection (esp. phosphorylation) with EVIDENCE, not a
    ``target.startswith("p")`` heuristic;
  * phospho-site (residue + position) parsing;
  * experiment-type classification from METHODS/CAPTION text (never from the
    image alone -- co-IP is a claim about the assay, not the picture);
  * loading-control recognition;
  * conservative protein-name normalization with an explicit "ambiguous" state.

Every function returns both the value *and* where it came from, so the product
can always answer "why did HiveBlot say this?".
"""
from __future__ import annotations

import re
from typing import Iterable, Optional

# --------------------------------------------------------------------------- #
# Reference vocabularies
# --------------------------------------------------------------------------- #

# Housekeeping / loading-control proteins. Matched case-insensitively against a
# normalized target token, so "beta-actin" and "b-actin" both hit "actin".
LOADING_CONTROLS: tuple[str, ...] = (
    "actin",
    "actb",        # gene symbol — "β-actin" matched but "ACTB" did not (QA M7)
    "b-actin",
    "beta-actin",
    "gapdh",
    "tubulin",
    "tuba1b",      # alpha-tubulin 1B gene symbol
    "alpha-tubulin",
    "vinculin",
    "hsp90",
    "hsp70",
    "lamin b",
    "lamin b1",
    "lamin a/c",
    "histone h3",
    "cyclophilin",
    "ponceau",
    "total protein",
)

# Antibody vendors we can recognize deterministically. Kept small and explicit;
# extend as researchers confirm more. Value = normalized vendor label.
VENDORS: dict[str, str] = {
    "cell signaling": "Cell Signaling Technology",
    "cst": "Cell Signaling Technology",
    "abcam": "Abcam",
    "santa cruz": "Santa Cruz Biotechnology",
    "sigma": "Sigma-Aldrich",
    "sigma-aldrich": "Sigma-Aldrich",
    "millipore": "Millipore (Merck)",
    "merck": "Millipore (Merck)",
    "thermo": "Thermo Fisher Scientific",
    "thermofisher": "Thermo Fisher Scientific",
    "thermo fisher": "Thermo Fisher Scientific",
    "invitrogen": "Thermo Fisher Scientific",
    "bd biosciences": "BD Biosciences",
    "r&d systems": "R&D Systems",
    "proteintech": "Proteintech",
    "bethyl": "Bethyl Laboratories",
    "genetex": "GeneTex",
    "novus": "Novus Biologicals",
    "biolegend": "BioLegend",
}

# Residue three-letter <-> one-letter for phospho-site normalization.
_RESIDUE_ONE_TO_THREE = {"y": "Tyr", "s": "Ser", "t": "Thr"}
_RESIDUE_THREE = {"tyr": "Tyr", "ser": "Ser", "thr": "Thr"}

# Minimal, curated protein alias -> (canonical symbol, UniProt) map. This is a
# deterministic offline stand-in; a live UniProt resolver can augment it in a
# later stage. Only high-confidence, unambiguous mappings live here.
PROTEIN_ALIASES: dict[str, tuple[str, Optional[str]]] = {
    "stat3": ("STAT3", "P40763"),
    "p-stat3": ("STAT3", "P40763"),
    "pstat3": ("STAT3", "P40763"),
    "phospho-stat3": ("STAT3", "P40763"),
    "akt": ("AKT1", "P31749"),
    "akt1": ("AKT1", "P31749"),
    "pkb": ("AKT1", "P31749"),
    "p-akt": ("AKT1", "P31749"),
    "p53": ("TP53", "P04637"),
    "tp53": ("TP53", "P04637"),
    "trp53": ("TP53", "P04637"),
    "erk": ("MAPK1/MAPK3", None),    # ERK is ambiguous (ERK1/ERK2) -> no single UniProt
    "erk1/2": ("MAPK1/MAPK3", None),
    "p44/42": ("MAPK1/MAPK3", None), # CST's name for total ERK1/2 (p44/42 MAPK)
    "mapk1/2": ("MAPK1/MAPK3", None),
    "p38": ("MAPK14", "Q16539"),
    "gapdh": ("GAPDH", "P04406"),
    "actin": ("ACTB", "P60709"),
    "beta-actin": ("ACTB", "P60709"),
    "b-actin": ("ACTB", "P60709"),
    "egfr": ("EGFR", "P00533"),
    "parp": ("PARP1", "P09874"),
    "parp1": ("PARP1", "P09874"),
}

# Organism wording -> NCBI taxonomy id, for scoping the UniProt query. Only
# explicit, unambiguous wordings map; anything else falls back to human (9606),
# which was the previous unconditional behavior. Never used to *invent* an
# organism claim — the claimed organism string is preserved separately.
ORGANISM_TAXON: dict[str, int] = {
    "human": 9606, "homo sapiens": 9606,
    "mouse": 10090, "mus musculus": 10090, "murine": 10090, "mice": 10090,
    "rat": 10116, "rattus norvegicus": 10116, "rats": 10116,
}
DEFAULT_TAXON = 9606


def organism_taxon_id(organism: Optional[str]) -> int:
    """Taxon id for an explicitly claimed organism string (default: human)."""
    if not organism:
        return DEFAULT_TAXON
    return ORGANISM_TAXON.get(_norm(organism).lower(), DEFAULT_TAXON)


# Proteins whose name legitimately starts with "p" + digits and must NEVER be
# auto-classified as phospho. (Documented guard; the regex handles the general
# case, this is belt-and-suspenders for the well-known ones.)
P_NUMBER_PROTEINS = {
    "p53", "p63", "p73", "p38", "p21", "p27", "p16", "p65", "p50",
    "p130", "p107", "p120", "p62", "p45", "p90", "p70", "p110",
}

# --------------------------------------------------------------------------- #
# Regexes
# --------------------------------------------------------------------------- #

# Strong site notation with an explicit residue name: "Ser473", "Tyr 705".
_SITE_THREE = re.compile(r"\b(Tyr|Thr|Ser)[\s\-]?(\d{1,4})\b", re.IGNORECASE)
# "p" + one-letter residue + position: "pY705", "pS473", "pT180".
_SITE_P_ONE = re.compile(r"\bp[\s\-]?([YST])[\s\-]?(\d{1,4})\b")
# One-letter residue + position, e.g. "Y705" -- only trusted inside phospho
# context (guarded in code) because "S1"/"T2" collide with figure labels.
_SITE_ONE = re.compile(r"\b([YST])(\d{2,4})\b")
# "phospho" word in any spelling: phospho, phospho-, phosphorylated, phosphorylation.
_PHOSPHO_WORD = re.compile(r"phospho", re.IGNORECASE)
# Hyphenated phospho prefix on a symbol: "p-STAT3", "p-AKT".
_PHOSPHO_HYPHEN = re.compile(r"\bp-\s?[A-Za-z]")
# Glued phospho prefix on an UPPERCASE symbol: "pSTAT3", "pAKT" (not p53).
_PHOSPHO_GLUED = re.compile(r"\bp([A-Z]{2,}[A-Za-z0-9/]*)")
# Phospho-specific antibody phrasing.
_PHOSPHO_AB = re.compile(r"phospho[-\s]?specific|anti[-\s]?phospho|phospho[-\s]?\w+\s+antibod", re.IGNORECASE)

# Other modifications -- only asserted on explicit words.
_MOD_WORDS = {
    "cleavage": re.compile(r"\bcleav(ed|age)\b", re.IGNORECASE),
    "ubiquitination": re.compile(r"\bubiquitin|poly[-\s]?ub\b|\bK\d{1,3}[-\s]?linked", re.IGNORECASE),
    "acetylation": re.compile(r"\bacetyl|\bac-K\d", re.IGNORECASE),
    "methylation": re.compile(r"\bmethylat|\btri[-\s]?methyl|\bme3\b", re.IGNORECASE),
    "sumoylation": re.compile(r"\bsumoylat|\bSUMO\b", re.IGNORECASE),
}

# Experiment-type evidence (must come from TEXT, never the image).
_CO_IP = re.compile(
    r"co[-\s]?immunoprecipitat|co[-\s]?ip\b|\bpull[-\s]?down|pulled\s+down|immunoprecipitat",
    re.IGNORECASE,
)
# Panel-scoped IP markers as printed ON the figure itself: "IP: PIK3CA" column
# headers and IgG-control lanes. Used to scope co-IP classification to the
# panel, so a methods paragraph about a co-IP elsewhere in the paper does not
# reclassify every unrelated panel on the page.
_IP_LANE = re.compile(r"\bIP\s*[:.]|\bIgG\b|\binput\b", re.IGNORECASE)
_PURIFIED = re.compile(
    r"\brecombinant\b|purified\s+protein|in\s+vitro\s+(?:binding|kinase|translat)|GST[-\s]?tag|His[-\s]?tag",
    re.IGNORECASE,
)
_INPUT_BLOT = re.compile(r"\binput\b", re.IGNORECASE)

# Catalog number: "#9145", "cat. no. 9145", "ab32157", "sc-482".
_CATALOG = re.compile(
    r"(?:cat(?:alog)?\.?\s*(?:no\.?|#|number)?\s*|#)\s*([A-Za-z]{0,3}[-\s]?\d{3,7})",
    re.IGNORECASE,
)
_CATALOG_VENDORCODE = re.compile(r"\b(ab\d{3,7}|sc[-\s]?\d{3,7})\b", re.IGNORECASE)
# Antibody dilution: "1:1000".
_DILUTION = re.compile(r"\b1\s?:\s?(\d{2,6})\b")
# Molecular weight: "86 kDa", "~120 kDa".
_KDA = re.compile(r"(~?\s?\d{1,4}(?:\.\d+)?)\s?kDa", re.IGNORECASE)
# Dose: "20 ng/mL", "10 uM", "0.2 umol/L".
_DOSE = re.compile(
    r"\b(\d+(?:\.\d+)?)\s?(ng/ml|[uµμ]g/ml|mg/ml|nmol/l|[uµμ]mol/l|mmol/l|nm|[uµμ]m|mm|mg/kg|ng/kg|%)\b",
    re.IGNORECASE,
)
# Duration: "30 min", "24 h", "48 hours". NOT case-insensitive for the
# single-letter units: "Fig 3D" / "Fig. 3H" are FIGURE PANEL references and
# "3D culture" is a dimensionality, yet a global IGNORECASE read them as
# 3 days / 3 hours — a fabricated duration rendered as "IL-6 · 3D" in the UI
# (manual-test issue 3). Durations in papers are written lowercase ("3 d",
# "24 h", "30 min"); multi-letter units stay case-insensitive via (?i:...).
_DURATION = re.compile(
    r"\b(\d+(?:\.\d+)?)\s?((?i:hrs?|hours?|mins?|minutes?|days?)|[hd])\b")

# A number immediately preceded by a figure/panel reference is a FIGURE
# NUMBER, never a dose or duration ("Fig 3D", "Figure 2, 4 h exposure" keeps
# the 4 h — only the number the reference points at is guarded).
_FIG_REF_BEFORE = re.compile(
    r"(?i)\b(?:fig(?:ure)?s?\.?|panels?|supp(?:lementary)?\.?(?:\s+fig(?:ure)?s?\.?)?)\s*$")


def is_figure_reference_number(text: str, num_start: int) -> bool:
    """True when the number starting at ``num_start`` follows a figure/panel
    reference and must not be read as a dose/duration value."""
    return bool(_FIG_REF_BEFORE.search(text[max(0, num_start - 20):num_start]))
# Enumerated series that share ONE trailing unit: "10, 30 and 60 ug/ml",
# "0, 5, 10, 20, 30, 60 min". The plain _DOSE/_DURATION regexes only match the
# final value (the earlier numbers carry no adjacent unit), which silently
# collapses a dose-response or time course to a single scalar.
# Leading (?<![\w.]) guard: without it the series regex started matching INSIDE
# an identifier — "BafA1, 20 nM" captured "1, 20 nM" and fabricated a 1 nM dose
# candidate from the trailing digit of the drug's NAME (independent QA, M6).
_DOSE_SERIES = re.compile(
    r"(?<![\w.])((?:\d+(?:\.\d+)?\s*(?:,|;|/|\bor\b|\band\b)\s*)+\d+(?:\.\d+)?)\s*"
    r"(ng/ml|[uµμ]g/ml|mg/ml|nmol/l|[uµμ]mol/l|mmol/l|nm|[uµμ]m|mm|mg/kg|ng/kg|%)\b",
    re.IGNORECASE,
)
_DURATION_SERIES = re.compile(
    r"(?<![\w.])((?:\d+(?:\.\d+)?\s*(?:,|;|/|(?i:\bor\b)|(?i:\band\b))\s*)+\d+(?:\.\d+)?)\s*"
    r"((?i:hrs?|hours?|mins?|minutes?|days?)|[hd])\b",
)
# Explicit "this figure varies it per lane" phrasing. Presence means a single
# scalar is NOT attributable to the panel even if only one value is parseable.
# Kind-specific: "for the indicated times" must not make the (single, settled)
# stimulus CONCENTRATION ambiguous, and vice versa.
_INDICATED_TIME = re.compile(
    r"\bindicated\s+(times?|time\s*points?|durations?|intervals?)\b", re.IGNORECASE)
_INDICATED_DOSE = re.compile(
    r"\bindicated\s+(doses?|concentrations?|amounts?)\b", re.IGNORECASE)

# --------------------------------------------------------------------------- #
# Band multiplicity / pattern (DESCRIPTIVE ONLY)
# --------------------------------------------------------------------------- #
# What the source SAYS the blot shows. This is not densitometry, not image
# segmentation, and never an inference from protein identity: "LC3B" does not
# imply a doublet, and "ubiquitin" does not imply a ladder -- only explicit
# wording (or an explicit observer claim) counts. Isoform / cleavage-product /
# dimer interpretation is deliberately NOT derived here; those are biochemical
# claims the wording alone does not license.
_NUMBER_WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6}

_BAND_DOUBLET = re.compile(r"\bdoublets?\b", re.IGNORECASE)
_BAND_SMEAR = re.compile(r"\bsmears?\b|\bsmear(?:ed|ing)\b|\bdiffuse\s+(?:band|signal)\b", re.IGNORECASE)
# high-MW alternation is PLURAL-ONLY: "a higher molecular weight band" is the
# standard phrasing for a SINGLE upshifted band (phospho/SUMO/mono-Ub/glyco
# forms) and must never become a "ladder" claim (review finding B2).
_BAND_LADDER = re.compile(
    r"\bladder[-\s]?like\b|\b(?:poly[-\s]?ubiquitin|polyubiquitin)\s+(?:ladder|smear|species|conjugates?)\b"
    r"|\bhigh(?:er)?[-\s]molecular[-\s]?weight\s+(?:species|forms|bands|conjugates)\b",
    re.IGNORECASE,
)
# "two bands", "three distinct bands", "2 bands"
_BAND_COUNT = re.compile(
    r"\b(two|three|four|five|six|\d{1,2})\s+(?:distinct\s+|discrete\s+|separate\s+|major\s+)?bands?\b",
    re.IGNORECASE,
)
# Immediately-preceding context that makes a "<number> bands" match NOT a
# multiplicity statement: figure/panel/lane references ("Fig. 3 bands" ranges
# like "1-2 bands", "n = 3 bands").
_COUNT_CONTEXT_GUARD = re.compile(
    r"(?:fig\.?|figure|panel|lane|lanes)\s*$|n\s*=\s*$|[\d][\s]*[–\-]\s*$", re.IGNORECASE)
# Negation directly governing a pattern mention: "no smearing", "without
# additional bands", "did not detect a doublet". Negated multiplicity is the
# STANDARD antibody-specificity boilerplate; asserting the pattern from it
# would invert the paper's claim (review finding B1). We ABSTAIN — a negated
# mention is not read as evidence of "single" either.
_NEGATION_GUARD = re.compile(
    r"\b(?:no|not|without|neither|nor|lack(?:s|ed|ing)?|absence\s+of|free\s+of|"
    r"did\s+not|does\s+not|do\s+not)\b[^.;]{0,40}$", re.IGNORECASE)
_BAND_MULTIPLE = re.compile(
    r"\bmultiple\s+bands?\b|\bseveral\s+bands?\b|\badditional\s+bands?\b|\bextra\s+bands?\b"
    r"|\bunexpected\s+bands?\b|\bnon[-\s]?specific\s+bands?\b",
    re.IGNORECASE,
)
_BAND_SINGLE = re.compile(r"\b(?:a\s+)?single\s+band\b|\bone\s+band\b", re.IGNORECASE)
# Hedged wording keeps multiplicity UNCERTAIN rather than asserting a pattern.
_BAND_HEDGE = re.compile(
    r"\b(?:may|might|could|possibly|possible|appears?\s+to|seem(?:s|ed)?\s+to|"
    r"unclear|ambiguous|difficult\s+to)\b", re.IGNORECASE)

# Recognized pattern vocabulary (order = precedence when several co-occur).
BAND_PATTERNS = ("smear", "ladder", "doublet", "multiple", "single", "uncertain")


def detect_band_pattern(*texts: str) -> Optional[dict]:
    """Descriptive band pattern from EXPLICIT source wording, or None.

    Returns ``{"pattern", "count", "raw", "hedged"}`` where ``count`` is filled
    only when the text literally states one ("two bands" -> 2). Returns None
    when the text says nothing about multiplicity -- callers must then leave the
    field MISSING rather than assume "single".
    """
    for text in texts:
        if not text:
            continue
        hedged = bool(_BAND_HEDGE.search(text))
        # (kind, raw, count, span) — spans let us (a) drop matches whose
        # wording is negated, and (b) prune a match fully contained inside a
        # more specific one ("polyubiquitin smear" matches both the smear and
        # the ladder regex on overlapping text; that is ONE ladder statement,
        # not two conflicting descriptions).
        found: list[tuple[str, str, Optional[int], tuple[int, int]]] = []

        def _negated(start: int) -> bool:
            return bool(_NEGATION_GUARD.search(text[max(0, start - 45): start]))

        for m in _BAND_SMEAR.finditer(text):
            if not _negated(m.start()):
                found.append(("smear", m.group(0), None, m.span()))
        for m in _BAND_LADDER.finditer(text):
            if not _negated(m.start()):
                found.append(("ladder", m.group(0), None, m.span()))
        for m in _BAND_DOUBLET.finditer(text):
            if not _negated(m.start()):
                found.append(("doublet", m.group(0), 2, m.span()))
        for m in _BAND_COUNT.finditer(text):
            if _negated(m.start()) or _COUNT_CONTEXT_GUARD.search(text[max(0, m.start() - 12): m.start()]):
                continue
            raw_n = m.group(1).lower()
            n = _NUMBER_WORDS.get(raw_n) or (int(raw_n) if raw_n.isdigit() else None)
            if n is not None and n >= 2:
                found.append(("doublet" if n == 2 else "multiple", m.group(0), n, m.span()))
        for m in _BAND_MULTIPLE.finditer(text):
            if not _negated(m.start()):
                found.append(("multiple", m.group(0), None, m.span()))
        for m in _BAND_SINGLE.finditer(text):
            if not _negated(m.start()):
                found.append(("single", m.group(0), 1, m.span()))
        if not found:
            continue
        # Containment pruning: keep only matches not inside a longer match.
        pruned = [f for f in found if not any(
            g is not f and g[3][0] <= f[3][0] and f[3][1] <= g[3][1]
            and (g[3][1] - g[3][0]) > (f[3][1] - f[3][0]) for g in found)]
        # Several distinct patterns in one statement -> do not pick a winner.
        kinds = {k for k, _, _, _ in pruned}
        if len(kinds) > 1:
            raw = "; ".join(r for _, r, _, _ in pruned)
            return {"pattern": "uncertain", "count": None, "raw": raw, "hedged": True}
        kind, raw, count, _span = pruned[0]
        return {"pattern": "uncertain" if hedged else kind,
                "count": None if hedged else count, "raw": raw, "hedged": hedged}
    return None


# Identifiers.
_DOI = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
_PMID = re.compile(r"\bPMID:?\s*(\d{6,9})\b", re.IGNORECASE)
_PMCID = re.compile(r"\bPMC(\d{5,9})\b", re.IGNORECASE)
_UNIPROT = re.compile(r"\b([OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})\b")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _norm(text: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _token(target: Optional[str]) -> str:
    """Lowercased, de-prefixed target token for vocabulary matching."""
    t = _norm(target).lower()
    t = re.sub(r"^(phospho[-\s]?|p[-\s])", "", t)  # strip a leading phospho marker
    return t.strip()


def _ev(source: str, text: str) -> dict:
    """A single provenance entry."""
    return {"type": source, "text": _norm(text)[:300]}


def _first_snippet(pattern: re.Pattern, *texts_with_src: tuple[str, str]) -> Optional[dict]:
    """Return an evidence dict for the first text in which ``pattern`` matches."""
    for src, text in texts_with_src:
        if not text:
            continue
        m = pattern.search(text)
        if m:
            start = max(0, m.start() - 60)
            end = min(len(text), m.end() + 60)
            return _ev(src, text[start:end])
    return None


# --------------------------------------------------------------------------- #
# Phospho-site parsing
# --------------------------------------------------------------------------- #

def parse_phospho_site(*texts: str) -> Optional[dict]:
    """Return {'residue': 'Tyr', 'position': 705, 'raw': 'Tyr705'} or None.

    Only strong, position-bearing notations are accepted:
      * three-letter residue + number  (Tyr705, Ser 473)
      * p + one-letter residue + number (pY705, pS473)
    Bare one-letter forms (Y705) are handled by the caller only once phospho
    context is already established, to avoid colliding with figure labels.
    """
    for text in texts:
        if not text:
            continue
        m = _SITE_THREE.search(text)
        if m:
            residue = _RESIDUE_THREE[m.group(1).lower()]
            return {"residue": residue, "position": int(m.group(2)), "raw": _norm(m.group(0))}
        m = _SITE_P_ONE.search(text)
        if m:
            residue = _RESIDUE_ONE_TO_THREE[m.group(1).lower()]
            return {"residue": residue, "position": int(m.group(2)), "raw": _norm(m.group(0))}
    return None


def _one_letter_site_in_context(*texts: str) -> Optional[dict]:
    for text in texts:
        if not text:
            continue
        m = _SITE_ONE.search(text)
        if m:
            residue = _RESIDUE_ONE_TO_THREE[m.group(1).lower()]
            return {"residue": residue, "position": int(m.group(2)), "raw": _norm(m.group(0))}
    return None


# --------------------------------------------------------------------------- #
# Modification detection  (the phospho-heuristic replacement)
# --------------------------------------------------------------------------- #

def _core_symbol(target: str) -> str:
    """Gene symbol with a leading phospho/total marker and any site stripped.

    Strips ONLY genuine modification/expression prefixes, and never a "p"/"P"
    that is part of the protein's own name:
      * "phospho-" / "phospho " (any case).
      * "p-" / "p " and total-protein "t-" / "t " -- a separator is REQUIRED, so
        p53, p38, PARP keep their leading letter (the old ``p[-\\s]?`` stripped a
        lone "p"/"P", mangling p53->53, p38->38, PARP->ARP, and left "t-" alone).
      * a glued *lowercase* "p" before an UPPERCASE run (pSTAT3, pERK) -- but not
        uppercase "P" (PARP) and not "p"+digits (p53).
    A trailing isoform designation is preserved and glued ("ERK 1/2" -> "ERK1/2")
    so a family label does not collapse to a bare-symbol false-friend (UniProt
    ``gene:ERK`` resolves to EPHB2, whose gene synonym is literally "ERK").
    """
    s = _norm(target)
    # Greek letters -> spelled-out forms so "β-actin" reaches the alias map /
    # UniProt as "beta-actin" (raw wording is preserved elsewhere).
    s = s.replace("β", "beta").replace("α", "alpha")
    # phospho word, or a p-/t- prefix with a REQUIRED separator.
    s = re.sub(r"^(phospho[-\s]?|[pt][-\s])", "", s, flags=re.IGNORECASE)
    # glued lowercase-p phospho prefix on an uppercase symbol: pSTAT3, pERK.
    s = re.sub(r"^p([A-Z]{2,})", r"\1", s)
    tokens = re.split(r"[\s(]+", s.strip())
    core = tokens[0] if tokens else ""
    # Glue a trailing pure-isoform token (digits / slashes): "ERK 1/2" -> "ERK1/2".
    if len(tokens) > 1 and re.fullmatch(r"[0-9/]+", tokens[1] or ""):
        core = core + tokens[1]
    return core.strip(" -()")


def _target_has_phospho_marker(target: str) -> bool:
    """True only when the TARGET NAME itself denotes phosphorylation.

    This is what prevents STAT3 (total) from being contaminated by a sibling
    'phospho-STAT3' band described in the same caption -- modification identity
    comes from the per-row target label, not the shared caption.
    """
    low = target.lower()
    token = _token(target)
    if token in P_NUMBER_PROTEINS or re.fullmatch(r"p\d{1,3}[a-z/]*", token):
        return False  # p53, p38, p21 ... never phospho by name alone
    if "phospho" in low:
        return True
    if re.search(r"\bp-\s?[A-Za-z]", target):  # p-STAT3, p-AKT
        return True
    if re.match(r"^p([A-Z]{2,}[A-Za-z0-9/]*)$", target):  # pSTAT3, pAKT, pERK (not pRb, not p53)
        return True
    return False


def _scoped_site(core: str, *texts: str) -> Optional[dict]:
    """Find a phospho-site near the target's core symbol; fall back to whole text.

    Scoping avoids grabbing a sibling target's site (e.g. picking Ser473 for a
    STAT3 row from '...phospho-AKT Ser473...'). Whole-text fallback only fires
    when the core symbol is not present, i.e. the text is plausibly about this
    single target.
    """
    core_low = (core or "").lower()
    found_core = False
    for text in texts:
        if not text or not core_low:
            continue
        low = text.lower()
        idx = low.find(core_low)
        while idx != -1:
            found_core = True
            window = text[max(0, idx - 10): idx + len(core) + 45]
            site = parse_phospho_site(window)
            if site:
                return site
            idx = low.find(core_low, idx + 1)
    if found_core:
        return None  # core present but no site next to it -> don't guess
    # core absent from all texts: text is likely about this one target -> allow
    return parse_phospho_site(*texts) or _one_letter_site_in_context(*texts)


def detect_modification(
    raw_target: str,
    caption: str = "",
    methods: str = "",
    antibody_text: str = "",
) -> dict:
    """Evidence-based modification detection, authoritative from the target name.

    Returns a dict:
        {
          "modification_type": "phosphorylation" | "cleavage" | ... | None,
          "residue": "Tyr" | None,
          "residue_position": 705 | None,
          "normalized_label": "phospho-Tyr705" | "phospho" | "cleaved" | None,
          "status": "SUPPORTED" | "AMBIGUOUS" | "MISSING",
          "phospho_specific_antibody": bool,
          "evidence": [ {type, text}, ... ],
        }

    Rules (deliberately conservative):
      * Modification identity comes from the per-row TARGET NAME. A shared
        caption listing several targets never upgrades a bare target.
      * ``p`` + digits (p53, p38, PARP) is NEVER phosphorylation.
      * A site is attached only when a residue notation is actually present near
        this target; 'phospho-STAT3' with no site stays site=None (never Tyr705).
    """
    target = _norm(raw_target)
    core = _core_symbol(target)

    # --- (A) explicit non-phospho modification encoded in the TARGET NAME -----
    for mod_type, pat in _MOD_WORDS.items():
        m = pat.search(target)
        if m:
            # The mod word being essentially the ENTIRE target means the row's
            # analyte IS that protein: an anti-ubiquitin blot detects the
            # protein ubiquitin; it does not establish that some other target
            # is ubiquitinated. Asserting a modification from the antibody's
            # own antigen name is the same failure class as the banned
            # startswith("p") phospho rule (independent QA finding C2).
            # "ubiquitinated EGFR" keeps the claim: a real target remains.
            rest = target[:m.start()] + target[m.end():]
            rest = re.sub(r"(?i)\b(?:ated|ation|ylation)\b|[-()\s]+", " ", rest)
            if not re.search(r"[A-Za-z]{2}", rest):
                continue
            label = m.group(0).lower() if mod_type == "cleavage" else mod_type
            return {
                "modification_type": mod_type,
                "residue": None,
                "residue_position": None,
                "normalized_label": label,
                "status": "SUPPORTED",
                "phospho_specific_antibody": False,
                "evidence": [_ev("target", target)],
            }

    # --- (B) phospho decided by the TARGET NAME (no sibling contamination) ----
    site = parse_phospho_site(target)
    target_phospho = bool(site) or _target_has_phospho_marker(target)
    if not target_phospho:
        return {
            "modification_type": None,
            "residue": None,
            "residue_position": None,
            "normalized_label": None,
            "status": "MISSING",  # no modification on this target -> total protein
            "phospho_specific_antibody": False,
            "evidence": [],
        }

    # Target is phospho: enrich the site (scoped) and phospho-antibody flag.
    if site is None:
        # One-letter site inside the SAME phospho-marked label — "p-AKT (S473)",
        # "p-RPS6KB1 (T389)" — is trustworthy: the phospho marker and the site
        # travel together in one short row label, which satisfies the phospho-
        # context guard that one-letter forms require. (Guarded from cell-line
        # tokens like T47D because \b never splits digit->letter.)
        site = _one_letter_site_in_context(target)
    if site is None:
        site = _scoped_site(core, caption, methods, antibody_text)
    phospho_ab_ev = _first_snippet(
        _PHOSPHO_AB, ("methods", methods), ("antibody", antibody_text), ("figure_caption", caption)
    )

    evidence = [_ev("target", target)]
    if site:
        site_ev = _first_snippet(_SITE_THREE, ("figure_caption", caption), ("methods", methods)) or \
            _first_snippet(_SITE_P_ONE, ("figure_caption", caption), ("methods", methods))
        if site_ev:
            evidence.append(site_ev)
        label = f"phospho-{site['residue']}{site['position']}"
    else:
        label = "phospho"
    if phospho_ab_ev:
        evidence.append(phospho_ab_ev)

    return {
        "modification_type": "phosphorylation",
        "residue": site["residue"] if site else None,
        "residue_position": site["position"] if site else None,
        "normalized_label": label,
        "status": "SUPPORTED",
        "phospho_specific_antibody": bool(phospho_ab_ev),
        "evidence": evidence,
    }


# --------------------------------------------------------------------------- #
# Loading-control & experiment-type classification
# --------------------------------------------------------------------------- #

def is_loading_control(target: str) -> bool:
    token = _token(target)
    return any(token == lc or token.startswith(lc) or lc in token for lc in LOADING_CONTROLS)


def classify_experiment(
    raw_target: str,
    caption: str = "",
    methods: str = "",
    modification: Optional[dict] = None,
    is_loading_control_flag: bool = False,
) -> dict:
    """Classify assay design from TEXT evidence (never the image alone).

    Returns:
        {
          "experiment_type": "co_ip" | "phospho_western" | "standard_western"
                             | "purified_protein" | "loading_control" | "unknown",
          "experiment_flags": [...],     # non-exclusive; co_ip + phospho can coexist
          "confidence": float,
          "evidence": [ {type, text}, ... ],
        }
    """
    flags: list[str] = []
    evidence: list[dict] = []

    loading = is_loading_control_flag or is_loading_control(raw_target)
    if loading:
        flags.append("loading_control")

    co_ip_ev = _first_snippet(_CO_IP, ("methods", methods), ("figure_caption", caption))
    if co_ip_ev:
        flags.append("co_ip")
        evidence.append(co_ip_ev)

    purified_ev = _first_snippet(_PURIFIED, ("methods", methods), ("figure_caption", caption))
    if purified_ev:
        flags.append("purified_protein")
        evidence.append(purified_ev)

    is_phospho = bool(modification and modification.get("modification_type") == "phosphorylation")
    if is_phospho:
        flags.append("phospho_western")
        evidence.extend(modification.get("evidence", [])[:1])

    # Primary label precedence: assay design beats modification label.
    if "co_ip" in flags:
        primary, conf = "co_ip", 0.9
    elif "purified_protein" in flags:
        primary, conf = "purified_protein", 0.85
    elif "loading_control" in flags:
        primary, conf = "loading_control", 0.9
    elif "phospho_western" in flags:
        primary = "phospho_western"
        conf = 0.9 if (modification or {}).get("status") == "SUPPORTED" else 0.6
    elif _looks_like_western(caption, methods):
        primary, conf = "standard_western", 0.5
        flags.append("standard_western")
    else:
        primary, conf = "unknown", 0.2

    return {
        "experiment_type": primary,
        "experiment_flags": sorted(set(flags)),
        "confidence": conf,
        "evidence": evidence,
    }


def _looks_like_western(caption: str, methods: str) -> bool:
    text = f"{caption} {methods}".lower()
    return any(k in text for k in ("western blot", "immunoblot", "blot", "wb "))


# --------------------------------------------------------------------------- #
# Per-source modification scanning (for the evidence-hierarchy reconciler)
# --------------------------------------------------------------------------- #

def _mention_state(pre: str, post: str) -> dict:
    """Classify a single mention of a core symbol from its surrounding chars.

    Three states, not two:
      * "phosphorylation" — explicit phospho marker / site at this mention.
      * "total"           — explicit total/pan marker ("total STAT3", "T-STAT3",
                            "pan-AKT"): the text really asserts unmodified.
      * "bare"            — the symbol alone ("PI3K/AKT/mTOR signaling"). A bare
                            mention asserts NOTHING about modification state; it
                            must never be read as a total-protein claim, or any
                            pathway sentence in page text would manufacture a
                            fake conflict against a phospho row.
    """
    pre_l = pre.lower()
    is_phospho = False
    if pre_l.rstrip().endswith("phospho") or pre_l.rstrip().endswith("phospho-") or pre_l.rstrip().endswith("phospho "):
        is_phospho = True
    elif re.search(r"p-\s*$", pre):                       # "p-STAT3"
        is_phospho = True
    elif re.search(r"(^|[^A-Za-z])p$", pre):              # glued "pSTAT3"
        is_phospho = True
    site = parse_phospho_site(post) or parse_phospho_site(pre)
    if site:
        is_phospho = True
    if is_phospho:
        return {"type": "phosphorylation", "site": site}
    if re.search(r"(total\s*-?\s*|pan\s*-\s*|\bt-\s*)$", pre, re.IGNORECASE):
        return {"type": "total", "site": None}
    return {"type": "bare", "site": None}


def caption_modification_for_core(core: str, text: str) -> Optional[dict]:
    """Return the modification state a piece of text asserts for ``core``.

    Returns None (abstain) when the text mentions the core in BOTH modified and
    unmodified forms -- a shared multi-target caption is not decisive for one
    row, so it must not contaminate a total-protein row. Returns None too when
    the core is not mentioned at all.

        {"modification_type": "phosphorylation"|None, "residue": "Tyr"|None,
         "residue_position": 705|None}
    """
    core = _norm(core)
    if not core or not text:
        return None
    core_low = core.lower()
    low = text.lower()
    states: set[str] = set()
    site_found: Optional[dict] = None
    idx = low.find(core_low)
    while idx != -1:
        pre = text[max(0, idx - 12): idx]
        post = text[idx + len(core): idx + len(core) + 14]
        st = _mention_state(pre, post)
        states.add(st["type"])
        if st.get("site") and site_found is None:
            site_found = st["site"]
        idx = low.find(core_low, idx + 1)

    # A bare mention either asserts nothing (alone: "PI3K/AKT/mTOR signaling"
    # must not become a total-protein claim) or signals the text spans multiple
    # rows (mixed with an explicit form: "pSTAT3 ... STAT3 ..." is about both a
    # phospho row and a total row) -> abstain either way.
    if "bare" in states:
        return None
    if len(states) != 1:            # no explicit claim, or conflicting -> abstain
        return None
    state = states.pop()
    if state == "phosphorylation":
        return {
            "modification_type": "phosphorylation",
            "residue": site_found["residue"] if site_found else None,
            "residue_position": site_found["position"] if site_found else None,
        }
    return {"modification_type": None, "residue": None, "residue_position": None}


def antibody_modification(antibody_target: str) -> dict:
    """Modification implied by an antibody's target string (rank-1 evidence)."""
    mod = detect_modification(antibody_target or "")
    return {
        "modification_type": mod["modification_type"],
        "residue": mod["residue"],
        "residue_position": mod["residue_position"],
    }


def core_symbol(target: str) -> str:
    """Public alias for the phospho/site-stripped gene symbol."""
    return _core_symbol(target)


# --------------------------------------------------------------------------- #
# Protein normalization (conservative, explicit ambiguity)
# --------------------------------------------------------------------------- #

def normalize_protein(raw_target: str) -> dict:
    """Resolve a raw target to a canonical symbol + UniProt where confident.

    Never overwrites the source wording -- both are returned. Ambiguity is
    surfaced, not guessed.

        {
          "raw": "pSTAT3",
          "canonical": "STAT3" | None,
          "uniprot_id": "P40763" | None,
          "status": "SUPPORTED" | "AMBIGUOUS" | "MISSING",
        }
    """
    raw = _norm(raw_target)
    token = _token(raw)
    if not token:
        return {"raw": raw, "canonical": None, "uniprot_id": None, "status": "MISSING"}

    if token in PROTEIN_ALIASES:
        canonical, uniprot = PROTEIN_ALIASES[token]
        # A resolved canonical name with no single UniProt (e.g. ERK1/2) is ambiguous.
        status = "AMBIGUOUS" if uniprot is None else "SUPPORTED"
        return {"raw": raw, "canonical": canonical, "uniprot_id": uniprot, "status": status}

    # Unknown to our offline map -> keep raw, flag for resolution. Not guessed.
    return {"raw": raw, "canonical": None, "uniprot_id": None, "status": "MISSING"}
