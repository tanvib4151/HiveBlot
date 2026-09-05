"""
Unit tests for the two auth dependencies.

The important property here isn't just "a bad key is rejected" - it's that the
internal key and the agent keys are two *separate* sets. Collapsing them back
into one shared secret would silently undo the reason /v1/search is versioned
and separately revocable.
"""

import asyncio

import pytest
from fastapi import HTTPException

from app.auth import require_agent_key, require_internal_key
from app.config import settings

INTERNAL = settings.internal_api_key
AGENT = next(iter(settings.agent_api_keys_set))


def call(dependency, header):
    return asyncio.run(dependency(authorization=header))


# --- require_agent_key ---------------------------------------------------


def test_valid_agent_key_is_accepted_and_returned():
    """The matched key comes back so callers can log which agent called."""
    assert call(require_agent_key, f"Bearer {AGENT}") == AGENT


def test_every_configured_agent_key_works():
    for key in settings.agent_api_keys_set:
        assert call(require_agent_key, f"Bearer {key}") == key


def test_unknown_agent_key_is_rejected():
    with pytest.raises(HTTPException) as e:
        call(require_agent_key, "Bearer not-a-real-key")

    assert e.value.status_code == 401


def test_removing_a_key_invalidates_it_immediately(monkeypatch):
    """
    agent_api_keys_set is recomputed per call rather than cached at import,
    so revoking an agent is a config change - not a redeploy, and not a key
    that keeps working until the process restarts.
    """
    assert call(require_agent_key, f"Bearer {AGENT}") == AGENT

    remaining = sorted(settings.agent_api_keys_set - {AGENT})
    monkeypatch.setattr(settings, "agent_api_keys", ",".join(remaining))

    with pytest.raises(HTTPException) as e:
        call(require_agent_key, f"Bearer {AGENT}")
    assert e.value.status_code == 401

    # ...and the keys that weren't revoked still work.
    for key in remaining:
        assert call(require_agent_key, f"Bearer {key}") == key


def test_agent_keys_are_split_on_commas_not_treated_as_one_string():
    monkeypatch_free = settings.agent_api_keys_set
    assert len(monkeypatch_free) == 2
    assert all("," not in k for k in monkeypatch_free)


def test_whitespace_around_configured_keys_is_ignored(monkeypatch):
    monkeypatch.setattr(settings, "agent_api_keys", "  spaced-key , other-key ")

    assert call(require_agent_key, "Bearer spaced-key") == "spaced-key"


def test_empty_agent_key_list_accepts_nothing(monkeypatch):
    monkeypatch.setattr(settings, "agent_api_keys", "")

    assert settings.agent_api_keys_set == set()
    for header in ["Bearer ", "Bearer x", None]:
        with pytest.raises(HTTPException):
            call(require_agent_key, header)


# --- require_internal_key ------------------------------------------------


def test_valid_internal_key_is_accepted():
    assert call(require_internal_key, f"Bearer {INTERNAL}") is None


def test_wrong_internal_key_is_rejected():
    with pytest.raises(HTTPException) as e:
        call(require_internal_key, "Bearer wrong")

    assert e.value.status_code == 401


# --- the two key sets must not overlap -----------------------------------


def test_internal_key_does_not_work_as_an_agent_key():
    with pytest.raises(HTTPException) as e:
        call(require_agent_key, f"Bearer {INTERNAL}")

    assert e.value.status_code == 401


def test_agent_key_does_not_work_as_the_internal_key():
    with pytest.raises(HTTPException) as e:
        call(require_internal_key, f"Bearer {AGENT}")

    assert e.value.status_code == 401


def test_configured_key_sets_are_actually_disjoint():
    """Guards against someone pasting the same generated value into both."""
    assert settings.internal_api_key not in settings.agent_api_keys_set


# --- header parsing ------------------------------------------------------


@pytest.mark.parametrize(
    "header",
    [None, "", AGENT, f"Basic {AGENT}", f"bearer {AGENT}", "Bearer", "Bearer "],
)
def test_malformed_authorization_headers_are_rejected(header):
    for dependency in (require_agent_key, require_internal_key):
        with pytest.raises(HTTPException) as e:
            call(dependency, header)
        assert e.value.status_code == 401
