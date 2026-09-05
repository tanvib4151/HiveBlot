from fastapi import Header, HTTPException

from .config import settings


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return authorization.removeprefix("Bearer ").strip()


async def require_internal_key(authorization: str | None = Header(default=None)) -> None:
    """Guards the internal endpoints the web/ frontend's BFF route calls."""
    token = _bearer_token(authorization)
    if token != settings.internal_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


async def require_agent_key(authorization: str | None = Header(default=None)) -> str:
    """
    Guards /v1/search, the external, agent-facing endpoint. Checks against a
    set of keys (not one shared secret) so individual agents/integrations can
    be issued and revoked independently. Returns the matched key so callers
    can log which agent made the request.
    """
    token = _bearer_token(authorization)
    if token not in settings.agent_api_keys_set:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return token
