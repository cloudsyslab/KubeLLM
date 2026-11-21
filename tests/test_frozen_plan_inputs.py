import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from data_analysis.frozen_plan_inputs import (
    load_and_validate_frozen_plans,
    stage_frozen_plans,
)


def _write_source(root: Path, source_root: str, *, prompt_tail: str = "") -> str:
    case_dir = root / "case-a"
    case_dir.mkdir(parents=True)
    prompt = f"Incident and file evidence: {source_root}/repo/case{prompt_tail}"
    response = f"Suggested command targets {source_root}/repo/case"
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
    response_hash = hashlib.sha256(response.encode()).hexdigest()
    (case_dir / "plan_001.txt").write_text(response, encoding="utf-8")
    metadata = {
        "schema_version": 1,
        "test_name": "case-a",
        "api_model": "gpt-5-mini",
        "prompt": prompt,
        "prompt_sha256": prompt_hash,
        "response": response,
        "response_sha256": response_hash,
        "source_run_id": "source-run",
        "source_run_uuid": "source-uuid",
    }
    (case_dir / "plan_001.txt.json").write_text(json.dumps(metadata), encoding="utf-8")
    return prompt


def test_frozen_plan_is_normalized_without_changing_plan_content_other_than_root():
    old_root = "/private/old-worktree"
    new_root = "/private/new-worktree"
    with TemporaryDirectory() as directory:
        temp = Path(directory)
        source = temp / "source"
        prompt = _write_source(source, old_root)
        current_prompt = prompt.replace(old_root, new_root)

        plans, manifest = load_and_validate_frozen_plans(
            source_dir=source,
            cases=["case-a"],
            replicates=1,
            source_root=old_root,
            target_root=new_root,
            current_prompts={"case-a": current_prompt},
        )
        destination = temp / "campaign" / "plans"
        stage_frozen_plans(plans, destination)

        response = (destination / "case-a/plan_001.txt").read_text()
        metadata = json.loads((destination / "case-a/plan_001.txt.json").read_text())

    assert response == f"Suggested command targets {new_root}/repo/case"
    assert metadata["prompt"] == current_prompt
    assert metadata["frozen_plan_normalization"]["response_root_replacements"] == 1
    assert metadata["frozen_plan_normalization"]["source_response_sha256"] != metadata["response_sha256"]
    assert manifest["plan_count"] == 1
    assert len(manifest["manifest_sha256"]) == 64


def test_frozen_plan_rejects_prompt_drift_and_sidecar_corruption():
    old_root = "/private/old-worktree"
    new_root = "/private/new-worktree"
    with TemporaryDirectory() as directory:
        source = Path(directory) / "source"
        _write_source(source, old_root)
        with pytest.raises(ValueError, match="differs from current task evidence"):
            load_and_validate_frozen_plans(
                source_dir=source,
                cases=["case-a"],
                replicates=1,
                source_root=old_root,
                target_root=new_root,
                current_prompts={"case-a": "unrelated prompt"},
            )

        prompt = f"Incident and file evidence: {old_root}/repo/case"
        current_prompt = prompt.replace(old_root, new_root)
        path = source / "case-a/plan_001.txt"
        path.write_text("changed response", encoding="utf-8")
        with pytest.raises(ValueError, match="response checksum mismatch"):
            load_and_validate_frozen_plans(
                source_dir=source,
                cases=["case-a"],
                replicates=1,
                source_root=old_root,
                target_root=new_root,
                current_prompts={"case-a": current_prompt},
            )


def test_frozen_plan_staging_requires_exact_existing_bytes_on_resume():
    old_root = "/private/old-worktree"
    new_root = "/private/new-worktree"
    with TemporaryDirectory() as directory:
        temp = Path(directory)
        source = temp / "source"
        prompt = _write_source(source, old_root)
        plans, _ = load_and_validate_frozen_plans(
            source_dir=source,
            cases=["case-a"],
            replicates=1,
            source_root=old_root,
            target_root=new_root,
            current_prompts={"case-a": prompt.replace(old_root, new_root)},
        )
        destination = temp / "campaign" / "plans"
        stage_frozen_plans(plans, destination)
        stage_frozen_plans(plans, destination, require_existing=True)

        (destination / "case-a/plan_001.txt").write_text("unexpected", encoding="utf-8")
        with pytest.raises(ValueError, match="differs from validated source"):
            stage_frozen_plans(plans, destination, require_existing=True)
