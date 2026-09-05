"""Optional figure-image download via the PMC Open Access service.

Text extraction (captions + methods) works without any images. When run with
--with-images, the pipeline uses this module to pull the article's OA package
(a .tar.gz of the full article, figures included) and map figure graphic
filenames to local image files so they can be sent to Claude's vision model
and shown as thumbnails in the UI.
"""
import io
import tarfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

import requests

from . import config

_IMG_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff")


def _oa_package_url(pmcid: str) -> Optional[str]:
    """Ask the OA service for the downloadable .tar.gz package URL."""
    resp = requests.get(
        config.OA_SERVICE, params={"id": pmcid}, timeout=60
    )
    resp.raise_for_status()
    root = ET.fromstring(resp.text)
    # <records><record><link format="tgz" href="ftp://..."/></record></records>
    for link in root.iter("link"):
        if link.get("format") == "tgz":
            href = link.get("href", "")
            # The FTP host also serves over HTTPS, which avoids FTP firewalls.
            return href.replace("ftp://ftp.ncbi.nlm.nih.gov", "https://ftp.ncbi.nlm.nih.gov")
    return None


def download_figures(pmcid: str) -> dict[str, Path]:
    """Return {image_basename: local_path} for every image in the OA package.

    Returns an empty dict if the article has no downloadable package
    (e.g. not in the OA subset) — the caller falls back to text-only.
    """
    out_dir = config.IMAGE_DIR / pmcid
    try:
        url = _oa_package_url(pmcid)
    except (requests.RequestException, ET.ParseError):
        return {}
    if not url:
        return {}

    try:
        resp = requests.get(url, timeout=180)
        resp.raise_for_status()
    except requests.RequestException:
        return {}

    mapping: dict[str, Path] = {}
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(fileobj=io.BytesIO(resp.content), mode="r:gz") as tar:
            for member in tar.getmembers():
                if not member.isfile():
                    continue
                name = Path(member.name).name
                if not name.lower().endswith(_IMG_EXTS):
                    continue
                target = out_dir / name
                if not target.exists():
                    with tar.extractfile(member) as src:
                        target.write_bytes(src.read())
                mapping[name] = target
    except (tarfile.TarError, OSError):
        return {}
    return mapping


def resolve_image(figure, image_map: dict[str, Path]) -> Optional[Path]:
    """Best-effort match of a Figure to a downloaded image file.

    Prefers the exact graphic filename BioC referenced; otherwise falls back
    to a loose match on the figure id (e.g. 'Fig1' -> '...g001.jpg').
    """
    if not image_map:
        return None
    if figure.image_filename:
        base = Path(figure.image_filename).name
        if base in image_map:
            return image_map[base]
    # Loose match: any digits in the figure id appearing in a filename.
    digits = "".join(ch for ch in figure.figure_id if ch.isdigit())
    if digits:
        for name, path in image_map.items():
            if digits in name:
                return path
    return None
