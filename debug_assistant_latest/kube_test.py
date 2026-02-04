from main import allStepsAtOnce, stepByStep, singleAgentApproach
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import time
import shutil
import os
import subprocess
import datetime
from pathlib import Path

# Use relative path from script location
SCRIPT_DIR = Path(__file__).parent.absolute()
filepath = SCRIPT_DIR / "troubleshooting"

# Validate that troubleshooting directory exists
if not filepath.exists():
    raise FileNotFoundError(
        f"Troubleshooting directory not found: {filepath}\n"
        f"Expected structure: <repo-root>/debug_assistant_latest/troubleshooting/"
    )

print(f"Troubleshooting directory: {filepath}")

# Data-driven teardown configuration for all test cases
# Each entry defines: docker images to remove, files to restore from backup, k8s manifests to delete
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


def backupEnviornment(testEnvName):
    """Create backups of files that may be modified during testing."""
    config = TEARDOWN_CONFIG.get(testEnvName)
    if not config:
        return

    test_dir = filepath / testEnvName
    for file_type in config["restore_files"]:
        if file_type == "yaml":
            src = test_dir / f"{testEnvName}.yaml"
            dst = test_dir / "backup_yaml.yaml"
        elif file_type == "app_service.yaml":
            src = test_dir / "app_service.yaml"
            dst = test_dir / "backup_app_service.yaml"
        else:
            src = test_dir / file_type
            dst = test_dir / f"backup_{file_type.replace('.', '_')}"
            # Handle common file names
            if file_type == "server.py":
                dst = test_dir / "backup_server.py"
            elif file_type == "Dockerfile":
                dst = test_dir / "backup_Dockerfile"

        if src.exists():
            shutil.copyfile(src, dst)


def tearDownEnviornment(testEnvName):
    """Teardown a test environment: remove docker images, restore files, delete k8s resources."""
    config = TEARDOWN_CONFIG.get(testEnvName)
    if not config:
        raise ValueError(f"Unknown test case: {testEnvName}")

    test_dir = filepath / testEnvName

    # 1. Docker cleanup - remove images (and any containers using them)
    for image in config["docker_images"]:
        # First remove any containers using this image
        subprocess.run(
            f"docker ps -a -q --filter ancestor={image} | xargs -r docker rm -f",
            shell=True, check=False
        )
        # Then remove the image
        subprocess.run(f"docker rmi -f {image}", shell=True, check=False)

    # 2. File restoration - restore from backups
    for file_type in config["restore_files"]:
        if file_type == "yaml":
            src = test_dir / "backup_yaml.yaml"
            dst = test_dir / f"{testEnvName}.yaml"
        elif file_type == "app_service.yaml":
            src = test_dir / "backup_app_service.yaml"
            dst = test_dir / "app_service.yaml"
        elif file_type == "server.py":
            src = test_dir / "backup_server.py"
            dst = test_dir / "server.py"
        elif file_type == "Dockerfile":
            src = test_dir / "backup_Dockerfile"
            dst = test_dir / "Dockerfile"
        else:
            continue

        # Remove modified file and restore from backup
        if dst.exists():
            os.remove(dst)
        if src.exists():
            shutil.copyfile(src, dst)

    # 3. K8s resource deletion
    for manifest in config["k8s_manifests"]:
        # Replace {name} placeholder with test case name
        manifest_file = manifest.format(name=testEnvName)
        manifest_path = SCRIPT_DIR / "troubleshooting" / testEnvName / manifest_file
        subprocess.run(
            ["kubectl", "delete", "-f", str(manifest_path), "--grace-period=5", "--ignore-not-found=true"],
            check=False
        )

def selectTestFunc(testName):
    """ return the test function based on the test name given """
    if testName == "allStepsAtOnce":
        return allStepsAtOnce
    elif testName == "stepByStep":
        return stepByStep
    elif testName == "singleAgent":
        return singleAgentApproach
    else:
        return None

def runSingleTest(testFunc, configFile):
    """ Run the test and collect the results from the run """
    startTime = time.time()
    result = testFunc(configFile = configFile)
    endTime = time.time()
    totalTime = endTime - startTime

    return {"TimeTaken":totalTime,"Result":result}

def appendResultsToLog(testTechnique, testName, model, results):

    todaysDate = datetime.date.today()
    file_path = SCRIPT_DIR / "result_logs" / "result_logs_agents_rag_memory.txt"
    print (f"Logging into {file_path}")
    # Ensure the parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Open the file in append mode and write some text
    with file_path.open("a") as file:
        file.write(f"({todaysDate}) : Model - {model}, Technique - {testTechnique}, Test Name - {testName} \n\nResult: {results} \n\n------------------------------------------------------------------ \n")


def run():
    """ main runner function which is responsilbe for setting up and running all tests """
    numTests = 20
    #testName = "allStepsAtOnce"
    #testEnvName = "incorrect_selector"
    results = {}
    model = "GPT-4o"
    for testName in ["allStepsAtOnce",""]:
        testFunc = selectTestFunc(testName)
        results[testName] = {}

        for testEnvName in ["incorrect_selector", "port_mismatch", "readiness_failure", "wrong_interface", "wrong_port"]:

            configFile = f"{filepath}/{testEnvName}/config_step.json"
            print (f'starting environment {testEnvName}')       
            #Set up backups
            backupEnviornment(testEnvName)

            allTestResults = {}
            if testFunc:
                for testNumber in range(numTests):
                    print(f"Running Test Number : {testNumber}")
                    testResults = runSingleTest(testFunc, configFile)
                    allTestResults[testNumber] = testResults
                    #Delete test yaml and replace with the backup
                    try:
                        tearDownEnviornment(testEnvName)
                    except:
                        break

                allTestResultsDF = pd.DataFrame(allTestResults).T
                appendResultsToLog(testName, testEnvName, model, allTestResults)

                #print("Finished All Tests!")
                #print(allTestResultsDF)

                results[testName][testEnvName] = allTestResultsDF.to_dict()
            else:
                print(f"Could not find test : {testName}")


    print("Finised All Tests")
    print(results)


if __name__ == "__main__":
    run()

