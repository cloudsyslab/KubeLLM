import os

import pytest

from orchestrator import lab_storage_hygiene as hygiene


def test_cache_manifest_enforces_fixed_cache_allowlist():
    with pytest.raises(hygiene.SafetyError, match="fixed allowlist"):
        hygiene.cache_manifest("../shared")


def test_cache_manifest_treats_missing_cache_as_already_clean(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(hygiene.Path, "home", classmethod(lambda cls: home))

    assert hygiene.cache_manifest(".cache/ms-playwright") is None


def test_cache_manifest_rejects_symlink(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    cache = home / ".cache" / "ms-playwright"
    cache.parent.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    cache.symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(hygiene.Path, "home", classmethod(lambda cls: home))

    with pytest.raises(hygiene.SafetyError, match="plain directory"):
        hygiene.cache_manifest(".cache/ms-playwright")


def test_cache_manifest_requires_current_user_ownership(tmp_path, monkeypatch):
    home = tmp_path / "home"
    cache = home / ".npm" / "_cacache"
    cache.mkdir(parents=True)
    (cache / "entry").write_text("cache")
    monkeypatch.setattr(hygiene.Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr(hygiene.os, "getuid", lambda: -1)

    with pytest.raises(hygiene.SafetyError, match="not owned"):
        hygiene.cache_manifest(".npm/_cacache")


def test_cache_manifest_fingerprints_content_shape(tmp_path, monkeypatch):
    home = tmp_path / "home"
    cache = home / ".cache" / "ms-playwright"
    cache.mkdir(parents=True)
    (cache / "entry").write_text("before")
    monkeypatch.setattr(hygiene.Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr(hygiene.os, "getuid", os.getuid)

    before = hygiene.cache_manifest(".cache/ms-playwright")
    (cache / "entry").write_text("after and longer")
    after = hygiene.cache_manifest(".cache/ms-playwright")

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
