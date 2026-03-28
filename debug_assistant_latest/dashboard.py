"""Simple dashboard for historical KubeLLM test runs."""

import json
from collections import Counter
from pathlib import Path
from typing import Dict, List


def _load_json(path: Path):
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_dashboard_data(runs_root: Path) -> Dict[str, object]:
    run_dirs = [path for path in runs_root.iterdir() if path.is_dir()] if runs_root.exists() else []
    complete_runs = []
    incomplete_runs = 0
    failure_counter: Counter[str] = Counter()
    total_tests = 0
    passed_tests = 0
    total_cost = 0.0

    for run_dir in sorted(run_dirs, key=lambda path: path.stat().st_mtime, reverse=True):
        aggregate = _load_json(run_dir / "aggregate.json")
        if not aggregate:
            incomplete_runs += 1
            continue

        complete_runs.append((run_dir, aggregate))
        total_tests += aggregate.get("total_tests", 0)
        passed_tests += aggregate.get("passed", 0)
        total_cost += aggregate.get("total_cost", 0.0)
        failure_counter.update(aggregate.get("failed_tests", []))
        failure_counter.update(aggregate.get("error_tests", []))

    recent_runs: List[Dict[str, object]] = []
    for run_dir, aggregate in complete_runs[:5]:
        recent_runs.append(
            {
                "run_id": aggregate.get("run_id", run_dir.name),
                "path": str(run_dir),
                "tests": aggregate.get("total_tests", 0),
                "passed": aggregate.get("passed", 0),
                "failed": aggregate.get("failed", 0),
                "errors": aggregate.get("errors", 0),
                "total_cost": aggregate.get("total_cost", 0.0),
            }
        )

    complete_count = len(complete_runs)
    return {
        "runs_root": str(runs_root),
        "total_run_dirs": len(run_dirs),
        "complete_runs": complete_count,
        "incomplete_runs": incomplete_runs,
        "total_tests": total_tests,
        "pass_rate": round((passed_tests / total_tests) * 100, 1) if total_tests else 0.0,
        "average_cost_per_run": round(total_cost / complete_count, 4) if complete_count else 0.0,
        "most_failing_tests": failure_counter.most_common(5),
        "recent_runs": recent_runs,
    }


def print_dashboard(data: Dict[str, object]) -> None:
    print("KubeLLM Dashboard")
    print("=" * 80)
    print(f"Runs root: {data['runs_root']}")
    print(
        f"Run dirs: {data['total_run_dirs']} total | "
        f"{data['complete_runs']} complete | {data['incomplete_runs']} incomplete"
    )
    print(f"Tests observed: {data['total_tests']} | Pass rate: {data['pass_rate']}%")
    print(f"Average cost per complete run: ${data['average_cost_per_run']:.4f}")

    print("\nMost failing tests:")
    most_failing = data["most_failing_tests"]
    if most_failing:
        for test_name, count in most_failing:
            print(f"  - {test_name}: {count}")
    else:
        print("  - none")

    print("\nRecent complete runs:")
    recent_runs = data["recent_runs"]
    if recent_runs:
        for run in recent_runs:
            print(
                f"  - {run['run_id']}: {run['passed']}/{run['tests']} passed, "
                f"{run['failed']} failed, {run['errors']} errors, cost ${run['total_cost']:.4f}"
            )
    else:
        print("  - none")
