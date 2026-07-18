import re
import shutil
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TROUBLESHOOTING_DIR = SCRIPT_DIR / "troubleshooting"
FIXTURE_BASELINES_DIR = SCRIPT_DIR / "fixture_baselines"

if not TROUBLESHOOTING_DIR.exists():
    raise FileNotFoundError(
        f"Troubleshooting directory not found: {TROUBLESHOOTING_DIR}\n"
        f"Expected structure: <repo-root>/debug_assistant_latest/troubleshooting/"
    )


TEARDOWN_CONFIG = {
    "correct_app": {
        "docker_images": [],
        "k8s_manifests": ["correct_app.yaml", "app_service.yaml"],
    },
    "no_pod_ip": {
        "docker_images": [],
        "k8s_manifests": ["correct_app.yaml", "app_service.yaml"],
    },
    "wrong_interface": {
        "docker_images": ["kube-wrong-interface-app"],
        "k8s_manifests": ["{name}.yaml", "app_service.yaml"],
    },
    "wrong_interface_bind_address": {
        "docker_images": ["kube-wrong-interface-bind-address-app"],
        "k8s_manifests": ["{name}.yaml", "app_service.yaml"],
    },
    "wrong_interface_env_host": {
        "docker_images": ["kube-wrong-interface-env-host-app"],
        "k8s_manifests": ["{name}.yaml", "app_service.yaml"],
    },
    "wrong_interface_container_args": {
        "docker_images": ["kube-wrong-interface-container-args-app"],
        "k8s_manifests": ["{name}.yaml", "app_service.yaml"],
    },
    "wrong_port": {
        "docker_images": ["kube-wrong-port-app", "marioutsa/kube-wrong-port-app"],
        "k8s_manifests": ["{name}.yaml"],
    },
    "wrong_port_9090": {
        "docker_images": ["kube-wrong-port-9090-app"],
        "k8s_manifests": ["{name}.yaml"],
    },
    "wrong_port_5000": {
        "docker_images": ["kube-wrong-port-5000-app"],
        "k8s_manifests": ["{name}.yaml"],
    },
    "wrong_port_7001": {
        "docker_images": ["kube-wrong-port-7001-app"],
        "k8s_manifests": ["{name}.yaml"],
    },
    "readiness_failure": {
        "docker_images": [],
        "k8s_manifests": ["{name}.yaml"],
    },
    "liveness_probe": {
        "docker_images": [],
        "k8s_manifests": ["{name}.yaml"],
    },
    "missing_dependency": {
        "docker_images": [],
        "k8s_manifests": ["{name}.yaml"],
    },
    "port_mismatch": {
        "docker_images": ["kube-port-mismatch-app"],
        "k8s_manifests": ["{name}.yaml", "app_service.yaml"],
    },
    "incorrect_selector": {
        "docker_images": ["kube-incorrect-selector-app"],
        "k8s_manifests": ["{name}.yaml", "app_service.yaml"],
    },
    "environment_variable": {
        "docker_images": ["kube-env-missing-app"],
        "k8s_manifests": ["{name}.yaml"],
    },
    "environment_variable_wrong_name": {
        "docker_images": ["kube-env-wrong-name-app"],
        "k8s_manifests": ["{name}.yaml"],
    },
    "port_mismatch_wrong_interface": {
        "docker_images": ["kube-port-mismatch-wrong-interface-app"],
        "k8s_manifests": ["{name}.yaml", "app_service.yaml"],
    },
    "readiness_missing_dependency": {
        "docker_images": ["kube-readiness-missing-dependency-app"],
        "k8s_manifests": ["{name}.yaml"],
    },
    "readiness_missing_dependency_transitive": {
        "docker_images": ["kube-readiness-transitive-dependency-app"],
        "k8s_manifests": ["{name}.yaml"],
    },
    "selector_env_variable": {
        "docker_images": ["kube-selector-env-app"],
        "k8s_manifests": ["{name}.yaml", "app_service.yaml"],
    },
    "selector_env_variable_label_and_secret": {
        "docker_images": ["kube-selector-env-secret-app"],
        "k8s_manifests": ["{name}.yaml", "app_service.yaml"],
    },
    "resource_limits_oom": {
        "docker_images": ["kube-resource-limits-oom-app"],
        "k8s_manifests": ["{name}.yaml"],
    },
    "resource_limits_cpu_starvation": {
        "docker_images": ["kube-resource-limits-cpu-starvation-app"],
        "k8s_manifests": ["{name}.yaml"],
    },
    "volume_mount": {
        "docker_images": ["marioutsa/kube-volume-mount-app"],
        "k8s_manifests": ["{name}.yaml"],
    },
    "incorrect_selector_missing_label": {
        "docker_images": ["kube-selector-missing-label-app"],
        "k8s_manifests": ["{name}.yaml", "app_service.yaml"],
    },
    "liveness_probe_wrong_path": {
        "docker_images": ["kube-liveness-wrong-path-app"],
        "k8s_manifests": ["{name}.yaml"],
    },
    "missing_dependency_requirements": {
        "docker_images": ["kube-missing-dependency-requirements-app"],
        "k8s_manifests": ["{name}.yaml"],
    },
    "port_mismatch_named_target": {
        "docker_images": ["kube-port-mismatch-named-target-app"],
        "k8s_manifests": ["{name}.yaml", "app_service.yaml"],
    },
    "readiness_failure_slow_start": {
        "docker_images": ["kube-readiness-slow-start-app"],
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

TRANSIENT_K8S_POD_NAME_PATTERNS = [
    re.compile(pattern)
    for pattern in [
        r"^curl-test[0-9]*$",
        r"^curl-check[0-9]*$",
        r"^curlcheck[0-9]*$",
        r"^curl-verify[0-9]*$",
        r"^test-curl[0-9]*$",
        r"^svc-test[0-9]*$",
        r"^net-test[0-9]*$",
    ]
]

def list_teardown_tests():
    return list(TEARDOWN_CONFIG.keys())


def _get_test_dir(test_env_name: str) -> Path:
    return TROUBLESHOOTING_DIR / test_env_name


def restore_fixture_baseline(test_env_name: str) -> None:
    """Replace one working fixture with its committed, immutable baseline."""
    if test_env_name not in TEARDOWN_CONFIG:
        raise ValueError(f"Unknown test case: {test_env_name}")

    baseline_dir = FIXTURE_BASELINES_DIR / test_env_name
    if not baseline_dir.is_dir():
        raise FileNotFoundError(f"Fixture baseline not found for {test_env_name}: {baseline_dir}")

    test_dir = _get_test_dir(test_env_name)
    if test_dir.exists():
        shutil.rmtree(test_dir)
    shutil.copytree(baseline_dir, test_dir)


def cleanup_transient_k8s_resources(namespace: str = "default") -> None:
    """Remove helper resources that agents may create while probing services."""
    for kind, name in TRANSIENT_K8S_RESOURCES:
        subprocess.run(
            ["kubectl", "delete", kind, name, "-n", namespace, "--ignore-not-found=true"],
            check=False,
        )

    result = subprocess.run(
        ["kubectl", "get", "pods", "-n", namespace, "-o", "name"],
        capture_output=True,
        text=True,
        check=False,
    )
    if not result or result.returncode != 0:
        return

    for line in result.stdout.splitlines():
        pod_name = line.removeprefix("pod/").strip()
        if not pod_name:
            continue
        if any(pattern.match(pod_name) for pattern in TRANSIENT_K8S_POD_NAME_PATTERNS):
            subprocess.run(
                ["kubectl", "delete", "pod", pod_name, "-n", namespace, "--ignore-not-found=true"],
                check=False,
            )


def cleanup_test_pods(namespace: str = "default") -> None:
    """Remove all pods after a test has completed verification."""
    subprocess.run(
        ["kubectl", "delete", "pods", "--all", "-n", namespace, "--ignore-not-found=true"],
        check=False,
    )


def teardown_environment(test_env_name: str) -> None:
    config = TEARDOWN_CONFIG.get(test_env_name)
    if not config:
        raise ValueError(f"Unknown test case: {test_env_name}")

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

    for manifest in config["k8s_manifests"]:
        manifest_path = TROUBLESHOOTING_DIR / test_env_name / manifest.format(name=test_env_name)
        subprocess.run(
            ["kubectl", "delete", "-f", str(manifest_path), "--grace-period=5", "--ignore-not-found=true"],
            check=False,
        )

    # Some legacy teardown entries only clean cluster resources and have no
    # runnable fixture directory. Full restoration applies when a committed
    # baseline exists for the case.
    if (FIXTURE_BASELINES_DIR / test_env_name).is_dir():
        restore_fixture_baseline(test_env_name)


# Backward-compatible alias while callers migrate.
tearDownEnviornment = teardown_environment
