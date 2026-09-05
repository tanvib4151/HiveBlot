"""Protein normalization via a real UniProt resolver, with caching and a small
offline fallback (correction 1).

Design goals:
  * Real resolution goes to UniProt (reviewed/Swiss-Prot, organism-aware).
  * Results are cached on disk so repeated queries cost nothing.
  * If the network is unavailable OR the query is ambiguous (>1 reviewed hit),
    the raw string is preserved and the status is MISSING / AMBIGUOUS.
  * A UniProt accession is NEVER guessed.

The curated map (biology.PROTEIN_ALIASES) is demoted to a *fallback / test*
resolver only -- it is not treated as production normalization.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from . import biology

# statuses mirror evidence_record
SUPPORTED = "SUPPORTED"
AMBIGUOUS = "AMBIGUOUS"
MISSING = "MISSING"

UNIPROT_SEARCH = "https://rest.uniprot.org/uniprotkb/search"

# Expected (calculated, canonical-sequence) masses in kDa for the offline set.
# NOTE: calculated mass often differs from observed migration (e.g. p53 calc
# ~43.7 kDa migrates ~53 kDa) -- this is exactly why reported != expected.
_LOCAL_MASS_KDA = {
    "P40763": 88.0,   # STAT3
    "P31749": 55.7,   # AKT1
    "P04637": 43.7,   # TP53 (migrates ~53)
    "Q16539": 41.3,   # MAPK14 / p38
    "P04406": 36.1,   # GAPDH
    "P60709": 41.7,   # ACTB
    "P00533": 134.3,  # EGFR
    "P09874": 113.1,  # PARP1
}


@dataclass
class ProteinResolution:
    raw: str
    canonical: Optional[str] = None
    uniprot_id: Optional[str] = None
    expected_mass_kda: Optional[float] = None
    organism: Optional[str] = None
    status: str = MISSING
    candidates: list[dict] = field(default_factory=list)
    source: str = "none"          # uniprot | cache | local_fallback | none


class ProteinResolver:
    def resolve(self, raw_name: str, organism_id: int = 9606) -> ProteinResolution:
        raise NotImplementedError


class LocalMapResolver(ProteinResolver):
    """Deterministic offline resolver over the curated alias map. Test/fallback."""

    def resolve(self, raw_name: str, organism_id: int = 9606) -> ProteinResolution:
        core = biology.core_symbol(raw_name)
        token = core.lower()
        if token in biology.PROTEIN_ALIASES:
            canonical, uniprot = biology.PROTEIN_ALIASES[token]
            if uniprot is None:  # e.g. ERK -> ambiguous, no single accession
                return ProteinResolution(raw=raw_name, canonical=canonical, status=AMBIGUOUS,
                                         source="local_fallback")
            return ProteinResolution(
                raw=raw_name, canonical=canonical, uniprot_id=uniprot,
                expected_mass_kda=_LOCAL_MASS_KDA.get(uniprot), organism="human",
                status=SUPPORTED, source="local_fallback",
            )
        return ProteinResolution(raw=raw_name, status=MISSING, source="local_fallback")


class UniProtResolver(ProteinResolver):
    """Live UniProt REST resolver (reviewed entries, organism-scoped)."""

    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    def resolve(self, raw_name: str, organism_id: int = 9606) -> ProteinResolution:
        import requests  # lazy: only when a live call actually happens

        core = biology.core_symbol(raw_name)
        if not core:
            return ProteinResolution(raw=raw_name, status=MISSING, source="uniprot")
        query = f"(gene:{core}) AND (organism_id:{organism_id}) AND (reviewed:true)"
        try:
            resp = requests.get(
                UNIPROT_SEARCH,
                params={"query": query, "fields": "accession,id,gene_primary,protein_name,mass",
                        "format": "json", "size": 5},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
        except Exception:
            # Network unavailable -> preserve raw, do not guess.
            return ProteinResolution(raw=raw_name, status=MISSING, source="uniprot")

        if not results:
            return ProteinResolution(raw=raw_name, status=MISSING, source="uniprot")

        parsed = [self._parse(r) for r in results]
        # Exact primary-gene matches take priority.
        exact = [p for p in parsed if (p.get("gene") or "").lower() == core.lower()]
        chosen_pool = exact or parsed
        if len(chosen_pool) == 1:
            p = chosen_pool[0]
            organism_name = {9606: "human", 10090: "mouse", 10116: "rat"}.get(organism_id)
            return ProteinResolution(
                raw=raw_name, canonical=p.get("gene") or core, uniprot_id=p["accession"],
                expected_mass_kda=p.get("mass_kda"), organism=organism_name,
                status=SUPPORTED, source="uniprot",
            )
        # Multiple reviewed hits -> ambiguous; list candidates, choose nothing.
        return ProteinResolution(
            raw=raw_name, canonical=core, status=AMBIGUOUS, source="uniprot",
            candidates=[{"uniprot_id": p["accession"], "gene": p.get("gene"),
                         "name": p.get("name"), "mass_kda": p.get("mass_kda")} for p in chosen_pool],
        )

    @staticmethod
    def _parse(r: dict) -> dict:
        gene = None
        genes = r.get("genes") or []
        if genes:
            gene = (genes[0].get("geneName") or {}).get("value")
        name = None
        pd = r.get("proteinDescription") or {}
        rec = pd.get("recommendedName") or {}
        name = (rec.get("fullName") or {}).get("value")
        mass = r.get("sequence", {}).get("molWeight")  # Daltons
        return {
            "accession": r.get("primaryAccession"),
            "gene": gene,
            "name": name,
            "mass_kda": round(mass / 1000.0, 1) if mass else None,
        }


class CachingResolver(ProteinResolver):
    """Wrap a resolver with an on-disk JSON cache and an offline fallback."""

    def __init__(self, primary: ProteinResolver, fallback: Optional[ProteinResolver] = None,
                 cache_path: Optional[Path] = None):
        self.primary = primary
        self.fallback = fallback or LocalMapResolver()
        self.cache_path = Path(cache_path or _default_cache_path())
        self._cache = self._load()

    def _load(self) -> dict:
        try:
            return json.loads(self.cache_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save(self) -> None:
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(self._cache, indent=2), encoding="utf-8")
        except OSError:
            pass

    def resolve(self, raw_name: str, organism_id: int = 9606) -> ProteinResolution:
        core = biology.core_symbol(raw_name)
        cache_key = f"{core.lower()}|{organism_id}"
        if cache_key in self._cache:
            data = dict(self._cache[cache_key])
            data["raw"] = raw_name
            return ProteinResolution(**data)

        # Curated ambiguity is AUTHORITATIVE and short-circuits the live query.
        # A family shorthand the curated map marks ambiguous (e.g. "ERK" ->
        # MAPK1/MAPK3, uniprot=None) must NOT be collapsed to a single UniProt
        # synonym false-friend: `gene:ERK` returns EPHB2 (whose gene synonym is
        # literally "ERK") as one confident hit. Trust the expert map here.
        curated = self.fallback.resolve(raw_name, organism_id)
        if curated.status == AMBIGUOUS:
            self._cache[cache_key] = {k: v for k, v in curated.__dict__.items() if k != "raw"}
            self._save()
            return curated

        res = self.primary.resolve(raw_name, organism_id)
        # If the primary couldn't resolve (e.g. offline), try the fallback but
        # keep it clearly labeled; never fabricate an accession.
        if res.status == MISSING and res.uniprot_id is None:
            fb = self.fallback.resolve(raw_name, organism_id)
            if fb.status != MISSING:
                res = fb
        # Cache only confident/ambiguous outcomes (not transient network misses).
        if res.status in (SUPPORTED, AMBIGUOUS):
            store = {k: v for k, v in res.__dict__.items() if k != "raw"}
            self._cache[cache_key] = store
            self._save()
        return res


def _default_cache_path() -> Path:
    override = os.environ.get("WBM_PROTEIN_CACHE")
    if override:
        return Path(override)
    return Path(__file__).resolve().parent / "data" / "protein_cache.json"


def default_resolver(offline: Optional[bool] = None) -> ProteinResolver:
    """Return the resolver appropriate to the environment.

    offline=True (or WBM_OFFLINE=1) uses the local map only -- handy for tests
    and demos with no network. Otherwise a cached UniProt resolver is used, with
    the local map as a fallback if UniProt is unreachable.
    """
    if offline is None:
        offline = os.environ.get("WBM_OFFLINE", "").strip().lower() in {"1", "true", "yes"}
    if offline:
        return LocalMapResolver()
    return CachingResolver(UniProtResolver(), fallback=LocalMapResolver())
