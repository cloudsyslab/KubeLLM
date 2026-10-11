import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

COMMAND_KEYWORDS = {
    "kubectl",
    "sed",
    "docker build",
    "apply -f",
    "delete pod",
    "replace --force",
    "get pod",
    "logs",
    "exec",
    "rollout",
    "describe",
    "printenv",
    "minikube",
    "kind load docker-image",
}
#how many dockers and kubectl commands are in the response, and how many times each command is used
#what type of commands

ISSUE_KEYWORDS = {
    "environment_variable": ["env:", "environment variable", "APP_MODE", "APP_ENV"],
    "incorrect_selector": ["selector", "service selector", "endpoints", "labels"],
    "liveness_probe": ["liveness probe", "livez", "healthz", "probe"],
    "missing_dependency": ["pip install", "dependency", "module not found", "ImportError"],
    "wrong_port": ["port", "service port", "container port", "targetPort"],
    "readiness": ["readiness", "readiness probe", "not ready"],
}

SHELL_BLOCK_RE = re.compile(r"```bash\n(.*?)```", re.DOTALL | re.IGNORECASE)
NUMERIC_STEP_RE = re.compile(r"^\s*(?:\d+\.|\-|\*)\s+", re.MULTILINE)
ANSI_ESCAPE_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
KNOWLEDGE_RESPONSE_START = "Perform the actions suggested here:"
KNOWLEDGE_RESPONSE_END = "The relevant configuration file is located in this path:"
ITERATION_RE = re.compile(r"^(?:.*[_-])?iter[-_]?(\d+)$", re.IGNORECASE)


def _clean_text(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _count_matches(text: str, patterns: Iterable[str]) -> int:
    count = 0
    text_lower = text.lower()
    for pattern in patterns:
        count += text_lower.count(pattern)
    return count


def _optional_bool_feature(value: Any) -> Any:
    """Encode a known Boolean as 1/0 and leave unknown values blank for CSV."""
    if value is True:
        return 1.0
    if value is False:
        return 0.0
    return ""


def _load_json_object(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return payload


def extract_logged_knowledge_response(stdout_text: str) -> str:
    """Recover the first knowledge-agent response embedded in a runner log."""
    clean_log = ANSI_ESCAPE_RE.sub("", stdout_text)
    start = clean_log.find(KNOWLEDGE_RESPONSE_START)
    if start < 0:
        raise ValueError(f"Could not find {KNOWLEDGE_RESPONSE_START!r}")
    start += len(KNOWLEDGE_RESPONSE_START)

    end = clean_log.find(KNOWLEDGE_RESPONSE_END, start)
    if end < 0:
        raise ValueError(f"Could not find {KNOWLEDGE_RESPONSE_END!r}")

    # Rich prefixes continuation lines with nine spaces and pads them to the
    # terminal width. Remove that presentation-only whitespace while keeping
    # the Markdown line structure used by the feature extractor.
    lines = []
    for raw_line in clean_log[start:end].splitlines():
        line = raw_line.rstrip()
        if line.startswith("         "):
            line = line[9:]
        else:
            line = line.lstrip()
        lines.append(line.rstrip())
    return "\n".join(lines).strip()


def extract_code_blocks(response: str) -> List[str]:
    """Return all fenced bash code blocks found in the response."""
    return [block.strip() for block in SHELL_BLOCK_RE.findall(response)]


def extract_step_lines(response: str) -> List[str]:
    """Return lines that look like numbered or bullet steps."""
    lines = []
    for line in response.splitlines():
        if NUMERIC_STEP_RE.match(line):
            lines.append(line.strip())
    return lines


def detect_issue_categories(response: str, top_n: int = 3) -> List[str]:
    """Detect likely issue categories from the knowledge-agent response."""
    text = _clean_text(response)
    scores = []
    for category, patterns in ISSUE_KEYWORDS.items():
        score = sum(text.count(pattern) for pattern in patterns)
        if score > 0:
            scores.append((score, category))
    scores.sort(reverse=True)
    return [category for _, category in scores[:top_n]]


def extract_features(
    response: str,
    config: Optional[Dict] = None,
    debug_metrics: Optional[Dict] = None,
) -> Dict[str, float]:
    """Extract numeric features from a raw knowledge agent response."""
    text = _clean_text(response)
    if not text:
        return {
            "response_length": 0,
            "num_code_blocks": 0,
            "num_step_lines": 0,
            "num_command_keywords": 0,
            "num_sentence_tokens": 0,
            "contains_verify": 0,
            "contains_wait": 0,
            "contains_logs": 0,
            "contains_apply": 0,
            "contains_sed": 0,
            "contains_env": 0,
            "contains_selector": 0,
            "contains_probe": 0,
            "contains_docker_build": 0,
            "category_count": 0,
        }

    code_blocks = extract_code_blocks(response)
    step_lines = extract_step_lines(response)

    features: Dict[str, float] = {
        "response_length": len(response),
        "response_word_count": len(text.split()),
        "num_code_blocks": len(code_blocks),
        "num_step_lines": len(step_lines),
        "num_command_keywords": _count_matches(response, COMMAND_KEYWORDS),
        "num_sentence_tokens": len(re.findall(r"[\w']+", response)),
        "contains_verify": float("verify" in text),
        "contains_wait": float("wait" in text),
        "contains_logs": float("logs" in text),
        "contains_apply": float("apply -f" in text or "kubectl apply" in text),
        "contains_sed": float("sed" in text),
        "contains_env": float("env:" in text or "environment variable" in text),
        "contains_selector": float("selector" in text or "service selector" in text),
        "contains_probe": float("probe" in text or "liveness" in text or "readiness" in text),
        "contains_docker_build": float("docker build" in text or "kind load docker-image" in text),
        "category_count": float(len(detect_issue_categories(response))),
    }

    if config is not None:
        features.update(
            {
                "has_test_name": float(bool(config.get("test-name"))),
                "has_yaml_file_name": float(bool(config.get("yaml-file-name"))),
            }
        )

    if debug_metrics is not None:
        features.update(
            {
                "debug_input_tokens": float(debug_metrics.get("input_tokens", 0)),
                "debug_output_tokens": float(debug_metrics.get("output_tokens", 0)),
                "debug_total_tokens": float(debug_metrics.get("total_tokens", 0)),
                "debug_task_status": float(debug_metrics.get("task_status", -1)),
            }
        )

    return features


def build_training_row(
    response: str,
    verification_status: Optional[bool] = None,
    config: Optional[Dict] = None,
    debug_metrics: Optional[Dict] = None,
) -> Dict[str, float]:
    """Build a training row for supervised models from response and status."""
    features = extract_features(response, config=config, debug_metrics=debug_metrics)
    features["label_success"] = 1.0 if verification_status else 0.0
    return features


def _iteration_number(case_dir: Path) -> int:
    for parent in (case_dir, *case_dir.parents):
        match = ITERATION_RE.match(parent.name)
        if match:
            return int(match.group(1))
    raise ValueError(f"Could not determine iteration from {case_dir}")


def _model_name(summary: Dict[str, Any], config: Dict[str, Any], phase: str) -> str:
    metrics = summary.get("metrics") or {}
    phase_metrics = metrics.get(phase) or {}
    if phase_metrics.get("model"):
        return str(phase_metrics["model"])

    config_key = {
        "api": "api-agent",
        "debug": "debug-agent",
        "verification": "verification-agent",
    }[phase]
    return str((config.get(config_key) or {}).get("model") or "")


def build_run_row(case_dir: Path, runs_root: Path) -> Dict[str, Any]:
    """Build one feature row from a KubeLLM test-result directory."""
    summary = _load_json_object(case_dir / "summary.json")
    config = _load_json_object(case_dir / "config_effective.json")

    response_artifact = case_dir / "knowledge_response.md"
    if response_artifact.is_file():
        response = response_artifact.read_text(encoding="utf-8")
    else:
        stdout_text = (case_dir / "stdout.log").read_text(
            encoding="utf-8", errors="replace"
        )
        response = extract_logged_knowledge_response(stdout_text)

    debug_metrics = dict(((summary.get("metrics") or {}).get("debug") or {}))
    debug_self_report = summary.get("debug_self_report")
    debug_metrics["task_status"] = (
        1 if debug_self_report is True else 0 if debug_self_report is False else -1
    )

    features = extract_features(response, config=config, debug_metrics=debug_metrics)
    ground_truth = summary.get("ground_truth_passed")
    features["label_success"] = _optional_bool_feature(ground_truth)

    try:
        relative_source_dir = str(case_dir.relative_to(runs_root))
        source_dir = str(Path(runs_root.name) / relative_source_dir)
    except ValueError:
        source_dir = str(case_dir)

    return {
        "dataset": runs_root.name,
        "iteration": _iteration_number(case_dir),
        "test_name": str(summary.get("test_name") or config.get("test-name") or case_dir.name),
        "source_dir": source_dir,
        "run_status": str(summary.get("status") or ""),
        "label_success": features.pop("label_success"),
        "label_available": float(isinstance(ground_truth, bool)),
        "ground_truth_passed": _optional_bool_feature(ground_truth),
        "verified": _optional_bool_feature(summary.get("verified")),
        "debug_self_report": _optional_bool_feature(debug_self_report),
        "api_model": _model_name(summary, config, "api"),
        "debug_model": _model_name(summary, config, "debug"),
        "verification_model": _model_name(summary, config, "verification"),
        "duration_s": float(summary.get("duration_s") or 0),
        **features,
    }


def export_run_features(
    runs_roots: Iterable[Path],
    output_path: Path,
    labeled_only: bool = False,
    strict: bool = False,
) -> List[Dict[str, Any]]:
    """Export one CSV row per discovered KubeLLM test result."""
    if isinstance(runs_roots, Path):
        roots = [runs_roots]
    else:
        roots = list(runs_roots)
    if not roots:
        raise ValueError("At least one runs root is required")

    discovered = []
    seen_summary_paths = set()
    for runs_root in roots:
        if not runs_root.is_dir():
            raise FileNotFoundError(f"Runs root does not exist: {runs_root}")
        for summary_path in runs_root.rglob("summary.json"):
            resolved_summary_path = summary_path.resolve()
            if resolved_summary_path in seen_summary_paths:
                continue
            try:
                iteration = _iteration_number(summary_path.parent)
            except ValueError as exc:
                if strict:
                    raise
                print(f"[WARN] Skipping {summary_path.parent}: {exc}", file=sys.stderr)
                continue
            seen_summary_paths.add(resolved_summary_path)
            discovered.append((runs_root, summary_path, iteration))

    discovered.sort(
        key=lambda item: (item[0].name, item[2], item[1].parent.name)
    )
    if not discovered:
        raise ValueError("No per-test summary.json files found under the supplied roots")

    rows: List[Dict[str, Any]] = []
    for runs_root, summary_path, _ in discovered:
        case_dir = summary_path.parent
        try:
            row = build_run_row(case_dir, runs_root)
        except Exception as exc:
            if strict:
                raise
            print(f"[WARN] Skipping {case_dir}: {exc}", file=sys.stderr)
            continue
        if labeled_only and not row["label_available"]:
            continue
        rows.append(row)

    if not rows:
        raise ValueError("No feature rows were produced")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return rows


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract numeric features from KubeLLM knowledge-agent responses."
    )
    parser.add_argument(
        "--runs-root",
        "--run-root",
        dest="runs_roots",
        action="append",
        type=Path,
        help=(
            "Directory containing model iteration results. May be supplied "
            "more than once to combine models."
        ),
    )
    parser.add_argument("--output", type=Path, help="Destination CSV path")
    parser.add_argument(
        "--labeled-only",
        action="store_true",
        help="Exclude ERROR runs whose ground-truth label is unavailable",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Stop on the first malformed run instead of warning and continuing",
    )
    args = parser.parse_args()
    if args.runs_roots is not None and args.output is None:
        parser.error("--output is required with --runs-root")
    if args.runs_roots is None and (
        args.output is not None or args.labeled_only or args.strict
    ):
        parser.error("--runs-root is required when batch options are used")
    return args


def sample_usage():
    """Example usage for feature extraction."""
    response = """
    1. Add the APP_MODE environment variable to the Pod manifest file.
    2. Delete the existing Pod.
    3. Recreate the Pod from the updated manifest.

    ```bash
    kubectl apply -f /path/to/environment_variable.yaml
    ```
    """
    row = build_training_row(response, verification_status=True)
    print(row)


if __name__ == "__main__":
    cli_args = _parse_args()
    if cli_args.runs_roots is None:
        sample_usage()
    else:
        exported_rows = export_run_features(
            cli_args.runs_roots,
            cli_args.output,
            labeled_only=cli_args.labeled_only,
            strict=cli_args.strict,
        )
        pass_count = sum(row["run_status"] == "PASS" for row in exported_rows)
        fail_count = sum(row["run_status"] == "FAIL" for row in exported_rows)
        error_count = sum(row["run_status"] == "ERROR" for row in exported_rows)
        print(f"Wrote {len(exported_rows)} rows to {cli_args.output}")
        print(f"PASS={pass_count} FAIL={fail_count} ERROR={error_count}")
