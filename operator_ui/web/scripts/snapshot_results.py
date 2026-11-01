#!/usr/bin/env python3
"""Write the fixture snapshot that the web app reads in demo mode.

The snapshot is the operator API's own projection of recorded runs: every
canonical and exploratory export under data/, passed through
operator_ui.results.public_run plus its per-case rows. Local operator runs and
filesystem paths are excluded. Rerun after data/ changes:

    python3 operator_ui/web/scripts/snapshot_results.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

WEB = Path(__file__).resolve().parents[1]
REPO = WEB.parents[1]
OUTPUT = WEB / "src" / "data" / "runs.snapshot.json"

sys.path.insert(0, str(REPO))
from operator_ui.results import all_runs, public_run  # noqa: E402


def main() -> None:
    runs = [
        public_run(run) | {"case_rows": run["case_rows"]}
        for run in all_runs(force_refresh=True)
        if run["source"] in {"canonical", "exploratory"}
    ]
    snapshot = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "producer": "operator_ui.results.all_runs via operator_ui/web/scripts/snapshot_results.py",
        "runs": runs,
    }
    text = json.dumps(snapshot, separators=(",", ":"), sort_keys=True)
    if "/Users/" in text or "/home/" in text:
        raise SystemExit("refusing to write a snapshot that contains a filesystem path")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(text + "\n", encoding="utf-8")
    print(f"wrote {len(runs)} runs to {OUTPUT.relative_to(REPO)} ({OUTPUT.stat().st_size // 1024} KiB)")


if __name__ == "__main__":
    main()
