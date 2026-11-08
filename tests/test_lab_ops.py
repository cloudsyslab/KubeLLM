from __future__ import annotations

import hashlib
import json
import stat
import subprocess
import zipfile
from types import SimpleNamespace
from pathlib import Path

from scripts import lab_ops
from scripts import lab_ops_backup
from scripts import install_lab_user_services
from scripts import supervise_lab_user_services


def test_cleanup_plan_only_allows_explicitly_owned_unreferenced_images():
    audit = {
        "docker": {
            "inventory_complete": True,
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
        "containers": [], "volumes": [], "reported": {}, "inventory_complete": True,
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
        "containers": [], "volumes": [], "reported": {}, "inventory_complete": True,
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


def test_remote_snapshot_requires_exact_approved_default_profile_id():
    container_id = "a" * 64
    args = SimpleNamespace(
        selector="/home/minh/.config/kubellm/lanes/minh.json",
        state_dir="/home/minh/KubeLLM/.local/operator_ui",
        repo_dir="/home/minh/KubeLLM",
        ssh_key=Path("/private/key"),
        host="minh@lab",
        expected_default_minikube_container_id=container_id,
    )

    command = lab_ops_backup.remote_command(args)

    assert container_id in command[-1]
    assert "approved default profile identity, volume, or running state changed" in lab_ops_backup.REMOTE_SNAPSHOT


def test_backup_stream_program_and_systemd_units_keep_scope_explicit():
    compile(lab_ops_backup.REMOTE_SNAPSHOT, "remote_snapshot.py", "exec")
    compile(lab_ops_backup.REMOTE_IDLE_CHECK, "remote_idle_check.py", "exec")
    unit = install_lab_user_services.unit_text(
        "KubeLLM operator UI", Path("/home/minh/KubeLLM"), Path("/home/minh/KubeLLM/.venv/bin/python"),
        Path("/home/minh/.config/kubellm/lanes/minh.json"), Path("/home/minh/KubeLLM/.local/operator_ui"),
        rag=False, service_path="/home/minh/KubeLLM/.venv/bin:/usr/bin",
    )

    assert "127.0.0.1" in unit
    assert "start_selected_lane_db.py" in unit
    assert "Minikube" not in unit
    assert "OPENAI_API_KEY" not in unit
    assert "After=default.target" not in unit
    assert "Environment=PATH=" in unit
    assert "include_default_profile" in lab_ops_backup.REMOTE_IDLE_CHECK
    assert "--lab-config=" in lab_ops_backup.REMOTE_IDLE_CHECK


def test_docker_inspect_inventory_fails_closed_on_partial_results(monkeypatch):
    calls = []

    def command(argv, **_kwargs):
        calls.append(argv)
        if argv[:3] == ["docker", "image", "ls"]:
            return subprocess.CompletedProcess(argv, 0, '{"ID":"sha256:' + "a" * 64 + '"}\n', "")
        if argv[:2] == ["docker", "ps"]:
            return subprocess.CompletedProcess(argv, 0, "", "")
        if argv[:3] == ["docker", "volume", "ls"]:
            return subprocess.CompletedProcess(argv, 0, "", "")
        if argv[:3] == ["docker", "image", "inspect"]:
            return subprocess.CompletedProcess(argv, 0, "[]", "")
        raise AssertionError(argv)

    monkeypatch.setattr(lab_ops, "command", command)
    try:
        lab_ops.docker_inventory()
    except lab_ops.OpsError as exc:
        assert "incomplete" in str(exc)
    else:
        raise AssertionError("incomplete Docker details were accepted")


def test_cleanup_targets_reject_incomplete_inventory():
    try:
        lab_ops.lane_cleanup_targets({"docker": {"inventory_complete": False}}, "minh")
    except lab_ops.OpsError as exc:
        assert "incomplete" in str(exc)
    else:
        raise AssertionError("cleanup candidates were created from incomplete inventory")


def test_backup_parts_round_trip_without_download_filename_collision(tmp_path, monkeypatch):
    source = tmp_path / "snapshot.age"
    source.write_bytes(b"encrypted test payload")
    output = tmp_path / "parts"
    output.mkdir()
    monkeypatch.setattr(lab_ops_backup, "ASSET_PART_BYTES", 7)

    parts = lab_ops_backup.split_encrypted_asset(source, output, "backup")
    assert [part.stat().st_size for part in parts] == [7, 7, 7, 1]
    downloaded = tmp_path / "fresh-download-dir"
    downloaded.mkdir()
    copies = []
    for part in parts:
        copy = downloaded / part.name
        copy.write_bytes(part.read_bytes())
        copies.append(copy)
    assembled = tmp_path / "assembled.age"

    digest = lab_ops_backup.concatenate_assets(copies, assembled)

    assert digest == hashlib.sha256(source.read_bytes()).hexdigest()
    assert assembled.read_bytes() == source.read_bytes()


def test_local_restore_engine_requires_isolated_x86_linux(monkeypatch):
    args = SimpleNamespace(restore_docker_host="unix:///isolated/docker.sock")
    monkeypatch.setattr(lab_ops_backup, "local_docker", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, b"linux x86_64\n", b""))

    lab_ops_backup.require_isolated_restore_engine(args)

    monkeypatch.setattr(lab_ops_backup, "local_docker", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, b"linux aarch64\n", b""))
    try:
        lab_ops_backup.require_isolated_restore_engine(args)
    except lab_ops_backup.BackupError as exc:
        assert "x86_64" in str(exc)
    else:
        raise AssertionError("arm64 Docker engine was accepted for an x86_64 recovery test")


def test_cron_fallback_preserves_unrelated_entries_and_is_idempotent():
    existing = "MAILTO=minh@example.test\n@reboot /home/minh/other-job\n"
    entry = "@reboot sleep 30; /home/minh/KubeLLM/supervisor # KUBELLM_LAB_SELECTED_SERVICES"
    with_fallback = install_lab_user_services.update_crontab(existing, entry=entry)

    assert "@reboot /home/minh/other-job" in with_fallback
    assert with_fallback.count("KUBELLM_LAB_SELECTED_SERVICES") == 1
    assert install_lab_user_services.update_crontab(with_fallback, entry=entry) == with_fallback
    assert install_lab_user_services.update_crontab(with_fallback, entry=None) == existing


def test_cron_fallback_sets_resolved_path_for_docker_and_app_imports():
    entry = install_lab_user_services.cron_entry(
        Path("/home/minh/KubeLLM"), Path("/home/minh/.config/kubellm/lanes/minh.json"),
        Path("/home/minh/KubeLLM/.local/operator_ui"), Path("/home/minh/KubeLLM/.venv/bin/python"),
        "/home/minh/KubeLLM/.venv/bin:/usr/bin:/bin",
    )

    assert entry.startswith("@reboot sleep 30; PATH=/home/minh/KubeLLM/.venv/bin:/usr/bin:/bin ")
    assert "--service-path" in entry
    assert "KUBELLM_LAB_SELECTED_SERVICES" in entry


def test_cron_fallback_can_use_supervisor_outside_the_clean_checkout(tmp_path):
    repo = tmp_path / "KubeLLM"
    private_supervisor = tmp_path / ".local" / "lab-ops" / "supervise.py"
    private_supervisor.parent.mkdir(parents=True)
    private_supervisor.touch()

    entry = install_lab_user_services.cron_entry(
        repo, Path("/home/minh/.config/kubellm/lanes/minh.json"), Path("/home/minh/KubeLLM/.local/operator_ui"),
        Path("/home/minh/KubeLLM/.venv/bin/python"), "/usr/bin:/bin", private_supervisor,
    )

    assert str(private_supervisor) in entry
    assert str(repo / "scripts" / "supervise_lab_user_services.py") not in entry


def test_service_supervisor_child_runs_from_checkout_and_retries_failed_launch(monkeypatch, tmp_path):
    class Logger:
        def error(self, *_args):
            pass

    calls = []

    def popen(*_args, **kwargs):
        calls.append(kwargs)
        raise OSError("missing temporarily")

    monkeypatch.setattr(supervise_lab_user_services.subprocess, "Popen", popen)
    child = supervise_lab_user_services.start_child("ui", ["python", "-m", "uvicorn"], {}, Logger(), tmp_path)

    assert child is None
    assert calls[0]["cwd"] == tmp_path


def test_service_supervisor_converts_transient_command_errors_to_retryable_results(monkeypatch):
    monkeypatch.setattr(
        supervise_lab_user_services.subprocess, "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("missing temporarily")),
    )

    result = supervise_lab_user_services.command(["docker", "info"], {})

    assert result.returncode == 127


def test_service_supervisor_parses_listener_pid_and_fails_closed(monkeypatch):
    monkeypatch.setattr(
        supervise_lab_user_services.subprocess, "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0,
            'LISTEN 0 2048 127.0.0.1:8787 0.0.0.0:* users:(("python",pid=1234,fd=7))\n', ""),
    )

    assert supervise_lab_user_services.listening_pids(8787) == [1234]

    monkeypatch.setattr(
        supervise_lab_user_services.subprocess, "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("ss unavailable")),
    )
    assert supervise_lab_user_services.listening_pids(8787) is None

    monkeypatch.setattr(
        supervise_lab_user_services.subprocess, "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0,
            "LISTEN 0 2048 127.0.0.1:8787 0.0.0.0:*\n", ""),
    )
    assert supervise_lab_user_services.listening_pids(8787) is None
