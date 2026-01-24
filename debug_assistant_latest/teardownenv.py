import kube_test
import sys

# Use TEARDOWN_CONFIG as single source of truth for valid test cases
TESTS = list(kube_test.TEARDOWN_CONFIG.keys())

if len(sys.argv) < 2:
    print("Usage: python teardownenv.py <testcase_name|all>")
    print(f"Available: {', '.join(TESTS)}")
    sys.exit(1)

test_env_name = sys.argv[1].lower()


def teardown_one(name: str) -> int:
    try:
        print(f"Tearing down: {name}")
        kube_test.tearDownEnviornment(name)
        print(f"  Done: {name}")
        return 0
    except Exception as exc:
        print(f"  Failed: {name} - {exc}")
        return 1


if test_env_name == "all":
    exit_code = 0
    for name in TESTS:
        exit_code |= teardown_one(name)
    sys.exit(exit_code)

if test_env_name not in TESTS:
    print(f"Unknown test case: {test_env_name}")
    print(f"Available: {', '.join(TESTS)}")
    sys.exit(1)

sys.exit(teardown_one(test_env_name))
