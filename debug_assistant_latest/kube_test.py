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

def backupEnviornment(testEnvName):
    if testEnvName == "wrong_interface":
        shutil.copyfile(f"{filepath}/{testEnvName}/server.py", f"{filepath}/{testEnvName}/backup_server.py")
        shutil.copyfile(f"{filepath}/{testEnvName}/{testEnvName}.yaml", f"{filepath}/{testEnvName}/backup_yaml.yaml")
        shutil.copyfile(f"{filepath}/{testEnvName}/Dockerfile", f"{filepath}/{testEnvName}/backup_Dockerfile")
    elif testEnvName == "readiness_failure":
        shutil.copyfile(f"{filepath}/{testEnvName}/{testEnvName}.yaml", f"{filepath}/{testEnvName}/backup_yaml.yaml")
    elif testEnvName == "wrong_port":
        shutil.copyfile(f"{filepath}/{testEnvName}/server.py", f"{filepath}/{testEnvName}/backup_server.py")
        shutil.copyfile(f"{filepath}/{testEnvName}/{testEnvName}.yaml", f"{filepath}/{testEnvName}/backup_yaml.yaml")
        shutil.copyfile(f"{filepath}/{testEnvName}/Dockerfile", f"{filepath}/{testEnvName}/backup_Dockerfile")
    elif testEnvName == "port_mismatch":
        shutil.copyfile(f"{filepath}/{testEnvName}/server.py", f"{filepath}/{testEnvName}/backup_server.py")
        shutil.copyfile(f"{filepath}/{testEnvName}/{testEnvName}.yaml", f"{filepath}/{testEnvName}/backup_yaml.yaml")
        shutil.copyfile(f"{filepath}/{testEnvName}/Dockerfile", f"{filepath}/{testEnvName}/backup_Dockerfile")
        shutil.copyfile(f"{filepath}/{testEnvName}/app_service.yaml", f"{filepath}/{testEnvName}/backup_app_service.yaml")
    elif testEnvName == "incorrect_selector":
        shutil.copyfile(f"{filepath}/{testEnvName}/server.py", f"{filepath}/{testEnvName}/backup_server.py")
        shutil.copyfile(f"{filepath}/{testEnvName}/{testEnvName}.yaml", f"{filepath}/{testEnvName}/backup_yaml.yaml")
        shutil.copyfile(f"{filepath}/{testEnvName}/Dockerfile", f"{filepath}/{testEnvName}/backup_Dockerfile")
        shutil.copyfile(f"{filepath}/{testEnvName}/app_service.yaml", f"{filepath}/{testEnvName}/backup_app_service.yaml")


def tearDownEnviornment(testEnvName):
    if testEnvName == "wrong_interface":
        #subprocess.run("docker stop wrong_interface_app", shell=True, check=True)
        #subprocess.run("docker rm wrong_interface_app", shell=True, check=True)
        subprocess.run("docker rmi -f kube-wrong-interface-app", shell=True, check=True)

        os.remove(f"{filepath}/{testEnvName}/{testEnvName}.yaml")
        os.remove(f"{filepath}/{testEnvName}/server.py")
        os.remove(f"{filepath}/{testEnvName}/Dockerfile")
        os.remove(f"{filepath}/{testEnvName}/app_service.yaml")
        
        shutil.copyfile(f"{filepath}/{testEnvName}/backup_yaml.yaml", f"{filepath}/{testEnvName}/{testEnvName}.yaml")        
        shutil.copyfile(f"{filepath}/{testEnvName}/backup_server.py", f"{filepath}/{testEnvName}/server.py")        
        shutil.copyfile(f"{filepath}/{testEnvName}/backup_Dockerfile", f"{filepath}/{testEnvName}/Dockerfile")        
        shutil.copyfile(f"{filepath}/{testEnvName}/backup_app_service.yaml", f"{filepath}/{testEnvName}/app_service.yaml")     
        subprocess.run(f"kubectl delete -f ./troubleshooting/{testEnvName}/{testEnvName}.yaml --grace-period=5", shell=True, check=True)
        subprocess.run(f"kubectl delete -f ./troubleshooting/{testEnvName}/app_service.yaml", shell=True, check=True)
    elif testEnvName == "readiness_failure":
        os.remove(f"{filepath}/{testEnvName}/{testEnvName}.yaml")
        shutil.copyfile(f"{filepath}/{testEnvName}/backup_yaml.yaml", f"{filepath}/{testEnvName}/{testEnvName}.yaml")        
        subprocess.run(f"kubectl delete -f ./troubleshooting/{testEnvName}/{testEnvName}.yaml --grace-period=5", shell=True, check=True)
    elif testEnvName == "liveness_probe":
        os.remove(f"{filepath}/{testEnvName}/{testEnvName}.yaml")
        shutil.copyfile(f"{filepath}/{testEnvName}/backup_yaml.yaml", f"{filepath}/{testEnvName}/{testEnvName}.yaml")        
        subprocess.run(f"kubectl delete -f ./troubleshooting/{testEnvName}/{testEnvName}.yaml --grace-period=5", shell=True, check=True)
    elif testEnvName == "missing_dependency":
        os.remove(f"{filepath}/{testEnvName}/{testEnvName}.yaml")
        os.remove(f"{filepath}/{testEnvName}/server.py")
        os.remove(f"{filepath}/{testEnvName}/Dockerfile")
 
        shutil.copyfile(f"{filepath}/{testEnvName}/backup_yaml.yaml", f"{filepath}/{testEnvName}/{testEnvName}.yaml")        
        shutil.copyfile(f"{filepath}/{testEnvName}/backup_server.py", f"{filepath}/{testEnvName}/server.py")        
        shutil.copyfile(f"{filepath}/{testEnvName}/backup_Dockerfile", f"{filepath}/{testEnvName}/Dockerfile")        
        subprocess.run(f"kubectl delete -f ./troubleshooting/{testEnvName}/{testEnvName}.yaml --grace-period=5", shell=True, check=True)
    elif testEnvName == "port_mismatch":
        #subprocess.run("docker stop port_mismatch_app", shell=True, check=True)
        #subprocess.run("docker rm port_mismatch_app", shell=True, check=True)
        subprocess.run("docker rmi -f kube-port-mismatch-app", shell=True, check=True)

        os.remove(f"{filepath}/{testEnvName}/{testEnvName}.yaml")
        os.remove(f"{filepath}/{testEnvName}/app_service.yaml")
        os.remove(f"{filepath}/{testEnvName}/server.py")
        os.remove(f"{filepath}/{testEnvName}/Dockerfile")

        shutil.copyfile(f"{filepath}/{testEnvName}/backup_yaml.yaml", f"{filepath}/{testEnvName}/{testEnvName}.yaml")   
        shutil.copyfile(f"{filepath}/{testEnvName}/backup_app_service.yaml", f"{filepath}/{testEnvName}/app_service.yaml")     
        shutil.copyfile(f"{filepath}/{testEnvName}/backup_server.py", f"{filepath}/{testEnvName}/server.py")        
        shutil.copyfile(f"{filepath}/{testEnvName}/backup_Dockerfile", f"{filepath}/{testEnvName}/Dockerfile")        

        subprocess.run(f"kubectl delete -f ./troubleshooting/{testEnvName}/{testEnvName}.yaml --grace-period=5", shell=True, check=True)
        subprocess.run(f"kubectl delete -f ./troubleshooting/{testEnvName}/app_service.yaml", shell=True, check=True)

    elif testEnvName == "incorrect_selector":

        #subprocess.run("docker stop incorrect_selector_app", shell=True, check=True)
        #subprocess.run("docker rm incorrect_selector_app", shell=True, check=True)
        #subprocess.run("docker rmi -f marioutsa/kube-incorrect-selector-app", shell=True, check=True)
        subprocess.run("docker rmi -f kube-incorrect-selector-app", shell=True, check=True)

        os.remove(f"{filepath}/{testEnvName}/{testEnvName}.yaml")
        os.remove(f"{filepath}/{testEnvName}/app_service.yaml")
        os.remove(f"{filepath}/{testEnvName}/server.py")
        os.remove(f"{filepath}/{testEnvName}/Dockerfile")

        shutil.copyfile(f"{filepath}/{testEnvName}/backup_yaml.yaml", f"{filepath}/{testEnvName}/{testEnvName}.yaml")   
        shutil.copyfile(f"{filepath}/{testEnvName}/backup_app_service.yaml", f"{filepath}/{testEnvName}/app_service.yaml")     
        shutil.copyfile(f"{filepath}/{testEnvName}/backup_server.py", f"{filepath}/{testEnvName}/server.py")        
        shutil.copyfile(f"{filepath}/{testEnvName}/backup_Dockerfile", f"{filepath}/{testEnvName}/Dockerfile")        

        subprocess.run(f"kubectl delete -f ./troubleshooting/{testEnvName}/{testEnvName}.yaml --grace-period=5", shell=True, check=True)
        subprocess.run(f"kubectl delete -f ./troubleshooting/{testEnvName}/app_service.yaml", shell=True, check=True)
    
    elif testEnvName == "environment_variable":
        #subprocess.run("docker stop environment_variable_app", shell=True, check=True)
        #subprocess.run("docker rm environment_variable_app", shell=True, check=True)
        #subprocess.run("docker rmi -f marioutsa/kube-env-missing-app", shell=True, check=True)
        subprocess.run("docker rmi -f kube-env-missing-app", shell=True, check=True)

        os.remove(f"{filepath}/{testEnvName}/{testEnvName}.yaml")
        os.remove(f"{filepath}/{testEnvName}/server.py")
        os.remove(f"{filepath}/{testEnvName}/Dockerfile")

        shutil.copyfile(f"{filepath}/{testEnvName}/backup_yaml.yaml", f"{filepath}/{testEnvName}/{testEnvName}.yaml")
        shutil.copyfile(f"{filepath}/{testEnvName}/backup_server.py", f"{filepath}/{testEnvName}/server.py")
        shutil.copyfile(f"{filepath}/{testEnvName}/backup_Dockerfile", f"{filepath}/{testEnvName}/Dockerfile")

        subprocess.run(f"kubectl delete -f ./troubleshooting/{testEnvName}/{testEnvName}.yaml --grace-period=5", shell=True, check=True)

    # New combined test cases - no backup/restore needed, just cleanup
    elif testEnvName == "port_mismatch_wrong_interface":
        # Clean up containers using this image first
        subprocess.run("docker ps -a -q --filter ancestor=kube-port-mismatch-wrong-interface-app | xargs -r docker rm -f",
                      shell=True, check=False)
        # Remove image
        subprocess.run("docker rmi -f kube-port-mismatch-wrong-interface-app", shell=True, check=False)
        # Delete k8s resources
        subprocess.run(f"kubectl delete -f ./troubleshooting/{testEnvName}/{testEnvName}.yaml", shell=True, check=False)
        subprocess.run(f"kubectl delete -f ./troubleshooting/{testEnvName}/app_service.yaml", shell=True, check=False)

    elif testEnvName == "readiness_missing_dependency":
        # Clean up containers using this image first
        subprocess.run("docker ps -a -q --filter ancestor=kube-readiness-missing-dependency-app | xargs -r docker rm -f",
                      shell=True, check=False)
        # Remove image
        subprocess.run("docker rmi -f kube-readiness-missing-dependency-app", shell=True, check=False)
        # Delete k8s resources
        subprocess.run(f"kubectl delete -f ./troubleshooting/{testEnvName}/{testEnvName}.yaml", shell=True, check=False)

    elif testEnvName == "selector_env_variable":
        # Clean up containers using this image first
        subprocess.run("docker ps -a -q --filter ancestor=kube-selector-env-app | xargs -r docker rm -f",
                      shell=True, check=False)
        # Remove image
        subprocess.run("docker rmi -f kube-selector-env-app", shell=True, check=False)
        # Delete k8s resources
        subprocess.run(f"kubectl delete -f ./troubleshooting/{testEnvName}/{testEnvName}.yaml", shell=True, check=False)
        subprocess.run(f"kubectl delete -f ./troubleshooting/{testEnvName}/app_service.yaml", shell=True, check=False)

    elif testEnvName == "resource_limits_oom":
        # Clean up containers using this image first
        subprocess.run("docker ps -a -q --filter ancestor=kube-resource-limits-oom-app | xargs -r docker rm -f",
                      shell=True, check=False)
        # Remove image
        subprocess.run("docker rmi -f kube-resource-limits-oom-app", shell=True, check=False)
        # Delete k8s resources
        subprocess.run(f"kubectl delete -f ./troubleshooting/{testEnvName}/{testEnvName}.yaml", shell=True, check=False)

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

