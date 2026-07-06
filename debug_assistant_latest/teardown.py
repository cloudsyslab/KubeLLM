import os
import shutil
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TROUBLESHOOTING_DIR = SCRIPT_DIR / "troubleshooting"

if not TROUBLESHOOTING_DIR.exists():
    raise FileNotFoundError(
        f"Troubleshooting directory not found: {TROUBLESHOOTING_DIR}\n"
        f"Expected structure: <repo-root>/debug_assistant_latest/troubleshooting/"
    )


TEARDOWN_CONFIG = {
    "correct_app": {
        "docker_images": [],
        "restore_files": [],
        "k8s_manifests": ["correct_app.yaml", "app_service.yaml"],
    },
    "no_pod_ip": {
        "docker_images": [],
        "restore_files": [],
        "k8s_manifests": ["correct_app.yaml", "app_service.yaml"],
    },
    "wrong_interface": {
        "docker_images": ["kube-wrong-interface-app"],
        "restore_files": ["yaml", "server.py", "Dockerfile", "app_service.yaml"],
        "k8s_manifests": ["{name}.yaml", "app_service.yaml"],
    },
    "wrong_interface_bind_address": {
        "docker_images": ["kube-wrong-interface-bind-address-app"],
        "restore_files": ["yaml", "server.py", "Dockerfile", "app_service.yaml"],
        "k8s_manifests": ["{name}.yaml", "app_service.yaml"],
    },
    "wrong_interface_env_host": {
        "docker_images": ["kube-wrong-interface-env-host-app"],
        "restore_files": ["yaml", "server.py", "Dockerfile", "app_service.yaml"],
        "k8s_manifests": ["{name}.yaml", "app_service.yaml"],
    },
    "wrong_interface_container_args": {
        "docker_images": ["kube-wrong-interface-container-args-app"],
        "restore_files": ["yaml", "server.py", "Dockerfile", "app_service.yaml"],
        "k8s_manifests": ["{name}.yaml", "app_service.yaml"],
    },
    "wrong_port": {
        "docker_images": ["kube-wrong-port-app", "marioutsa/kube-wrong-port-app"],
        "restore_files": ["yaml", "server.py", "Dockerfile"],
        "k8s_manifests": ["{name}.yaml"],
    },
    "wrong_port_9090": {
        "docker_images": ["kube-wrong-port-9090-app"],
        "restore_files": ["yaml", "server.py", "Dockerfile"],
        "k8s_manifests": ["{name}.yaml"],
    },
    "wrong_port_5000": {
        "docker_images": ["kube-wrong-port-5000-app"],
        "restore_files": ["yaml", "server.py", "Dockerfile"],
        "k8s_manifests": ["{name}.yaml"],
    },
    "wrong_port_7001": {
        "docker_images": ["kube-wrong-port-7001-app"],
        "restore_files": ["yaml", "server.py", "Dockerfile"],
        "k8s_manifests": ["{name}.yaml"],
    },
    "readiness_failure": {
        "docker_images": [],
        "restore_files": ["yaml"],
        "k8s_manifests": ["{name}.yaml"],
    },
    "liveness_probe": {
        "docker_images": [],
        "restore_files": ["yaml", "server.py", "Dockerfile"],
        "k8s_manifests": ["{name}.yaml"],
    },
    "missing_dependency": {
        "docker_images": [],
        "restore_files": ["yaml", "server.py", "Dockerfile"],
        "k8s_manifests": ["{name}.yaml"],
    },
    "port_mismatch": {
        "docker_images": ["kube-port-mismatch-app"],
        "restore_files": ["yaml", "server.py", "Dockerfile", "app_service.yaml"],
        "k8s_manifests": ["{name}.yaml", "app_service.yaml"],
    },
    "incorrect_selector": {
        "docker_images": ["kube-incorrect-selector-app"],
        "restore_files": ["yaml", "server.py", "Dockerfile", "app_service.yaml"],
        "k8s_manifests": ["{name}.yaml", "app_service.yaml"],
    },
    "environment_variable": {
        "docker_images": ["kube-env-missing-app"],
        "restore_files": ["yaml", "server.py", "Dockerfile"],
        "k8s_manifests": ["{name}.yaml"],
    },
    "environment_variable_wrong_name": {
        "docker_images": ["kube-env-wrong-name-app"],
        "restore_files": ["yaml", "server.py", "Dockerfile"],
        "k8s_manifests": ["{name}.yaml"],
    },
    "port_mismatch_wrong_interface": {
        "docker_images": ["kube-port-mismatch-wrong-interface-app"],
        "restore_files": ["yaml", "server.py", "Dockerfile", "app_service.yaml"],
        "k8s_manifests": ["{name}.yaml", "app_service.yaml"],
    },
    "readiness_missing_dependency": {
        "docker_images": ["kube-readiness-missing-dependency-app"],
        "restore_files": ["yaml", "server.py", "Dockerfile"],
        "k8s_manifests": ["{name}.yaml"],
    },
    "readiness_missing_dependency_transitive": {
        "docker_images": ["kube-readiness-transitive-dependency-app"],
        "restore_files": ["yaml", "server.py", "Dockerfile", "helper_config.py"],
        "k8s_manifests": ["{name}.yaml"],
    },
    "selector_env_variable": {
        "docker_images": ["kube-selector-env-app"],
        "restore_files": ["yaml", "server.py", "Dockerfile", "app_service.yaml"],
        "k8s_manifests": ["{name}.yaml", "app_service.yaml"],
    },
    "selector_env_variable_label_and_secret": {
        "docker_images": ["kube-selector-env-secret-app"],
        "restore_files": ["yaml", "server.py", "Dockerfile", "app_service.yaml"],
        "k8s_manifests": ["{name}.yaml", "app_service.yaml"],
    },
    "resource_limits_oom": {
        "docker_images": ["kube-resource-limits-oom-app"],
        "restore_files": ["yaml", "server.py", "Dockerfile"],
        "k8s_manifests": ["{name}.yaml"],
    },
    "resource_limits_cpu_starvation": {
        "docker_images": ["kube-resource-limits-cpu-starvation-app"],
        "restore_files": ["yaml", "server.py", "Dockerfile"],
        "k8s_manifests": ["{name}.yaml"],
    },
    "volume_mount": {
        "docker_images": ["marioutsa/kube-volume-mount-app"],
        "restore_files": ["yaml", "server.py", "Dockerfile"],
        "k8s_manifests": ["{name}.yaml"],
    },
    "incorrect_selector_missing_label": {
        "docker_images": ["kube-selector-missing-label-app"],
        "restore_files": ["yaml", "server.py", "Dockerfile", "app_service.yaml"],
        "k8s_manifests": ["{name}.yaml", "app_service.yaml"],
    },
    "liveness_probe_wrong_path": {
        "docker_images": ["kube-liveness-wrong-path-app"],
        "restore_files": ["yaml", "server.py", "Dockerfile"],
        "k8s_manifests": ["{name}.yaml"],
    },
    "missing_dependency_requirements": {
        "docker_images": ["kube-missing-dependency-requirements-app"],
        "restore_files": ["yaml", "server.py", "Dockerfile", "requirements.txt"],
        "k8s_manifests": ["{name}.yaml"],
    },
    "port_mismatch_named_target": {
        "docker_images": ["kube-port-mismatch-named-target-app"],
        "restore_files": ["yaml", "server.py", "Dockerfile", "app_service.yaml"],
        "k8s_manifests": ["{name}.yaml", "app_service.yaml"],
    },
    "readiness_failure_slow_start": {
        "docker_images": ["kube-readiness-slow-start-app"],
        "restore_files": ["yaml", "server.py", "Dockerfile"],
        "k8s_manifests": ["{name}.yaml"],
    },
}


TRANSIENT_K8S_RESOURCES = [
    ("pod", "curl-test"),
    ("service", "curl-test"),
    ("pod", "curl-check"),
    ("service", "curl-check"),
    ("pod", "curlcheck"),
    ("service", "curlcheck"),
]


def list_teardown_tests():
    return list(TEARDOWN_CONFIG.keys())


def _get_test_dir(test_env_name: str) -> Path:
    return TROUBLESHOOTING_DIR / test_env_name


def _resolve_restore_paths(test_dir: Path, test_env_name: str, file_type: str):
    if file_type == "yaml":
        return test_dir / f"{test_env_name}.yaml", test_dir / "backup_yaml.yaml"
    if file_type == "app_service.yaml":
        return test_dir / "app_service.yaml", test_dir / "backup_app_service.yaml"
    if file_type == "server.py":
        return test_dir / "server.py", test_dir / "backup_server.py"
    if file_type == "Dockerfile":
        return test_dir / "Dockerfile", test_dir / "backup_Dockerfile"
    return test_dir / file_type, test_dir / f"backup_{file_type.replace('.', '_')}"


def _fixture_tree_dirty_paths() -> list[str]:
    repo_root = TROUBLESHOOTING_DIR.parent.parent
    try:
        fixture_path = TROUBLESHOOTING_DIR.relative_to(repo_root)
    except ValueError:
        fixture_path = TROUBLESHOOTING_DIR

    try:
        result = subprocess.run(
            [
                "git",
                "status",
                "--porcelain",
                "--untracked-files=no",
                "--",
                str(fixture_path),
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return []

    if result.returncode != 0:
        # Non-git test roots should not make teardown helpers unusable.
        return []

    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def assert_fixture_tree_clean() -> None:
    dirty_paths = _fixture_tree_dirty_paths()
    if not dirty_paths:
        return

    sample = "\n".join(f"  {path}" for path in dirty_paths[:20])
    extra = "" if len(dirty_paths) <= 20 else f"\n  ... and {len(dirty_paths) - 20} more"
    raise RuntimeError(
        "Fixture tree is not clean; aborting before backup to avoid preserving corrupted files.\n"
        "Clean or inspect these changes first:\n"
        f"{sample}{extra}"
    )


def backup_environment(test_env_name: str) -> None:
    config = TEARDOWN_CONFIG.get(test_env_name)
    if not config:
        return

    assert_fixture_tree_clean()

    test_dir = _get_test_dir(test_env_name)
    for file_type in config["restore_files"]:
        src, backup = _resolve_restore_paths(test_dir, test_env_name, file_type)
        if src.exists():
            shutil.copyfile(src, backup)


def cleanup_transient_k8s_resources(namespace: str = "default") -> None:
    """Remove helper resources that agents may create while probing services."""
    for kind, name in TRANSIENT_K8S_RESOURCES:
        subprocess.run(
            ["kubectl", "delete", kind, name, "-n", namespace, "--ignore-not-found=true"],
            check=False,
        )


def teardown_environment(test_env_name: str) -> None:
    config = TEARDOWN_CONFIG.get(test_env_name)
    if not config:
        raise ValueError(f"Unknown test case: {test_env_name}")

    test_dir = _get_test_dir(test_env_name)

    cleanup_transient_k8s_resources()

    for image in config["docker_images"]:
        # Get container IDs (cross-platform, no pipe/xargs)
        result = subprocess.run(
            ["docker", "ps", "-a", "-q", "--filter", f"ancestor={image}"],
            capture_output=True,
            text=True,
        )
        for cid in result.stdout.strip().split('\n'):
            if cid:
                subprocess.run(["docker", "rm", "-f", cid], check=False)
        # Remove image
        subprocess.run(["docker", "rmi", "-f", image], check=False)

    for file_type in config["restore_files"]:
        dst, backup = _resolve_restore_paths(test_dir, test_env_name, file_type)
        if dst.exists():
            os.remove(dst)
        if backup.exists():
            shutil.copyfile(backup, dst)

    for manifest in config["k8s_manifests"]:
        manifest_path = TROUBLESHOOTING_DIR / test_env_name / manifest.format(name=test_env_name)
        subprocess.run(
            ["kubectl", "delete", "-f", str(manifest_path), "--grace-period=5", "--ignore-not-found=true"],
            check=False,
        )


# Backward-compatible aliases while callers migrate.
backupEnviornment = backup_environment
tearDownEnviornment = teardown_environment
