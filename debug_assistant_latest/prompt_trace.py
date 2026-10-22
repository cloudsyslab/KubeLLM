"""Private, opt-in prompt traces for paired benchmark runs."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Optional


def _write_once(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def write_prompt_trace(runtime_context: Optional[dict[str, Any]], phase: str, prompt: str) -> None:
    if not runtime_context or not runtime_context.get("capture_prompts") or not runtime_context.get("log_dir"):
        return
    log_dir = Path(runtime_context["log_dir"])
    prompt_path = log_dir / f"{phase}_prompt.txt"
    metadata_path = log_dir / f"{phase}_prompt.meta.json"
    digest = hashlib.sha256(prompt.encode("utf-8", errors="replace")).hexdigest()
    _write_once(prompt_path, prompt)
    metadata = {
        "schema_version": 1,
        "phase": phase,
        "sha256": digest,
        "character_count": len(prompt),
        "byte_count": len(prompt.encode("utf-8", errors="replace")),
    }
    try:
        _write_once(metadata_path, json.dumps(metadata, indent=2) + "\n")
    except Exception:
        prompt_path.unlink(missing_ok=True)
        raise
