"""Stage the figure crops the reviewed corpus references into api/crops/,
ready for the API container image (see api/Dockerfile).

Records store an ABSOLUTE image_crop_ref and GET /records/{id}/crop requires
the path to resolve inside CROP_BASE_DIR, so the image recreates the authoring
path verbatim and this script only has to mirror the tail after `pdf_runs/`.
Copies only the crops actually referenced by eval/demo/*/supabase_rows.json
(21 files, ~6 MB) — not the whole 148 MB pipeline run directory.

    python scripts/stage_crops.py            # copy
    python scripts/stage_crops.py --check    # report only, copy nothing

Missing sources are reported, never fatal: a deployment without the crop
archive degrades to the text-only evidence panel by design.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEST = REPO / "api" / "crops"
MARKER = "pdf_runs/"


def main(check_only: bool) -> int:
    refs: set[str] = set()
    for path in sorted((REPO / "eval" / "demo").glob("*/supabase_rows.json")):
        for row in json.loads(path.read_text()):
            if row.get("image_crop_ref"):
                refs.add(row["image_crop_ref"])

    copied = missing = skipped = 0
    for ref in sorted(refs):
        src = Path(ref)
        if MARKER not in ref:
            print(f"  skip (not under {MARKER}): {ref}")
            skipped += 1
            continue
        rel = ref.split(MARKER, 1)[1]
        if not src.is_file():
            print(f"  missing: {rel}")
            missing += 1
            continue
        if check_only:
            copied += 1
            continue
        out = DEST / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)
        copied += 1

    total = sum(f.stat().st_size for f in DEST.rglob("*.png"))
    verb = "would copy" if check_only else "staged"
    print(f"{verb} {copied}/{len(refs)} referenced crops -> {DEST.relative_to(REPO)} "
          f"({total / 1e6:.1f} MB on disk); missing {missing}, skipped {skipped}")
    if missing:
        print("Missing crops are not fatal: those records serve a 404 and the "
              "evidence panel falls back to text-only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main("--check" in sys.argv))
