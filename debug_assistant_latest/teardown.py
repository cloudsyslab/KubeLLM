import re
import shutil
import subprocess
from pathlib import Path

from debug_assistant_latest.lab_context import active_lane_config, assert_lane_target, is_lane_active

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

KUBECTL_COMMAND_TIMEOUT_S = 20


class TeardownFailure(RuntimeError):
    """One or more case-scoped cleanup steps failed."""

    def __init__(self, test_name: str, failures: list[str]):
        self.test_name = test_name
        self.failures = tuple(failures)
        super().__init__(f"Teardown failed for {test_name}: {'; '.join(failures)}")


def _cleanup_command(operation: str, command: list[str], timeout: int, failures: list[str]) -> subprocess.CompletedProcess | None:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        failures.append(f"{operation} timed out after {timeout}s")
        return None
    except OSError as exc:
        failures.append(f"{operation} failed ({type(exc).__name__})")
        return None

    if result.returncode != 0:
        failures.append(f"{operation} exited with status {result.returncode}")
    return result


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


def cleanup_transient_k8s_resources(
    namespace: str = "default", *, strict: bool = False, validate_target: bool = True
) -> None:
    """Remove helper resources that agents may create while probing services."""
    failures: list[str] = []
    if validate_target and is_lane_active():
        try:
            assert_lane_target()
        except Exception as exc:
            if strict:
                raise TeardownFailure(
                    "transient resources", [f"selected lane validation failed ({type(exc).__name__})"]
                ) from exc
            raise
    for kind, name in TRANSIENT_K8S_RESOURCES:
        command = ["kubectl", "delete", kind, name, "-n", namespace, "--ignore-not-found=true"]
        if strict:
            _cleanup_command(f"delete transient {kind} {name}", command, KUBECTL_COMMAND_TIMEOUT_S, failures)
        else:
            subprocess.run(command, check=False, timeout=KUBECTL_COMMAND_TIMEOUT_S)

    if strict:
        result = _cleanup_command(
            "list transient pods",
            ["kubectl", "get", "pods", "-n", namespace, "-o", "name"],
            KUBECTL_COMMAND_TIMEOUT_S,
            failures,
        )
    else:
        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", namespace, "-o", "name"],
            capture_output=True,
            text=True,
            check=False,
            timeout=KUBECTL_COMMAND_TIMEOUT_S,
        )
    if not result or result.returncode != 0:
        if failures:
            raise TeardownFailure("transient resources", failures)
        return

    for line in result.stdout.splitlines():
        pod_name = line.removeprefix("pod/").strip()
        if not pod_name:
            continue
        if any(pattern.match(pod_name) for pattern in TRANSIENT_K8S_POD_NAME_PATTERNS):
            command = ["kubectl", "delete", "pod", pod_name, "-n", namespace, "--ignore-not-found=true"]
            if strict:
                _cleanup_command(f"delete transient pod {pod_name}", command, KUBECTL_COMMAND_TIMEOUT_S, failures)
            else:
                subprocess.run(command, check=False, timeout=KUBECTL_COMMAND_TIMEOUT_S)

    if failures:
        raise TeardownFailure("transient resources", failures)


def cleanup_test_pods(namespace: str = "default") -> None:
    """Remove all pods after a test has completed verification."""
    if is_lane_active():
        # Case teardown deletes only the case manifests. Never sweep an entire
        # namespace, since other work may have been added to this cluster.
        return
    subprocess.run(
        [
            "kubectl",
            "delete",
            "pods",
            "--all",
            "-n",
            namespace,
            "--ignore-not-found=true",
            "--wait=false",
        ],
        check=False,
        timeout=KUBECTL_COMMAND_TIMEOUT_S,
    )


def teardown_environment(test_env_name: str) -> None:
    config = TEARDOWN_CONFIG.get(test_env_name)
    if not config:
        raise ValueError(f"Unknown test case: {test_env_name}")

    lane = active_lane_config() if is_lane_active() else None
    failures: list[str] = []
    may_mutate_lab = True
    try:
        if lane:
            # Validate every target before deleting even one resource.
            try:
                assert_lane_target()
            except Exception as exc:
                failures.append(f"selected lane validation failed ({type(exc).__name__})")
                may_mutate_lab = False

        if may_mutate_lab:
            try:
                cleanup_transient_k8s_resources(strict=True, validate_target=False)
            except Exception as exc:
                failures.append(f"transient resource cleanup failed ({type(exc).__name__})")

            for image in config["docker_images"]:
                if lane:
                    _cleanup_command(
                        f"remove case image {image}",
                        ["minikube", "-p", lane["minikube_profile"], "image", "rm", image],
                        120,
                        failures,
                    )
                    continue

                result = _cleanup_command(
                    f"find containers for case image {image}",
                    ["docker", "ps", "-a", "-q", "--filter", f"ancestor={image}"],
                    30,
                    failures,
                )
                for cid in (result.stdout.strip().splitlines() if result else []):
                    _cleanup_command(f"remove case container for {image}", ["docker", "rm", "-f", cid], 30, failures)
                _cleanup_command(f"remove case image {image}", ["docker", "rmi", "-f", image], 120, failures)

            for manifest in config["k8s_manifests"]:
                manifest_path = TROUBLESHOOTING_DIR / test_env_name / manifest.format(name=test_env_name)
                _cleanup_command(
                    f"delete case manifest {manifest}",
                    ["kubectl", "delete", "-f", str(manifest_path), "--grace-period=5", "--ignore-not-found=true"],
                    KUBECTL_COMMAND_TIMEOUT_S,
                    failures,
                )
    finally:
        # Restore local inputs even when lab cleanup times out or lane validation fails.
        if (FIXTURE_BASELINES_DIR / test_env_name).is_dir():
            try:
                restore_fixture_baseline(test_env_name)
            except Exception as exc:
                failures.append(f"fixture restoration failed ({type(exc).__name__})")

    if failures:
        raise TeardownFailure(test_env_name, failures)


# Backward-compatible alias while callers migrate.
tearDownEnviornment = teardown_environment
