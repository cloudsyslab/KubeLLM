#!/usr/bin/env python3
"""
Teardown script for new test cases
Usage: python3 teardown_new_tests.py <test_name>
Example: python3 teardown_new_tests.py port_mismatch_wrong_interface
"""

import subprocess
import sys
import os
from pathlib import Path

filepath = Path("~").expanduser() / "KubeLLM/debug_assistant_latest/troubleshooting"

def teardown_port_mismatch_wrong_interface():
    """Teardown for port_mismatch_wrong_interface test"""
    test_dir = filepath / "port_mismatch_wrong_interface"

    try:
        # Delete Kubernetes resources
        subprocess.run(f"kubectl delete -f {test_dir}/port_mismatch_wrong_interface.yaml --grace-period=5",
                      shell=True, check=False)
        subprocess.run(f"kubectl delete -f {test_dir}/app_service.yaml --grace-period=5",
                      shell=True, check=False)

        # Delete Docker image
        subprocess.run("docker rmi -f kube-port-mismatch-wrong-interface-app",
                      shell=True, check=False)

        print("✓ Teardown complete for port_mismatch_wrong_interface")
    except Exception as e:
        print(f"Error during teardown: {e}")

def teardown_readiness_missing_dependency():
    """Teardown for readiness_missing_dependency test"""
    test_dir = filepath / "readiness_missing_dependency"

    try:
        # Delete Kubernetes resources
        subprocess.run(f"kubectl delete -f {test_dir}/readiness_missing_dependency.yaml --grace-period=5",
                      shell=True, check=False)

        # Delete Docker image
        subprocess.run("docker rmi -f kube-readiness-missing-dep-app",
                      shell=True, check=False)

        print("✓ Teardown complete for readiness_missing_dependency")
    except Exception as e:
        print(f"Error during teardown: {e}")

def teardown_selector_env_variable():
    """Teardown for selector_env_variable test"""
    test_dir = filepath / "selector_env_variable"

    try:
        # Delete Kubernetes resources
        subprocess.run(f"kubectl delete -f {test_dir}/selector_env_variable.yaml --grace-period=5",
                      shell=True, check=False)
        subprocess.run(f"kubectl delete -f {test_dir}/app_service.yaml --grace-period=5",
                      shell=True, check=False)

        # Delete Docker image
        subprocess.run("docker rmi -f kube-selector-env-app",
                      shell=True, check=False)

        print("✓ Teardown complete for selector_env_variable")
    except Exception as e:
        print(f"Error during teardown: {e}")

def teardown_resource_limits_oom():
    """Teardown for resource_limits_oom test"""
    test_dir = filepath / "resource_limits_oom"

    try:
        # Delete Kubernetes resources
        subprocess.run(f"kubectl delete -f {test_dir}/resource_limits_oom.yaml --grace-period=5",
                      shell=True, check=False)

        # Delete Docker image
        subprocess.run("docker rmi -f kube-resource-limits-app",
                      shell=True, check=False)

        print("✓ Teardown complete for resource_limits_oom")
    except Exception as e:
        print(f"Error during teardown: {e}")

def teardown_all():
    """Teardown all new test cases"""
    print("Tearing down all new test cases...")
    teardown_port_mismatch_wrong_interface()
    teardown_readiness_missing_dependency()
    teardown_selector_env_variable()
    teardown_resource_limits_oom()
    print("\n✓ All teardowns complete")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 teardown_new_tests.py <test_name>")
        print("\nAvailable test names:")
        print("  - port_mismatch_wrong_interface")
        print("  - readiness_missing_dependency")
        print("  - selector_env_variable")
        print("  - resource_limits_oom")
        print("  - all  (teardown all tests)")
        sys.exit(1)

    test_name = sys.argv[1].lower()

    teardown_functions = {
        "port_mismatch_wrong_interface": teardown_port_mismatch_wrong_interface,
        "readiness_missing_dependency": teardown_readiness_missing_dependency,
        "selector_env_variable": teardown_selector_env_variable,
        "resource_limits_oom": teardown_resource_limits_oom,
        "all": teardown_all,
    }

    if test_name in teardown_functions:
        teardown_functions[test_name]()
    else:
        print(f"Unknown test name: {test_name}")
        print("Run without arguments to see available test names")
        sys.exit(1)
