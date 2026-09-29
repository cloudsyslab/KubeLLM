#!/usr/bin/env python3
"""Publish allowlisted run evidence, never raw logs or execution payloads.

The .archived config name deliberately excludes exports from default analysis.
Model identifiers must be explicitly reviewed and supplied by the operator.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "inspect_run", REPO / ".agents/skills/audit-kubellm/scripts/inspect_run.py"
)
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)
TECHNIQUES = {"allStepsAtOnce", "stepByStep", "singleAgent", "knowledgeAgentOnly"}


def archive_run(source: Path, destination: Path, model_ids: set[str]) -> None:
    source = source.resolve(strict=True)

    def read(relative: Path | str) -> dict | None:
        path = source / relative
        if not path.exists():
            return None
        if path.is_symlink() or path.resolve() != path or not path.is_file():
            raise ValueError("Refusing linked or non-file input")
        if path.stat().st_size > reader.MAX_JSON_BYTES:
            raise ValueError("Input exceeds structured artifact size limit")
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("Expected a JSON object")
        return value

    config = read("run_config.json")
    if not config or config.get("technique") not in TECHNIQUES:
        raise ValueError("Missing run config or unsupported technique")
    cases = config.get("test_names")
    if not isinstance(cases, list) or not cases or any(
        not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,100}", name)
        for name in cases
    ) or len(set(cases)) != len(cases):
        raise ValueError("Invalid case names")
    run_id = config.get("run_id")
    if not isinstance(run_id, str) or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d-\d\d-\d\d", run_id):
        raise ValueError("Unsupported run identifier")
    safe_config = {"run_id": run_id, "technique": config["technique"], "test_names": cases}
    if type(config.get("jobs")) is int:
        safe_config["jobs"] = config["jobs"]
    if type(config.get("teardown_after_run")) is bool:
        safe_config["teardown_after_run"] = config["teardown_after_run"]
    outputs = {Path("run_config.archived.json"): safe_config}
    provenance = read("provenance.json")
    if provenance is not None:
        safe_provenance = {"run_id": run_id}
        commit = provenance.get("git_commit")
        if isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{40}", commit):
            safe_provenance["git_commit"] = commit
        if type(provenance.get("git_dirty")) is bool:
            safe_provenance["git_dirty"] = provenance["git_dirty"]
        outputs[Path("provenance.archived.json")] = safe_provenance
    aggregate = read("aggregate.json")
    if aggregate is not None:
        outputs[Path("aggregate.json")] = reader._aggregate(aggregate)
    run_control = read("run_control.json")
    if run_control is not None:
        outputs[Path("run_control.json")] = reader._run_control(run_control)
    for case in cases:
        for name, project in (("summary.json", reader._summary),
                              ("knowledge_execution.json", reader._knowledge_execution)):
            relative = Path(case) / name
            value = read(relative)
            if value is not None:
                outputs[relative] = project(value)
        effective = read(Path(case) / "config_effective.json")
        if effective is not None:
            safe_effective = {}
            for role in ("api-agent", "debug-agent", "verification-agent"):
                details = effective.get(role)
                if not isinstance(details, dict):
                    continue
                safe_role = {}
                if "model" in details:
                    if details["model"] not in model_ids:
                        raise ValueError("Unreviewed model identifier; inspect privately first")
                    safe_role["model"] = details["model"]
                if type(details.get("temperature")) in (int, float):
                    safe_role["temperature"] = details["temperature"]
                safe_effective[role] = safe_role
            outputs[Path(case) / "config_effective.json"] = safe_effective
    # Prepare everything before creating a new destination; never overwrite evidence.
    encoded = {path: json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
               for path, value in outputs.items()}
    destination.mkdir(parents=True, exist_ok=False)
    for relative, content in encoded.items():
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--model-id", action="append", default=[])
    args = parser.parse_args()
    archive_run(args.source, args.destination, set(args.model_id))
