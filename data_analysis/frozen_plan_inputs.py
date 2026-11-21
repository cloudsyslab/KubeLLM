"""Validate, normalize, and stage frozen KnowledgeAgent plans for paired replay."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
from typing import Any


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_current_knowledge_prompts(cases: list[str], repo_root: Path) -> dict[str, str]:
    """Build current prompts offline, without initializing API/RAG services."""
    debug_dir = str(repo_root / "debug_assistant_latest")
    if debug_dir not in sys.path:
        sys.path.insert(0, debug_dir)
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from api_agents import AgentAPI
    from config_merge import load_config_with_overrides
    from test_discovery import get_config_path

    prompts: dict[str, str] = {}
    for case in cases:
        config = load_config_with_overrides(get_config_path(case), {})
        agent = AgentAPI("api-agent", config)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            agent.preparePrompt()
        prompts[case] = agent.prompt
    return prompts


def load_and_validate_frozen_plans(
    *,
    source_dir: Path,
    cases: list[str],
    replicates: int,
    source_root: str,
    target_root: str,
    current_prompts: dict[str, str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source_dir = source_dir.expanduser().resolve()
    source_root = str(Path(source_root).expanduser().resolve())
    target_root = str(Path(target_root).expanduser().resolve())
    if not source_dir.is_dir():
        raise ValueError(f"Frozen plan source directory is missing: {source_dir}")
    if replicates < 1:
        raise ValueError("Frozen plan replicate count must be positive")
    if set(current_prompts) != set(cases):
        raise ValueError("Current prompt map does not match the requested cases")

    expected: dict[str, tuple[str, int, Path]] = {}
    for case in cases:
        for replicate in range(1, replicates + 1):
            relative = Path(case) / f"plan_{replicate:03d}.txt"
            expected[relative.as_posix()] = (case, replicate, source_dir / relative)
    actual_txt = {path.relative_to(source_dir).as_posix() for path in source_dir.rglob("*.txt")}
    actual_meta = {
        path.relative_to(source_dir).as_posix()
        for path in source_dir.rglob("*.txt.json")
    }
    expected_meta = {name + ".json" for name in expected}
    if actual_txt != set(expected) or actual_meta != expected_meta:
        raise ValueError(
            "Frozen plan source inventory differs from the requested schedule "
            f"(expected {len(expected)} plans and metadata files; found {len(actual_txt)} and {len(actual_meta)})"
        )

    plans: list[dict[str, Any]] = []
    entries: list[dict[str, Any]] = []
    for relative, (case, replicate, response_path) in sorted(expected.items()):
        metadata_path = response_path.with_suffix(response_path.suffix + ".json")
        if response_path.is_symlink() or metadata_path.is_symlink():
            raise ValueError(f"Frozen plan artifacts must be regular files: {relative}")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        response = response_path.read_text(encoding="utf-8")
        prompt = metadata.get("prompt")
        if metadata.get("schema_version") != 1 or metadata.get("test_name") != case:
            raise ValueError(f"Frozen plan metadata schema or case mismatch: {relative}")
        if not isinstance(prompt, str) or not isinstance(response, str):
            raise ValueError(f"Frozen plan prompt/response is missing: {relative}")
        original_prompt_sha256 = sha256_text(prompt)
        original_response_sha256 = sha256_text(response)
        if metadata.get("prompt_sha256") != original_prompt_sha256:
            raise ValueError(f"Frozen plan prompt checksum mismatch: {relative}")
        if metadata.get("response_sha256") != original_response_sha256:
            raise ValueError(f"Frozen plan response checksum mismatch: {relative}")
        if metadata.get("response") != response:
            raise ValueError(f"Frozen plan response body differs from its sidecar: {relative}")

        normalized_prompt = prompt.replace(source_root, target_root)
        expected_prompt = current_prompts[case]
        if normalized_prompt != expected_prompt:
            raise ValueError(f"Frozen plan prompt differs from current task evidence after path normalization: {relative}")
        prompt_replacements = prompt.count(source_root)
        if source_root != target_root and prompt_replacements == 0:
            raise ValueError(f"Expected source worktree root was absent from frozen prompt: {relative}")
        normalized_response = response.replace(source_root, target_root)
        if source_root in normalized_response:
            raise ValueError(f"Frozen response retains its source worktree root: {relative}")
        response_replacements = response.count(source_root)

        adapted = dict(metadata)
        adapted["prompt"] = normalized_prompt
        adapted["prompt_sha256"] = sha256_text(normalized_prompt)
        adapted["response"] = normalized_response
        adapted["response_sha256"] = sha256_text(normalized_response)
        adapted["frozen_plan_normalization"] = {
            "source_root": source_root,
            "target_root": target_root,
            "prompt_root_replacements": prompt_replacements,
            "response_root_replacements": response_replacements,
            "source_prompt_sha256": original_prompt_sha256,
            "source_response_sha256": original_response_sha256,
            "source_text_sha256": sha256_file(response_path),
            "source_metadata_sha256": sha256_file(metadata_path),
        }
        output_metadata = json.dumps(adapted, indent=2, sort_keys=True) + "\n"
        relative_meta = relative + ".json"
        plan = {
            "case": case,
            "replicate": replicate,
            "relative_path": relative,
            "response": normalized_response,
            "metadata_text": output_metadata,
            "metadata": adapted,
        }
        plans.append(plan)
        entries.append(
            {
                "pair_id": f"{case}__plan_{replicate:03d}",
                "source_text_sha256": adapted["frozen_plan_normalization"]["source_text_sha256"],
                "source_metadata_sha256": adapted["frozen_plan_normalization"]["source_metadata_sha256"],
                "source_prompt_sha256": original_prompt_sha256,
                "source_response_sha256": original_response_sha256,
                "normalized_prompt_sha256": adapted["prompt_sha256"],
                "normalized_response_sha256": adapted["response_sha256"],
                "prompt_root_replacements": prompt_replacements,
                "response_root_replacements": response_replacements,
            }
        )

    manifest_basis = {
        "source_dir": str(source_dir),
        "source_root": source_root,
        "target_root": target_root,
        "plan_count": len(entries),
        "entries": entries,
    }
    encoded_basis = json.dumps(manifest_basis, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest = {
        **manifest_basis,
        "manifest_sha256": hashlib.sha256(encoded_basis).hexdigest(),
    }
    return plans, manifest


def stage_frozen_plans(
    plans: list[dict[str, Any]],
    destination_dir: Path,
    *,
    require_existing: bool = False,
) -> None:
    destination_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    expected: set[str] = set()
    for plan in plans:
        relative = Path(plan["relative_path"])
        rel = relative.as_posix()
        rel_meta = rel + ".json"
        expected.update((rel, rel_meta))
        response_path = destination_dir / relative
        metadata_path = destination_dir / rel_meta
        response_bytes = plan["response"].encode("utf-8")
        metadata_bytes = plan["metadata_text"].encode("utf-8")
        for path, payload in ((response_path, response_bytes), (metadata_path, metadata_bytes)):
            if path.exists():
                if path.is_symlink() or not path.is_file() or path.read_bytes() != payload:
                    raise ValueError(f"Staged frozen plan differs from validated source: {path}")
            elif require_existing:
                raise ValueError(f"Staged frozen plan is missing during resume: {path}")
            else:
                path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                path.write_bytes(payload)
                os.chmod(path, 0o600)
        os.chmod(response_path.parent, 0o700)

    actual = {
        path.relative_to(destination_dir).as_posix()
        for path in destination_dir.rglob("*")
        if path.is_file()
    }
    if actual != expected:
        raise ValueError("Staged frozen plan directory contains missing or unexpected files")
    os.chmod(destination_dir, 0o700)
