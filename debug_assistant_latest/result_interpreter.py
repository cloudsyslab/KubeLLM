"""Structured diagnosis for KubeLLM run artifacts."""

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from error_catalog import ERROR_PATTERNS
from report import collect_summaries_from_run, TestSummary


class FailureCategory(str, Enum):
    TIMEOUT = "TIMEOUT"
    IMPORT_ERROR = "IMPORT_ERROR"
    LLM_STALL = "LLM_STALL"
    VERIFICATION_MISMATCH = "VERIFICATION_MISMATCH"
    GROUND_TRUTH_FAIL = "GROUND_TRUTH_FAIL"
    TEARDOWN_FAIL = "TEARDOWN_FAIL"
    CONFIG_ERROR = "CONFIG_ERROR"
    K8S_ERROR = "K8S_ERROR"
    UNKNOWN = "UNKNOWN"


@dataclass
class RunDiagnosis:
    run_dir: str
    status: str
    category: FailureCategory
    summary: str
    test_name: Optional[str] = None
    evidence: List[str] = field(default_factory=list)
    suggested_actions: List[str] = field(default_factory=list)
    source_files: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "run_dir": self.run_dir,
            "status": self.status,
            "category": self.category.value,
            "summary": self.summary,
            "test_name": self.test_name,
            "evidence": self.evidence,
            "suggested_actions": self.suggested_actions,
            "source_files": self.source_files,
        }


def _load_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _status_priority(status: str) -> int:
    return {
        "TIMEOUT": 0,
        "ERROR": 1,
        "FAIL": 2,
        "PASS": 3,
    }.get(status, 4)


def _collect_candidate_summaries(run_dir: Path) -> List[TestSummary]:
    summaries = collect_summaries_from_run(run_dir)
    return sorted(summaries, key=lambda summary: (_status_priority(summary.status), summary.test_name))


def _find_target_test_dir(run_dir: Path, test_name: Optional[str]) -> Optional[Path]:
    if test_name:
        candidate = run_dir / test_name
        if candidate.exists():
            return candidate

    for child in sorted(run_dir.iterdir(), key=lambda path: path.name):
        if child.is_dir() and ((child / "stderr.log").exists() or (child / "stdout.log").exists()):
            return child
    return None


def _first_nonempty_lines(text: str, limit: int = 5) -> List[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[:limit]


def _dedupe(items: List[str]) -> List[str]:
    seen = set()
    ordered = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _categorize(summary: Optional[TestSummary], aggregate: Optional[dict], combined_text: str) -> tuple[FailureCategory, List[str]]:
    if summary and summary.status == "TIMEOUT":
        category = FailureCategory.TIMEOUT
        for pattern in ERROR_PATTERNS:
            if pattern.category_name == category.value:
                return category, pattern.actions

    if summary and summary.ground_truth_passed is False:
        for pattern in ERROR_PATTERNS:
            if pattern.category_name == FailureCategory.GROUND_TRUTH_FAIL.value:
                return FailureCategory.GROUND_TRUTH_FAIL, pattern.actions

    if summary and summary.verified is False:
        for pattern in ERROR_PATTERNS:
            if pattern.category_name == FailureCategory.VERIFICATION_MISMATCH.value:
                return FailureCategory.VERIFICATION_MISMATCH, pattern.actions

    for pattern in ERROR_PATTERNS:
        if re.search(pattern.regex, combined_text, re.IGNORECASE):
            return FailureCategory[pattern.category_name], pattern.actions

    if aggregate and aggregate.get("passed") == aggregate.get("total_tests") and aggregate.get("total_tests", 0) > 0:
        return FailureCategory.UNKNOWN, ["No failure detected. The run appears to have passed."]

    return FailureCategory.UNKNOWN, [
        "Read stderr.log and stdout.log directly for the failing test.",
        "Use grep or ripgrep on the error text to locate the responsible code path.",
        "Re-run the test after the next fix to confirm whether the failure class changes.",
    ]


def interpret_run(run_dir: Path | str) -> RunDiagnosis:
    run_path = Path(run_dir)
    if not run_path.exists():
        raise FileNotFoundError(f"Run directory does not exist: {run_path}")

    aggregate_path = run_path / "aggregate.json"
    aggregate = _load_json(aggregate_path)
    summaries = _collect_candidate_summaries(run_path)
    summary = summaries[0] if summaries else None

    test_dir = _find_target_test_dir(run_path, summary.test_name if summary else None)
    stderr_path = None if test_dir is None else test_dir / "stderr.log"
    stdout_path = None if test_dir is None else test_dir / "stdout.log"

    stderr_text = "" if stderr_path is None else _read_text(stderr_path)
    stdout_text = "" if stdout_path is None else _read_text(stdout_path)

    status = "UNKNOWN"
    if summary is not None:
        status = summary.status
    elif aggregate is not None:
        if aggregate.get("errors", 0):
            status = "ERROR"
        elif aggregate.get("failed", 0):
            status = "FAIL"
        elif aggregate.get("passed", 0):
            status = "PASS"

    evidence = []
    if summary and summary.error_message:
        evidence.append(summary.error_message)
    evidence.extend(_first_nonempty_lines(stderr_text, limit=5))
    if not evidence:
        evidence.extend(_first_nonempty_lines(stdout_text, limit=3))
    if aggregate and aggregate.get("error_tests"):
        evidence.append(f"error_tests={aggregate['error_tests']}")
    if aggregate and aggregate.get("failed_tests"):
        evidence.append(f"failed_tests={aggregate['failed_tests']}")
    evidence = _dedupe(evidence)

    combined_text = "\n".join(
        part
        for part in [
            json.dumps(aggregate, indent=2) if aggregate else "",
            summary.error_message if summary and summary.error_message else "",
            stderr_text,
            stdout_text,
        ]
        if part
    )

    category, actions = _categorize(summary, aggregate, combined_text)

    if status == "PASS":
        summary_text = "Run passed; no failure detected."
    elif summary is not None:
        summary_text = f"{summary.status} in {summary.test_name}: {category.value}"
    else:
        summary_text = f"{status} run: {category.value}"

    source_files = []
    for path in (aggregate_path, stderr_path, stdout_path):
        if path and path.exists():
            source_files.append(str(path))

    return RunDiagnosis(
        run_dir=str(run_path),
        status=status,
        category=category,
        summary=summary_text,
        test_name=None if summary is None else summary.test_name,
        evidence=evidence,
        suggested_actions=actions,
        source_files=source_files,
    )
