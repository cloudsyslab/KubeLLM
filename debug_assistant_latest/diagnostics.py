#!/usr/bin/env python3
"""Latest-run discovery, dashboard, and run directory diagnosis."""

import json
from pathlib import Path
from typing import List, Optional

from dashboard import build_dashboard_data, print_dashboard
from result_interpreter import interpret_run

from debug_assistant_latest.executor import REPO_ROOT, _display_path


def _runs_root() -> Path:
    return REPO_ROOT / ".local" / "test_runs"


def _run_dirs() -> List[Path]:
    root = _runs_root()
    if not root.exists():
        return []
    return sorted(
        [path for path in root.iterdir() if path.is_dir()],
        key=lambda path: (path.stat().st_mtime, path.name),
        reverse=True,
    )


def _is_diagnosable_run_dir(run_dir: Path) -> bool:
    if (run_dir / "aggregate.json").exists():
        return True
    if any(run_dir.rglob("summary.json")):
        return True
    return any(run_dir.rglob("stderr.log")) or any(run_dir.rglob("stdout.log"))


def get_latest_run_dir(*, diagnosable_only: bool = False) -> Optional[Path]:
    for run_dir in _run_dirs():
        if not diagnosable_only or _is_diagnosable_run_dir(run_dir):
            return run_dir
    return None


def cmd_latest_run(args):
    run_dir = get_latest_run_dir()
    if run_dir is None:
        print("No run directories found")
        return 1
    print(_display_path(run_dir))
    return 0


def cmd_diagnose(args, run_dir: Path):
    try:
        diagnosis = interpret_run(run_dir)
    except Exception as exc:
        print(f"Could not diagnose run {run_dir}: {exc}")
        return 1
    print(json.dumps(diagnosis.to_dict(), indent=2))
    return 0


def cmd_diagnose_last(args):
    run_dir = get_latest_run_dir(diagnosable_only=True)
    if run_dir is None:
        print("No diagnosable run directories found")
        return 1
    return cmd_diagnose(args, run_dir)


def cmd_dashboard(args):
    data = build_dashboard_data(_runs_root())
    print_dashboard(data)
    return 0
