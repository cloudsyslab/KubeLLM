#!/usr/bin/env python3
"""Plan and remove only Minh-owned idle caches and dangling images in minh-lane.

This tool never lists, prunes, or removes images from the shared host Docker
daemon. Docker image operations run only inside the verified private Minikube
node container.
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
import time
from typing import Any

CACHE_RELATIVE_PATHS = (
    ".cache/ms-playwright",
    ".npm/_cacache",
    ".minikube/cache/images/amd64",
)
LANE_CONFIG = Path.home() / ".config/kubellm/lanes/minh.json"
EXPECTED_LANE = {
    "lane_id": "minh",
    "minikube_profile": "minh-lane",
    "minikube_container": "minh-lane",
}
PLAN_TTL_SECONDS = 3600


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


def cache_path(relative: str) -> Path:
    if relative not in CACHE_RELATIVE_PATHS:
        raise SafetyError("cache path is outside the fixed allowlist")
    return Path.home() / relative


def _walk_error(exc: OSError) -> None:
    raise SafetyError("cache could not be fully inspected") from exc


def cache_manifest(relative: str) -> dict[str, Any] | None:
    root = cache_path(relative)
    try:
        root_stat = root.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise SafetyError(f"cache target could not be inspected: {relative}") from exc
    if stat.S_ISLNK(root_stat.st_mode) or not stat.S_ISDIR(root_stat.st_mode):
        raise SafetyError(f"cache target is not a plain directory: {relative}")
    if root.resolve(strict=True) != root:
        raise SafetyError(f"cache target traverses a symlink: {relative}")
    uid = os.getuid()
    if root_stat.st_uid != uid:
        raise SafetyError(f"cache target is not owned by the current user: {relative}")

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
                    f"cache changed while being inspected: {relative}"
                ) from exc
            if stat.S_ISLNK(item_stat.st_mode):
                raise SafetyError(f"cache contains a symlink: {relative}")
            if item_stat.st_uid != uid:
                raise SafetyError(f"cache contains another owner's file: {relative}")
            if item_stat.st_dev != root_stat.st_dev:
                raise SafetyError(f"cache crosses a filesystem boundary: {relative}")
            kind = "d" if is_dir else "f"
            rel = item.relative_to(root).as_posix()
            records.append(
                (rel, kind, item_stat.st_ino, item_stat.st_size, item_stat.st_mtime_ns,
                 item_stat.st_mode, item_stat.st_nlink, item_stat.st_blocks)
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
        raise SafetyError("could not verify cache has no open files") from exc
    if result.returncode not in (0, 1):
        raise SafetyError("lsof could not verify cache use")
    if result.stdout.strip():
        raise SafetyError(f"cache has open files: {path}")


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


def free_bytes() -> int:
    return shutil.disk_usage("/").free


def inventory() -> dict[str, Any]:
    _, container = read_lane()
    caches = []
    for relative in CACHE_RELATIVE_PATHS:
        manifest = cache_manifest(relative)
        if manifest is None:
            continue
        assert_no_open_files(manifest["path"])
        caches.append(manifest)
    now = int(time.time())
    return {
        "schema_version": 1,
        "created_at": now,
        "expires_at": now + PLAN_TTL_SECONDS,
        "host": os.uname().nodename,
        "uid": os.getuid(),
        "free_bytes_before": free_bytes(),
        "lane_container": container,
        "caches": caches,
        "private_dangling_images": private_dangling_images(container),
    }


def write_private_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = path.with_suffix(path.suffix + ".tmp")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
    os.replace(temp, path)
    os.chmod(path, 0o600)


def apply_plan(plan_path: Path) -> dict[str, Any]:
    try:
        plan = json.loads(plan_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SafetyError("plan file is unavailable or invalid") from exc
    if plan.get("schema_version") != 1 or plan.get("uid") != os.getuid():
        raise SafetyError("plan schema or owner does not match this user")
    if plan.get("host") != os.uname().nodename or int(plan.get("expires_at", 0)) < time.time():
        raise SafetyError("plan host differs or the plan has expired")
    fresh = inventory()
    for key in ("lane_container", "caches", "private_dangling_images"):
        if fresh.get(key) != plan.get(key):
            raise SafetyError(f"targets changed since plan creation: {key}")

    removed_caches: list[dict[str, Any]] = []
    for target in fresh["caches"]:
        current = cache_manifest(target["relative_path"])
        assert_no_open_files(current["path"])
        if current != target:
            raise SafetyError(f"cache changed before removal: {target['relative_path']}")
        shutil.rmtree(current["path"])
        removed_caches.append({
            "relative_path": target["relative_path"],
            "allocated_bytes": target["allocated_bytes"],
        })

    removed_images: list[str] = []
    image_ids = [item["id"] for item in fresh["private_dangling_images"]]
    if image_ids:
        # No force flag: the private daemon refuses any image in use by a container.
        run([
            "docker", "exec", fresh["lane_container"], "docker", "image", "rm",
            *image_ids,
        ])
        removed_images = image_ids

    return {
        "host": os.uname().nodename,
        "free_bytes_before": plan["free_bytes_before"],
        "free_bytes_after": free_bytes(),
        "removed_caches": removed_caches,
        "removed_private_dangling_image_ids": removed_images,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--plan", action="store_true", help="write a fresh reviewable plan")
    group.add_argument("--apply", type=Path, metavar="PLAN", help="apply a fresh plan")
    parser.add_argument(
        "--plan-file", type=Path,
        default=Path.home() / ".local/lab-ops/storage-hygiene-plan.json",
    )
    args = parser.parse_args()
    try:
        if args.plan:
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
