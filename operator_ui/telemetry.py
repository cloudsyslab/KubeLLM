"""Read-only, bounded host and selected-lane telemetry for the operator UI."""

from __future__ import annotations

import csv
import io
import json
import os
import pwd
import re
import shutil
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from debug_assistant_latest.lab_context import LANE_OWNER_LABEL, load_lane_config

from .config import private_lab_config


COMMAND_TIMEOUT_S = 5
MAX_PROCESSES = 40
MAX_PODS = 300
MAX_PROFILES = 30
_CPU_LOCK = threading.Lock()
_CPU_PREVIOUS: dict[str, tuple[int, ...]] = {}


def _stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _command(argv: list[str], *, timeout: int = COMMAND_TIMEOUT_S) -> str | None:
    """Run one bounded read-only command without a shell or inherited input."""
    try:
        result = subprocess.run(
            argv,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout[:2_000_000]


def _cpu_rows() -> list[dict[str, Any]]:
    global _CPU_PREVIOUS
    try:
        lines = Path("/proc/stat").read_text(encoding="ascii").splitlines()
    except OSError:
        return []
    current: dict[str, tuple[int, ...]] = {}
    for line in lines:
        fields = line.split()
        if not fields or not re.fullmatch(r"cpu(?:\d+)?", fields[0]):
            continue
        try:
            current[fields[0]] = tuple(int(value) for value in fields[1:9])
        except ValueError:
            continue

    rows = []
    with _CPU_LOCK:
        previous = _CPU_PREVIOUS
        _CPU_PREVIOUS = current
    for name, values in current.items():
        old = previous.get(name)
        percent = None
        if old and len(old) == len(values):
            total_delta = sum(values) - sum(old)
            idle_delta = (values[3] + values[4]) - (old[3] + old[4])
            if total_delta > 0:
                percent = round(max(0.0, min(100.0, 100 * (total_delta - idle_delta) / total_delta)), 1)
        rows.append({"id": "total" if name == "cpu" else name[3:], "percent": percent})
    return rows


def _memory() -> dict[str, Any] | None:
    try:
        values: dict[str, int] = {}
        for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
            name, _, rest = line.partition(":")
            fields = rest.split()
            if fields and fields[0].isdigit():
                values[name] = int(fields[0]) * (1024 if len(fields) > 1 and fields[1] == "kB" else 1)
        total = values["MemTotal"]
        available = values.get("MemAvailable")
    except (OSError, KeyError, ValueError):
        return None
    if total <= 0 or available is None:
        return None
    used = max(0, total - available)
    cache = values.get("Cached", 0) + values.get("SReclaimable", 0)
    return {
        "total_bytes": total,
        "used_bytes": used,
        "available_bytes": available,
        "cache_bytes": cache,
        "percent": round(100 * used / total, 1),
    }


def _disk() -> dict[str, Any] | None:
    docker_root = (_command(["docker", "info", "--format", "{{.DockerRootDir}}"], timeout=3) or "/").strip()
    if not docker_root or not Path(docker_root).is_absolute():
        docker_root = "/"
    try:
        usage = shutil.disk_usage(docker_root)
    except OSError:
        return {"path": docker_root, "total_bytes": None, "used_bytes": None, "free_bytes": None, "free_gib": None, "percent": None}
    return {
        "path": docker_root,
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
        "free_gib": round(usage.free / 1024**3, 2),
        "percent": round(100 * usage.used / usage.total, 1) if usage.total else None,
    }


def _gpus() -> list[dict[str, Any]] | None:
    raw = _command([
        "nvidia-smi",
        "--query-gpu=index,name,utilization.gpu,memory.total,memory.used,temperature.gpu,power.draw",
        "--format=csv,noheader,nounits",
    ])
    if raw is None:
        return None
    rows = []
    for values in csv.reader(io.StringIO(raw)):
        if len(values) != 7:
            continue
        try:
            index = int(values[0].strip())
        except ValueError:
            continue
        def number(value: str) -> float | None:
            value = value.strip()
            if not value or value.upper() in {"N/A", "[N/A]"}:
                return None
            try:
                return float(value)
            except ValueError:
                return None
        rows.append({
            "index": index,
            "name": values[1].strip()[:100],
            "utilization_pct": number(values[2]),
            "memory_total_mib": number(values[3]),
            "memory_used_mib": number(values[4]),
            "temperature_c": number(values[5]),
            "power_w": number(values[6]),
        })
    return rows


def _processes() -> list[dict[str, Any]] | None:
    raw = _command(["ps", "-eo", "pid=,uid=,pcpu=,rss=,comm=", "--sort=-pcpu"])
    if raw is None:
        # macOS/non-GNU ps fallback; do not read process arguments or environment.
        raw = _command(["ps", "-axo", "pid=,uid=,%cpu=,rss=,comm="])
    if raw is None:
        return None
    rows = []
    for line in raw.splitlines():
        fields = line.split(None, 4)
        if len(fields) != 5:
            continue
        try:
            pid, uid = int(fields[0]), int(fields[1])
            cpu_pct, rss_kib = float(fields[2]), int(fields[3])
            username = pwd.getpwuid(uid).pw_name
        except (ValueError, KeyError, OSError):
            continue
        if pid == os.getpid() or not fields[4].strip():
            continue
        rows.append({
            "pid": pid,
            "user": username[:64],
            "name": fields[4].strip()[:100],
            "cpu_pct": round(max(0.0, cpu_pct), 1),
            "memory_bytes": max(0, rss_kib) * 1024,
            "attribution": "unconfirmed",
        })
        if len(rows) >= MAX_PROCESSES:
            break
    return rows


def host_snapshot() -> dict[str, Any]:
    cpus = _cpu_rows()
    cpu = {
        "total_pct": next((item["percent"] for item in cpus if item["id"] == "total"), None),
        "per_core": [item["percent"] for item in cpus if item["id"] != "total"],
    }
    memory = _memory() or {
        "total_bytes": None,
        "used_bytes": None,
        "available_bytes": None,
        "cache_bytes": None,
        "percent": None,
    }
    disk = _disk()
    gpus = _gpus()
    processes = _processes()
    unavailable = []
    if not cpus or all(item["percent"] is None for item in cpus):
        unavailable.append("CPU")
    if memory["total_bytes"] is None:
        unavailable.append("memory")
    if disk is None or disk["total_bytes"] is None:
        unavailable.append("disk")
    if gpus is None:
        unavailable.append("GPU")
    if processes is None:
        unavailable.append("process")
    return {
        "sampled_at": _stamp(),
        "stale": False,
        "status": "unavailable" if len(unavailable) == 5 else "partial" if unavailable else "ok",
        "reason": f"Unavailable telemetry: {', '.join(unavailable)}." if unavailable else None,
        "gpu_inventory_available": gpus is not None,
        "process_inventory_available": processes is not None,
        "cpu": cpu,
        "memory": memory,
        "disk": disk,
        "gpus": [] if gpus is None else [
            {
                "index": item["index"],
                "name": item["name"],
                "utilization_pct": item["utilization_pct"],
                "memory_total_bytes": None if item["memory_total_mib"] is None else int(item["memory_total_mib"] * 1024**2),
                "memory_used_bytes": None if item["memory_used_mib"] is None else int(item["memory_used_mib"] * 1024**2),
                "temperature_c": item["temperature_c"],
                "power_w": item["power_w"],
            }
            for item in gpus
        ],
        "processes": processes or [],
    }


def _profile_names() -> list[str]:
    root = Path.home() / ".minikube" / "profiles"
    try:
        names = sorted(path.name for path in root.iterdir() if path.is_dir() and not path.is_symlink())
    except OSError:
        names = []
    return [name for name in names if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,62}", name)][:MAX_PROFILES]


def _objects(payload: object) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        return []
    return [item for item in payload["items"] if isinstance(item, dict)]


def _pods(kubeconfig: Path) -> list[dict[str, Any]] | None:
    raw = _command(["kubectl", "--kubeconfig", str(kubeconfig), "get", "pods", "--all-namespaces", "--chunk-size=100", "-o", "json"], timeout=10)
    if raw is None:
        return None
    try:
        items = _objects(json.loads(raw))
    except ValueError:
        return None
    pods = []
    for item in items[:MAX_PODS]:
        meta = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        status = item.get("status") if isinstance(item.get("status"), dict) else {}
        spec = item.get("spec") if isinstance(item.get("spec"), dict) else {}
        containers = spec.get("containers") if isinstance(spec.get("containers"), list) else []
        statuses = status.get("containerStatuses") if isinstance(status.get("containerStatuses"), list) else []
        ready = sum(1 for entry in statuses if isinstance(entry, dict) and entry.get("ready") is True)
        total = len(containers)
        restarts = sum(max(0, int(entry.get("restartCount", 0) or 0)) for entry in statuses if isinstance(entry, dict) and str(entry.get("restartCount", 0)).isdigit())
        phase = status.get("phase") if isinstance(status.get("phase"), str) else "Unknown"
        reason = None
        for entry in statuses:
            state = entry.get("state") if isinstance(entry, dict) and isinstance(entry.get("state"), dict) else {}
            for value in state.values():
                if isinstance(value, dict) and isinstance(value.get("reason"), str):
                    reason = value["reason"][:100]
                    break
            if reason:
                break
        pods.append({
            "name": str(meta.get("name", "unknown"))[:253],
            "namespace": str(meta.get("namespace", "default"))[:63],
            "status": reason or phase,
            "ready": f"{ready}/{total}",
            "restarts": restarts,
            "age": meta.get("creationTimestamp"),
            "kind": "system" if meta.get("namespace") == "kube-system" else "workload",
            "ownership": "unconfirmed",
        })
    return pods


def _selected_profile(config: dict[str, Any]) -> dict[str, Any]:
    profile = str(config["minikube_profile"])
    kubeconfig = Path(config["kubeconfig_path"])
    status = _command(["minikube", "-p", profile, "status", "--format={{.Host}}"], timeout=6)
    selected_status = "Running" if status and "running" in status.casefold() else "Unknown"
    node_raw = _command(["kubectl", "--kubeconfig", str(kubeconfig), "get", "nodes", "--chunk-size=100", "-o", "json"], timeout=8)
    nodes = []
    if node_raw:
        try:
            for item in _objects(json.loads(node_raw))[:50]:
                meta = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
                status_obj = item.get("status") if isinstance(item.get("status"), dict) else {}
                conditions = status_obj.get("conditions") if isinstance(status_obj.get("conditions"), list) else []
                ready = next((condition.get("status") == "True" for condition in conditions if isinstance(condition, dict) and condition.get("type") == "Ready"), None)
                addresses = status_obj.get("addresses") if isinstance(status_obj.get("addresses"), list) else []
                ip = next((item.get("address") for item in addresses if isinstance(item, dict) and item.get("type") == "InternalIP"), None)
                nodes.append({"name": str(meta.get("name", "unknown"))[:253], "status": "Ready" if ready is True else "NotReady" if ready is False else "Unknown", "ip": ip if isinstance(ip, str) else None})
        except ValueError:
            nodes = []
    version_raw = _command(["kubectl", "--kubeconfig", str(kubeconfig), "version", "-o", "json"], timeout=8)
    version = None
    if version_raw:
        try:
            version = json.loads(version_raw).get("serverVersion", {}).get("gitVersion")
        except (ValueError, AttributeError):
            pass
    return {
        "name": profile,
        "status": selected_status,
        "selected": True,
        "kubernetes": version if isinstance(version, str) else None,
        "driver": "docker",
        "nodes": nodes,
        "pods": _pods(kubeconfig),
    }


def _service_health(url: str, timeout: float = 2.0) -> bool | None:
    try:
        with urlopen(Request(url, headers={"Accept": "application/json"}), timeout=timeout) as response:
            return 200 <= response.status < 400
    except URLError:
        return False
    except (TimeoutError, OSError, ValueError):
        return False


def topology_snapshot() -> dict[str, Any]:
    try:
        config = load_lane_config(private_lab_config())
    except Exception:
        return {
            "sampled_at": _stamp(),
            "stale": False,
            "status": "unavailable",
            "reason": "The selected lane configuration could not be loaded.",
            "profiles": [],
            "selected_profile": None,
            "services": [],
        }
    selected = _selected_profile(config)
    profiles = [
        {"name": name, "status": selected["status"] if name == selected["name"] else "Unknown", "selected": name == selected["name"]}
        for name in _profile_names()
    ]
    if selected["name"] not in {item["name"] for item in profiles}:
        profiles.append({"name": selected["name"], "status": selected["status"], "selected": True})
    pg_name = str(config.get("pgvector_container", ""))
    pg_status = None
    if pg_name and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", pg_name):
        inspect = _command(["docker", "inspect", "--format={{json .}}", pg_name], timeout=3)
        if inspect:
            try:
                container = json.loads(inspect)
                labels = (container.get("Config") or {}).get("Labels") or {}
                running = bool((container.get("State") or {}).get("Running"))
                pg_status = running and labels.get(LANE_OWNER_LABEL) == config["lane_id"]
            except (ValueError, AttributeError, TypeError):
                pg_status = None
    services = [
        {"name": "RAG API", "detail": "Selected lane loopback service", "status": "Healthy" if _service_health(str(config["rag_api_url"]).rstrip("/") + "/healthz/") is True else "Unavailable", "uptime": None},
        {"name": "pgvector", "detail": "Selected lane database container", "status": "Healthy" if pg_status is True else "Unavailable" if pg_status is False else "Unknown", "uptime": None},
    ]
    ollama = _service_health("http://127.0.0.1:11434/api/tags")
    services.append({"name": "Ollama", "detail": "127.0.0.1:11434", "status": "Healthy" if ollama is True else "Unavailable", "uptime": None})
    unavailable = selected["pods"] is None and not selected["nodes"]
    return {
        "sampled_at": _stamp(),
        "stale": False,
        "status": "unavailable" if unavailable else "ok",
        "reason": "Selected lane topology could not be read." if unavailable else None,
        "profiles": profiles,
        "selected_profile": selected,
        "services": services,
    }
