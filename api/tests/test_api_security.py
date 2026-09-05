"""
Endpoint-level checks for the properties EXECUTION_PLAN step 6 calls out:
auth on both surfaces, no overlap between the internal and agent key sets,
and independent rate-limit budgets.

These run against the real app via TestClient with only the search pipeline
itself stubbed out, so they cover the wiring (dependencies, router prefixes,
limiter registration) rather than re-testing execute_search. The parts of
step 6 that need live infrastructure - a real OpenAI-generated query getting
rejected by sql_guard, and hive_readonly's Postgres grants - can't be covered
here; see EXECUTION_PLAN.
"""

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.limiter import limiter
from app.main import app
from app.schemas import SearchResponse

INTERNAL = settings.internal_api_key
AGENT = next(iter(settings.agent_api_keys_set))

BODY = {"query": "p53 in HeLa cells", "limit": 10}


@pytest.fixture(autouse=True)
def _no_real_search(monkeypatch):
    """
    Stub the shared pipeline: these tests are about auth and rate limiting,
    not about NL->SQL. Both routers import execute_search by value, so both
    module namespaces get patched.
    """

    async def fake_execute_search(query: str, limit: int) -> SearchResponse:
        return SearchResponse(
            question=query,
            generated_sql=f"SELECT * FROM {settings.table_name} LIMIT {limit}",
            count=0,
            results=[],
        )

    import app.routers.external as external
    import app.routers.internal as internal

    monkeypatch.setattr(internal, "execute_search", fake_execute_search)
    monkeypatch.setattr(external, "execute_search", fake_execute_search)


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """Rate-limit state is process-global; don't let one test spend another's
    budget."""
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def auth(key):
    return {"Authorization": f"Bearer {key}"}


# --- both surfaces require auth -----------------------------------------


@pytest.mark.parametrize("path", ["/search", "/v1/search"])
def test_search_without_authorization_is_401(client, path):
    assert client.post(path, json=BODY).status_code == 401


@pytest.mark.parametrize("path", ["/search", "/v1/search"])
def test_search_with_a_junk_key_is_401(client, path):
    assert client.post(path, json=BODY, headers=auth("junk")).status_code == 401


def test_proteins_requires_the_internal_key(client):
    assert client.get("/proteins", params={"name": "p53"}).status_code == 401


# --- the two key sets must not overlap in practice ----------------------


def test_internal_key_is_rejected_by_the_agent_endpoint(client):
    assert client.post("/v1/search", json=BODY, headers=auth(INTERNAL)).status_code == 401


def test_agent_key_is_rejected_by_the_internal_endpoint(client):
    assert client.post("/search", json=BODY, headers=auth(AGENT)).status_code == 401


# --- the right key gets through -----------------------------------------


def test_internal_key_reaches_the_internal_search(client):
    r = client.post("/search", json=BODY, headers=auth(INTERNAL))

    assert r.status_code == 200
    assert r.json()["question"] == BODY["query"]


def test_agent_key_reaches_the_external_search(client):
    r = client.post("/v1/search", json=BODY, headers=auth(AGENT))

    assert r.status_code == 200
    assert r.json()["question"] == BODY["query"]


def test_health_is_public(client):
    r = client.get("/health")

    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# --- request validation --------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        {"query": "", "limit": 10},
        {"query": "x" * 501, "limit": 10},
        {"query": "ok", "limit": 0},
        {"query": "ok", "limit": 100_000},
        {"limit": 10},
    ],
)
def test_bad_request_bodies_are_422(client, body):
    r = client.post("/v1/search", json=body, headers=auth(AGENT))

    assert r.status_code == 422


# --- independent rate-limit budgets --------------------------------------


def parse_per_minute(limit_string: str) -> int:
    return int(limit_string.split("/")[0])


def test_internal_and_agent_rate_limits_are_independent(client):
    """
    Spending the whole internal budget must not consume the agent budget:
    an agent's traffic and the frontend's traffic are separately tunable
    (SEARCH_RATE_LIMIT vs AGENT_RATE_LIMIT) precisely so one can't starve
    the other.
    """
    internal_budget = parse_per_minute(settings.search_rate_limit)

    for _ in range(internal_budget):
        assert client.post("/search", json=BODY, headers=auth(INTERNAL)).status_code == 200
    assert client.post("/search", json=BODY, headers=auth(INTERNAL)).status_code == 429

    # The agent endpoint is untouched by the internal endpoint's exhaustion.
    assert client.post("/v1/search", json=BODY, headers=auth(AGENT)).status_code == 200


def test_agent_rate_limit_is_enforced(client):
    agent_budget = parse_per_minute(settings.agent_rate_limit)

    for _ in range(agent_budget):
        assert client.post("/v1/search", json=BODY, headers=auth(AGENT)).status_code == 200
    assert client.post("/v1/search", json=BODY, headers=auth(AGENT)).status_code == 429

    assert client.post("/search", json=BODY, headers=auth(INTERNAL)).status_code == 200


# --- CORS is not wide open ----------------------------------------------


def test_cors_does_not_allow_arbitrary_origins(client):
    r = client.options(
        "/search",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert r.headers.get("access-control-allow-origin") != "*"
    assert r.headers.get("access-control-allow-origin") != "https://evil.example"


def test_cors_allows_the_configured_origin(client):
    origin = settings.allowed_origins_list[0]
    r = client.options(
        "/search",
        headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
    )

    assert r.headers.get("access-control-allow-origin") == origin
