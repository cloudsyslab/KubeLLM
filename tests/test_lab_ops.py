from __future__ import annotations

import hashlib
import json
import shlex
import stat
import subprocess
import zipfile
from types import SimpleNamespace
from pathlib import Path

from scripts import lab_ops
from scripts import lab_ops_backup
from scripts import install_lab_user_services


def test_cleanup_plan_only_allows_explicitly_owned_unreferenced_images():
    audit = {
        "docker": {
            "containers": [
                {"id": "stopped-owned", "name": "old-owned", "owner_lane": "minh", "running": False},
                {"id": "running-owned", "name": "live-owned", "owner_lane": "minh", "running": True},
            ],
            "images": [
                {"id": "owned-image", "tags": ["owned:old"], "size_bytes": 100, "owner_lane": "minh", "container_ids": []},
                {"id": "used-image", "tags": ["owned:live"], "size_bytes": 200, "owner_lane": "minh", "container_ids": ["running-owned"]},
                {"id": "unknown-image", "tags": ["<none>"], "size_bytes": 300, "owner_lane": None, "container_ids": []},
                {"id": "foreign-image", "tags": ["other:old"], "size_bytes": 400, "owner_lane": "other", "container_ids": []},
            ],
            "volumes": [
                {"name": "empty-owned-volume", "owner_lane": "minh", "container_ids": []},
            ],
        },
    }

    targets = lab_ops.lane_cleanup_targets(audit, "minh")
    by_id = {item["id"]: item for item in targets}

    assert by_id["owned-image"]["safe_to_apply"] is True
    assert by_id["stopped-owned"]["safe_to_apply"] is False
    assert "used-image" not in by_id
    assert by_id["unknown-image"]["safe_to_apply"] is False
    assert by_id["foreign-image"]["safe_to_apply"] is False
    assert by_id["empty-owned-volume"]["safe_to_apply"] is False


def test_apply_rechecks_owner_and_container_references(monkeypatch, tmp_path):
    plan = {
        "schema_version": 1,
        "created_at": lab_ops.dt.datetime.now(lab_ops.dt.timezone.utc).isoformat(),
        "lane_id": "minh",
        "host": lab_ops.socket.gethostname(),
        "targets": [{"kind": "unused_image", "id": "sha256:abc", "owner_lane": "minh", "size_bytes": 123, "safe_to_apply": True}],
    }
    plan["fingerprint"] = hashlib.sha256(
        json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan), encoding="utf-8")
    monkeypatch.setattr(lab_ops, "docker_inventory", lambda: {
        "images": [{"id": "sha256:abc", "owner_lane": "minh", "container_ids": [], "size_bytes": 123}],
        "containers": [], "volumes": [], "reported": {},
    })
    calls = []
    monkeypatch.setattr(lab_ops, "command", lambda argv, **kwargs: calls.append(argv) or lab_ops.subprocess.CompletedProcess(argv, 0, "removed", ""))

    lab_ops.apply_target(path, "sha256:abc", "minh", yes=True)

    assert calls == [["docker", "image", "rm", "--no-prune", "sha256:abc"]]


def test_apply_refuses_if_image_becomes_referenced(monkeypatch, tmp_path):
    plan = {
        "schema_version": 1,
        "created_at": lab_ops.dt.datetime.now(lab_ops.dt.timezone.utc).isoformat(),
        "lane_id": "minh",
        "host": lab_ops.socket.gethostname(),
        "targets": [{"kind": "unused_image", "id": "sha256:abc", "owner_lane": "minh", "size_bytes": 123, "safe_to_apply": True}],
    }
    plan["fingerprint"] = hashlib.sha256(
        json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan), encoding="utf-8")
    monkeypatch.setattr(lab_ops, "docker_inventory", lambda: {
        "images": [{"id": "sha256:abc", "owner_lane": "minh", "container_ids": ["container"], "size_bytes": 123}],
        "containers": [], "volumes": [], "reported": {},
    })
    monkeypatch.setattr(lab_ops, "command", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not remove")))

    try:
        lab_ops.apply_target(path, "sha256:abc", "minh", yes=True)
    except lab_ops.OpsError as exc:
        assert "changed since planning" in str(exc)
    else:
        raise AssertionError("apply accepted an image that became referenced")


def test_plan_writer_uses_owner_only_permissions(tmp_path):
    path = tmp_path / "private" / "cleanup.json"

    lab_ops.save_plan(path, {"lane_id": "minh"})

    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700


def test_backup_member_checksum_streams_archive_content(tmp_path):
    path = tmp_path / "snapshot.zip"
    content = b"selected lane evidence" * 100_000
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("evidence.bin", content)

    with zipfile.ZipFile(path, "r") as archive:
        digest = lab_ops_backup.archive_member_sha256(archive, "evidence.bin")

    assert digest == hashlib.sha256(content).hexdigest()


def test_restore_capacity_guard_targets_immutable_container_and_parses(monkeypatch):
    calls = []
    monkeypatch.setattr(
        lab_ops_backup,
        "run",
        lambda argv, **kwargs: calls.append(argv) or subprocess.CompletedProcess(argv, 0, b"", b""),
    )
    container_id = "a" * 64
    args = SimpleNamespace(ssh_key=Path("/private/key"), host="minh@lab")

    lab_ops_backup.remote_check_restore_capacity(args, container_id)

    command = shlex.split(calls[0][-1])
    assert command[:3] == ["docker", "exec", container_id]
    assert "size * 2 + 2147483648" in command[-1]
    syntax = subprocess.run(["sh", "-n", "-c", command[-1]], capture_output=True, check=False)
    assert syntax.returncode == 0


def test_backup_stream_program_and_systemd_units_keep_scope_explicit():
    compile(lab_ops_backup.REMOTE_SNAPSHOT, "remote_snapshot.py", "exec")
    compile(lab_ops_backup.REMOTE_IDLE_CHECK, "remote_idle_check.py", "exec")
    compile(lab_ops_backup.REMOTE_DATABASE_IDENTITY_CHECK, "database_identity_check.py", "exec")
    unit = install_lab_user_services.unit_text(
        "KubeLLM operator UI", Path("/home/minh/KubeLLM"), Path("/home/minh/KubeLLM/.venv/bin/python"),
        Path("/home/minh/.config/kubellm/lanes/minh.json"), Path("/home/minh/KubeLLM/.local/operator_ui"), rag=False,
    )

    assert "127.0.0.1" in unit
    assert "start_selected_lane_db.py" in unit
    assert "Minikube" not in unit
    assert "OPENAI_API_KEY" not in unit
