"""
External API - the one stable, documented endpoint meant to be called
directly by third-party agents/integrations, not routed through web/'s BFF.

Versioned (/v1/...) so its request/response contract can be held stable even
if the internal API's shape changes. Auth is a set of per-agent keys (see
auth.require_agent_key), not the same shared secret the frontend uses, so an
individual agent's access can be revoked without affecting the frontend or
other agents.
"""

from fastapi import APIRouter, Depends, Request

from ..auth import require_agent_key
from ..config import settings
from ..limiter import limiter
from ..schemas import SearchRequest, SearchResponse
from ..search_service import execute_search

router = APIRouter(prefix="/v1")


@router.post(
    "/search",
    response_model=SearchResponse,
    dependencies=[Depends(require_agent_key)],
    summary="Search Western Blot evidence with a natural-language question",
    description=(
        "Accepts a natural-language question about Western Blot experiments "
        "(protein/target, cell line or organism, treatment/condition) and "
        "returns matching records. Intended for use as an agent tool call - "
        "the `question` field should be the agent's own natural-language "
        "query, not pre-formatted SQL or structured filters."
    ),
)
@limiter.limit(settings.agent_rate_limit)
async def agent_search(request: Request, body: SearchRequest):
    return await execute_search(body.query, body.limit)
