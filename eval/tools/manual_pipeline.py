"""Agent-in-the-loop driver for a REAL paper through the Evidence Record engine.

No automated model backend (no Bedrock/Anthropic/OpenAI creds) is available in
this environment. Instead, a real model (the Claude Code agent) performs the
Stage-2 semantic extraction by looking at the real panel crop + caption/methods
and hand-writing the observed `rows` JSON. The DETERMINISTIC biology
(record_builder -> reconcile -> live UniProt resolve -> validation/anomalies),
which is the biologically sensitive part, runs exactly as in production.

Transport is agent-in-the-loop; the reconciliation/resolution path is real.

Usage:
  # Stage 1: OpenCV candidate detection on a real PDF, emit inspection requests
  python manual_pipeline.py preprocess <paper.pdf>

  # Stage 2->4: inject observed rows JSON, run the real records stage + UniProt
  python manual_pipeline.py run <out_dir> <responses.json>

`responses.json` is a list, in candidate order, of objects:
  [{"candidate_path": "...", "rows": [ ... OUTPUT_CONTRACT rows ... ]}, ...]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Import the real package.
REPO = Path(__file__).resolve()
for p in REPO.parents:
    if (p / "western_blot_miner" / "__init__.py").exists():
        sys.path.insert(0, str(p))
        break

from western_blot_miner import pdf_preprocess, pipeline, resolve  # noqa: E402
from western_blot_miner.llm_client import LLMClient  # noqa: E402


class SequentialAgentClient(LLMClient):
    """Returns pre-observed `rows` JSON, one candidate at a time, in order.

    Escalation must stay off (WBM_ESCALATE unset) so there is exactly one
    complete_json call per candidate, matching candidate iteration order.
    """

    name = "agent_in_the_loop"
    model = "claude-opus-4.8 (agent-in-the-loop)"

    def __init__(self, responses: list[dict]):
        # Preserve candidate_path so we can sanity-check ordering against the
        # text embedded in the prompt.
        self._responses = list(responses)
        self._i = 0

    def complete_json(self, system, user, image_data_url=None, max_tokens=4096, temperature=0.0):
        if self._i >= len(self._responses):
            raise RuntimeError("Ran out of pre-observed responses (escalation on?)")
        item = self._responses[self._i]
        self._i += 1
        return {"rows": item.get("rows", [])}


def cmd_preprocess(pdf_path: str) -> None:
    summary = pdf_preprocess.preprocess_pdf(pdf_path=Path(pdf_path))
    out_dir = Path(summary["out_dir"])
    candidates = json.loads((out_dir / "llm_candidates.json").read_text())
    contexts = pipeline._read_contexts(out_dir / "candidate_contexts.jsonl")

    requests = []
    for i, c in enumerate(candidates):
        cp = c["candidate_path"]
        requests.append({
            "index": i,
            "candidate_path": cp,
            "page": c.get("page"),
            "text_context": contexts.get(cp, ""),
        })
    (out_dir / "extraction_requests.json").write_text(json.dumps(requests, indent=2))

    print(f"paper_id: {summary['paper_id']}")
    print(f"out_dir: {out_dir}")
    print(f"pages={summary['pages']} candidates={summary['candidate_count']} "
          f"llm_candidates={summary['llm_candidate_count']}")
    print(f"extraction_requests: {out_dir / 'extraction_requests.json'}")
    print("\n--- CANDIDATE CROPS TO INSPECT ---")
    for r in requests:
        print(f"[{r['index']}] page={r['page']} crop={r['candidate_path']}")
        ctx = (r["text_context"] or "").strip().replace("\n", " ")
        print(f"      text[:300]: {ctx[:300]}")


def cmd_run(out_dir: str, responses_path: str) -> None:
    out_dir = Path(out_dir)
    summary = json.loads((out_dir / "summary.json").read_text())
    responses = json.loads(Path(responses_path).read_text())

    client = SequentialAgentClient(responses)
    resolver = resolve.default_resolver()  # live UniProt + cache

    result = pipeline.run_records_stage(
        summary, use_cache=False, client=client, resolver=resolver
    )
    print(json.dumps(result, indent=2))
    print("\n--- EVIDENCE RECORDS ---")
    print((out_dir / "evidence_records.json").read_text())


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "preprocess":
        cmd_preprocess(sys.argv[2])
    elif cmd == "run":
        cmd_run(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
        sys.exit(1)
