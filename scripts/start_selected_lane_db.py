#!/usr/bin/env python3
"""Start only the database named by an explicitly selected private lane."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"Could not run {Path(argv[0]).name}: {type(exc).__name__}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lab-config", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(REPO))
    from debug_assistant_latest.lab_context import load_lane_config

    try:
        lane = load_lane_config(args.lab_config)
        inspect = run(["docker", "inspect", lane["pgvector_container"], "--format", "{{json .}}"])
        if inspect.returncode:
            raise RuntimeError("Selected lane database container is unavailable.")
        container = json.loads(inspect.stdout)
        container_id = str(container.get("Id", ""))
        labels = (container.get("Config") or {}).get("Labels") or {}
        if labels.get("io.kubellm.lane") != lane["lane_id"]:
            raise RuntimeError("Selected database owner label does not match the private lane.")
        if (container.get("State") or {}).get("Running") is not True:
            start = run(["docker", "start", container_id])
            if start.returncode:
                # UI and RAG units can run ExecStartPre at the same time. If
                # they both observed a stopped DB, let the second one follow
                # the first rather than treating Docker's already-started
                # response as a service failure.
                inspect = run(["docker", "inspect", container_id, "--format", "{{json .}}"])
                if inspect.returncode:
                    raise RuntimeError("Could not start the selected lane database.")
                container = json.loads(inspect.stdout)
                labels = (container.get("Config") or {}).get("Labels") or {}
                if labels.get("io.kubellm.lane") != lane["lane_id"] or (container.get("State") or {}).get("Running") is not True:
                    raise RuntimeError("Could not start the selected lane database.")
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            ready = run(["docker", "exec", container_id, "pg_isready", "-q"])
            if ready.returncode == 0:
                return 0
            time.sleep(3)
        raise RuntimeError("Selected lane database did not become ready within 120 seconds.")
    except Exception as exc:
        print(f"lab-db-start: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
