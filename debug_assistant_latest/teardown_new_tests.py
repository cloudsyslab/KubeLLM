#!/usr/bin/env python3
"""
Teardown script for new test cases
Usage: python3 teardown_new_tests.py <test_name>
Example: python3 teardown_new_tests.py port_mismatch_wrong_interface
"""

import subprocess
import sys
import os
import logging
from pathlib import Path

# Use relative path from script location
script_dir = Path(__file__).parent.resolve()
filepath = script_dir / "troubleshooting"

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def check_pod_exists(label_selector):
    """Check if pod with given label exists"""
    result = subprocess.run(
        ["kubectl", "get", "pod", "-l", label_selector],
        capture_output=True, text=True
    )
    return result.returncode == 0 and result.stdout.strip() and "No resources found" not in result.stdout

def check_service_exists(service_name):
    """Check if service exists"""
    result = subprocess.run(
        ["kubectl", "get", "service", service_name],
        capture_output=True, text=True
    )
    return result.returncode == 0

def check_image_exists(image_name):
    """Check if Docker image exists"""
    result = subprocess.run(
        ["docker", "images", "-q", image_name],
        capture_output=True, text=True
    )
    return result.returncode == 0 and result.stdout.strip()

def teardown_port_mismatch_wrong_interface():
    """Teardown for port_mismatch_wrong_interface test"""
    test_dir = filepath / "port_mismatch_wrong_interface"
    logger.info("Starting teardown for port_mismatch_wrong_interface...")

    try:
        # Check and delete pod
        if check_pod_exists("app=port-mismatch-wrong-interface-app"):
            logger.info("Deleting pod...")
            subprocess.run(f"kubectl delete -f {test_dir}/port_mismatch_wrong_interface.yaml",
                          shell=True, check=False)
        else:
            logger.info("Pod not found, skipping")

        # Check and delete service
        if check_service_exists("port-mismatch-app-service"):
            logger.info("Deleting service...")
            subprocess.run(f"kubectl delete -f {test_dir}/app_service.yaml",
                          shell=True, check=False)
        else:
            logger.info("Service not found, skipping")

        # Check and delete Docker image (remove containers first)
        if check_image_exists("kube-port-mismatch-wrong-interface-app"):
            logger.info("Removing containers using the image...")
            subprocess.run("docker ps -a -q --filter ancestor=kube-port-mismatch-wrong-interface-app | xargs -r docker rm -f",
                          shell=True, check=False)
            logger.info("Deleting Docker image...")
            subprocess.run("docker rmi -f kube-port-mismatch-wrong-interface-app",
                          shell=True, check=False)
        else:
            logger.info("Docker image not found, skipping")

        logger.info("✓ Teardown complete for port_mismatch_wrong_interface")
    except Exception as e:
        logger.error(f"Error during teardown: {e}")

def teardown_readiness_missing_dependency():
    """Teardown for readiness_missing_dependency test"""
    test_dir = filepath / "readiness_missing_dependency"
    logger.info("Starting teardown for readiness_missing_dependency...")

    try:
        # Check and delete pod
        if check_pod_exists("app=readiness-missing-dependency-app"):
            logger.info("Deleting pod...")
            subprocess.run(f"kubectl delete -f {test_dir}/readiness_missing_dependency.yaml",
                          shell=True, check=False)
        else:
            logger.info("Pod not found, skipping")

        # Check and delete Docker image (remove containers first)
        if check_image_exists("kube-readiness-missing-dependency-app"):
            logger.info("Removing containers using the image...")
            subprocess.run("docker ps -a -q --filter ancestor=kube-readiness-missing-dependency-app | xargs -r docker rm -f",
                          shell=True, check=False)
            logger.info("Deleting Docker image...")
            subprocess.run("docker rmi -f kube-readiness-missing-dependency-app",
                          shell=True, check=False)
        else:
            logger.info("Docker image not found, skipping")

        logger.info("✓ Teardown complete for readiness_missing_dependency")
    except Exception as e:
        logger.error(f"Error during teardown: {e}")

def teardown_selector_env_variable():
    """Teardown for selector_env_variable test"""
    test_dir = filepath / "selector_env_variable"
    logger.info("Starting teardown for selector_env_variable...")

    try:
        # Check and delete pod
        if check_pod_exists("app=selector-env-app"):
            logger.info("Deleting pod...")
            subprocess.run(f"kubectl delete -f {test_dir}/selector_env_variable.yaml",
                          shell=True, check=False)
        else:
            logger.info("Pod not found, skipping")

        # Check and delete service
        if check_service_exists("selector-env-app-service"):
            logger.info("Deleting service...")
            subprocess.run(f"kubectl delete -f {test_dir}/app_service.yaml",
                          shell=True, check=False)
        else:
            logger.info("Service not found, skipping")

        # Check and delete Docker image (remove containers first)
        if check_image_exists("kube-selector-env-app"):
            logger.info("Removing containers using the image...")
            subprocess.run("docker ps -a -q --filter ancestor=kube-selector-env-app | xargs -r docker rm -f",
                          shell=True, check=False)
            logger.info("Deleting Docker image...")
            subprocess.run("docker rmi -f kube-selector-env-app",
                          shell=True, check=False)
        else:
            logger.info("Docker image not found, skipping")

        logger.info("✓ Teardown complete for selector_env_variable")
    except Exception as e:
        logger.error(f"Error during teardown: {e}")

def teardown_resource_limits_oom():
    """Teardown for resource_limits_oom test"""
    test_dir = filepath / "resource_limits_oom"
    logger.info("Starting teardown for resource_limits_oom...")

    try:
        # Check and delete pod
        if check_pod_exists("app=resource-limits-oom-app"):
            logger.info("Deleting pod...")
            subprocess.run(f"kubectl delete -f {test_dir}/resource_limits_oom.yaml",
                          shell=True, check=False)
        else:
            logger.info("Pod not found, skipping")

        # Check and delete Docker image (remove containers first)
        if check_image_exists("kube-resource-limits-oom-app"):
            logger.info("Removing containers using the image...")
            subprocess.run("docker ps -a -q --filter ancestor=kube-resource-limits-oom-app | xargs -r docker rm -f",
                          shell=True, check=False)
            logger.info("Deleting Docker image...")
            subprocess.run("docker rmi -f kube-resource-limits-oom-app",
                          shell=True, check=False)
        else:
            logger.info("Docker image not found, skipping")

        logger.info("✓ Teardown complete for resource_limits_oom")
    except Exception as e:
        logger.error(f"Error during teardown: {e}")

def teardown_all():
    """Teardown all new test cases"""
    logger.info("Tearing down all new test cases...")
    teardown_port_mismatch_wrong_interface()
    teardown_readiness_missing_dependency()
    teardown_selector_env_variable()
    teardown_resource_limits_oom()
    logger.info("\n✓ All teardowns complete")

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
