"""Reviewed, path-scoped export of sanitized local campaign results."""

from __future__ import annotations

import hashlib
import json
import os
import re
import runpy
import secrets
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import jobs
from .config import JOBS_DIR, REPO
from .results import _read_json, _safe_model


ARCHIVER = REPO / "scripts" / "archive_exploratory_run.py"
PREVIEW_TTL = timedelta(minutes=30)
SAFE_BRANCH = re.compile(r"^[A-Za-z0-9._/-]{1,160}$")
PROTECTED_BRANCHES = frozenset({"main", "master"})
_ARCHIVE_RUN = None


def _private_write(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    temporary = path.with_suffix(path.suffix + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=True, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    os.chmod(path, 0o600)


def _git(args: list[str], *, timeout: int = 15, check: bool = True) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        result = subprocess.run(
            ["git", *args], cwd=REPO, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            encoding="utf-8", errors="replace", timeout=timeout, env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Git could not verify the publication target.") from exc
    if check and result.returncode:
        raise RuntimeError("Git could not verify the publication target.")
    return result


def _remote_default_branch(remote: str) -> str | None:
    ref = _git(["symbolic-ref", "--quiet", "--short", f"refs/remotes/{remote}/HEAD"], check=False).stdout.strip()
    return ref.split("/", 1)[1] if ref.startswith(f"{remote}/") else None


def _publication_target() -> dict:
    branch = _git(["branch", "--show-current"]).stdout.strip()
    upstream = _git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"]).stdout.strip()
    head = _git(["rev-parse", "HEAD"]).stdout.strip()
    if not SAFE_BRANCH.fullmatch(branch) or not SAFE_BRANCH.fullmatch(upstream):
        raise RuntimeError("Check out a branch with a configured upstream before publishing results.")
    remote, _, upstream_branch = upstream.partition("/")
    if not upstream_branch or remote not in _git(["remote"]).stdout.split():
        raise RuntimeError("The current branch must track a branch on a configured remote before publishing results.")
    # Results never go straight to the default branch: publish on a results
    # branch and integrate it through a pull request.
    protected = PROTECTED_BRANCHES | {name for name in (_remote_default_branch(remote),) if name}
    if branch in protected or upstream_branch in protected:
        raise RuntimeError("Publishing never pushes to the default branch. Check out a results branch with its own upstream, then publish and open a pull request.")
    ahead = _git(["rev-list", "--count", f"{upstream}..HEAD"]).stdout.strip()
    if ahead != "0":
        raise RuntimeError("The current branch has unpublished commits. Push or integrate them before publishing results.")
    return {"branch": branch, "upstream": upstream, "remote": remote, "upstream_branch": upstream_branch, "head": head}


def _ensure_paths_clean(paths: list[str]) -> None:
    if not paths:
        raise ValueError("No publication files were prepared.")
    diff = _git(["diff", "--quiet", "HEAD", "--", *paths], check=False)
    status = _git(["status", "--porcelain", "--untracked-files=all", "--", *paths], check=False)
    if diff.returncode != 0 or status.stdout.strip():
        raise RuntimeError("A publication path has local changes. Resolve them before publishing results.")


def _campaign(campaign_job_id: str) -> tuple[dict, dict]:
    job = jobs.get_job(campaign_job_id)
    internal = jobs.worker_config(campaign_job_id)
    if not job or not internal or internal["kind"] != "campaign":
        raise FileNotFoundError("Campaign not found.")
    if job["status"] not in {"completed", "stopped", "failed", "interrupted"}:
        raise ValueError("Wait for this campaign to finish before preparing an export.")
    return job, internal


def _campaign_root(campaign_job_id: str, run_root: str) -> Path:
    campaign_dir = JOBS_DIR / campaign_job_id
    source_root = Path(run_root)
    if campaign_dir.is_symlink() or source_root.is_symlink():
        raise ValueError("The campaign results directory is linked.")
    root = source_root.resolve(strict=True)
    expected = campaign_dir.resolve(strict=True)
    try:
        root.relative_to(expected)
    except ValueError as exc:
        raise ValueError("The campaign results are outside the operator results directory.") from exc
    return root


def _source_attempts(job: dict, root: Path) -> list[tuple[dict, Path]]:
    attempts_root = root / "attempts"
    if attempts_root.is_symlink() or not attempts_root.is_dir():
        return []
    found = []
    directories = sorted(
        (item for item in attempts_root.iterdir() if item.is_dir() and not item.is_symlink()),
        key=lambda item: item.name,
    )
    for record in sorted(job.get("attempts", []), key=lambda item: item.get("sequence", 0)):
        sequence = record.get("sequence")
        if type(sequence) is not int or sequence < 1:
            continue
        matches = [item for item in directories if item.name.startswith(f"{sequence:04d}-")]
        if len(matches) != 1:
            continue
        source = matches[0].resolve(strict=True)
        try:
            source.relative_to(attempts_root.resolve(strict=True))
        except ValueError:
            continue
        if (source / "run_config.json").is_file() and not (source / "run_config.json").is_symlink():
            found.append((record, source))
    return found


def _model_ids(sources: list[tuple[dict, Path]]) -> set[str]:
    models: set[str] = set()
    for _, source in sources:
        config = _read_json(source / "run_config.json") or {}
        cases = config.get("test_names", [])
        if not isinstance(cases, list):
            continue
        for case in cases:
            if not isinstance(case, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,100}", case):
                continue
            effective = _read_json(source / case / "config_effective.json") or {}
            for role in ("api-agent", "debug-agent", "verification-agent"):
                settings = effective.get(role)
                model = _safe_model(settings.get("model")) if isinstance(settings, dict) else None
                if model:
                    models.add(model)
    return models


def _archive_run(source: Path, destination: Path, models: set[str]) -> None:
    global _ARCHIVE_RUN
    if _ARCHIVE_RUN is None:
        module = runpy.run_path(str(ARCHIVER))
        _ARCHIVE_RUN = module["archive_run"]
    _ARCHIVE_RUN(source, destination, models)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(text, encoding="utf-8")
    os.chmod(path, 0o600)


def _readiness_marker(job: dict) -> str:
    status = job.get("status", "incomplete").upper()
    return status if re.fullmatch(r"[A-Z_]{1,24}", status) else "INCOMPLETE"


def _prepare_preview(campaign_job_id: str) -> dict:
    job, internal = _campaign(campaign_job_id)
    root = _campaign_root(campaign_job_id, internal["run_root"])
    sources = _source_attempts(job, root)
    if not sources:
        raise ValueError("No runner attempts with structured configurations are available to export.")

    campaign_dir = (JOBS_DIR / campaign_job_id).resolve(strict=True)
    preview_root = campaign_dir / "publish-preview"
    if preview_root.is_symlink():
        raise ValueError("The private publication preview path is invalid.")
    if preview_root.exists():
        shutil.rmtree(preview_root)
    preview_root.mkdir(mode=0o700)
    os.chmod(preview_root, 0o700)

    started_at = job.get("started_at") or job.get("created_at") or datetime.now(timezone.utc).isoformat()
    try:
        date_part = datetime.fromisoformat(started_at.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        date_part = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    pack_name = f"operator-campaign-{date_part}-{campaign_job_id[:8]}"
    pack_root = preview_root / "pack"
    pack_root.mkdir(mode=0o700)

    models = sorted(_model_ids(sources))
    exported: list[dict] = []
    for record, source in sources:
        sequence = record["sequence"]
        case = record.get("case") if isinstance(record.get("case"), str) else "case"
        technique = record.get("technique") if isinstance(record.get("technique"), str) else "technique"
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,100}", case) or technique not in {
            "allStepsAtOnce", "stepByStep", "singleAgent", "knowledgeAgentOnly"
        }:
            continue
        relative = Path(technique) / f"attempt-{sequence:04d}-{case}"
        destination = pack_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            _archive_run(source, destination, set(models))
        except (OSError, ValueError, RuntimeError) as exc:
            raise RuntimeError("The sanitized export could not be prepared.") from exc
        exported.append({"sequence": sequence, "case": case, "technique": technique})

    if not exported:
        raise ValueError("No supported attempts were available to export.")

    attempts = job.get("attempts", [])
    exported_sequences = {item["sequence"] for item in exported}
    exported_records = [item for item in attempts if item.get("sequence") in exported_sequences]
    gt_known = sum(
        type(item.get("ground_truth_passed")) is bool and item.get("ground_truth_configured") is not False
        for item in exported_records
    )
    gt_passed = sum(
        item.get("ground_truth_passed") is True and item.get("ground_truth_configured") is not False
        for item in exported_records
    )
    verifier_known = sum(type(item.get("verified")) is bool for item in exported_records)
    verifier_comparable = [
        item for item in exported_records
        if type(item.get("verified")) is bool
        and type(item.get("ground_truth_passed")) is bool
        and item.get("ground_truth_configured") is not False
    ]
    verifier_agrees = sum(item["verified"] == item["ground_truth_passed"] for item in verifier_comparable)
    observed_cases = sum(
        1 for item in attempts
        if item.get("outcome") == "recorded" and item.get("status") in {"PASS", "FAIL", "ERROR", "TIMEOUT"}
    )
    planned = job.get("total") if type(job.get("total")) is int else len(attempts)
    unstarted = max(0, planned - len(attempts))
    excluded_attempts = max(0, len(attempts) - len(exported))
    techniques = sorted({item["technique"] for item in exported})
    cases = sorted({item["case"] for item in exported})
    status = _readiness_marker(job)
    model_md = ", ".join(f"`{model}`" for model in models) if models else "Not recorded"
    case_md = ", ".join(f"`{case}`" for case in cases)
    technique_md = ", ".join(f"`{technique}`" for technique in techniques)
    readme = "\n".join([
        f"# {pack_name}",
        "",
        "Private KubeLLM operator campaign exported as an exploratory evidence pack.",
        "",
        f"- Campaign status: **{status}**.",
        f"- Structured attempts exported: **{len(exported)} of {planned} planned**.",
        f"- Case outcomes with configured Ground Truth: **{gt_passed} of {gt_known} known**; unknown outcomes remain unavailable.",
        f"- Independent Verifier results recorded: **{verifier_known}**; agreement with known Ground Truth: **{verifier_agrees} of {len(verifier_comparable)} comparable**.",
        f"- Attempts without an exportable structured configuration: **{excluded_attempts}**; planned attempts not started: **{unstarted}**.",
        f"- Cases: {case_md}.",
        f"- Techniques: {technique_md}.",
        f"- Reviewed model identifiers: {model_md}.",
        "",
        "Each attempt is stored under its technique as a sanitized structured projection. This exploratory pack is excluded from canonical analysis by the `run_config.archived.json` marker.",
        "",
        "Raw logs, progress traces, prompts, generated commands, free-form results, endpoints, credentials, and private lane details were excluded by `scripts/archive_exploratory_run.py`.",
        "",
    ])
    _write_text(pack_root / "README.md", readme)

    explorer_index = REPO / "data" / "exploratory" / "README.md"
    data_index = REPO / "data" / "README.md"
    if explorer_index.is_symlink() or data_index.is_symlink():
        raise RuntimeError("A result index is linked; resolve it before publishing.")
    explorer_text = explorer_index.read_text(encoding="utf-8")
    marker = "\n\nNew sanitized packs use `scripts/archive_exploratory_run.py`"
    if marker not in explorer_text:
        raise RuntimeError("The exploratory archive index has changed; update the publication flow before continuing.")
    row = (
        f"\n| [`{pack_name}/`]({pack_name}/) | {observed_cases} case outcomes across {len(exported)} exported attempts | "
        f"Operator campaign; {gt_known} configured Ground Truth outcome(s) known; {excluded_attempts} attempt(s) lacked exportable structure and {unstarted} planned attempt(s) were not started. |")
    new_explorer_text = explorer_text.replace(marker, row + marker, 1)
    data_text = data_index.read_text(encoding="utf-8")
    link_line = (
        f"\n\nThe [{pack_name}](exploratory/{pack_name}/README.md) operator campaign is an exploratory, "
        "sanitized evidence pack; it does not change the canonical benchmark dataset."
    )
    new_data_text = data_text.rstrip() + link_line + "\n"

    local_paths = {
        f"data/exploratory/{pack_name}/{path.relative_to(pack_root).as_posix()}": path
        for path in sorted(pack_root.rglob("*")) if path.is_file() and not path.is_symlink()
    }
    _write_text(preview_root / "index" / "exploratory-README.md", new_explorer_text)
    _write_text(preview_root / "index" / "data-README.md", new_data_text)
    local_paths["data/exploratory/README.md"] = preview_root / "index" / "exploratory-README.md"
    local_paths["data/README.md"] = preview_root / "index" / "data-README.md"
    files = []
    for destination, local_path in sorted(local_paths.items()):
        files.append({
            "path": destination,
            "preview_path": local_path.relative_to(preview_root).as_posix(),
            "sha256": _hash_file(local_path),
        })
    paths = [item["path"] for item in files]
    if any(path.startswith("data/exploratory/") and path != "data/exploratory/README.md" and not path.startswith(f"data/exploratory/{pack_name}/") for path in paths):
        raise RuntimeError("The prepared export contains an unexpected path.")
    _ensure_paths_clean(["data/exploratory/README.md", "data/README.md"])
    base_files = {
        path: _hash_file(REPO / path)
        for path in ("data/exploratory/README.md", "data/README.md")
    }
    if (REPO / "data" / "exploratory" / pack_name).exists():
        raise RuntimeError("An export folder with this campaign ID already exists.")
    target = _publication_target()

    token = secrets.token_hex(16)
    expires_at = (datetime.now(timezone.utc) + PREVIEW_TTL).isoformat()
    manifest = {
        "version": 1,
        "campaign_job_id": campaign_job_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expires_at,
        "preview_token": token,
        "preview_root": str(preview_root),
        "pack_name": pack_name,
        "target": target,
        "files": files,
        "base_files": base_files,
        "campaign_status": status,
        "attempts_recorded": len(exported),
        "attempts_planned": planned,
        "ground_truth_known": gt_known,
        "ground_truth_passed": gt_passed,
        "verifier_known": verifier_known,
        "verifier_comparable": len(verifier_comparable),
        "verifier_agrees": verifier_agrees,
        "attempts_excluded": excluded_attempts,
        "attempts_unstarted": unstarted,
        "models": models,
    }
    _private_write(campaign_dir / "publish-preview.json", manifest)
    return {
        "preview_token": token,
        "branch": target["branch"],
        "upstream": target["upstream"],
        "campaign_status": status,
        "attempts_recorded": len(exported),
        "attempts_planned": planned,
        "ground_truth_known": gt_known,
        "ground_truth_passed": gt_passed,
        "verifier_known": verifier_known,
        "verifier_comparable": len(verifier_comparable),
        "verifier_agrees": verifier_agrees,
        "attempts_excluded": excluded_attempts,
        "attempts_unstarted": unstarted,
        "models": models,
        "files": [{"path": item["path"], "sha256": item["sha256"]} for item in files],
    }


def create_publish_preview(campaign_job_id: str) -> dict:
    return _prepare_preview(campaign_job_id)


def _manifest(campaign_job_id: str) -> dict | None:
    path = JOBS_DIR / campaign_job_id / "publish-preview.json"
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) and value.get("version") == 1 else None
    except (OSError, ValueError):
        return None


def _verified_manifest(campaign_job_id: str, token: str) -> dict | None:
    manifest = _manifest(campaign_job_id)
    if not manifest or not secrets.compare_digest(manifest.get("preview_token", ""), token):
        return None
    try:
        expires = datetime.fromisoformat(manifest["expires_at"])
        if datetime.now(timezone.utc) > expires:
            return None
        preview_root = Path(manifest["preview_root"]).resolve(strict=True)
        preview_root.relative_to((JOBS_DIR / campaign_job_id).resolve(strict=True))
        target = manifest["target"]
        current = _publication_target()
        if current != target:
            return None
        if (REPO / "data" / "exploratory" / manifest["pack_name"]).exists():
            return None
        for item in manifest["files"]:
            path = item["path"]
            if not (path == "data/README.md" or path == "data/exploratory/README.md" or path.startswith(f"data/exploratory/{manifest['pack_name']}/")):
                return None
            candidate = preview_root / item["preview_path"]
            if candidate.is_symlink():
                return None
            local = candidate.resolve(strict=True)
            local.relative_to(preview_root)
            if local.is_symlink() or not local.is_file() or _hash_file(local) != item["sha256"]:
                return None
        for path, expected_hash in manifest["base_files"].items():
            base = REPO / path
            if base.is_symlink() or not base.is_file() or _hash_file(base) != expected_hash:
                return None
        _ensure_paths_clean(["data/exploratory/README.md", "data/README.md"])
        return manifest
    except (OSError, KeyError, TypeError, ValueError, RuntimeError, subprocess.TimeoutExpired):
        return None


def validate_publish_token(campaign_job_id: str, token: str) -> bool:
    return _verified_manifest(campaign_job_id, token) is not None


def _log_git(job_id: str, args: list[str], *, timeout: int = 60) -> subprocess.CompletedProcess:
    directory = JOBS_DIR / job_id
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(directory, 0o700)
    log_path = directory / "publish.log"
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    with log_path.open("ab") as log:
        try:
            result = subprocess.run(
                ["git", *args], cwd=REPO, stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT, timeout=timeout, check=False, env=env,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError("The Git publication step did not finish.") from exc
    return result


def _finish_publish(job_id: str, status: str, label: str) -> None:
    jobs.update_job(job_id, status=status, finished_at=jobs.now(), current_label=label)


def publish_campaign(publish_job_id: str, campaign_job_id: str, token: str) -> None:
    publish_job = jobs.worker_config(publish_job_id)
    if not publish_job or publish_job["kind"] != "publish":
        return
    jobs.update_job(publish_job_id, status="running", started_at=jobs.now(), current_label="Verifying reviewed files and Git target.")
    manifest = _verified_manifest(campaign_job_id, token)
    if not manifest:
        _finish_publish(publish_job_id, "failed", "The preview expired or files changed; review a fresh preview.")
        return

    paths = [item["path"] for item in manifest["files"]]
    pathspecs = [f":(literal){path}" for path in paths]
    preview_root = Path(manifest["preview_root"]).resolve(strict=True)
    existing_indexes = {
        "data/exploratory/README.md": (REPO / "data" / "exploratory" / "README.md").read_bytes(),
        "data/README.md": (REPO / "data" / "README.md").read_bytes(),
    }
    for path, expected_hash in manifest["base_files"].items():
        target = REPO / path
        if target.is_symlink() or not target.is_file() or _hash_file(target) != expected_hash:
            _finish_publish(publish_job_id, "failed", "A result index changed after review; prepare a fresh preview.")
            return
    created_pack = REPO / "data" / "exploratory" / manifest["pack_name"]
    created_pack.mkdir(parents=False, exist_ok=False)
    copied = []
    committed = False
    initial_head = manifest["target"]["head"]
    try:
        for item in manifest["files"]:
            candidate = preview_root / item["preview_path"]
            if candidate.is_symlink():
                raise RuntimeError("A reviewed file changed before publication.")
            source = candidate.resolve(strict=True)
            source.relative_to(preview_root)
            if _hash_file(source) != item["sha256"]:
                raise RuntimeError("A reviewed file changed before publication.")
            destination = REPO / item["path"]
            if destination.exists() and item["path"] not in existing_indexes:
                raise RuntimeError("An export destination already exists.")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            copied.append(destination)
        jobs.update_job(publish_job_id, current_label="Adding only the reviewed export paths.")
        added = _log_git(publish_job_id, ["add", "--", *pathspecs])
        if added.returncode:
            raise RuntimeError("Git could not stage the reviewed export files.")
        current_head = _git(["rev-parse", "HEAD"]).stdout.strip()
        if current_head != initial_head:
            raise RuntimeError("The current branch changed after preview; no commit was created.")
        message_file = JOBS_DIR / publish_job_id / "commit-message.txt"
        message_file.write_text(f"Archive KubeLLM operator campaign {campaign_job_id[:8]}\n", encoding="utf-8")
        os.chmod(message_file, 0o600)
        jobs.update_job(publish_job_id, current_label="Creating a commit containing the reviewed result files.")
        commit = _log_git(publish_job_id, ["commit", "--only", "--file", str(message_file), "--", *pathspecs])
        if commit.returncode:
            raise RuntimeError("Git could not create the export commit.")
        committed = True
        jobs.update_job(publish_job_id, current_label="Pushing the export commit to the configured upstream.")
        # An explicit refspec pushes only this commit to the reviewed upstream
        # branch, whatever the server's push.default says.
        reviewed = manifest["target"]
        pushed = _log_git(publish_job_id, ["push", reviewed["remote"], f"HEAD:refs/heads/{reviewed['upstream_branch']}"], timeout=180)
        if pushed.returncode:
            _finish_publish(publish_job_id, "failed", "The export commit is local, but pushing it failed. Check server Git access and push the current branch.")
            return
        _finish_publish(publish_job_id, "completed", "Sanitized results were committed and pushed.")
    except BaseException:
        if not committed:
            try:
                current_head = _git(["rev-parse", "HEAD"], check=False).stdout.strip()
            except BaseException:
                current_head = ""
            if current_head == initial_head:
                _git(["reset", "--", *pathspecs], check=False)
                for path, content in existing_indexes.items():
                    target = REPO / path
                    target.write_bytes(content)
                if created_pack.is_dir() and not created_pack.is_symlink():
                    shutil.rmtree(created_pack)
        if committed:
            label = "The export commit exists locally, but the push outcome could not be confirmed. Check the upstream before retrying."
        elif current_head and current_head != initial_head:
            label = "The current branch changed during publication. Inspect it before retrying."
        else:
            label = "The export could not be committed. No unrelated paths were staged by the operator app."
        _finish_publish(publish_job_id, "failed", label)
