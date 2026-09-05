"""Record-detail shaping + feedback endpoints.

DB calls are stubbed (no live Postgres in unit tests); what's under test:
- provenance envelope -> RecordDetail curation (field selection, candidate
  preservation, conflict visibility, internal metadata excluded)
- feedback scope validation rules
- endpoint auth + wiring
- the auditability invariant: feedback INSERTs never touch western_blot_records
"""

import pytest
from app.config import settings
from app.limiter import limiter
from app.main import app
from app.record_detail import build_record_detail
from app.schemas import FeedbackSubmission
from fastapi.testclient import TestClient

INTERNAL = settings.internal_api_key
AUTH = {"Authorization": f"Bearer {INTERNAL}"}


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def client():
    return TestClient(app)


# --- provenance -> RecordDetail shaping -------------------------------------

def _envelope(value, status="SUPPORTED", confidence=0.9, sources=None, candidates=None):
    return {"value": value, "confidence": confidence, "status": status,
            "sources": sources or [], "candidates": candidates or []}


ROW = {
    "id": 42,
    "paper_id": "10.3892/br.2026.2108",
    "title": None, "doi": "10.3892/br.2026.2108", "pmcid": None, "pmid": None,
    "figure_label": None, "panel_label": None, "page": 4,
    "figure_caption": None, "image_crop_ref": "/x/crop.png",
    "raw_target_name": "P-STAT3 (Tyr705)", "target": "P-STAT3 (Tyr705)",
    "canonical_target": "STAT3", "uniprot_id": "P40763",
    "modification_label": "phospho-Tyr705", "experiment_type": "phospho_western",
    "cell_line": "Hep3B", "organism": None, "sample": "Hep3B",
    "band_state": "present", "lane_condition": "30 min",
    "reported_molecular_weight_kda": None, "expected_molecular_weight_kda": 88.1,
    "molecular_weight_source": "uniprot_reference",
    "needs_review": False,
    "anomaly_flags": [{"code": "X", "message": "y", "internal": "drop-me-not-required"}],
    "validation": {"record_status": "SUPPORTED", "needs_review": False},
    "provenance": {
        "record_id": "deadbeef", "extraction": {"model": "secret-internal"},
        "target": {
            "raw_target_name": "P-STAT3 (Tyr705)",
            "canonical_target": _envelope("STAT3", sources=[{"type": "uniprot_reference", "rank": 0, "text": "P40763"}]),
            "uniprot_id": _envelope("P40763"),
        },
        "modification": {
            "modification_type": _envelope("phosphorylation"),
            "residue": _envelope("Tyr"),
            "residue_position": _envelope(705),
            "phospho_specific_antibody": _envelope(True),
        },
        "experiment": {
            "experiment_type": _envelope(None, status="CONFLICTING", confidence=0.0,
                                         candidates=[{"value": "co_ip", "source_type": "methods", "confidence": 0.5, "evidence": []},
                                                     {"value": "standard_western", "source_type": "model_target", "confidence": 0.5, "evidence": []}]),
            "experiment_flags": _envelope(["phospho_western"]),
            "ip_bait_protein": _envelope(None, status="MISSING", confidence=0.0),
        },
        "sample": {"sample": _envelope("Hep3B"), "cell_line": _envelope("Hep3B"),
                   "organism": _envelope(None, status="MISSING", confidence=0.0),
                   "tissue": _envelope(None, status="MISSING", confidence=0.0),
                   "genotype": _envelope(None, status="MISSING", confidence=0.0)},
        "treatment": {"treatment_name": _envelope("IL-6"), "dose": _envelope(10.0),
                      "dose_unit": _envelope("ng/ml"), "duration": _envelope(30.0),
                      "duration_unit": _envelope("min"), "treatment_context": _envelope("...")},
        "molecular_weight": {"reported_kda": _envelope(None, status="MISSING", confidence=0.0),
                             "expected_kda": _envelope(88.1)},
        "antibodies": [{
            "antibody_target": _envelope("phospho-STAT3 (Tyr705)",
                                         sources=[{"type": "methods", "rank": 3, "text": "CST #9145"}]),
            "vendor": _envelope("Cell Signaling Technology"),
            "catalog_number": _envelope("9145"), "clone": _envelope(None, status="MISSING"),
            "dilution": _envelope("1:1,000"), "role": "detection",
            "phospho_specific": _envelope(True),
            "detection_confidence": 0.9, "association_confidence": 0.7,
        }],
        "bands": [{"lane_index": 1, "lane_condition": _envelope("30 min"),
                   "band_state": _envelope("present", confidence=0.9)}],
    },
}


def test_detail_shaping_core_fields():
    d = build_record_detail(ROW)
    assert d.id == 42
    assert d.canonical_target == "STAT3" and d.uniprot_id == "P40763"
    f = d.fields
    assert f["canonical_target"].value == "STAT3"
    assert f["residue_position"].value == 705
    assert f["canonical_target"].sources == [{"type": "uniprot_reference", "text": "P40763"}]
    # rank is internal — must not leak through
    assert "rank" not in (f["canonical_target"].sources[0].keys())


def test_detail_conflict_candidates_preserved():
    d = build_record_detail(ROW)
    exp = d.fields["experiment_type"]
    assert exp.status == "CONFLICTING" and exp.value is None
    vals = {c["value"] for c in exp.candidates}
    assert vals == {"co_ip", "standard_western"}  # disagreement stays visible


def test_detail_missing_fields_dropped_except_informative():
    d = build_record_detail(ROW)
    assert "organism" not in d.fields          # MISSING + not informative -> dropped
    assert "reported_molecular_weight_kda" in d.fields   # MISSING but informative -> kept
    assert d.fields["reported_molecular_weight_kda"].status == "MISSING"


def test_detail_antibody_and_bands():
    d = build_record_detail(ROW)
    ab = d.antibodies[0]
    assert ab.catalog_number == "9145" and ab.role == "detection"
    assert ab.association_confidence == 0.7    # detection vs association kept distinct
    assert d.bands[0].band_state == "present" and d.bands[0].lane_condition == "30 min"


def test_detail_excludes_internal_metadata():
    d = build_record_detail(ROW).model_dump()
    blob = str(d)
    assert "secret-internal" not in blob and "deadbeef" not in blob


# --- endpoint wiring ---------------------------------------------------------

def test_record_detail_endpoint(client, monkeypatch):
    async def fake_fetch(record_id):
        return dict(ROW) if record_id == 42 else None
    import app.routers.internal as internal
    monkeypatch.setattr(internal, "fetch_record_by_id", fake_fetch)

    r = client.get("/records/42", headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body["fields"]["experiment_type"]["status"] == "CONFLICTING"

    assert client.get("/records/999", headers=AUTH).status_code == 404
    assert client.get("/records/42").status_code in (401, 403)  # auth required


def test_feedback_endpoint_validates_and_inserts(client, monkeypatch):
    inserted = {}

    async def fake_insert(fields):
        inserted.update(fields)
        return 7
    import app.routers.internal as internal
    monkeypatch.setattr(internal, "insert_feedback", fake_insert)
    monkeypatch.setattr(settings, "db_feedback_url", "postgresql://stub")

    good = {"feedback_scope": "field", "record_id": 42, "field_name": "cell_line",
            "feedback_type": "incorrect", "model_value": "Hep3B",
            "suggested_value": "HepG2", "comment": "wrong line"}
    r = client.post("/feedback", json=good, headers=AUTH)
    assert r.status_code == 200 and r.json()["feedback_id"] == 7
    # correction stored as suggested_value; nothing resembling an UPDATE of
    # the record: the stored dict targets hiveblot_feedback columns only.
    assert inserted["suggested_value"] == "HepG2"
    assert inserted["model_value"] == "Hep3B"
    assert "target" not in inserted and "canonical_target" not in inserted

    # scope validation failures -> 400
    bad = [
        {"feedback_scope": "field", "feedback_type": "incorrect"},          # no record/field
        {"feedback_scope": "record", "record_id": 1, "feedback_type": "nope"},
        {"feedback_scope": "search", "feedback_type": "understood_yes"},    # no query
        {"feedback_scope": "ui"},                                           # no comment
        {"feedback_scope": "banana"},
    ]
    for b in bad:
        assert client.post("/feedback", json=b, headers=AUTH).status_code == 400, b

    # auth required
    assert client.post("/feedback", json=good).status_code in (401, 403)


def test_feedback_503_when_unconfigured(client, monkeypatch):
    monkeypatch.setattr(settings, "db_feedback_url", "")
    good = {"feedback_scope": "ui", "comment": "hi"}
    assert client.post("/feedback", json=good, headers=AUTH).status_code == 503


def test_feedback_rehydration_endpoint(client, monkeypatch):
    """P0 regression (manual beta): submitted feedback must be retrievable for
    a record so the UI can rehydrate after refresh. Persistence was verified in
    the DB; the missing piece was retrieval. The payload keeps feedback clearly
    separate from the extraction (its own endpoint/shape) and is read-only."""
    import datetime

    import app.routers.internal as internal

    async def fake_record(record_id):
        # The record's reseed-proof identity, resolved server-side.
        return {"id": record_id, "stable_row_key": "abc123def456:1"}

    async def fake_fetch(record_id, stable_row_key=None):
        assert record_id == 673
        # The OR-match key must be passed through: this is what makes
        # feedback survive a reseed (serial ids change; the hash does not).
        assert stable_row_key == "abc123def456:1"
        return [{
            "feedback_id": 3,
            "created_at": datetime.datetime(2026, 8, 13, 7, 27, 2),
            "feedback_scope": "field",
            "stable_row_key": "abc123def456:1",
            "field_name": "modification_type",
            "model_value": None,
            "feedback_type": "incorrect",
            "suggested_value": "phosphorylation",
            "comment": "picked from candidates",
            "session_id": "abc",
        }]
    monkeypatch.setattr(internal, "fetch_record_by_id", fake_record)
    monkeypatch.setattr(internal, "fetch_feedback_for_record", fake_fetch)
    monkeypatch.setattr(settings, "db_feedback_url", "postgresql://stub")

    r = client.get("/records/673/feedback", headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body["record_id"] == 673
    item = body["items"][0]
    # The AI claim (model_value) and the human correction (suggested_value)
    # both survive the round trip — the auditable pair, never a merge.
    assert item["model_value"] is None
    assert item["suggested_value"] == "phosphorylation"
    assert item["field_name"] == "modification_type"
    # auth required; unconfigured -> 503
    assert client.get("/records/673/feedback").status_code in (401, 403)
    monkeypatch.setattr(settings, "db_feedback_url", "")
    assert client.get("/records/673/feedback", headers=AUTH).status_code == 503


def test_feedback_scope_rules_direct():
    ok = FeedbackSubmission(feedback_scope="missing_field", field_name="antibody dilution")
    assert ok.validate_scope() is None
    assert FeedbackSubmission(feedback_scope="missing_field").validate_scope()
    s = FeedbackSubmission(feedback_scope="search", search_query="x",
                           feedback_type="understood_partially")
    assert s.validate_scope() is None


# --- figure-crop endpoint ----------------------------------------------------

def _stub_record(monkeypatch, row):
    async def fake_fetch(record_id):
        return row
    monkeypatch.setattr("app.routers.internal.fetch_record_by_id", fake_fetch)


def test_crop_requires_auth(client):
    assert client.get("/records/1/crop").status_code in (401, 403)


def test_crop_404_when_no_ref(client, monkeypatch):
    _stub_record(monkeypatch, {"id": 1, "image_crop_ref": None})
    assert client.get("/records/1/crop", headers=AUTH).status_code == 404


def test_crop_rejects_paths_outside_base_dir(client, monkeypatch, tmp_path):
    # A poisoned image_crop_ref outside the allowed base must 404, never serve.
    secret = tmp_path / "secret.png"
    secret.write_bytes(b"\x89PNG\r\n\x1a\n")
    _stub_record(monkeypatch, {"id": 1, "image_crop_ref": str(secret)})
    assert client.get("/records/1/crop", headers=AUTH).status_code == 404


def test_crop_rejects_non_png(client, monkeypatch):
    from pathlib import Path
    inside = Path(settings.crop_base_dir) / "x" / "notes.txt"
    _stub_record(monkeypatch, {"id": 1, "image_crop_ref": str(inside)})
    assert client.get("/records/1/crop", headers=AUTH).status_code == 404


def test_crop_serves_png_inside_base_dir(client, monkeypatch, tmp_path):
    png = tmp_path / "panel.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 16)
    monkeypatch.setattr(settings, "crop_base_dir", str(tmp_path))
    _stub_record(monkeypatch, {"id": 1, "image_crop_ref": str(png)})
    resp = client.get("/records/1/crop", headers=AUTH)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content.startswith(b"\x89PNG")
