"""End-to-end local PDF pipeline.

Run it:
    python -m western_blot_miner.pipeline papers/example.pdf
"""
import argparse
import json
import os
from pathlib import Path

from . import env, pdf_preprocess, supabase_loader, vlm_extract


def run_pdf_pipeline(pdf_path: str | Path, use_cache: bool = True, mode: str | None = None) -> dict:
    """Preprocess a PDF, then extract with the selected engine.

    The OpenCV candidate filtering (cheap Stage 1/2) always runs. The extraction
    stage is selected by ``mode`` (or ``WBM_EXTRACTION_MODE``):
      * ``legacy``  (default) -> vlm_extract.run_vlm_extraction (old flat rows)
      * ``records``           -> the Phase-3 Evidence Record engine
                                 (extract_records.extract_panel).
    The legacy path is preserved so the new path can be adopted without risk.
    """
    pdf_path = Path(pdf_path)
    mode = (mode or os.environ.get("WBM_EXTRACTION_MODE", "legacy")).lower()
    summary = pdf_preprocess.preprocess_pdf(
        pdf_path=pdf_path,
        paper_id=None,
        out_dir=None,
        dpi=_env_int("WBM_PDF_DPI", pdf_preprocess.DEFAULT_DPI),
        min_candidate_score=_env_float(
            "WBM_MIN_CANDIDATE_SCORE",
            pdf_preprocess.DEFAULT_MIN_CANDIDATE_SCORE,
        ),
        min_llm_score=_env_float("WBM_MIN_LLM_SCORE", pdf_preprocess.DEFAULT_MIN_LLM_SCORE),
    )
    print(
        f"Rendered {summary['pages']} pages; "
        f"{summary['candidate_count']} candidates after CV filtering; "
        f"{summary['llm_candidate_count']} candidates above the model threshold."
    )
    print(f"Paper ID: {summary['paper_id']}")
    print(f"Output: {summary['out_dir']}")
    print(f"Extraction mode: {mode}")

    if mode == "records":
        records_summary = run_records_stage(summary, use_cache=use_cache)
        return {"preprocess": summary, "records": records_summary, "mode": "records"}

    # ---------------- legacy VLM path (default) ----------------
    if use_cache:
        print(
            "VLM resume is enabled: cached successful extractions are reused; "
            "only missing or failed candidates query the VLM.",
            flush=True,
        )
    else:
        print(
            "VLM cache is disabled: every candidate above threshold will query the VLM.",
            flush=True,
        )

    supabase_stream_path = Path(summary["out_dir"]) / "supabase_rows_streamed.jsonl"
    if not use_cache and supabase_stream_path.exists():
        supabase_stream_path.write_text("", encoding="utf-8")

    def upload_positive(record: dict) -> int:
        rows = supabase_loader.flatten_json([record])
        if not rows:
            return 0
        with supabase_stream_path.open("a", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row) + "\n")
        uploaded = supabase_loader.upload_rows(
            rows,
            table_name=os.environ.get("SUPABASE_TABLE", supabase_loader.DEFAULT_TABLE_NAME),
            idempotent=_env_bool("SUPABASE_IDEMPOTENT", True),
        )
        print(
            f"Supabase upload: {uploaded} rows from {record['candidate_path']}",
            flush=True,
        )
        return uploaded

    vlm_summary = vlm_extract.run_vlm_extraction(
        run_dir=summary["out_dir"],
        model=os.environ.get("WBM_VLM_MODEL", vlm_extract.DEFAULT_VLM_MODEL),
        max_tokens=_env_int("WBM_VLM_MAX_TOKENS", vlm_extract.DEFAULT_MAX_TOKENS),
        timeout=_env_int("WBM_VLM_TIMEOUT", vlm_extract.DEFAULT_TIMEOUT),
        image_max_side=_env_int("WBM_VLM_IMAGE_MAX_SIDE", vlm_extract.DEFAULT_IMAGE_MAX_SIDE),
        resume=use_cache,
        on_positive=upload_positive,
    )
    print(
        f"VLM results: {vlm_summary['results']} records; "
        f"{vlm_summary['positive_results']} western blot positives."
    )
    print(
        "VLM work this run: "
        f"{vlm_summary['cached_results']} cached, "
        f"{vlm_summary['queried_candidates']} queried."
    )
    print(
        "Supabase streamed during VLM extraction: "
        f"{vlm_summary['streamed_positive_rows']} rows"
    )
    if use_cache and vlm_summary["queried_candidates"] == 0:
        print(
            "Supabase streaming skipped: all VLM results came from cache, "
            "so no new positive-candidate upload callbacks ran.",
            flush=True,
        )

    flattened_path = Path(summary["out_dir"]) / "supabase_rows.json"
    supabase_summary = supabase_loader.convert_and_upload(
        json_path=vlm_summary["positives_json"],
        output_path=flattened_path,
        upload=False,
    )
    print(
        f"Supabase rows: {supabase_summary['rows']} written locally to {flattened_path} "
        "(not uploaded in this final conversion step)."
    )

    return {
        "preprocess": summary,
        "vlm": vlm_summary,
        "supabase": supabase_summary,
    }


def run_records_stage(summary: dict, use_cache: bool = True, client=None, resolver=None) -> dict:
    """Phase-3 Evidence Record extraction over the OpenCV panel candidates.

    Reuses the same candidate crops + text context the legacy path uses, but runs
    each panel through extract_records.extract_panel to produce biologically
    reconciled Evidence Records, then projects them to Supabase rows. Resumable:
    candidates already recorded in evidence_records.jsonl are skipped.
    """
    from . import extract_records, llm_client, resolve
    from .evidence_record import EvidenceRecord

    run_dir = Path(summary["out_dir"])
    candidates = json.loads((run_dir / "llm_candidates.json").read_text(encoding="utf-8"))
    contexts = _read_contexts(run_dir / "candidate_contexts.jsonl")

    client = client or llm_client.get_client()
    escalate_client = (
        llm_client.get_client(escalation=True) if _env_bool("WBM_ESCALATE", False) else None
    )
    resolver = resolver or resolve.default_resolver()
    image_max_side = _env_int("WBM_VLM_IMAGE_MAX_SIDE", vlm_extract.DEFAULT_IMAGE_MAX_SIDE)

    records_jsonl = run_dir / "evidence_records.jsonl"
    done: set[str] = set()
    if use_cache and records_jsonl.exists():
        for line in records_jsonl.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(json.loads(line).get("candidate_path"))
    elif not use_cache and records_jsonl.exists():
        records_jsonl.write_text("", encoding="utf-8")

    queried = 0
    failures = 0
    with records_jsonl.open("a", encoding="utf-8") as handle:
        for idx, cand in enumerate(candidates, 1):
            cpath = cand["candidate_path"]
            if cpath in done:
                continue
            queried += 1
            panel_context = _panel_context(summary, cand, contexts.get(cpath, ""))
            try:
                image_url = vlm_extract.image_data_url(cpath, max_side=image_max_side)
            except Exception:
                image_url = None
            try:
                recs = extract_records.extract_panel(
                    panel_context, image_data_url=image_url,
                    client=client, resolver=resolver, escalate_client=escalate_client,
                )
            except Exception as exc:  # model/network failure -> record and continue
                failures += 1
                handle.write(json.dumps({"candidate_path": cpath, "error": str(exc)}) + "\n")
                handle.flush()
                print(f"  [{idx}/{len(candidates)}] {cpath}: extraction failed: {exc}", flush=True)
                continue
            for rec in recs:
                d = rec.model_dump(mode="json")
                d["candidate_path"] = cpath
                handle.write(json.dumps(d) + "\n")
                handle.flush()
            print(f"  [{idx}/{len(candidates)}] {cpath}: {len(recs)} record(s)", flush=True)

    # Rebuild ALL records (cached + new) from the jsonl for the final artifacts.
    all_records = []
    for line in records_jsonl.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        if "error" in d or "record_id" not in d:
            continue
        all_records.append(EvidenceRecord.model_validate(d))

    (run_dir / "evidence_records.json").write_text(
        json.dumps([r.model_dump(mode="json") for r in all_records], indent=2), encoding="utf-8")
    rows = extract_records.records_to_supabase_rows(all_records)
    (run_dir / "supabase_rows.json").write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")

    uploaded = 0
    if _env_bool("WBM_UPLOAD", False) and os.environ.get("SUPABASE_URL"):
        uploaded = supabase_loader.upload_rows(
            rows,
            table_name=os.environ.get("SUPABASE_TABLE", supabase_loader.DEFAULT_TABLE_NAME),
            idempotent=_env_bool("SUPABASE_IDEMPOTENT", True),
        )

    print(
        f"Evidence Records: {len(all_records)} ({queried} queried, {failures} failed); "
        f"{len(rows)} supabase rows; {uploaded} uploaded."
    )
    return {
        "records": len(all_records),
        "queried": queried,
        "failures": failures,
        "rows": len(rows),
        "uploaded": uploaded,
        "records_path": str(run_dir / "evidence_records.json"),
        "rows_path": str(run_dir / "supabase_rows.json"),
    }


def _panel_context(summary: dict, candidate: dict, text_context: str) -> dict:
    """Map an OpenCV candidate + its retrieved text into an extract_panel context."""
    return {
        "paper": {
            "paper_id": summary.get("paper_id"),
            "doi": summary.get("extracted_doi"),
        },
        "figure": {
            "page": candidate.get("page"),
            "image_crop_ref": candidate.get("candidate_path"),
        },
        # The PDF retrieval blob mixes caption + methods context; give it to the
        # model as `methods`. Per-source modification claims still come from the
        # antibody strings the model reports (rank-1 evidence).
        "texts": {"caption": "", "methods": text_context},
    }


def _read_contexts(path: Path) -> dict[str, str]:
    contexts: dict[str, str] = {}
    if not path.exists():
        return contexts
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            contexts[rec["candidate_path"]] = rec.get("text_context", "")
    return contexts


def main() -> None:
    env.load_env()

    ap = argparse.ArgumentParser(
        description="Extract western blot data from a PDF and write positives to Supabase."
    )
    ap.add_argument("pdf", type=Path, help="Path to the paper PDF")
    ap.add_argument(
        "--no-cache",
        action="store_true",
        help="Ignore cached extraction JSONL and rerun every candidate.",
    )
    ap.add_argument(
        "--mode",
        choices=["legacy", "records"],
        default=None,
        help="Extraction engine: 'legacy' VLM path or 'records' Evidence Record engine "
        "(default: WBM_EXTRACTION_MODE or 'legacy').",
    )
    args = ap.parse_args()
    run_pdf_pipeline(args.pdf, use_cache=not args.no_cache, mode=args.mode)


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    return int(value) if value else default


def _env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    return float(value) if value else default


if __name__ == "__main__":
    main()
