# HiveBlot beta API. Canonical host: Render free Web Service (see render.yaml
# and DEPLOYMENT.md §2). Also runs unchanged on Fly.io, Cloud Run, EC2, or
# locally. The build context is the REPO ROOT, not api/, because the staged
# figure crops live outside api/app:
#   docker build -f api/Dockerfile -t hiveblot-api .
# Render is told the same thing by render.yaml (dockerContext: .).
#
# PORT: Render injects it. The CMD binds 0.0.0.0:$PORT and falls back to 8000
# locally, so the same image works in both places.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY api/app ./app
COPY api/db ./db

# --- figure crops ------------------------------------------------------------
# Records store an ABSOLUTE image_crop_ref and /records/{id}/crop requires the
# path to resolve inside CROP_BASE_DIR, so the image reproduces the authoring
# path verbatim. That serves crops in a container with zero code change and,
# more importantly, zero change to the reviewed corpus. Storing crop refs
# relative to CROP_BASE_DIR would be cleaner; it is the tracked follow-up.
# api/crops/ is TRACKED (21 files, ~6 MB) because Render builds from the GitHub
# clone — an untracked directory would mean no figure evidence in the hosted
# beta. Refresh it with `python scripts/stage_crops.py`.
COPY api/crops/ /Users/niks/hive/western_blot_miner/data/pdf_runs/
ENV CROP_BASE_DIR=/Users/niks/hive/western_blot_miner/data/pdf_runs

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
