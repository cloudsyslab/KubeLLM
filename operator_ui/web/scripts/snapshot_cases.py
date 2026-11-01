#!/usr/bin/env python3
"""Write operator-facing scenario explanations for the web app's hover cards.

For every troubleshooting case this collects, verbatim:
- the symptom the agents receive (config_step.json knowledge-prompt problem-desc);
- the Ground Truth description and its checks (what must be true to pass);
- from readme.txt when present: the title, broken setup, and expected fix.
Some readmes are a single fix sentence; that text becomes the fix.

The output in src/data/cases.json is for human operators only. Agent-facing
case prompts stay symptom-only and never read it. Rerun after a case changes:

    python3 operator_ui/web/scripts/snapshot_cases.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1]
REPO = WEB.parents[1]
CASES = REPO / "debug_assistant_latest" / "troubleshooting"
OUTPUT = WEB / "src" / "data" / "cases.json"

SECTIONS = {
    "case setup": "setup",
    "replication steps": "replication",
    "solution steps": "solution",
    "solution state": "solved",
}


def items(lines: list[str]) -> list[str]:
    """Join wrapped lines into bullet or numbered items."""
    out: list[str] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        match = re.match(r"^(?:[-*•]|\d+[.)])\s+(.*)$", line)
        if match or not out:
            out.append((match.group(1) if match else line).strip())
        else:
            out[-1] = f"{out[-1]} {line}"
    return out


def parse(text: str) -> dict:
    title = ""
    current: str | None = None
    buckets: dict[str, list[str]] = {key: [] for key in SECTIONS.values()}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("CASE:"):
            title = stripped[5:].strip()
            continue
        heading = stripped.rstrip(":").lower()
        if stripped.endswith(":") and heading in SECTIONS:
            current = SECTIONS[heading]
            continue
        if current:
            buckets[current].append(line)
    return {"title": title} | {key: items(lines) for key, lines in buckets.items()}


def from_config(path: Path) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    truth = config.get("ground-truth") or {}
    checks = [check.get("description") for check in truth.get("checks", []) if isinstance(check, dict) and check.get("description")]
    return {
        "symptom": (config.get("knowledge-prompt") or {}).get("problem-desc") or "",
        "ground_truth": truth.get("description") or "",
        "checks": checks,
    }


def main() -> None:
    cases = {}
    for config in sorted(CASES.glob("*/config_step.json")):
        name = config.parent.name
        case = {"title": "", "setup": [], "solution": [], "solved": []} | from_config(config)
        readme = config.parent / "readme.txt"
        if readme.is_file():
            text = readme.read_text(encoding="utf-8", errors="replace").strip()
            parsed = parse(text)
            if parsed["title"]:
                case |= {key: parsed[key] for key in ("title", "setup", "solution", "solved")}
            elif text:
                case["solution"] = [" ".join(text.split())]
        cases[name] = case
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    source = "debug_assistant_latest/troubleshooting/*/{config_step.json,readme.txt}"
    OUTPUT.write_text(json.dumps({"source": source, "cases": cases}, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    without_setup = [name for name, case in cases.items() if not case["setup"]]
    print(f"wrote {len(cases)} cases to {OUTPUT.relative_to(REPO)}; without a documented broken setup: {len(without_setup)}")


if __name__ == "__main__":
    main()
