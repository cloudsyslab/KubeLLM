#!/usr/bin/env python3
"""Ownership-aware, read-mostly operations helpers for a KubeLLM lab host.

The default audit is read-only. Cleanup plans are immutable snapshots; apply
rechecks the selected lane, resource owner, and container references before
removing one exact lane-labeled, unused image. Stopped containers, volumes, and
resources with missing or ambiguous ownership are never removed by this tool.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import socket
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
PLAN_SCHEMA = 1
PLAN_MAX_AGE_SECONDS = 3600
MIN_FREE_GIB = 30


class OpsError(RuntimeError):
    pass


def command(argv: list[str], *, timeout: int = 15) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            argv, stdin=subprocess.DEVNULL, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise OpsError(f"Could not complete {Path(argv[0]).name}: {type(exc).__name__}") from exc


def json_lines(text: str) -> list[dict[str, Any]]:
    rows = []
    for line in text.splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def require_lane(path: str) -> dict[str, Any]:
    sys.path.insert(0, str(REPO))
    from debug_assistant_latest.lab_context import load_lane_config

    try:
        lane = load_lane_config(path)
    except Exception as exc:
        raise OpsError(f"The explicit private lane selector failed validation: {type(exc).__name__}") from exc
    return lane


def docker_inventory() -> dict[str, Any]:
    images_result = command(["docker", "image", "ls", "-a", "--no-trunc", "--format", "{{json .}}"])
    containers_result = command(["docker", "ps", "-a", "--no-trunc", "--format", "{{json .}}"])
    volumes_result = command(["docker", "volume", "ls", "--format", "{{json .}}"])
    if images_result.returncode or containers_result.returncode or volumes_result.returncode:
        raise OpsError("Docker inventory is unavailable; no cleanup action was attempted.")

    image_rows = json_lines(images_result.stdout)
    container_rows = json_lines(containers_result.stdout)
    volume_rows = json_lines(volumes_result.stdout)

    image_ids = list(dict.fromkeys(row.get("ID", "") for row in image_rows if row.get("ID")))
    image_details: dict[str, dict[str, Any]] = {}
    if image_ids:
        result = command(["docker", "image", "inspect", *image_ids])
        if result.returncode == 0:
            try:
                payload = json.loads(result.stdout)
            except ValueError:
                payload = []
            for image in payload if isinstance(payload, list) else []:
                if not isinstance(image, dict):
                    continue
                image_id = str(image.get("Id", ""))
                image_details[image_id] = {
                    "id": image_id,
                    "created": image.get("Created"),
                    "size_bytes": image.get("Size"),
                    "tags": image.get("RepoTags") or [],
                    "owner_lane": ((image.get("Config") or {}).get("Labels") or {}).get("io.kubellm.lane"),
                }

    container_ids = list(dict.fromkeys(row.get("ID", "") for row in container_rows if row.get("ID")))
    container_details: list[dict[str, Any]] = []
    if container_ids:
        result = command(["docker", "container", "inspect", *container_ids])
        if result.returncode == 0:
            try:
                payload = json.loads(result.stdout)
            except ValueError:
                payload = []
            for item in payload if isinstance(payload, list) else []:
                if not isinstance(item, dict):
                    continue
                state = item.get("State") or {}
                container_details.append({
                    "id": item.get("Id"),
                    "name": str(item.get("Name", "")).lstrip("/"),
                    "image_id": item.get("Image"),
                    "running": state.get("Running") is True,
                    "status": state.get("Status"),
                    "owner_lane": ((item.get("Config") or {}).get("Labels") or {}).get("io.kubellm.lane"),
                    "minikube_profile": ((item.get("Config") or {}).get("Labels") or {}).get("name.minikube.sigs.k8s.io"),
                    "mount_names": [mount.get("Name") for mount in item.get("Mounts", []) if mount.get("Name")],
                    "restart_policy": ((item.get("HostConfig") or {}).get("RestartPolicy") or {}).get("Name"),
                })

    volume_names = list(dict.fromkeys(row.get("Name", "") for row in volume_rows if row.get("Name")))
    volume_details: list[dict[str, Any]] = []
    if volume_names:
        result = command(["docker", "volume", "inspect", *volume_names])
        if result.returncode == 0:
            try:
                payload = json.loads(result.stdout)
            except ValueError:
                payload = []
            for item in payload if isinstance(payload, list) else []:
                if isinstance(item, dict):
                    volume_details.append({
                        "name": item.get("Name"),
                        "owner_lane": (item.get("Labels") or {}).get("io.kubellm.lane"),
                        "mountpoint": item.get("Mountpoint"),
                    })

    for image in image_details.values():
        image["container_ids"] = sorted(
            str(container["id"]) for container in container_details
            if container.get("image_id") == image["id"]
        )
    for volume in volume_details:
        volume["container_ids"] = sorted(
            str(container["id"]) for container in container_details
            if volume["name"] in container.get("mount_names", [])
        )

    return {
        "images": sorted(image_details.values(), key=lambda item: item["id"]),
        "containers": sorted(container_details, key=lambda item: item["id"]),
        "volumes": sorted(volume_details, key=lambda item: item["name"]),
        "reported": {"image_rows": len(image_rows), "container_rows": len(container_rows), "volume_rows": len(volume_rows)},
    }


def host_inventory() -> dict[str, Any]:
    usage = shutil.disk_usage("/")
    docker_root_result = command(["docker", "info", "--format", "{{.DockerRootDir}}"])
    docker_root = docker_root_result.stdout.strip() if docker_root_result.returncode == 0 else None
    docker_usage = None
    if docker_root:
        try:
            value = shutil.disk_usage(docker_root)
            docker_usage = {"total_bytes": value.total, "used_bytes": value.used, "free_bytes": value.free}
        except OSError:
            pass
    breakdown: dict[str, Any] = {"available": False, "requires_root": os.geteuid() != 0}
    if shutil.which("du"):
        try:
            result = command(["du", "-x", "-B1", "--max-depth=2", "/"], timeout=90)
        except OpsError:
            result = None
        if result is not None and (result.returncode == 0 or result.stdout):
            rows = []
            for line in result.stdout.splitlines():
                size, separator, path = line.partition("\t")
                if separator and size.isdecimal():
                    rows.append({"path": path, "bytes": int(size)})
            breakdown = {"available": result.returncode == 0, "requires_root": os.geteuid() != 0, "rows": rows[-500:]}
    df = command(["df", "-Pi", "/"])
    free_inodes = None
    if df.returncode == 0:
        fields = df.stdout.splitlines()[-1].split()
        if len(fields) >= 6:
            free_inodes = fields[3]
    return {
        "hostname": socket.gethostname(),
        "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "uid": os.geteuid(),
        "root": {"total_bytes": usage.total, "used_bytes": usage.used, "free_bytes": usage.free,
                 "free_gib": round(usage.free / 1024**3, 2), "percent_used": round(100 * usage.used / usage.total, 1),
                 "free_inodes": free_inodes},
        "docker_root": docker_root,
        "docker_filesystem": docker_usage,
        "directory_breakdown": breakdown,
        "capacity_targets": {"minikube_startup_gate_gib": 20, "recommended_free_gib": MIN_FREE_GIB},
    }


def check_loopback(url: str) -> dict[str, Any]:
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "kubellm-lab-ops/1"})
        with urllib.request.urlopen(request, timeout=3) as response:
            return {"reachable": 200 <= response.status < 300, "status": response.status}
    except (OSError, urllib.error.URLError):
        return {"reachable": False}


def lane_inventory(lane: dict[str, Any], docker: dict[str, Any], *, ui_port: int) -> dict[str, Any]:
    selector = str(lane.get("config_path", ""))
    profile = lane["minikube_profile"]
    profile_status = command(["minikube", "-p", profile, "status", "--format", "json"], timeout=10)
    if profile_status.returncode == 0:
        try:
            status: Any = json.loads(profile_status.stdout)
        except ValueError:
            status = profile_status.stdout[:1000]
    else:
        status = {"available": False, "exit_code": profile_status.returncode}

    service_checks: dict[str, Any] = {
        "ui": check_loopback(f"http://127.0.0.1:{ui_port}/api/session"),
        "rag": check_loopback(str(lane["rag_api_url"]).rstrip("/") + "/server_info/"),
    }
    selected_container_names = {lane["pgvector_container"], lane["minikube_container"]}
    selected = [item for item in docker["containers"] if item["name"] in selected_container_names]
    selected.extend(item for item in docker["containers"] if item["owner_lane"] == lane["lane_id"] and item not in selected)
    selected_ids = {item["id"] for item in selected}
    for container in docker["containers"]:
        if container["id"] in selected_ids and container["name"] == lane["pgvector_container"]:
            service_checks["database_container"] = {
                "present": True, "running": container["running"], "owner_lane": container["owner_lane"],
                "restart_policy": container["restart_policy"],
            }
    if "database_container" not in service_checks:
        service_checks["database_container"] = {"present": False}
    return {
        "lane_id": lane["lane_id"],
        "selector": selector,
        "selector_permissions": oct(stat.S_IMODE(Path(selector).stat().st_mode)),
        "profile": profile,
        "profile_status": status,
        "service_checks": service_checks,
        "selected_containers": selected,
        "private_files": {
            "service_env_permissions": oct(stat.S_IMODE(Path(lane["service_env_file"]).stat().st_mode)),
            "kubeconfig_permissions": oct(stat.S_IMODE(Path(lane["kubeconfig_path"]).stat().st_mode)),
        },
    }


def build_audit(lane_path: str, *, ui_port: int) -> dict[str, Any]:
    lane = require_lane(lane_path)
    docker = docker_inventory()
    host = host_inventory()
    return {
        "schema_version": 1,
        "host": host,
        "docker": docker,
        "selected_lane": lane_inventory(lane, docker, ui_port=ui_port),
    }


def lane_cleanup_targets(audit: dict[str, Any], lane_id: str) -> list[dict[str, Any]]:
    docker = audit["docker"]
    targets: list[dict[str, Any]] = []
    for container in docker["containers"]:
        if container.get("owner_lane") == lane_id and not container.get("running"):
            targets.append({
                "kind": "stopped_container", "id": container["id"], "name": container["name"],
                "owner_lane": lane_id, "safe_to_apply": False,
                "reason": "Stopped container logs may contain benchmark evidence; review and archive first.",
            })
    for image in docker["images"]:
        if image.get("owner_lane") == lane_id and not image.get("container_ids"):
            targets.append({
                "kind": "unused_image", "id": image["id"], "tags": image["tags"],
                "size_bytes": image["size_bytes"], "owner_lane": lane_id,
                "safe_to_apply": True,
                "reason": "Explicit lane label, no container references, exact image ID will be rechecked before removal.",
            })
    for volume in docker["volumes"]:
        if volume.get("owner_lane") == lane_id and not volume.get("container_ids"):
            targets.append({
                "kind": "unused_volume", "id": volume["name"], "owner_lane": lane_id,
                "safe_to_apply": False,
                "reason": "Volume deletion remains manual because it can destroy persistent benchmark/database state.",
            })
    # Keep unknown and foreign resources visible without implying permission.
    for image in docker["images"]:
        if not image.get("container_ids") and image.get("owner_lane") != lane_id:
            targets.append({
                "kind": "unowned_image", "id": image["id"], "tags": image["tags"],
                "size_bytes": image["size_bytes"], "owner_lane": image.get("owner_lane"),
                "safe_to_apply": False,
                "reason": "Ownership is absent or belongs to another lane; obtain target-specific owner approval.",
            })
    return targets


def save_plan(path: Path, plan: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with tmp.open("x", encoding="utf-8") as handle:
            os.fchmod(handle.fileno(), stat.S_IRUSR | stat.S_IWUSR)
            json.dump(plan, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    finally:
        tmp.unlink(missing_ok=True)


def apply_target(plan_path: Path, resource_id: str, lane_id: str, *, yes: bool) -> None:
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise OpsError("Cleanup plan is unreadable or invalid.") from exc
    if (plan.get("schema_version") != PLAN_SCHEMA or plan.get("lane_id") != lane_id
            or plan.get("host") != socket.gethostname()):
        raise OpsError("Cleanup plan does not match the explicitly selected lane.")
    try:
        age = time.time() - dt.datetime.fromisoformat(plan["created_at"]).timestamp()
    except (KeyError, ValueError, TypeError) as exc:
        raise OpsError("Cleanup plan has no valid creation time.") from exc
    if age < 0 or age > PLAN_MAX_AGE_SECONDS:
        raise OpsError("Cleanup plan is older than one hour; generate a fresh audit and plan.")
    digest = plan.get("fingerprint")
    payload = {key: value for key, value in plan.items() if key != "fingerprint"}
    expected = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if digest != expected:
        raise OpsError("Cleanup plan fingerprint is invalid.")
    target = next((item for item in plan.get("targets", []) if item.get("id") == resource_id), None)
    if not target or target.get("owner_lane") != lane_id or not target.get("safe_to_apply"):
        raise OpsError("Resource is not an apply-eligible target owned by the selected lane.")
    if not yes:
        raise OpsError("Apply requires --yes after you review the exact target in the cleanup plan.")

    current = docker_inventory()
    if target["kind"] == "unused_image":
        image = next((item for item in current["images"] if item["id"] == resource_id), None)
        if not image or image.get("owner_lane") != lane_id or image.get("container_ids"):
            raise OpsError("Image ownership or use changed since planning; nothing was removed.")
        if image.get("size_bytes") != target.get("size_bytes"):
            raise OpsError("Image metadata changed since planning; nothing was removed.")
        result = command(["docker", "image", "rm", "--no-prune", resource_id], timeout=60)
    else:
        raise OpsError("This target type cannot be removed by apply.")
    if result.returncode:
        raise OpsError("Docker refused the exact removal; inspect the current resource before retrying.")
    print(json.dumps({"removed": resource_id, "kind": target["kind"], "lane_id": lane_id}, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit and safely plan KubeLLM lab hygiene actions.")
    parser.add_argument("--lab-config", required=True, help="Explicit owner-only private lane selector JSON.")
    parser.add_argument("--ui-port", type=int, default=8787)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("audit", aliases=["status", "doctor"], help="Read-only host, Docker, and selected-lane inventory.")
    plan_parser = sub.add_parser("plan", help="Write a one-hour, revalidated cleanup plan.")
    plan_parser.add_argument("--output", type=Path, default=Path(".local/lab-ops/cleanup-plan.json"))
    apply_parser = sub.add_parser("apply", help="Remove one explicitly listed lane-owned dangling image.")
    apply_parser.add_argument("--plan", type=Path, required=True)
    apply_parser.add_argument("--resource", required=True, help="Exact immutable Docker image ID from the reviewed plan.")
    apply_parser.add_argument("--yes", action="store_true", help="Confirm the exact selected-lane target.")
    args = parser.parse_args()
    try:
        lane = require_lane(args.lab_config)
        if args.action in {"audit", "status", "doctor"}:
            print(json.dumps(build_audit(args.lab_config, ui_port=args.ui_port), indent=2, sort_keys=True))
        elif args.action == "plan":
            audit = build_audit(args.lab_config, ui_port=args.ui_port)
            payload = {
                "schema_version": PLAN_SCHEMA,
                "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "lane_id": lane["lane_id"],
                "host": audit["host"]["hostname"],
                "targets": lane_cleanup_targets(audit, lane["lane_id"]),
                "policy": "Only exact lane-labeled unused images can be applied. Volumes, foreign or unlabeled objects, and stopped containers require manual evidence review.",
            }
            payload["fingerprint"] = hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            save_plan(args.output, payload)
            print(json.dumps({"plan": str(args.output), "fingerprint": payload["fingerprint"],
                              "lane_id": lane["lane_id"], "target_count": len(payload["targets"]),
                              "apply_eligible": sum(item["safe_to_apply"] for item in payload["targets"])}, sort_keys=True))
        elif args.action == "apply":
            apply_target(args.plan, args.resource, lane["lane_id"], yes=args.yes)
        return 0
    except (OpsError, KeyError, OSError, ValueError) as exc:
        print(f"lab-ops: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
