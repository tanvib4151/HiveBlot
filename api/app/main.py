from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .config import settings
from .limiter import limiter
from .routers import external, internal

app = FastAPI(
    title="Hive API",
    version="0.1.0",
    description=(
        "Internal endpoints (/, /health, /proteins, /search) back the Hive "
        "web frontend only. /v1/search is the stable, documented endpoint "
        "for external agents/integrations - see its description in this "
        "OpenAPI schema for how to call it."
    ),
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS applies to browser requests. It's meaningful for the internal API
# (called from web/'s server, but locking it down costs nothing) and largely
# irrelevant to /v1/search, which is meant to be called server-to-server by
# agents, not from a browser - auth (require_agent_key) is what actually
# guards that endpoint.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(internal.router)
app.include_router(external.router)
