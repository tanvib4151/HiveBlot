"""Flatten VLM western blot JSON and upload band records to Supabase."""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any

from . import biology, env

# ``requests`` is only needed for the HTTP upload path; importing it lazily keeps
# the deterministic flatten/enrich pipeline runnable with the standard library
# alone (and testable without network dependencies).


DEFAULT_TABLE_NAME = "western_blot_records"


def determine_blot_type(
    target: str | None,
    loading: bool,
    caption: str = "",
    methods: str = "",
) -> str:
    """Legacy blot-type value, now computed from evidence (no startswith('p')).

    Kept for backward compatibility with the existing ``western_blot_type``
    column. The authoritative classification is ``experiment_type`` produced by
    :func:`western_blot_miner.biology.classify_experiment`; this maps that to the
    three legacy values {loading_control, phospho_signaling, total_protein}.
    """
    if loading or biology.is_loading_control(target or ""):
        return "loading_control"
    modification = biology.detect_modification(target or "", caption=caption, methods=methods)
    if modification["modification_type"] == "phosphorylation":
        return "phospho_signaling"
    return "total_protein"


def load_json(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def flatten_json(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Expand positive VLM figure-level extractions into band-level rows."""
    rows: list[dict[str, Any]] = []

    for figure in data:
        extraction = figure.get("extraction")
        if not isinstance(extraction, dict):
            continue
        if extraction.get("is_western_blot") is not True:
            continue

        for panel in _iter_panel_extractions(extraction):
            sample = (
                panel.get("cell_line_tissue")
                or panel.get("biological_sample")
                or panel.get("sample_type")
                or None
            )
            organism = panel.get("organism") or None
            figure_label = _format_figure_label(
                panel.get("figure_label"),
                panel.get("panel_label"),
            )
            caption = panel.get("figure_caption") or ""
            methods = panel.get("methods") or panel.get("methods_context") or ""
            antibody_text = panel.get("antibody") or panel.get("antibody_context") or ""

            lane_lookup = {
                lane.get("lane_index"): lane.get("condition")
                for lane in panel.get("lanes_left_to_right", [])
                if isinstance(lane, dict)
            }
            row_lookup = {
                target.get("row_index"): target
                for target in panel.get("targets_top_to_bottom", [])
                if isinstance(target, dict)
            }
            target_lookup = {
                target.get("target"): target
                for target in panel.get("targets_top_to_bottom", [])
                if isinstance(target, dict) and target.get("target")
            }

            for band in panel.get("bands", []):
                if not isinstance(band, dict):
                    continue

                target = band.get("target")
                row_index = band.get("row_index")
                target_info = row_lookup.get(row_index) or target_lookup.get(target) or {}
                if not target:
                    target = target_info.get("target")
                if not target:
                    continue

                condition = lane_lookup.get(band.get("lane_index"))
                loading_flag = bool(target_info.get("is_loading_control", False))

                base_row = {
                    "paper_id": figure.get("paper_id"),
                    "page": figure.get("page"),
                    "western_blot_type": determine_blot_type(
                        target, loading_flag, caption=caption, methods=methods
                    ),
                    "sample": sample,
                    "organism": organism,
                    "treatment_context": panel.get("treatment_context") or None,
                    "figure_label": figure_label,
                    "target": target,
                    "condition": condition,
                    "band_detected": band.get("band_state") == "present",
                    "confidence": _confidence_value(
                        band.get("confidence") or target_info.get("confidence")
                    ),
                }
                base_row.update(
                    enrich_biological_fields(
                        target=target,
                        caption=caption,
                        methods=methods,
                        antibody_text=antibody_text,
                        treatment_context=panel.get("treatment_context") or "",
                        condition=condition or "",
                        band_state=band.get("band_state"),
                        is_loading_control=loading_flag,
                    )
                )
                rows.append(base_row)

    return rows


# Legacy experiment_type -> legacy western_blot_type value.
_LEGACY_BLOT_TYPE = {
    "loading_control": "loading_control",
    "phospho_western": "phospho_signaling",
    "co_ip": "total_protein",
    "purified_protein": "total_protein",
    "standard_western": "total_protein",
    "unknown": "total_protein",
}


def enrich_biological_fields(
    target: str,
    caption: str = "",
    methods: str = "",
    antibody_text: str = "",
    treatment_context: str = "",
    condition: str = "",
    band_state: str | None = None,
    is_loading_control: bool = False,
) -> dict[str, Any]:
    """Compute the additive Western Blot Evidence Record fields for one band row.

    Everything here is deterministic (Stage-1) biology from
    :mod:`western_blot_miner.biology` plus regex extractors. Semantic fields the
    VLM is better at (already present on the row) are not recomputed. Provenance
    and per-field validation status travel with the values so the UI can always
    show *why* a value was assigned.
    """
    text_blob = " ".join(t for t in (caption, methods, antibody_text, treatment_context, condition) if t)

    modification = biology.detect_modification(target, caption, methods, antibody_text)
    experiment = biology.classify_experiment(
        target, caption, methods, modification=modification, is_loading_control_flag=is_loading_control
    )
    protein = biology.normalize_protein(target)
    antibody = extract_antibody(antibody_text or methods or caption)
    doses = extract_dose(f"{condition} {treatment_context}")
    durations = extract_duration(f"{condition} {treatment_context}")
    reported_mw = extract_kda(caption or methods)

    provenance = {
        "canonical_target": protein["status"],
        "modification": modification["status"],
        "experiment_type": "SUPPORTED" if experiment["confidence"] >= 0.8 else "AMBIGUOUS",
        "sources": {
            "caption": bool(caption),
            "methods": bool(methods),
            "antibody_text": bool(antibody_text),
        },
        "modification_evidence": modification.get("evidence", []),
        "experiment_evidence": experiment.get("evidence", []),
    }

    return {
        # --- protein identity ---
        "raw_target_name": target,
        "canonical_target": protein["canonical"],
        "uniprot_id": protein["uniprot_id"],
        "protein_status": protein["status"],
        # --- modification ---
        "modification_type": modification["modification_type"],
        "residue": modification["residue"],
        "residue_position": modification["residue_position"],
        "modification_label": modification["normalized_label"],
        "modification_status": modification["status"],
        "phospho_specific_antibody": modification["phospho_specific_antibody"],
        # --- experiment ---
        "experiment_type": experiment["experiment_type"],
        "experiment_flags": experiment["experiment_flags"],
        "experiment_type_confidence": experiment["confidence"],
        # --- sample extras ---
        "loading_control": is_loading_control or biology.is_loading_control(target),
        # --- treatment (deterministic parse; never invented) ---
        "treatment_name": None,  # semantic; filled by VLM stage where available
        "dose": doses[0]["value"] if doses else None,
        "dose_unit": doses[0]["unit"] if doses else None,
        "duration": durations[0]["value"] if durations else None,
        "duration_unit": durations[0]["unit"] if durations else None,
        # --- antibody ---
        "antibody_target": antibody.get("target"),
        "antibody_vendor": antibody.get("vendor"),
        "antibody_catalog_number": antibody.get("catalog_number"),
        "antibody_clone": antibody.get("clone"),
        "antibody_dilution": antibody.get("dilution"),
        # --- molecular weight (reported only; NOT measured from image) ---
        "reported_molecular_weight_kda": reported_mw,
        "expected_molecular_weight_kda": None,  # reference lookup, filled later
        "molecular_weight_source": "caption_or_methods_text" if reported_mw else None,
        # --- provenance + validation scaffold (Phase 4 expands validation) ---
        "provenance": provenance,
        "needs_review": _needs_review(protein, modification, experiment),
        "extraction_stage": "deterministic+vlm",
    }


def _needs_review(protein: dict, modification: dict, experiment: dict) -> bool:
    if protein["status"] in ("AMBIGUOUS", "MISSING"):
        return True
    if modification["status"] == "AMBIGUOUS":
        return True
    if experiment["experiment_type"] == "unknown" or experiment["confidence"] < 0.5:
        return True
    return False


# --------------------------------------------------------------------------- #
# Stage-1 deterministic extractors (regex; no model)
# --------------------------------------------------------------------------- #

def extract_kda(text: str) -> float | None:
    m = biology._KDA.search(text or "")
    if not m:
        return None
    try:
        return float(m.group(1).replace("~", "").strip())
    except ValueError:
        return None


def extract_dose(text: str) -> list[dict[str, Any]]:
    text = text or ""
    return [
        {"value": float(m.group(1)), "unit": m.group(2)}
        for m in biology._DOSE.finditer(text)
        if not biology.is_figure_reference_number(text, m.start(1))
    ]


def extract_duration(text: str) -> list[dict[str, Any]]:
    text = text or ""
    return [
        {"value": float(m.group(1)), "unit": m.group(2)}
        for m in biology._DURATION.finditer(text)
        if not biology.is_figure_reference_number(text, m.start(1))
    ]


def _expand_series(text: str, series_re, single_re) -> list[dict[str, Any]]:
    """Every value a text states, INCLUDING enumerated series sharing one unit.

    "10, 30 and 60 ug/ml" -> three values, not one; "0, 5, 10, 20, 30, 60 min"
    -> six timepoints. Order is preserved and duplicates are kept out; nothing
    is inferred that the text does not literally state.
    """
    text = text or ""
    out: list[dict[str, Any]] = []
    consumed: list[tuple[int, int]] = []
    for m in series_re.finditer(text):
        if biology.is_figure_reference_number(text, m.start(1)):
            # "Figs. 2, 3 and 4" is a FIGURE LIST, not a value series — and its
            # trailing number must not leak back in through the singles pass.
            consumed.append(m.span())
            continue
        unit = m.group(2)
        # group(1) is the whole enumeration INCLUDING its final value.
        for num in re.findall(r"\d+(?:\.\d+)?", m.group(1)):
            out.append({"value": float(num), "unit": unit})
        consumed.append(m.span())
    # Singles outside any series span.
    for m in single_re.finditer(text):
        if any(s <= m.start() < e for s, e in consumed):
            continue
        if biology.is_figure_reference_number(text, m.start(1)):
            continue
        out.append({"value": float(m.group(1)), "unit": m.group(2)})
    # De-duplicate, preserving first-seen order.
    seen, uniq = set(), []
    for d in out:
        k = (d["value"], d["unit"].lower())
        if k not in seen:
            seen.add(k)
            uniq.append(d)
    return uniq


def extract_dose_series(text: str) -> list[dict[str, Any]]:
    """All doses stated, expanding enumerations (dose-response aware)."""
    return _expand_series(text, biology._DOSE_SERIES, biology._DOSE)


def extract_duration_series(text: str) -> list[dict[str, Any]]:
    """All durations/timepoints stated, expanding enumerations (time-course aware)."""
    return _expand_series(text, biology._DURATION_SERIES, biology._DURATION)


def extract_antibody(text: str) -> dict[str, Any]:
    """Best-effort antibody metadata from a text blob. Nulls, never inventions."""
    text = text or ""
    low = text.lower()
    vendor = None
    for key, label in biology.VENDORS.items():
        if key in low:
            vendor = label
            break
    cat = biology._CATALOG.search(text) or biology._CATALOG_VENDORCODE.search(text)
    catalog_number = cat.group(1).strip() if cat else None
    dil = biology._DILUTION.search(text)
    dilution = f"1:{dil.group(1)}" if dil else None
    clone_m = re.search(r"\bclone\s+([A-Za-z0-9\-]+)", text, re.IGNORECASE)
    clone = clone_m.group(1) if clone_m else None
    return {
        "target": None,
        "vendor": vendor,
        "catalog_number": catalog_number,
        "clone": clone,
        "dilution": dilution,
    }


def _iter_panel_extractions(extraction: dict[str, Any]) -> list[dict[str, Any]]:
    panels = extraction.get("panels")
    if not isinstance(panels, list) or not panels:
        return [extraction]

    merged_panels = []
    root_context = {
        key: extraction.get(key)
        for key in (
            "figure_label",
            "figure_caption",
            "biological_sample",
            "cell_line_tissue",
            "organism",
            "sample_type",
            "treatment_context",
        )
    }
    for panel in panels:
        if not isinstance(panel, dict):
            continue
        merged = {
            **root_context,
            **{key: value for key, value in panel.items() if value not in (None, "")},
        }
        merged_panels.append(merged)
    return merged_panels


def _format_figure_label(figure_label: Any, panel_label: Any) -> str | None:
    figure = str(figure_label).strip() if figure_label else ""
    panel = str(panel_label).strip() if panel_label else ""
    if figure and panel and not _ends_with_panel_label(figure, panel):
        return f"{figure}{panel}"
    return figure or panel or None


def _ends_with_panel_label(figure_label: str, panel_label: str) -> bool:
    figure = figure_label.strip()
    panel = panel_label.strip()
    if not figure.lower().endswith(panel.lower()):
        return False
    prefix = figure[: -len(panel)]
    return not prefix or not prefix[-1].isalpha()


def _confidence_value(confidence: Any) -> float | None:
    if isinstance(confidence, (int, float)):
        return float(confidence)
    if not isinstance(confidence, str):
        return None
    return {
        "high": 0.9,
        "medium": 0.6,
        "low": 0.3,
    }.get(confidence.strip().lower())


def upload_rows(
    rows: list[dict[str, Any]],
    supabase_url: str | None = None,
    supabase_key: str | None = None,
    table_name: str = DEFAULT_TABLE_NAME,
    idempotent: bool = False,
    chunk_size: int = 500,
) -> int:
    """Upload rows to Supabase using the PostgREST endpoint."""
    supabase_url = (supabase_url or os.environ.get("SUPABASE_URL", "")).rstrip("/")
    supabase_key = supabase_key or os.environ.get("SUPABASE_KEY", "")
    if not supabase_url:
        raise ValueError("SUPABASE_URL is required")
    if not supabase_key:
        raise ValueError("SUPABASE_KEY is required")

    endpoint = f"{supabase_url}/rest/v1/{table_name}"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    import requests  # lazy: only needed for the HTTP upload path

    uploaded = 0
    if idempotent:
        rows = [
            row for row in rows
            if not _row_exists(endpoint, headers, row)
        ]

    for start in range(0, len(rows), chunk_size):
        chunk = rows[start : start + chunk_size]
        response = requests.post(endpoint, headers=headers, json=chunk, timeout=120)
        response.raise_for_status()
        uploaded += len(chunk)
    return uploaded


def convert_and_upload(
    json_path: str | Path,
    output_path: str | Path | None = None,
    upload: bool = False,
    supabase_url: str | None = None,
    supabase_key: str | None = None,
    table_name: str = DEFAULT_TABLE_NAME,
    idempotent: bool = False,
) -> dict[str, Any]:
    data = load_json(json_path)
    rows = flatten_json(data)

    if output_path is not None:
        Path(output_path).write_text(json.dumps(rows, indent=2), encoding="utf-8")

    uploaded = 0
    if upload:
        uploaded = upload_rows(
            rows,
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            table_name=table_name,
            idempotent=idempotent,
        )

    return {
        "figures": len(data),
        "rows": len(rows),
        "uploaded": uploaded,
        "output_path": str(output_path) if output_path else None,
    }


def watch_jsonl_and_upload(
    jsonl_path: str | Path,
    state_path: str | Path | None = None,
    output_path: str | Path | None = None,
    supabase_url: str | None = None,
    supabase_key: str | None = None,
    table_name: str = DEFAULT_TABLE_NAME,
    poll_seconds: float = 5.0,
    stop_after_idle_seconds: float | None = None,
    start_at_end: bool = False,
) -> dict[str, Any]:
    """Watch a VLM JSONL file and upload positive records as they appear."""
    jsonl_path = Path(jsonl_path)
    state_path = Path(state_path) if state_path else jsonl_path.with_suffix(".upload_state.json")
    output_path = Path(output_path) if output_path else jsonl_path.with_name("supabase_rows_streamed.jsonl")

    if start_at_end and not state_path.exists():
        line_offset = _count_lines(jsonl_path)
        _write_upload_state(state_path, line_offset)
    else:
        line_offset = _read_upload_state(state_path)
    uploaded_total = 0
    positive_figures = 0
    idle_started_at: float | None = None

    while True:
        uploaded_this_pass = 0
        line_count = 0
        if jsonl_path.exists():
            with jsonl_path.open(encoding="utf-8") as handle:
                for line_count, line in enumerate(handle, 1):
                    if line_count <= line_offset:
                        continue
                    if not line.strip():
                        continue

                    record = json.loads(line)
                    rows = flatten_json([record])
                    line_offset = line_count
                    _write_upload_state(state_path, line_offset)
                    if not rows:
                        continue

                    positive_figures += 1
                    with output_path.open("a", encoding="utf-8") as out:
                        for row in rows:
                            out.write(json.dumps(row) + "\n")

                    uploaded = upload_rows(
                        rows,
                        supabase_url=supabase_url,
                        supabase_key=supabase_key,
                        table_name=table_name,
                        idempotent=True,
                    )
                    uploaded_total += uploaded
                    uploaded_this_pass += uploaded
                    print(
                        f"Uploaded {uploaded} rows from {record.get('candidate_path')} "
                        f"(total {uploaded_total})",
                        flush=True,
                    )

        if uploaded_this_pass:
            idle_started_at = None
        elif stop_after_idle_seconds is not None:
            now = time.monotonic()
            if idle_started_at is None:
                idle_started_at = now
            elif now - idle_started_at >= stop_after_idle_seconds:
                break

        time.sleep(poll_seconds)

    return {
        "line_offset": line_offset,
        "positive_figures": positive_figures,
        "uploaded": uploaded_total,
        "state_path": str(state_path),
        "output_path": str(output_path),
    }


def main() -> None:
    env.load_env()

    parser = argparse.ArgumentParser(description="Load VLM western blot JSON into Supabase.")
    parser.add_argument("json_path", type=Path, help="Positive-only VLM JSON path")
    parser.add_argument("--output", type=Path, help="Write flattened rows to this JSON file")
    parser.add_argument("--upload", action="store_true", help="Upload flattened rows to Supabase")
    parser.add_argument("--watch-jsonl", action="store_true", help="Watch a VLM JSONL file and upload positives as they arrive")
    parser.add_argument("--state", type=Path, help="State file for --watch-jsonl line offsets")
    parser.add_argument("--supabase-url", help="Supabase project URL")
    parser.add_argument("--supabase-key", help="Supabase API key")
    parser.add_argument(
        "--table",
        default=os.environ.get("SUPABASE_TABLE", DEFAULT_TABLE_NAME),
        help="Supabase table name",
    )
    parser.add_argument(
        "--idempotent",
        action="store_true",
        help="Skip rows that already match paper_id,page,target,condition",
    )
    parser.add_argument("--poll-seconds", type=float, default=5.0, help="Polling interval for --watch-jsonl")
    parser.add_argument("--stop-after-idle-seconds", type=float, help="Stop watch mode after this much idle time")
    parser.add_argument("--start-at-end", action="store_true", help="In watch mode, skip currently written JSONL lines")
    args = parser.parse_args()

    if args.watch_jsonl:
        summary = watch_jsonl_and_upload(
            args.json_path,
            state_path=args.state,
            output_path=args.output,
            supabase_url=args.supabase_url,
            supabase_key=args.supabase_key,
            table_name=args.table,
            poll_seconds=args.poll_seconds,
            stop_after_idle_seconds=args.stop_after_idle_seconds,
            start_at_end=args.start_at_end,
        )
    else:
        summary = convert_and_upload(
            args.json_path,
            output_path=args.output,
            upload=args.upload,
            supabase_url=args.supabase_url,
            supabase_key=args.supabase_key,
            table_name=args.table,
            idempotent=args.idempotent,
        )
    print(json.dumps(summary, indent=2))


def _read_upload_state(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        return int(json.loads(path.read_text(encoding="utf-8")).get("line_offset", 0))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return 0


def _write_upload_state(path: Path, line_offset: int) -> None:
    path.write_text(json.dumps({"line_offset": line_offset}, indent=2), encoding="utf-8")


def _count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as handle:
        return sum(1 for _ in handle)


def _row_exists(endpoint: str, headers: dict[str, str], row: dict[str, Any]) -> bool:
    import requests  # lazy: only needed for the HTTP upload path

    params = {
        "select": "id",
        "limit": "1",
    }
    for key in ("paper_id", "page", "target", "condition"):
        value = row.get(key)
        if value is None:
            params[key] = "is.null"
        else:
            params[key] = f"eq.{value}"

    response = requests.get(endpoint, headers=headers, params=params, timeout=60)
    response.raise_for_status()
    return bool(response.json())


if __name__ == "__main__":
    main()
