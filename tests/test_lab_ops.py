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
from scripts import lab_ops_github
from scripts import lab_ops_native_remote
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


def test_recompress_archive_preserves_members_and_deflates_data(tmp_path):
    source = tmp_path / "stored.zip"
    compressed = tmp_path / "compressed.zip"
    payload = (b"kubellm-lab-snapshot-data\n" * 250_000)
    with zipfile.ZipFile(source, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("manifest.json", b'{"schema_version":1}\n')
        archive.writestr("legacy/minikube/var-volume.tar", payload)

    compressed_size = lab_ops_backup.recompress_archive(source, compressed)

    with zipfile.ZipFile(compressed, "r") as archive:
        assert archive.testzip() is None
        assert archive.read("manifest.json") == b'{"schema_version":1}\n'
        assert archive.read("legacy/minikube/var-volume.tar") == payload
        assert all(item.compress_type == zipfile.ZIP_DEFLATED for item in archive.infolist())
    assert compressed_size < source.stat().st_size // 10


def test_release_part_upload_is_individually_resumable(monkeypatch, tmp_path):
    part = tmp_path / "snapshot-part-001.age"
    part.write_bytes(b"ciphertext-part")
    release_assets = []
    calls = []

    def fake_run(argv, **_kwargs):
        calls.append(argv)
        if argv[:3] == ["gh", "release", "view"]:
            payload = {"tagName": "lab-backup-20261108T000000Z", "isDraft": True,
                       "assets": release_assets.copy()}
            return subprocess.CompletedProcess(argv, 0, json.dumps(payload).encode(), b"")
        if argv[:3] == ["gh", "release", "upload"]:
            uploaded = Path(argv[4])
            release_assets.append({"name": uploaded.name, "size": uploaded.stat().st_size})
            return subprocess.CompletedProcess(argv, 0, b"", b"")
        if argv[:3] == ["gh", "release", "download"]:
            name = argv[argv.index("--pattern") + 1]
            destination = Path(argv[argv.index("--dir") + 1]) / name
            destination.write_bytes(part.read_bytes())
            return subprocess.CompletedProcess(argv, 0, b"", b"")
        raise AssertionError(argv)

    monkeypatch.setattr(lab_ops_backup, "run", fake_run)
    lab_ops_backup.upload_release_parts("owner/repo", "lab-backup-20261108T000000Z", [part], tmp_path)
    lab_ops_backup.upload_release_parts("owner/repo", "lab-backup-20261108T000000Z", [part], tmp_path)

    assert sum(call[:3] == ["gh", "release", "upload"] for call in calls) == 1
    assert len(release_assets) == 1


def test_release_part_upload_refuses_unexpected_existing_assets(monkeypatch, tmp_path):
    part = tmp_path / "snapshot-part-001.age"
    part.write_bytes(b"ciphertext-part")
    payload = {"tagName": "lab-backup-20261108T000000Z", "isDraft": True,
               "assets": [{"name": "other.age", "size": 1}]}
    monkeypatch.setattr(lab_ops_backup, "run", lambda argv, **_kwargs: subprocess.CompletedProcess(
        argv, 0, json.dumps(payload).encode(), b""))

    try:
        lab_ops_backup.upload_release_parts("owner/repo", "lab-backup-20261108T000000Z", [part], tmp_path)
    except lab_ops_backup.BackupError as exc:
        assert "unexpected assets" in str(exc)
    else:
        raise AssertionError("unexpected draft assets must not be replaced")


def test_lab_github_asset_manifest_and_download_verify_order_and_hashes(monkeypatch, tmp_path):
    source = tmp_path / "ciphertext.age"
    source.write_bytes(b"the encrypted snapshot")
    tag = "lab-backup-20261108T000000Z"
    chunks = lab_ops_github.chunk_manifest(source, tag, chunk_bytes=7)
    assets = []
    pieces = {}
    with source.open("rb") as stream:
        for chunk in chunks:
            stream.seek(chunk["offset"])
            piece = stream.read(chunk["size"])
            pieces[chunk["name"]] = piece
            assets.append({"id": len(assets) + 1, "name": chunk["name"], "size": len(piece),
                           "digest": "sha256:" + hashlib.sha256(piece).hexdigest()})
    release = {"assets": assets}

    class FakeResponse:
        status = 200

        def __init__(self, payload):
            self.payload = payload
            self.url = "https://api.github.com/download"

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, size=-1):
            if size < 0:
                value, self.payload = self.payload, b""
                return value
            value, self.payload = self.payload[:size], self.payload[size:]
            return value

        def geturl(self):
            return self.url

    def fake_urlopen(request, timeout):
        assert timeout == 120
        asset_id = int(request.full_url.rsplit("/", 1)[1])
        return FakeResponse(pieces[chunks[asset_id - 1]["name"]])

    monkeypatch.setattr(lab_ops_github, "urlopen", fake_urlopen)
    restored = tmp_path / "restore" / "snapshot.age"
    lab_ops_github.download_assets("owner", "private-backups", release, chunks, restored, "scoped-token")

    assert restored.read_bytes() == source.read_bytes()


def test_lab_github_token_must_be_owner_only_and_release_tag_is_scoped(tmp_path):
    token = tmp_path / "token"
    token.write_text("github_pat_test-token\n", encoding="ascii")
    token.chmod(0o600)
    assert lab_ops_github.read_scoped_token(token) == "github_pat_test-token"
    token.chmod(0o640)
    try:
        lab_ops_github.read_scoped_token(token)
    except lab_ops_github.GitHubReleaseError as exc:
        assert "owner-only" in str(exc)
    else:
        raise AssertionError("group-readable GitHub token files must be rejected")
    assert lab_ops_github.release_endpoint("owner", "repo", "lab-backup-20261108T000000Z").endswith(
        "/releases/tags/lab-backup-20261108T000000Z")
    try:
        lab_ops_github.release_endpoint("owner", "repo", "latest")
    except lab_ops_github.GitHubReleaseError:
        pass
    else:
        raise AssertionError("release API paths must only accept lab-backup timestamp tags")


def test_lab_github_upload_url_template_is_removed_before_querying_asset_name():
    host, path = lab_ops_github._asset_upload_path(
        "https://uploads.github.com/repos/owner/repo/releases/1/assets{?name,label}",
        "backup-part-001.age",
    )

    assert host == "uploads.github.com"
    assert path == "/repos/owner/repo/releases/1/assets?name=backup-part-001.age"


def test_lab_github_upload_recovers_lost_success_only_for_matching_asset(monkeypatch, tmp_path):
    source = tmp_path / "snapshot.age"
    source.write_bytes(b"encrypted bytes")
    tag = "lab-backup-20261108T000000Z"
    chunks = lab_ops_github.chunk_manifest(source, tag)
    chunk = chunks[0]
    exact_asset = {"id": 1, "name": chunk["name"], "size": chunk["size"],
                   "digest": "sha256:" + chunk["digest"]}
    release = {"tag_name": tag, "upload_url": "https://uploads.github.com/repos/owner/repo/releases/1/assets{?name,label}",
               "assets": []}
    calls = []

    def fail_after_server_acceptance(*_args, **_kwargs):
        raise lab_ops_github.GitHubReleaseError("GitHub rejected encrypted asset upload (HTTP 422).")

    def refreshed(*_args, **_kwargs):
        calls.append("refresh")
        return 200, {"assets": [exact_asset], "tag_name": tag}

    monkeypatch.setattr(lab_ops_github, "_post_asset_stream", fail_after_server_acceptance)
    monkeypatch.setattr(lab_ops_github, "api_json", refreshed)

    result = lab_ops_github.upload_missing_chunks("owner", "repo", release, chunks, source, "github_pat_test")

    assert result == [exact_asset]
    assert calls == ["refresh"]


def test_lab_native_qemu_is_egress_restricted_and_loopback_only(tmp_path):
    vm = lab_ops_native_remote.RestoreVM(tmp_path)
    argv = vm.argv(None, restricted=True)
    network = next(value for value in argv if value.startswith("user,id="))

    assert "restrict=on" in network
    assert "hostfwd=tcp:127.0.0.1:" in network
    assert "hostfwd=tcp:0.0.0.0:" not in network
    assert argv[argv.index("-m") + 1] == str(32 * 1024)
    assert "-accel" in argv and "tcg,thread=multi" in argv


def test_lab_native_preflight_requires_kubectl(monkeypatch):
    monkeypatch.setattr(lab_ops_native_remote.shutil, "which",
                        lambda executable: None if executable == "kubectl" else "/usr/bin/" + executable)

    try:
        lab_ops_native_remote.check_tools()
    except lab_ops_native_remote.JobError as exc:
        assert "kubectl" in str(exc)
    else:
        raise AssertionError("snapshot and retirement commands require kubectl")


def test_lab_native_docker_readiness_retries_slow_daemon(monkeypatch, tmp_path):
    vm = lab_ops_native_remote.RestoreVM(tmp_path)
    calls = []

    def docker(_argv, **_kwargs):
        calls.append("probe")
        if len(calls) == 1:
            raise lab_ops_native_remote.JobError("docker did not complete (TimeoutExpired).")
        return SimpleNamespace(returncode=0, stdout=b"linux x86_64")

    monkeypatch.setattr(vm, "docker", docker)
    monkeypatch.setattr(vm, "pid", lambda: 1)
    monkeypatch.setattr(lab_ops_native_remote.Path, "exists", lambda _path: True)
    monkeypatch.setattr(lab_ops_native_remote, "assert_capacity", lambda _work: None)
    monkeypatch.setattr(lab_ops_native_remote.time, "sleep", lambda _seconds: None)

    vm.wait_for_docker()

    assert calls == ["probe", "probe"]


def test_lab_native_bootstrap_grants_docker_access_after_install(monkeypatch, tmp_path):
    def make_iso(argv, **_kwargs):
        Path(argv[argv.index("-output") + 1]).touch()
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(lab_ops_native_remote, "run", make_iso)

    seed = lab_ops_native_remote.create_seed(tmp_path, "ssh-ed25519 AAAA test", "bootstrap")
    user_data = (tmp_path / "seed-bootstrap" / "user-data").read_text(encoding="utf-8")

    assert seed.is_file()
    assert "packages:\n  - docker.io\n" in user_data
    assert "runcmd:\n  - [usermod, -aG, docker, ubuntu]\n" in user_data


def test_lab_native_pinned_pull_requires_the_exact_registry_digest():
    assert lab_ops_native_remote.verify_pulled_digest(
        json.dumps([lab_ops_native_remote.IMAGE_DIGEST])) == lab_ops_native_remote.IMAGE_DIGEST

    try:
        lab_ops_native_remote.verify_pulled_digest(json.dumps(["ghcr.io/openclaw/openclaw@sha256:" + "0" * 64]))
    except lab_ops_native_remote.JobError as exc:
        assert "exact pinned OpenClaw registry digest" in str(exc)
    else:
        raise AssertionError("the digest-pinned pull must retain the exact reviewed registry digest")


def test_lab_native_backup_archive_checks_manifest_members(tmp_path):
    archive_path = tmp_path / "snapshot.zip"
    selector = b'{"lane_id":"minh"}\n'
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("lane/selector.json", selector)
        archive.writestr("manifest.json", json.dumps({
            "schema_version": 1,
            "lane_id": "minh",
            "legacy_minikube": {"container_id": "a" * 64},
            "contents": [{"path": "lane/selector.json", "sha256": hashlib.sha256(selector).hexdigest()}],
        }))

    manifest, count = lab_ops_native_remote.verify_archive(archive_path, "minh")

    assert manifest["lane_id"] == "minh"
    assert count == 2
    try:
        lab_ops_native_remote.verify_archive(archive_path, "other-lane")
    except lab_ops_native_remote.JobError as exc:
        assert "selected lane" in str(exc) or "selected lane and approved" in str(exc)
    else:
        raise AssertionError("a different lane ID must not pass archive verification")


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
    assert "modules_mount = next((mount for mount in mounts" in lab_ops_backup.REMOTE_SNAPSHOT
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


def test_default_minikube_restore_accepts_only_reviewed_dynamic_loopback_ports():
    valid = {port: [{"HostIp": "127.0.0.1", "HostPort": ""}]
             for port in lab_ops_backup.DEFAULT_MINIKUBE_LOOPBACK_PORTS}

    assert lab_ops_backup.has_reviewed_dynamic_loopback_ports(valid)
    public = {**valid, "8443/tcp": [{"HostIp": "0.0.0.0", "HostPort": ""}]}
    assert not lab_ops_backup.has_reviewed_dynamic_loopback_ports(public)
    fixed_port = {**valid, "8443/tcp": [{"HostIp": "127.0.0.1", "HostPort": "8443"}]}
    assert not lab_ops_backup.has_reviewed_dynamic_loopback_ports(fixed_port)
    assert not lab_ops_backup.has_reviewed_dynamic_loopback_ports({"8443/tcp": valid["8443/tcp"]})


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
