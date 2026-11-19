#!/usr/bin/env python3
"""Plan and remove Minh-owned rebuildable artifacts and unused private images.

This tool never lists, prunes, or removes images from the shared host Docker
daemon. Docker image operations run only inside the verified private Minikube
node container. Tagged case images require checked-in build configs and
Dockerfiles; base images require registry digests. Both have no container or pod
references before removal. Storage reports are read-only and never auto-delete.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
from datetime import datetime, timezone
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
REBUILDABLE_RELATIVE_PATHS = (
    ".cache/fontconfig",
    ".cache/ms-playwright",
    ".cache/pip",
    ".codex/packages/app-server-daemon/releases/0.169.1-x86_64-unknown-linux-musl",
    ".codex/packages/standalone/releases/0.163.0-x86_64-unknown-linux-musl",
    ".minikube/cache/images/amd64",
    ".minikube/cache/kic",
    ".minikube/cache/linux/amd64",
    ".minikube/cache/preloaded-tarball",
    ".npm/_cacache",
    "KubeLLM/.local/operator_ui/worktrees/source-9740024/operator_ui/web/node_modules",
    "KubeLLM/.local/prediction_pilot/venv",
    "KubeLLM/design-exploration/kubellm-operator/room/node_modules",
)
PRIVATE_REBUILDABLE_BASE_IMAGE_TAGS = (
    "python:3",
    "python:3.11",
    "python:3.11-slim",
    "python:3.12-alpine",
)
SAFE_EXTERNAL_SYMLINKS = {
    ("KubeLLM/.local/prediction_pilot/venv", "bin/python", "python3"),
    ("KubeLLM/.local/prediction_pilot/venv", "bin/python3", "/usr/bin/python3"),
    ("KubeLLM/.local/prediction_pilot/venv", "bin/python3.10", "python3"),
}
CAMPAIGN_STARTUP_FREE_BYTES = 20_000_000_000
CAMPAIGN_ATTEMPT_FREE_BYTES = 10_000_000_000
PROFILE_START_DOCKER_FREE_BYTES = 20 * 1024**3
STORAGE_WARNING_FREE_BYTES = 25 * 1024**3
REPORT_PATHS = (
    ".cache",
    ".codex/.tmp",
    ".codex/cache",
    ".codex/packages",
    ".codex/sessions",
    ".local/lib/python3.10",
    ".local/share/nodejs",
    ".local/share/uv/python",
    ".minikube/cache",
    "KubeLLM/data",
    "KubeLLM/.local/campaigns",
    "KubeLLM/.local/operator_ui/worktrees",
    "KubeLLM/.local/prediction_campaigns",
    "KubeLLM/.local/prediction_pilot",
    "KubeLLM/.local/retired-workspaces",
    "KubeLLM/.local/test_runs",
)
LANE_CONFIG = Path.home() / ".config/kubellm/lanes/minh.json"
EXPECTED_LANE = {
    "lane_id": "minh",
    "minikube_profile": "minh-lane",
    "minikube_container": "minh-lane",
    "kubeconfig_path": str(Path.home() / ".config/kubellm/lanes/minh.kubeconfig"),
}
PLAN_TTL_SECONDS = 3600
TEMP_BUILD_CONTEXT_DIR = Path("/tmp")
TEMP_BUILD_CONTEXT_MIN_AGE_SECONDS = 30 * 24 * 60 * 60
IMAGE_RESTORE_MANIFEST = (
    Path.home() / ".local/lab-ops/private-image-restore-manifest.json"
)
DEFAULT_REPORT_PATH = (
    Path.home() / ".local/state/kubellm-storage/latest.json"
)


class SafetyError(RuntimeError):
    pass


def run(argv: list[str], *, timeout: int = 60) -> str:
    try:
        result = subprocess.run(
            argv, check=False, capture_output=True, text=True, timeout=timeout
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SafetyError(f"command could not be verified: {argv[0]}") from exc
    if result.returncode != 0:
        raise SafetyError(
            f"verification command failed ({argv[0]}, exit {result.returncode})"
        )
    return result.stdout.strip()


def rebuildable_path(relative: str) -> Path:
    if relative not in REBUILDABLE_RELATIVE_PATHS:
        raise SafetyError("path is outside the rebuildable allowlist")
    return Path.home() / relative


def _walk_error(exc: OSError) -> None:
    raise SafetyError("rebuildable path could not be fully inspected") from exc


def rebuildable_path_manifest(relative: str) -> dict[str, Any] | None:
    root = rebuildable_path(relative)
    try:
        root_stat = root.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise SafetyError(f"rebuildable path could not be inspected: {relative}") from exc
    if stat.S_ISLNK(root_stat.st_mode) or not stat.S_ISDIR(root_stat.st_mode):
        raise SafetyError(f"rebuildable path is not a plain directory: {relative}")
    if root.resolve(strict=True) != root:
        raise SafetyError(f"rebuildable path traverses a symlink: {relative}")
    uid = os.getuid()
    if root_stat.st_uid != uid:
        raise SafetyError(f"rebuildable path is not owned by the current user: {relative}")

    records: list[tuple[Any, ...]] = []
    allocated = 0
    file_count = 0
    for current, dirs, files in os.walk(
        root, topdown=True, followlinks=False, onerror=_walk_error
    ):
        current_path = Path(current)
        entries = [(name, True) for name in dirs] + [(name, False) for name in files]
        for name, is_dir in entries:
            item = current_path / name
            try:
                item_stat = item.lstat()
            except OSError as exc:
                raise SafetyError(
                    f"rebuildable path changed while being inspected: {relative}"
                ) from exc
            rel = item.relative_to(root).as_posix()
            link_target = None
            if stat.S_ISLNK(item_stat.st_mode):
                link_target = os.readlink(item)
                try:
                    resolved_target = item.resolve(strict=True)
                    target_stat = resolved_target.stat()
                except OSError as exc:
                    raise SafetyError(
                        f"rebuildable path contains a dangling symlink: {relative}"
                    ) from exc
                allowed_external = (
                    relative,
                    rel,
                    link_target,
                ) in SAFE_EXTERNAL_SYMLINKS
                if not resolved_target.is_relative_to(root) and not allowed_external:
                    raise SafetyError(
                        f"rebuildable path symlink escapes its target: {relative}"
                    )
                if allowed_external and not stat.S_ISREG(target_stat.st_mode):
                    raise SafetyError(
                        f"allowlisted external symlink target is not a regular file: {relative}"
                    )
                if target_stat.st_uid != uid and not allowed_external:
                    raise SafetyError(
                        f"rebuildable path symlink targets another owner's file: {relative}"
                    )
            if item_stat.st_uid != uid:
                raise SafetyError(f"rebuildable path contains another owner's file: {relative}")
            if item_stat.st_dev != root_stat.st_dev:
                raise SafetyError(f"rebuildable path crosses a filesystem boundary: {relative}")
            kind = "d" if is_dir else "f"
            records.append(
                (rel, kind, item_stat.st_ino, item_stat.st_size, item_stat.st_mtime_ns,
                 item_stat.st_mode, item_stat.st_nlink, item_stat.st_blocks, link_target)
            )
            if not is_dir:
                allocated += item_stat.st_blocks * 512
                file_count += 1
    records.sort()
    encoded = json.dumps(records, separators=(",", ":"), ensure_ascii=True).encode()
    return {
        "path": str(root),
        "relative_path": relative,
        "allocated_bytes": allocated,
        "file_count": file_count,
        "fingerprint": hashlib.sha256(encoded).hexdigest(),
    }


def assert_no_open_files(path: str) -> None:
    try:
        result = subprocess.run(
            ["lsof", "-t", "+D", path],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SafetyError("could not verify target has no open files") from exc
    if result.returncode not in (0, 1):
        raise SafetyError("lsof could not verify target use")
    if result.stdout.strip():
        raise SafetyError(f"rebuildable path has open files: {path}")


def assert_no_open_file(path: Path) -> None:
    try:
        result = subprocess.run(
            ["lsof", "-t", str(path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SafetyError("could not verify temporary file has no open handles") from exc
    if result.returncode not in (0, 1):
        raise SafetyError("lsof could not verify temporary file use")
    if result.stdout.strip():
        raise SafetyError(f"temporary build context has open handles: {path}")


def temp_build_context_manifest(
    path: Path,
    *,
    root_info: os.stat_result | None = None,
    cutoff_ns: int | None = None,
    check_open: bool = True,
) -> dict[str, Any] | None:
    """Inspect one exact stale build tar, optionally using a validated root snapshot."""
    root = TEMP_BUILD_CONTEXT_DIR
    if root_info is None:
        try:
            root_info = root.lstat()
        except OSError as exc:
            raise SafetyError("temporary directory could not be inspected") from exc
        if stat.S_ISLNK(root_info.st_mode) or not stat.S_ISDIR(root_info.st_mode):
            raise SafetyError("temporary directory is not a plain directory")
        if root.resolve(strict=True) != root:
            raise SafetyError("temporary directory traverses a symlink")

    if path.parent != root:
        raise SafetyError("temporary build context is outside the temporary directory")
    suffix = path.name[len("build."):-len(".tar")] if (
        path.name.startswith("build.") and path.name.endswith(".tar")
    ) else ""
    if not suffix.isdigit():
        return None
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise SafetyError("temporary build context changed during inspection") from exc

    uid = os.getuid()
    if info.st_uid != uid:
        return None
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise SafetyError(f"temporary build context is not a regular file: {path}")
    if info.st_dev != root_info.st_dev or info.st_nlink != 1:
        raise SafetyError(f"temporary build context has unexpected storage links: {path}")
    if cutoff_ns is None:
        cutoff_ns = time.time_ns() - TEMP_BUILD_CONTEXT_MIN_AGE_SECONDS * 1_000_000_000
    if info.st_mtime_ns > cutoff_ns:
        return None

    if check_open:
        assert_no_open_file(path)
    try:
        valid_tar = tarfile.is_tarfile(path)
    except OSError as exc:
        raise SafetyError(f"temporary build context could not be checked: {path}") from exc
    if not valid_tar:
        return None

    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        after = path.lstat()
    except OSError as exc:
        raise SafetyError(f"temporary build context could not be hashed: {path}") from exc
    identity_before = (
        info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_nlink,
        info.st_size, info.st_mtime_ns,
    )
    identity_after = (
        after.st_dev, after.st_ino, after.st_mode, after.st_uid, after.st_nlink,
        after.st_size, after.st_mtime_ns,
    )
    if identity_before != identity_after:
        raise SafetyError(f"temporary build context changed while being hashed: {path}")

    return {
        "path": str(path),
        "size_bytes": info.st_size,
        "allocated_bytes": info.st_blocks * 512,
        "mtime_ns": info.st_mtime_ns,
        "fingerprint": digest.hexdigest(),
    }


def stale_temp_build_contexts() -> list[dict[str, Any]]:
    root = TEMP_BUILD_CONTEXT_DIR
    try:
        root_info = root.lstat()
    except OSError as exc:
        raise SafetyError("temporary directory could not be inspected") from exc
    if stat.S_ISLNK(root_info.st_mode) or not stat.S_ISDIR(root_info.st_mode):
        raise SafetyError("temporary directory is not a plain directory")
    if root.resolve(strict=True) != root:
        raise SafetyError("temporary directory traverses a symlink")

    cutoff_ns = time.time_ns() - TEMP_BUILD_CONTEXT_MIN_AGE_SECONDS * 1_000_000_000
    targets = []
    for path in sorted(root.glob("build.*.tar")):
        manifest = temp_build_context_manifest(
            path, root_info=root_info, cutoff_ns=cutoff_ns
        )
        if manifest is not None:
            targets.append(manifest)
    return targets


def read_lane() -> tuple[dict[str, Any], str]:
    try:
        info = LANE_CONFIG.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            raise SafetyError("private lane configuration is not a regular file")
        lane = json.loads(LANE_CONFIG.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SafetyError("private lane configuration is unavailable or invalid") from exc
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise SafetyError("private lane configuration must be user-owned and owner-only")
    if any(lane.get(k) != v for k, v in EXPECTED_LANE.items()):
        raise SafetyError("configured lane does not match the approved private lane")
    kubeconfig_path = Path(lane["kubeconfig_path"])
    try:
        kubeconfig_stat = kubeconfig_path.lstat()
    except OSError as exc:
        raise SafetyError("private lane kubeconfig is unavailable") from exc
    if (
        stat.S_ISLNK(kubeconfig_stat.st_mode)
        or not stat.S_ISREG(kubeconfig_stat.st_mode)
        or kubeconfig_stat.st_uid != os.getuid()
        or stat.S_IMODE(kubeconfig_stat.st_mode) & 0o077
        or kubeconfig_path.resolve(strict=True) != kubeconfig_path
    ):
        raise SafetyError("private lane kubeconfig must be user-owned and owner-only")
    container = EXPECTED_LANE["minikube_container"]
    output = run([
        "docker", "inspect", "--format",
        "{{json .Config.Labels}}|{{.State.Status}}", container,
    ])
    try:
        labels_text, state = output.rsplit("|", 1)
        labels = json.loads(labels_text)
    except (ValueError, json.JSONDecodeError) as exc:
        raise SafetyError("private Minikube container identity is unreadable") from exc
    if (
        state != "running"
        or labels.get("created_by.minikube.sigs.k8s.io") != "true"
        or labels.get("name.minikube.sigs.k8s.io") != "minh-lane"
    ):
        raise SafetyError("Minh's private Minikube node is not verified and running")
    return lane, container


def private_dangling_images(container: str) -> list[dict[str, Any]]:
    # Every image command below is executed inside this verified private node.
    ids_text = run([
        "docker", "exec", container, "docker", "image", "ls",
        "--no-trunc", "--quiet", "--filter", "dangling=true",
    ])
    ids = sorted(set(line.strip() for line in ids_text.splitlines() if line.strip()))
    container_ids_text = run([
        "docker", "exec", container, "docker", "container", "ls",
        "--all", "--quiet", "--no-trunc",
    ])
    references: set[str] = set()
    for container_id in sorted(set(container_ids_text.split())):
        image_id = run([
            "docker", "exec", container, "docker", "inspect",
            "--format", "{{.Image}}", container_id,
        ])
        if image_id:
            references.add(image_id)
    targets: list[dict[str, Any]] = []
    for image_id in ids:
        details = run([
            "docker", "exec", container, "docker", "image", "inspect",
            "--format", "{{.Id}}|{{.Size}}|{{json .RepoTags}}", image_id,
        ])
        try:
            inspected_id, size_text, tags_text = details.split("|", 2)
            tags = json.loads(tags_text)
            size = int(size_text)
        except (ValueError, json.JSONDecodeError) as exc:
            raise SafetyError("private dangling image inspection was invalid") from exc
        if inspected_id != image_id or tags not in (["<none>:<none>"], [], None):
            raise SafetyError("private image no longer matches the dangling filter")
        if inspected_id in references:
            continue
        targets.append({"id": inspected_id, "size_bytes": size})
    return targets


def rebuildable_case_image_tags() -> set[str]:
    """Return exact local case-image tags backed by checked-in Dockerfiles."""
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from debug_assistant_latest.lab_context import configured_local_images

    cases_root = REPO_ROOT / "debug_assistant_latest" / "troubleshooting"
    allowed: set[str] = set()
    cases_root = cases_root.resolve(strict=True)
    for config_path in sorted(cases_root.glob("*/config_step.json")):
        case_dir = config_path.parent
        dockerfile = case_dir / "Dockerfile"
        if (
            case_dir.is_symlink()
            or config_path.is_symlink()
            or dockerfile.is_symlink()
            or not case_dir.resolve(strict=True).is_relative_to(cases_root)
        ):
            raise SafetyError("case image source contains a symlink or escapes the repository")
        if not dockerfile.is_file():
            continue
        try:
            document = json.loads(config_path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise SafetyError("case image configuration could not be read") from exc
        if not isinstance(document, dict):
            raise SafetyError("case image configuration is not an object")
        config = document.get("config", document)
        if not isinstance(config, dict):
            raise SafetyError("case image config is not an object")
        allowed.update(
            image for image in configured_local_images(config)
            if isinstance(image, str) and image
        )
    return allowed


def _pod_image_references(kubeconfig_path: str) -> set[str]:
    output = run([
        "kubectl", "--kubeconfig", kubeconfig_path, "get", "pods",
        "--all-namespaces", "-o", "json",
    ], timeout=90)
    try:
        document = json.loads(output)
        pods = document["items"]
        if not isinstance(pods, list):
            raise ValueError("items is not a list")
        references = set()
        for pod in pods:
            spec = pod.get("spec") or {}
            for field in ("containers", "initContainers", "ephemeralContainers"):
                references.update(
                    entry["image"] for entry in spec.get(field, [])
                    if isinstance(entry.get("image"), str)
                )
        return references
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise SafetyError("private lane pod image references are unreadable") from exc


def private_allowlisted_images(
    container: str,
    kubeconfig_path: str,
    allowed_tags: set[str],
) -> list[dict[str, Any]]:
    """Find exact allowlisted private images without Docker or pod references."""
    if not allowed_tags:
        return []

    ids_text = run([
        "docker", "exec", container, "docker", "image", "ls",
        "--no-trunc", "--quiet",
    ])
    image_ids = sorted(set(line.strip() for line in ids_text.splitlines() if line.strip()))
    container_ids_text = run([
        "docker", "exec", container, "docker", "container", "ls",
        "--all", "--quiet", "--no-trunc",
    ])
    container_references: set[str] = set()
    for container_id in sorted(set(container_ids_text.split())):
        image_id = run([
            "docker", "exec", container, "docker", "inspect", "--format",
            "{{.Image}}", container_id,
        ])
        if image_id:
            container_references.add(image_id)

    pod_references = _pod_image_references(kubeconfig_path)
    targets: list[dict[str, Any]] = []
    for image_id in image_ids:
        details = run([
            "docker", "exec", container, "docker", "image", "inspect",
            "--format",
            "{{.Id}}|{{.Size}}|{{json .RepoTags}}|{{json .RepoDigests}}",
            image_id,
        ])
        try:
            inspected_id, size_text, tags_text, digests_text = details.split("|", 3)
            tags = json.loads(tags_text) or []
            digests = json.loads(digests_text) or []
            size = int(size_text)
        except (ValueError, json.JSONDecodeError) as exc:
            raise SafetyError("private image inspection was invalid") from exc
        if (
            inspected_id != image_id
            or not isinstance(tags, list)
            or not all(isinstance(tag, str) for tag in tags)
            or not isinstance(digests, list)
            or not all(isinstance(digest, str) for digest in digests)
        ):
            raise SafetyError("private image identity was invalid")
        tags = sorted(tag for tag in tags if tag != "<none>:<none>")
        digests = sorted(digests)
        if not tags or not set(tags).issubset(allowed_tags):
            continue
        if image_id in container_references or set(tags + digests).intersection(pod_references):
            continue
        targets.append({
            "id": inspected_id,
            "repo_tags": tags,
            "repo_digests": digests,
            "size_bytes": size,
        })
    return targets


def private_rebuildable_case_images(
    container: str, kubeconfig_path: str
) -> list[dict[str, Any]]:
    """Find unused lane case images that checked-in configs can rebuild."""
    return private_allowlisted_images(
        container, kubeconfig_path, rebuildable_case_image_tags()
    )


def private_rebuildable_base_images(
    container: str, kubeconfig_path: str
) -> list[dict[str, Any]]:
    """Find unused pinned base tags that can be restored by their registry digest."""
    images = private_allowlisted_images(
        container, kubeconfig_path, set(PRIVATE_REBUILDABLE_BASE_IMAGE_TAGS)
    )
    if any(not image["repo_digests"] for image in images):
        raise SafetyError("private base image lacks a registry digest for recovery")
    return images


def free_bytes() -> int:
    return shutil.disk_usage("/").free


def inventory() -> dict[str, Any]:
    lane, container = read_lane()
    rebuildable_paths = []
    for relative in REBUILDABLE_RELATIVE_PATHS:
        manifest = rebuildable_path_manifest(relative)
        if manifest is None:
            continue
        assert_no_open_files(manifest["path"])
        rebuildable_paths.append(manifest)
    stale_temp_targets = stale_temp_build_contexts()
    now = int(time.time())
    return {
        "schema_version": 5,
        "created_at": now,
        "expires_at": now + PLAN_TTL_SECONDS,
        "host": os.uname().nodename,
        "uid": os.getuid(),
        "free_bytes_before": free_bytes(),
        "lane_container": container,
        "rebuildable_paths": rebuildable_paths,
        "stale_temp_build_contexts": stale_temp_targets,
        "private_dangling_images": private_dangling_images(container),
        "private_rebuildable_case_images": private_rebuildable_case_images(
            container, lane["kubeconfig_path"]
        ),
        "private_rebuildable_base_images": private_rebuildable_base_images(
            container, lane["kubeconfig_path"]
        ),
    }


def write_private_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    parent_info = path.parent.lstat()
    if (
        stat.S_ISLNK(parent_info.st_mode)
        or not stat.S_ISDIR(parent_info.st_mode)
        or parent_info.st_uid != os.getuid()
    ):
        raise SafetyError("private report directory must be a user-owned directory")
    if path.parent.resolve(strict=True) != path.parent:
        raise SafetyError("private report directory must not traverse a symlink")
    os.chmod(path.parent, 0o700)
    try:
        existing = path.lstat()
    except FileNotFoundError:
        existing = None
    if existing is not None and (
        stat.S_ISLNK(existing.st_mode)
        or not stat.S_ISREG(existing.st_mode)
        or existing.st_uid != os.getuid()
    ):
        raise SafetyError("private report file must be user-owned and regular")
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temp = Path(temp_name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
        os.replace(temp, path)
        os.chmod(path, 0o600)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def apply_plan(plan_path: Path) -> dict[str, Any]:
    try:
        plan = json.loads(plan_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SafetyError("plan file is unavailable or invalid") from exc
    if plan.get("schema_version") != 5 or plan.get("uid") != os.getuid():
        raise SafetyError("plan schema or owner does not match this user")
    if plan.get("host") != os.uname().nodename or int(plan.get("expires_at", 0)) < time.time():
        raise SafetyError("plan host differs or the plan has expired")
    fresh = inventory()
    for key in (
        "lane_container", "rebuildable_paths", "stale_temp_build_contexts",
        "private_dangling_images", "private_rebuildable_case_images",
        "private_rebuildable_base_images",
    ):
        if fresh.get(key) != plan.get(key):
            raise SafetyError(f"targets changed since plan creation: {key}")

    dangling_ids = [item["id"] for item in fresh["private_dangling_images"]]
    case_image_ids = [item["id"] for item in fresh["private_rebuildable_case_images"]]
    base_images = fresh["private_rebuildable_base_images"]
    base_image_ids = [item["id"] for item in base_images]
    planned_ids = dangling_ids + case_image_ids + base_image_ids
    image_ids = sorted(set(planned_ids))
    if len(image_ids) != len(planned_ids):
        raise SafetyError("private image target categories overlap")
    if base_images:
        try:
            restore_manifest = json.loads(IMAGE_RESTORE_MANIFEST.read_text())
        except FileNotFoundError:
            restore_manifest = {"schema_version": 1, "images": []}
        except (OSError, json.JSONDecodeError) as exc:
            raise SafetyError("private image restore manifest is unreadable") from exc
        if restore_manifest.get("schema_version") != 1 or not isinstance(restore_manifest.get("images"), list):
            raise SafetyError("private image restore manifest has an unsupported format")
        known = {
            (item.get("id"), tuple(item.get("repo_digests", [])))
            for item in restore_manifest["images"]
            if isinstance(item, dict)
        }
        for image in base_images:
            key = (image["id"], tuple(image["repo_digests"]))
            if key not in known:
                restore_manifest["images"].append({
                    **image,
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                })
                known.add(key)
        write_private_json(IMAGE_RESTORE_MANIFEST, restore_manifest)

    removed_rebuildable_paths: list[dict[str, Any]] = []
    removed_temp_build_contexts: list[dict[str, Any]] = []
    for target in fresh["stale_temp_build_contexts"]:
        current = temp_build_context_manifest(
            Path(target["path"]), check_open=False
        )
        if current != target:
            raise SafetyError(f"temporary build context changed before removal: {target['path']}")
        assert_no_open_file(Path(target["path"]))
        Path(target["path"]).unlink()
        removed_temp_build_contexts.append({
            "path": target["path"],
            "allocated_bytes": target["allocated_bytes"],
        })

    for target in fresh["rebuildable_paths"]:
        current = rebuildable_path_manifest(target["relative_path"])
        assert_no_open_files(current["path"])
        if current != target:
            raise SafetyError(f"rebuildable path changed before removal: {target['relative_path']}")
        shutil.rmtree(current["path"])
        removed_rebuildable_paths.append({
            "relative_path": target["relative_path"],
            "allocated_bytes": target["allocated_bytes"],
        })

    if image_ids:
        # No force flag: the private daemon refuses images used by a container.
        run([
            "docker", "exec", fresh["lane_container"], "docker", "image", "rm",
            *image_ids,
        ])

    return {
        "host": os.uname().nodename,
        "free_bytes_before": plan["free_bytes_before"],
        "free_bytes_after": free_bytes(),
        "removed_rebuildable_paths": removed_rebuildable_paths,
        "removed_temp_build_contexts": removed_temp_build_contexts,
        "removed_private_dangling_image_ids": dangling_ids,
        "removed_private_rebuildable_case_image_ids": case_image_ids,
        "removed_private_rebuildable_base_image_ids": base_image_ids,
        "private_image_restore_manifest": (
            str(IMAGE_RESTORE_MANIFEST) if base_images else None
        ),
    }


def _path_usage(relative_path: str) -> dict[str, Any] | None:
    path = Path.home() / relative_path
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise SafetyError(f"could not inspect report path: {relative_path}") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise SafetyError(f"report path is not a plain directory: {relative_path}")
    if info.st_uid != os.getuid() or path.resolve(strict=True) != path:
        raise SafetyError(f"report path is not user-owned: {relative_path}")
    output = run(["du", "-sx", "--block-size=1", "--", str(path)], timeout=300)
    try:
        allocated = int(output.split(maxsplit=1)[0])
    except (IndexError, ValueError) as exc:
        raise SafetyError(f"report size could not be parsed: {relative_path}") from exc
    return {"relative_path": relative_path, "allocated_bytes": allocated}


def build_storage_report() -> dict[str, Any]:
    campaign_usage = shutil.disk_usage(REPO_ROOT)
    try:
        docker_root_text = run(["docker", "info", "--format", "{{.DockerRootDir}}"])
        docker_root = Path(docker_root_text)
        if not docker_root.is_absolute() or not docker_root.is_dir():
            raise SafetyError("Docker data-root path is unavailable")
        docker_usage = shutil.disk_usage(docker_root)
        docker_data_root = {
            "status": "available",
            "path": str(docker_root),
            "free_bytes": docker_usage.free,
            "free_gib": round(docker_usage.free / 1024**3, 2),
            "profile_start_required_bytes": PROFILE_START_DOCKER_FREE_BYTES,
            "profile_start_gate_met": docker_usage.free >= PROFILE_START_DOCKER_FREE_BYTES,
        }
    except (OSError, SafetyError) as exc:
        docker_data_root = {
            "status": f"unavailable: {exc}",
            "profile_start_required_bytes": PROFILE_START_DOCKER_FREE_BYTES,
            "profile_start_gate_met": False,
        }

    private = None
    try:
        private = inventory()
        private_lane = {
            "rebuildable_path_targets": len(private["rebuildable_paths"]),
            "dangling_images": len(private["private_dangling_images"]),
            "rebuildable_case_images": len(private["private_rebuildable_case_images"]),
            "rebuildable_base_images": len(private["private_rebuildable_base_images"]),
        }
        private_lane_status = "available"
    except SafetyError as exc:
        private_lane = None
        private_lane_status = f"unavailable: {exc}"

    if private is not None:
        stale_temp_targets = private["stale_temp_build_contexts"]
        stale_temp_status = "available"
    else:
        try:
            stale_temp_targets = stale_temp_build_contexts()
            stale_temp_status = "available"
        except SafetyError as exc:
            stale_temp_targets = []
            stale_temp_status = f"unavailable: {exc}"

    paths = [
        snapshot for relative in REPORT_PATHS
        if (snapshot := _path_usage(relative)) is not None
    ]
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "campaign_filesystem": {
            "path": str(REPO_ROOT),
            "total_bytes": campaign_usage.total,
            "used_bytes": campaign_usage.used,
            "free_bytes": campaign_usage.free,
            "free_gib": round(campaign_usage.free / 1024**3, 2),
            "campaign_startup_required_bytes": CAMPAIGN_STARTUP_FREE_BYTES,
            "campaign_startup_gate_met": (
                campaign_usage.free >= CAMPAIGN_STARTUP_FREE_BYTES
            ),
            "campaign_before_attempt_required_bytes": CAMPAIGN_ATTEMPT_FREE_BYTES,
            "warning_threshold_bytes": STORAGE_WARNING_FREE_BYTES,
            "warning": campaign_usage.free < STORAGE_WARNING_FREE_BYTES,
        },
        "docker_data_root": docker_data_root,
        "private_lane_status": private_lane_status,
        "private_lane_candidates": private_lane,
        "stale_temp_build_contexts": {
            "status": stale_temp_status,
            "count": len(stale_temp_targets),
            "allocated_bytes": sum(item["allocated_bytes"] for item in stale_temp_targets),
        },
        "owned_path_usage": paths,
    }


def write_storage_report(path: Path = DEFAULT_REPORT_PATH) -> dict[str, Any]:
    report = build_storage_report()
    write_private_json(path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--plan", action="store_true", help="write a fresh reviewable plan")
    group.add_argument("--apply", type=Path, metavar="PLAN", help="apply a fresh plan")
    group.add_argument("--report", action="store_true", help="write a read-only storage report")
    parser.add_argument(
        "--plan-file", type=Path,
        default=Path.home() / ".local/lab-ops/storage-hygiene-plan.json",
    )
    parser.add_argument(
        "--report-file", type=Path, default=DEFAULT_REPORT_PATH,
        help="destination for --report",
    )
    args = parser.parse_args()
    try:
        if args.report:
            report = write_storage_report(args.report_file)
            print(json.dumps(report, indent=2, sort_keys=True))
        elif args.plan:
            plan = inventory()
            write_private_json(args.plan_file, plan)
            print(json.dumps(plan, indent=2, sort_keys=True))
        else:
            result = apply_plan(args.apply)
            print(json.dumps(result, indent=2, sort_keys=True))
    except SafetyError as exc:
        print(f"blocked: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
