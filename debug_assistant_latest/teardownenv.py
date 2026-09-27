import sys
import argparse
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from debug_assistant_latest.lab_context import LaneConfigurationError, bootstrap_from_argv

try:
    bootstrap_from_argv()
except LaneConfigurationError as exc:
    print(f"Lab lane configuration error: {exc}", file=sys.stderr)
    sys.exit(2)

from teardown import TEARDOWN_CONFIG, teardown_environment

# Use TEARDOWN_CONFIG as single source of truth for valid test cases.
TESTS = list(TEARDOWN_CONFIG.keys())
parser = argparse.ArgumentParser(description="Remove one KubeLLM case from the selected environment.")
parser.add_argument("test_case", choices=[*TESTS, "all"])
parser.add_argument("--lab-config", default=os.environ.get("KUBELLM_LAB_CONFIG"))
args = parser.parse_args()
test_env_name = args.test_case.lower()


def teardown_one(name: str) -> int:
    try:
        print(f"Tearing down: {name}")
        teardown_environment(name)
        print(f"  Done: {name}")
        return 0
    except Exception as exc:
        print(f"  Failed: {name} - {exc}")
        return 1


if test_env_name == "all":
    from debug_assistant_latest.lab_context import is_lane_active

    if is_lane_active():
        print("Refusing broad all-case teardown in a personal lab lane; tear down one selected case at a time.", file=sys.stderr)
        sys.exit(2)
    exit_code = 0
    for name in TESTS:
        exit_code |= teardown_one(name)
    sys.exit(exit_code)

if test_env_name not in TESTS:
    print(f"Unknown test case: {test_env_name}")
    print(f"Available: {', '.join(TESTS)}")
    sys.exit(1)

sys.exit(teardown_one(test_env_name))
