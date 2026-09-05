# Hive

Western Blot evidence search. Successor to `QBI`/`blot_backend`, rebuilt clean
- see [EXECUTION_PLAN.md](EXECUTION_PLAN.md) for the full rationale and the
remaining steps to get this to production.

```
hive/
├── web/   # Next.js frontend - see web/README (if present) or app/ directly
└── api/   # FastAPI backend  - see api/README.md
```

Quick start (once each app's `.env` is filled in, see each app's `.env.example`):

```bash
# terminal 1
cd api && pip install -r requirements.txt && uvicorn app.main:app --reload

# terminal 2
cd web && npm install && npm run dev
```
