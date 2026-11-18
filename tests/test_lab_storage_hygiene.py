import io
import os
import tarfile
import time

import pytest

from orchestrator import lab_storage_hygiene as hygiene


def test_rebuildable_path_manifest_enforces_fixed_cache_allowlist():
    with pytest.raises(hygiene.SafetyError, match="rebuildable allowlist"):
        hygiene.rebuildable_path_manifest("../shared")


def test_rebuildable_path_manifest_treats_missing_cache_as_already_clean(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(hygiene.Path, "home", classmethod(lambda cls: home))

    assert hygiene.rebuildable_path_manifest(".cache/ms-playwright") is None


def test_rebuildable_path_manifest_rejects_symlink(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    cache = home / ".cache" / "ms-playwright"
    cache.parent.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    cache.symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(hygiene.Path, "home", classmethod(lambda cls: home))

    with pytest.raises(hygiene.SafetyError, match="plain directory"):
        hygiene.rebuildable_path_manifest(".cache/ms-playwright")


def test_rebuildable_path_manifest_requires_current_user_ownership(tmp_path, monkeypatch):
    home = tmp_path / "home"
    cache = home / ".npm" / "_cacache"
    cache.mkdir(parents=True)
    (cache / "entry").write_text("cache")
    monkeypatch.setattr(hygiene.Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr(hygiene.os, "getuid", lambda: -1)

    with pytest.raises(hygiene.SafetyError, match="not owned"):
        hygiene.rebuildable_path_manifest(".npm/_cacache")


def test_rebuildable_path_manifest_fingerprints_content_shape(tmp_path, monkeypatch):
    home = tmp_path / "home"
    cache = home / ".cache" / "ms-playwright"
    cache.mkdir(parents=True)
    (cache / "entry").write_text("before")
    monkeypatch.setattr(hygiene.Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr(hygiene.os, "getuid", os.getuid)

    before = hygiene.rebuildable_path_manifest(".cache/ms-playwright")
    (cache / "entry").write_text("after and longer")
    after = hygiene.rebuildable_path_manifest(".cache/ms-playwright")

    assert before["fingerprint"] != after["fingerprint"]
    assert after["allocated_bytes"] >= before["allocated_bytes"]


def test_lane_config_is_fixed_to_approved_private_lane(tmp_path, monkeypatch):
    config = tmp_path / "lane.json"
    config.write_text(
        '{"lane_id":"other","minikube_profile":"minh-lane",'
        '"minikube_container":"minh-lane"}'
    )
    config.chmod(0o600)
    monkeypatch.setattr(hygiene, "LANE_CONFIG", config)

    with pytest.raises(hygiene.SafetyError, match="approved private lane"):
        hygiene.read_lane()


def test_open_file_check_blocks_any_reported_pid(monkeypatch):
    class Result:
        returncode = 0
        stdout = "1234\n"
    monkeypatch.setattr(hygiene.subprocess, "run", lambda *a, **k: Result())

    with pytest.raises(hygiene.SafetyError, match="open files"):
        hygiene.assert_no_open_files("/home/minh/.cache/ms-playwright")


def test_inner_docker_commands_are_scoped_to_private_node(monkeypatch):
    calls = []

    def fake_run(argv, *, timeout=60):
        calls.append(argv)
        if argv[4:7] == ["image", "ls", "--no-trunc"]:
            return "sha256:abc"
        if argv[4:7] == ["container", "ls", "--all"]:
            return ""
        if argv[4:7] == ["image", "inspect", "--format"]:
            return 'sha256:abc|100|["<none>:<none>"]'
        raise AssertionError(argv)

    monkeypatch.setattr(hygiene, "run", fake_run)
    found = hygiene.private_dangling_images("minh-lane")

    assert found == [{"id": "sha256:abc", "size_bytes": 100}]
    assert all(command[:3] == ["docker", "exec", "minh-lane"] for command in calls)


def test_rebuildable_case_tags_require_config_and_checked_in_dockerfile(tmp_path, monkeypatch):
    cases = tmp_path / "debug_assistant_latest" / "troubleshooting"
    with_dockerfile = cases / "fixture-case"
    without_dockerfile = cases / "missing-build"
    with_dockerfile.mkdir(parents=True)
    without_dockerfile.mkdir(parents=True)
    (with_dockerfile / "Dockerfile").write_text("FROM python:3.13-slim\n")
    (with_dockerfile / "config_step.json").write_text(
        '{"config":{"_lane_local_images":["fixture:latest","missing:latest"]}}'
    )
    (without_dockerfile / "config_step.json").write_text(
        '{"config":{"_lane_local_images":["no-dockerfile:latest"]}}'
    )
    monkeypatch.setattr(hygiene, "REPO_ROOT", tmp_path)

    assert hygiene.rebuildable_case_image_tags() == {
        "fixture:latest",
        "missing:latest",
    }


def test_rebuildable_private_images_exclude_container_pod_and_unknown_refs(monkeypatch):
    calls = []
    image_details = {
        "sha256:unused": (
            'sha256:unused|100|["fixture:latest"]|null'
        ),
        "sha256:container-used": (
            'sha256:container-used|200|["container-case:latest"]|null'
        ),
        "sha256:pod-used": (
            'sha256:pod-used|300|["pod-case:latest"]|null'
        ),
        "sha256:python": (
            'sha256:python|400|["python:3.13-slim"]|null'
        ),
    }

    def fake_run(argv, *, timeout=60):
        calls.append(argv)
        if argv[:3] == ["docker", "exec", "minh-lane"]:
            inner = argv[3:]
            if inner[:4] == ["docker", "image", "ls", "--no-trunc"]:
                return "\n".join(image_details)
            if inner[:4] == ["docker", "container", "ls", "--all"]:
                return "container-1"
            if inner[:2] == ["docker", "inspect"]:
                return "sha256:container-used"
            if inner[:4] == ["docker", "image", "inspect", "--format"]:
                return image_details[inner[-1]]
        if argv[:2] == ["kubectl", "--kubeconfig"]:
            return (
                '{"items":[{"spec":{"containers":[{"image":"pod-case:latest"}],'
                '"initContainers":[{"image":"init:latest"}]}}]}'
            )
        raise AssertionError(argv)

    monkeypatch.setattr(hygiene, "run", fake_run)
    monkeypatch.setattr(
        hygiene,
        "rebuildable_case_image_tags",
        lambda: {
            "fixture:latest",
            "container-case:latest",
            "pod-case:latest",
        },
    )

    found = hygiene.private_rebuildable_case_images(
        "minh-lane", "/home/minh/.config/kubellm/lanes/minh.kubeconfig"
    )

    assert found == [
        {
            "id": "sha256:unused",
            "repo_tags": ["fixture:latest"],
            "repo_digests": [],
            "size_bytes": 100,
        }
    ]
    assert all(
        argv[:3] == ["docker", "exec", "minh-lane"]
        for argv in calls
        if argv[0] == "docker"
    )
    kubectl = next(argv for argv in calls if argv[0] == "kubectl")
    assert kubectl[1:3] == [
        "--kubeconfig",
        "/home/minh/.config/kubellm/lanes/minh.kubeconfig",
    ]


def test_private_rebuildable_base_images_require_registry_digest(monkeypatch):
    image = {
        "id": "sha256:base",
        "repo_tags": ["python:3.11"],
        "repo_digests": ["python@sha256:abc"],
        "size_bytes": 100,
    }
    calls = []
    monkeypatch.setattr(
        hygiene,
        "private_allowlisted_images",
        lambda container, kubeconfig, tags: calls.append((container, kubeconfig, tags)) or [image],
    )

    assert hygiene.private_rebuildable_base_images("minh-lane", "/lane/kubeconfig") == [image]
    assert calls == [
        (
            "minh-lane",
            "/lane/kubeconfig",
            set(hygiene.PRIVATE_REBUILDABLE_BASE_IMAGE_TAGS),
        )
    ]

    monkeypatch.setattr(
        hygiene,
        "private_allowlisted_images",
        lambda *args: [{**image, "repo_digests": []}],
    )
    with pytest.raises(hygiene.SafetyError, match="registry digest"):
        hygiene.private_rebuildable_base_images("minh-lane", "/lane/kubeconfig")


def test_storage_report_distinguishes_campaign_and_profile_start_gates(tmp_path, monkeypatch):
    class Usage:
        total = 100_000_000_000
        used = 80_000_000_000
        free = 20_000_000_000

    monkeypatch.setattr(hygiene.shutil, "disk_usage", lambda _: Usage())
    monkeypatch.setattr(hygiene, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(hygiene, "run", lambda *args, **kwargs: str(tmp_path))
    monkeypatch.setattr(
        hygiene,
        "inventory",
        lambda: {
            "rebuildable_paths": [1, 2],
            "stale_temp_build_contexts": [],
            "private_dangling_images": [1],
            "private_rebuildable_case_images": [1, 2, 3],
            "private_rebuildable_base_images": [1],
        },
    )
    monkeypatch.setattr(
        hygiene,
        "_path_usage",
        lambda relative: {"relative_path": relative, "allocated_bytes": 42},
    )

    report = hygiene.build_storage_report()

    assert report["campaign_filesystem"]["campaign_startup_required_bytes"] == 20_000_000_000
    assert report["campaign_filesystem"]["campaign_startup_gate_met"] is True
    assert report["campaign_filesystem"]["campaign_before_attempt_required_bytes"] == 10_000_000_000
    assert report["campaign_filesystem"]["warning_threshold_bytes"] == 25 * 1024**3
    assert report["campaign_filesystem"]["warning"] is True
    assert report["docker_data_root"]["status"] == "available"
    assert report["docker_data_root"]["path"] == str(tmp_path)
    assert report["docker_data_root"]["profile_start_required_bytes"] == 20 * 1024**3
    assert report["docker_data_root"]["profile_start_gate_met"] is False
    assert report["stale_temp_build_contexts"] == {
        "status": "available",
        "count": 0,
        "allocated_bytes": 0,
    }
    assert report["private_lane_candidates"] == {
        "rebuildable_path_targets": 2,
        "dangling_images": 1,
        "rebuildable_case_images": 3,
        "rebuildable_base_images": 1,
    }


def test_write_private_json_uses_owner_only_atomic_file(tmp_path):
    destination = tmp_path / "state" / "report.json"

    hygiene.write_private_json(destination, {"status": "ok"})

    assert destination.read_text() == '{\n  "status": "ok"\n}\n'
    assert destination.stat().st_mode & 0o777 == 0o600
    assert list(destination.parent.glob("*.tmp")) == []
    assert list(destination.parent.glob(".*.tmp")) == []


def test_write_private_json_rejects_symlink_destination(tmp_path):
    outside = tmp_path / "outside.json"
    outside.write_text("keep")
    destination = tmp_path / "state" / "report.json"
    destination.parent.mkdir()
    destination.symlink_to(outside)

    with pytest.raises(hygiene.SafetyError, match="regular"):
        hygiene.write_private_json(destination, {"status": "bad"})

    assert outside.read_text() == "keep"


def test_rebuildable_path_manifest_allows_only_internal_owned_symlinks(tmp_path, monkeypatch):
    home = tmp_path / "home"
    target = home / ".codex" / "releases" / "old"
    target.mkdir(parents=True)
    binary = target / "bin"
    binary.mkdir()
    (binary / "codex").write_text("executable")
    (target / "codex").symlink_to("bin/codex")
    monkeypatch.setattr(hygiene.Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr(
        hygiene,
        "REBUILDABLE_RELATIVE_PATHS",
        (".codex/releases/old",),
    )

    manifest = hygiene.rebuildable_path_manifest(".codex/releases/old")

    assert manifest["file_count"] == 2
    assert manifest["fingerprint"]

    outside = tmp_path / "outside"
    outside.write_text("keep")
    (target / "escape").symlink_to(outside)
    with pytest.raises(hygiene.SafetyError, match="symlink escapes"):
        hygiene.rebuildable_path_manifest(".codex/releases/old")


def test_rebuildable_path_manifest_allows_one_exact_external_python_link(tmp_path, monkeypatch):
    home = tmp_path / "home"
    target = home / ".local" / "prediction_pilot" / "venv"
    (target / "bin").mkdir(parents=True)
    python_binary = tmp_path / "system-python"
    python_binary.write_text("python")
    link = target / "bin" / "python3"
    link.symlink_to(python_binary)
    relative = ".local/prediction_pilot/venv"
    monkeypatch.setattr(hygiene.Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr(hygiene, "REBUILDABLE_RELATIVE_PATHS", (relative,))
    monkeypatch.setattr(
        hygiene,
        "SAFE_EXTERNAL_SYMLINKS",
        {(relative, "bin/python3", str(python_binary))},
    )

    manifest = hygiene.rebuildable_path_manifest(relative)

    assert manifest["file_count"] == 1


def test_stale_temp_build_contexts_require_old_owned_closed_tar(tmp_path, monkeypatch):
    old_tar = tmp_path / "build.123.tar"
    with tarfile.open(old_tar, "w") as archive:
        payload = b"FROM alpine\n"
        member = tarfile.TarInfo("Dockerfile")
        member.size = len(payload)
        archive.addfile(member, io.BytesIO(payload))
    old_time = time.time() - 31 * 24 * 60 * 60
    os.utime(old_tar, (old_time, old_time))

    recent_tar = tmp_path / "build.456.tar"
    with tarfile.open(recent_tar, "w") as archive:
        payload = b"FROM alpine\n"
        member = tarfile.TarInfo("Dockerfile")
        member.size = len(payload)
        archive.addfile(member, io.BytesIO(payload))

    monkeypatch.setattr(hygiene, "TEMP_BUILD_CONTEXT_DIR", tmp_path)
    monkeypatch.setattr(hygiene, "TEMP_BUILD_CONTEXT_MIN_AGE_SECONDS", 30 * 24 * 60 * 60)
    monkeypatch.setattr(hygiene, "assert_no_open_file", lambda path: None)

    targets = hygiene.stale_temp_build_contexts()

    assert [target["path"] for target in targets] == [str(old_tar)]
    assert targets[0]["allocated_bytes"] > 0
    assert targets[0]["fingerprint"]


def test_stale_temp_build_contexts_block_open_old_tar(tmp_path, monkeypatch):
    path = tmp_path / "build.789.tar"
    with tarfile.open(path, "w") as archive:
        payload = b"FROM alpine\n"
        member = tarfile.TarInfo("Dockerfile")
        member.size = len(payload)
        archive.addfile(member, io.BytesIO(payload))
    old_time = time.time() - 31 * 24 * 60 * 60
    os.utime(path, (old_time, old_time))
    monkeypatch.setattr(hygiene, "TEMP_BUILD_CONTEXT_DIR", tmp_path)

    def block_open_file(candidate):
        raise hygiene.SafetyError("temporary build context has open handles")

    monkeypatch.setattr(hygiene, "assert_no_open_file", block_open_file)

    with pytest.raises(hygiene.SafetyError, match="open handles"):
        hygiene.stale_temp_build_contexts()
