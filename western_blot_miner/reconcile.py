"""Evidence-hierarchy reconciliation.

Turns competing per-source claims into :class:`EvidenceField` values. The row
target is NOT treated as ground truth (correction 2): every source is a claim,
ranked by the evidence hierarchy, and genuine disagreement produces a
CONFLICTING field with ``value=None`` and the candidates preserved (correction
1) rather than a silently-chosen value.

Pure stdlib + evidence_record models; no network / no model calls.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from .evidence_record import (
    AMBIGUOUS,
    CONFLICTING,
    MISSING,
    SUPPORTED,
    Candidate,
    EvidenceField,
    Source,
)


class Claim:
    """A single source's assertion about a field."""

    __slots__ = ("value", "source_type", "rank", "confidence", "text", "locator")

    def __init__(self, value: Any, source_type: str, rank: int, confidence: float,
                 text: str = "", locator: Optional[str] = None):
        self.value = value
        self.source_type = source_type
        self.rank = rank
        self.confidence = confidence
        self.text = text
        self.locator = locator

    def source(self) -> Source:
        return Source(type=self.source_type, rank=self.rank, text=self.text, locator=self.locator)

    def candidate(self) -> Candidate:
        return Candidate(value=self.value, source_type=self.source_type, rank=self.rank,
                         confidence=self.confidence, evidence=[self.source()])


def _default_key(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip().lower()
    return value


def reconcile_field(
    claims: list[Claim],
    key: Callable[[Any], Any] = _default_key,
    mutually_exclusive: bool = True,
) -> EvidenceField:
    """Reconcile simple scalar claims into one EvidenceField.

    * no claims with a value            -> MISSING
    * all agree                         -> SUPPORTED
    * one under-supported value         -> AMBIGUOUS (value kept, marked unsettled)
    * >=2 distinct credible values      -> CONFLICTING (value=None, candidates kept)
    """
    valued = [c for c in claims if c.value not in (None, "", [])]
    if not valued:
        return EvidenceField.missing()

    groups: dict[Any, list[Claim]] = {}
    for c in valued:
        groups.setdefault(key(c.value), []).append(c)

    if len(groups) == 1:
        members = valued
        best = min(members, key=lambda c: (c.rank, -c.confidence))
        conf = min(0.99, max(c.confidence for c in members) + 0.03 * (len(members) - 1))
        return EvidenceField.supported(best.value, conf, [c.source() for c in members])

    # Multiple distinct values.
    candidates = [_merge_candidate(members) for members in groups.values()]
    if mutually_exclusive:
        # Genuine conflict: don't settle (correction 1).
        return EvidenceField.conflicting(candidates)
    # Non-exclusive (e.g. multiple valid aliases): keep as ambiguous best-guess.
    return EvidenceField.ambiguous(candidates)


def _merge_candidate(members: list[Claim]) -> Candidate:
    best = min(members, key=lambda c: (c.rank, -c.confidence))
    return Candidate(
        value=best.value,
        source_type=best.source_type,
        rank=best.rank,
        confidence=max(c.confidence for c in members),
        evidence=[c.source() for c in members],
    )


# --------------------------------------------------------------------------- #
# Modification is a composite (type + residue + position) and needs bespoke
# reconciliation so "phospho with no site" and "phospho Tyr705" MERGE (the site
# refines) while "phospho" vs "total" CONFLICT.
# --------------------------------------------------------------------------- #

class ModClaim:
    __slots__ = ("mod_type", "residue", "position", "source_type", "rank", "confidence", "text")

    def __init__(self, mod_type, residue, position, source_type, rank, confidence, text=""):
        self.mod_type = mod_type          # "phosphorylation" | "cleavage" | ... | None (=total)
        self.residue = residue
        self.position = position
        self.source_type = source_type
        self.rank = rank
        self.confidence = confidence
        self.text = text

    def source(self) -> Source:
        return Source(type=self.source_type, rank=self.rank, text=self.text)


def reconcile_modification(claims: list[ModClaim]) -> dict[str, EvidenceField]:
    """Return {modification_type, residue, residue_position, normalized_label,
    phospho_specific_antibody-independent} EvidenceFields."""
    claims = [c for c in claims if c is not None]
    if not claims:
        return _empty_mod()

    # Bucket by modification identity: phospho, an explicit other-mod, or total.
    phospho = [c for c in claims if c.mod_type == "phosphorylation"]
    other = [c for c in claims if c.mod_type not in ("phosphorylation", None)]
    total = [c for c in claims if c.mod_type is None]

    distinct_types = set(c.mod_type for c in claims)
    # Treat "no claim of total" specially: a source that simply didn't mention a
    # modification is already filtered out upstream; a total claim is an explicit
    # "unmodified" assertion.

    # --- other (cleavage/ubiquitin/...) vs anything else -> conflict ----------
    if other and (phospho or total):
        cands = _mod_candidates(phospho, other, total)
        return _conflict_mod(cands)
    if other and not phospho and not total:
        best = min(other, key=lambda c: (c.rank, -c.confidence))
        f_type = EvidenceField.supported(best.mod_type, best.confidence, [c.source() for c in other])
        label = EvidenceField.supported(best.mod_type, best.confidence, [best.source()])
        return {
            "modification_type": f_type,
            "residue": EvidenceField.missing(),
            "residue_position": EvidenceField.missing(),
            "normalized_label": label,
        }

    # --- phospho vs total -> conflict (value=None, candidates kept) -----------
    if phospho and total:
        cands = _mod_candidates(phospho, other, total)
        result = _conflict_mod(cands)
        # A claimed site exists but the modification itself is disputed. Keep the
        # site visible ONLY as an unsettled candidate -- never as a settled value
        # (a disputed modification must not surface a confirmed-looking residue).
        site_claim = next((c for c in phospho if c.residue), None)
        if site_claim:
            result["residue"] = EvidenceField(
                value=None, status=AMBIGUOUS, confidence=0.0,
                candidates=[Candidate(value=site_claim.residue, source_type=site_claim.source_type,
                                      rank=site_claim.rank, confidence=site_claim.confidence,
                                      evidence=[site_claim.source()])])
            result["residue_position"] = EvidenceField(
                value=None, status=AMBIGUOUS, confidence=0.0,
                candidates=[Candidate(value=site_claim.position, source_type=site_claim.source_type,
                                      rank=site_claim.rank, confidence=site_claim.confidence,
                                      evidence=[site_claim.source()])])
        return result

    # --- only phospho supporters: merge; reconcile the SITE -------------------
    if phospho:
        type_conf = min(0.99, max(c.confidence for c in phospho) + 0.02 * (len(phospho) - 1))
        f_type = EvidenceField.supported("phosphorylation", type_conf, [c.source() for c in phospho])
        residue_field, position_field, site = _reconcile_site(phospho)
        if site:
            label_val = f"phospho-{site[0]}{site[1]}"
        else:
            label_val = "phospho"
        f_label = EvidenceField.supported(label_val, type_conf, [c.source() for c in phospho])
        return {
            "modification_type": f_type,
            "residue": residue_field,
            "residue_position": position_field,
            "normalized_label": f_label,
        }

    # --- only total supporters: unmodified / total protein --------------------
    type_conf = min(0.99, max(c.confidence for c in total) + 0.02 * (len(total) - 1))
    f_type = EvidenceField.supported(None, type_conf, [c.source() for c in total])  # value None == "total"
    return {
        "modification_type": f_type,
        "residue": EvidenceField.missing(),
        "residue_position": EvidenceField.missing(),
        "normalized_label": EvidenceField.supported("total", type_conf, [c.source() for c in total]),
    }


def _reconcile_site(phospho: list[ModClaim]):
    sited = [c for c in phospho if c.residue and c.position]
    if not sited:
        return EvidenceField.missing(), EvidenceField.missing(), None
    keys = set((c.residue, c.position) for c in sited)
    if len(keys) == 1:
        r, p = next(iter(keys))
        srcs = [c.source() for c in sited]
        conf = max(c.confidence for c in sited)
        return (
            EvidenceField.supported(r, conf, srcs),
            EvidenceField.supported(p, conf, srcs),
            (r, p),
        )
    # Different sites claimed -> residue conflict.
    r_cands = [Candidate(value=r, source_type="mixed", rank=1, confidence=0.5,
                         evidence=[c.source() for c in sited if (c.residue, c.position) == (r, p)])
               for (r, p) in keys]
    p_cands = [Candidate(value=p, source_type="mixed", rank=1, confidence=0.5,
                         evidence=[c.source() for c in sited if (c.residue, c.position) == (r, p)])
               for (r, p) in keys]
    return EvidenceField.conflicting(r_cands), EvidenceField.conflicting(p_cands), None


def _mod_candidates(phospho, other, total) -> list[Candidate]:
    cands: list[Candidate] = []
    if phospho:
        site = next((c for c in phospho if c.residue), None)
        label = f"phospho-{site.residue}{site.position}" if site else "phosphorylation"
        cands.append(Candidate(value=label, source_type=_top(phospho).source_type,
                               rank=_top(phospho).rank, confidence=max(c.confidence for c in phospho),
                               evidence=[c.source() for c in phospho]))
    for c in other:
        cands.append(Candidate(value=c.mod_type, source_type=c.source_type, rank=c.rank,
                               confidence=c.confidence, evidence=[c.source()]))
    if total:
        cands.append(Candidate(value="none", source_type=_top(total).source_type,
                               rank=_top(total).rank, confidence=max(c.confidence for c in total),
                               evidence=[c.source() for c in total]))
    return cands


def _conflict_mod(cands: list[Candidate]) -> dict[str, EvidenceField]:
    return {
        "modification_type": EvidenceField.conflicting(cands),
        "residue": EvidenceField.missing(),
        "residue_position": EvidenceField.missing(),
        "normalized_label": EvidenceField.conflicting(cands),
    }


def _empty_mod() -> dict[str, EvidenceField]:
    return {
        "modification_type": EvidenceField.missing(),
        "residue": EvidenceField.missing(),
        "residue_position": EvidenceField.missing(),
        "normalized_label": EvidenceField.missing(),
    }


def _top(claims):
    return min(claims, key=lambda c: (c.rank, -c.confidence))
