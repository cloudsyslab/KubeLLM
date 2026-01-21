import kube_test
import sys

TESTS = [
    "correct_app",
    "incorrect_selector",
    "no_pod_ip",
    "port_mismatch",
    "readiness_failure",
    "wrong_interface",
    "wrong_port",
    "environment_variable",
    "liveness_probe",
    "missing_dependency",
    "port_mismatch_wrong_interface",
    "readiness_missing_dependency",
    "selector_env_variable",
    "resource_limits_oom",
    "volume_mount",
]

if len(sys.argv) < 2:
    print("provide a testcase name or 'all'")
    sys.exit(1)

test_env_name = sys.argv[1].lower()

def teardown_one(name: str) -> int:
    try:
        kube_test.tearDownEnviornment(name)
        return 0
    except Exception as exc:
        print(f"teardown failed for {name}: {exc}")
        return 1

if test_env_name == "all":
    exit_code = 0
    for name in TESTS:
        exit_code |= teardown_one(name)
    sys.exit(exit_code)

if test_env_name not in TESTS:
    print("provide a valid testcase name or 'all'")
    sys.exit(1)

sys.exit(teardown_one(test_env_name))
