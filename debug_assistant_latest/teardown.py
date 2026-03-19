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
    "wrong_port": {
        "docker_images": ["kube-wrong-port-app", "marioutsa/kube-wrong-port-app"],
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
    "selector_env_variable": {
        "docker_images": ["kube-selector-env-app"],
        "restore_files": ["yaml", "server.py", "Dockerfile", "app_service.yaml"],
        "k8s_manifests": ["{name}.yaml", "app_service.yaml"],
    },
    "resource_limits_oom": {
        "docker_images": ["kube-resource-limits-oom-app"],
        "restore_files": ["yaml", "server.py", "Dockerfile"],
        "k8s_manifests": ["{name}.yaml"],
    },
    "volume_mount": {
        "docker_images": ["marioutsa/kube-volume-mount-app"],
        "restore_files": ["yaml", "server.py", "Dockerfile"],
        "k8s_manifests": ["{name}.yaml"],
    },
}


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


def backup_environment(test_env_name: str) -> None:
    config = TEARDOWN_CONFIG.get(test_env_name)
    if not config:
        return

    test_dir = _get_test_dir(test_env_name)
    for file_type in config["restore_files"]:
        src, backup = _resolve_restore_paths(test_dir, test_env_name, file_type)
        if src.exists():
            shutil.copyfile(src, backup)


def teardown_environment(test_env_name: str) -> None:
    config = TEARDOWN_CONFIG.get(test_env_name)
    if not config:
        raise ValueError(f"Unknown test case: {test_env_name}")

    test_dir = _get_test_dir(test_env_name)

    for image in config["docker_images"]:
        subprocess.run(
            f"docker ps -a -q --filter ancestor={image} | xargs -r docker rm -f",
            shell=True,
            check=False,
        )
        subprocess.run(f"docker rmi -f {image}", shell=True, check=False)

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
