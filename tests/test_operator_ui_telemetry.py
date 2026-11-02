from __future__ import annotations

import json
from pathlib import Path

from operator_ui import telemetry


def test_host_snapshot_keeps_unknown_metrics_null_and_inventory_shapes_stable(monkeypatch):
    monkeypatch.setattr(telemetry, "_cpu_rows", lambda: [{"id": "total", "percent": None}, {"id": "0", "percent": 12.5}])
    monkeypatch.setattr(telemetry, "_memory", lambda: None)
    monkeypatch.setattr(telemetry, "_disk", lambda: {"path": "/", "total_bytes": None, "used_bytes": None, "free_bytes": None, "free_gib": None, "percent": None})
    monkeypatch.setattr(telemetry, "_gpus", lambda: None)
    monkeypatch.setattr(telemetry, "_processes", lambda: None)

    sample = telemetry.host_snapshot()

    assert sample["cpu"] == {"total_pct": None, "per_core": [12.5]}
    assert sample["memory"]["total_bytes"] is None
    assert sample["disk"]["free_gib"] is None
    assert sample["gpus"] == []
    assert sample["processes"] == []
    assert sample["stale"] is False
    assert sample["status"] == "partial"
    assert sample["gpu_inventory_available"] is False
    assert sample["process_inventory_available"] is False


def test_topology_does_not_mark_a_foreign_pgvector_container_healthy(monkeypatch):
    monkeypatch.setattr(telemetry, "private_lab_config", lambda: Path("/private/lane.json"))
    monkeypatch.setattr(telemetry, "load_lane_config", lambda _path: {
        "lane_id": "owned-lane",
        "minikube_profile": "owned-profile",
        "kubeconfig_path": "/private/owned.kubeconfig",
        "pgvector_container": "owned-db",
        "rag_api_url": "http://127.0.0.1:18004",
    })
    monkeypatch.setattr(telemetry, "_selected_profile", lambda _config: {
        "name": "owned-profile", "status": "Running", "selected": True,
        "kubernetes": None, "driver": "docker", "nodes": [], "pods": None,
    })
    monkeypatch.setattr(telemetry, "_profile_names", lambda: ["owned-profile", "other-profile"])
    monkeypatch.setattr(telemetry, "_command", lambda argv, **_kwargs: json.dumps({
        "Config": {"Labels": {"io.kubellm.lane": "other-lane"}},
        "State": {"Running": True},
    }) if argv[:2] == ["docker", "inspect"] else None)
    monkeypatch.setattr(telemetry, "_service_health", lambda *_args, **_kwargs: None)

    snapshot = telemetry.topology_snapshot()

    assert snapshot["selected_profile"]["name"] == "owned-profile"
    assert snapshot["profiles"] == [
        {"name": "owned-profile", "status": "Running", "selected": True},
        {"name": "other-profile", "status": "Unknown", "selected": False},
    ]
    pgvector = next(item for item in snapshot["services"] if item["name"] == "pgvector")
    assert pgvector["status"] == "Unavailable"
