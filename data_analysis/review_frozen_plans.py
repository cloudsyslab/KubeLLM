#!/usr/bin/env python3
"""Blind, resumable review of frozen KnowledgeAgent plans before model outcomes."""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

from openai import AsyncOpenAI

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "debug_assistant_latest"))

from data_analysis.frozen_plan_inputs import build_current_knowledge_prompts, load_and_validate_frozen_plans  # noqa: E402
from lab_context import bootstrap_from_argv  # noqa: E402
from test_discovery import match_pattern  # noqa: E402


REVIEW_MODEL = "gpt-6.2-sol"
LABELS = ("usable", "incomplete", "wrong", "uncertain")
ISSUE_CODES = (
    "plausible_actionable",
    "missing_detail",
    "contradicts_visible_evidence",
    "unsupported_assumption",
    "ambiguous",
    "other",
)
INSTRUCTIONS = """You are an independent reviewer assessing a frozen KnowledgeAgent repair plan before any model-execution outcomes are known.

Use only the incident description, evidence made available to the KnowledgeAgent, and the proposed plan. Do not infer hidden Ground Truth, expected values, or evaluator results. Do not invent missing cluster observations. A plan is usable when it proposes a plausible repair supported by the visible evidence and gives enough direction for a DebugAgent to act. Label incomplete when a key step or detail is missing; wrong when it contradicts visible evidence; uncertain when the available evidence cannot support a clear judgment. Keep the plan in the benchmark regardless of your label. Return only the required structured fields; do not write prose."""
SCHEMA = {
    "type": "object",
    "properties": {
        "label": {"type": "string", "enum": list(LABELS)},
        "issue_codes": {
            "type": "array",
            "items": {"type": "string", "enum": list(ISSUE_CODES)},
            "maxItems": 3,
        },
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["label", "issue_codes", "confidence"],
    "additionalProperties": False,
}


def _read_existing(path: Path, model: str, manifest_sha256: str, resume: bool) -> dict[str, dict]:
    if not path.exists():
        return {}
    if not resume:
        raise ValueError(f"Review output already exists; use --resume after inspection: {path}")
    records: dict[str, dict] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("review_model") != model or row.get("plan_manifest_sha256") != manifest_sha256:
            raise ValueError(f"Existing review provenance differs at line {number}")
        if row.get("label") not in LABELS or not row.get("pair_id"):
            raise ValueError(f"Existing review record is invalid at line {number}")
        if row["pair_id"] in records:
            raise ValueError(f"Duplicate plan review record at line {number}")
        records[row["pair_id"]] = row
    return records


async def _review_all(
    plans: list[dict],
    *,
    model: str,
    manifest_sha256: str,
    output_path: Path,
    existing: dict[str, dict],
    concurrency: int,
) -> dict[str, dict]:
    client = AsyncOpenAI(max_retries=2, timeout=180.0)
    semaphore = asyncio.Semaphore(concurrency)
    write_lock = asyncio.Lock()
    results = dict(existing)
    output_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(output_path.parent, 0o700)

    async def review(plan: dict) -> None:
        pair_id = f"{plan['case']}__plan_{plan['replicate']:03d}"
        if pair_id in results:
            return
        request_content = json.dumps(
            {
                "incident_and_visible_evidence": plan["metadata"]["prompt"],
                "frozen_knowledge_agent_plan": plan["response"],
            },
            ensure_ascii=False,
        )
        async with semaphore:
            response = None
            payload = None
            for output_attempt in range(2):
                response = await client.responses.create(
                    model=model,
                    input=[
                        {"role": "system", "content": [{"type": "input_text", "text": INSTRUCTIONS}]},
                        {"role": "user", "content": [{"type": "input_text", "text": request_content}]},
                    ],
                    text={
                        "format": {
                            "type": "json_schema",
                            "name": "frozen_plan_usability_review",
                            "strict": True,
                            "schema": SCHEMA,
                        }
                    },
                    max_output_tokens=700,
                )
                try:
                    payload = json.loads(response.output_text)
                    break
                except (json.JSONDecodeError, TypeError):
                    if output_attempt == 1:
                        status = getattr(response, "status", "unknown")
                        raise ValueError(f"Reviewer returned incomplete structured output for {pair_id} (status={status})")
            if getattr(response, "status", "completed") != "completed":
                raise ValueError(f"Reviewer response did not complete for {pair_id}")
        label = payload.get("label")
        issue_codes = payload.get("issue_codes")
        confidence = payload.get("confidence")
        if label not in LABELS or not isinstance(issue_codes, list) or confidence not in {"high", "medium", "low"}:
            raise ValueError(f"Reviewer returned an invalid schema for {pair_id}")
        if any(code not in ISSUE_CODES for code in issue_codes):
            raise ValueError(f"Reviewer returned an unknown issue code for {pair_id}")
        usage = getattr(response, "usage", None)
        row = {
            "pair_id": pair_id,
            "test_name": plan["case"],
            "plan_replicate": plan["replicate"],
            "label": label,
            "issue_codes": issue_codes,
            "confidence": confidence,
            "review_model": model,
            "plan_manifest_sha256": manifest_sha256,
            "input_tokens": getattr(usage, "input_tokens", None),
            "output_tokens": getattr(usage, "output_tokens", None),
            "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        async with write_lock:
            with output_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, sort_keys=True) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(output_path, 0o600)
            results[pair_id] = row

    await asyncio.gather(*(review(plan) for plan in plans))
    await client.close()
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--cases", default="all")
    parser.add_argument("--replicates", type=int, default=5)
    parser.add_argument("--model", default=REVIEW_MODEL)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--lab-config", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / ".local/prediction_campaigns/model-router-consumer-v1/plan_review.jsonl")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.replicates < 1 or args.concurrency < 1:
        parser.error("--replicates and --concurrency must be positive")
    output = args.output.expanduser().resolve()
    private_root = (ROOT / ".local").resolve()
    try:
        output.relative_to(private_root)
    except ValueError:
        parser.error("Plan-review artifacts must remain under repository .local")
    cases = match_pattern(args.cases)
    prompts = build_current_knowledge_prompts(cases, ROOT)
    plans, manifest = load_and_validate_frozen_plans(
        source_dir=args.source_dir,
        cases=cases,
        replicates=args.replicates,
        source_root=args.source_root,
        target_root=str(ROOT),
        current_prompts=prompts,
    )
    bootstrap_from_argv(["--lab-config", str(args.lab_config.expanduser().resolve())])
    existing = _read_existing(output, args.model, manifest["manifest_sha256"], args.resume)
    completed = asyncio.run(
        _review_all(
            plans,
            model=args.model,
            manifest_sha256=manifest["manifest_sha256"],
            output_path=output,
            existing=existing,
            concurrency=args.concurrency,
        )
    )
    counts = Counter(row["label"] for row in completed.values())
    issue_counts = Counter(code for row in completed.values() for code in row["issue_codes"])
    usage_input = sum(int(row.get("input_tokens") or 0) for row in completed.values())
    usage_output = sum(int(row.get("output_tokens") or 0) for row in completed.values())
    summary = {
        "schema_version": 1,
        "review_model": args.model,
        "plan_manifest_sha256": manifest["manifest_sha256"],
        "plan_count": len(plans),
        "reviewed_count": len(completed),
        "label_counts": {label: counts.get(label, 0) for label in LABELS},
        "issue_code_counts": dict(sorted(issue_counts.items())),
        "input_tokens": usage_input,
        "output_tokens": usage_output,
        "reviewed_before_v1_outcomes": True,
        "labels_passed_to_router_or_agents": False,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    summary_path = output.with_name("plan_review_summary.json")
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    os.chmod(summary_path, 0o600)
    print(json.dumps({key: value for key, value in summary.items() if key != "created_at_utc"}, sort_keys=True))
    return 0 if len(completed) == len(plans) else 1


if __name__ == "__main__":
    raise SystemExit(main())
