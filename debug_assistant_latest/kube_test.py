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

filepath = Path("~").expanduser() / "KubeLLM/debug_assistant_latest/troubleshooting"
print (filepath)

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
        subprocess.run("docker stop wrong_interface_app", shell=True, check=True)
        subprocess.run("docker rm wrong_interface_app", shell=True, check=True)
        subprocess.run("docker rmi -f marioutsa/kube-wrong-interface-app", shell=True, check=True)
        subprocess.run("docker rmi -f kube-wrong-interface-app", shell=True, check=True)

        os.remove(f"{filepath}/{testEnvName}/{testEnvName}.yaml")
        os.remove(f"{filepath}/{testEnvName}/server.py")
        os.remove(f"{filepath}/{testEnvName}/Dockerfile")

        shutil.copyfile(f"{filepath}/{testEnvName}/backup_yaml.yaml", f"{filepath}/{testEnvName}/{testEnvName}.yaml")        
        shutil.copyfile(f"{filepath}/{testEnvName}/backup_server.py", f"{filepath}/{testEnvName}/server.py")        
        shutil.copyfile(f"{filepath}/{testEnvName}/backup_Dockerfile", f"{filepath}/{testEnvName}/Dockerfile")        

        subprocess.run(f"kubectl delete -f ./troubleshooting/{testEnvName}/{testEnvName}.yaml", shell=True, check=True)

    elif testEnvName == "readiness_failure":
        os.remove(f"{filepath}/{testEnvName}/{testEnvName}.yaml")
        shutil.copyfile(f"{filepath}/{testEnvName}/backup_yaml.yaml", f"{filepath}/{testEnvName}/{testEnvName}.yaml")        
        subprocess.run(f"kubectl delete -f ./troubleshooting/{testEnvName}/{testEnvName}.yaml", shell=True, check=True)

    elif testEnvName == "wrong_port":
        subprocess.run("docker stop wrong_port_app", shell=True, check=True)
        subprocess.run("docker rm wrong_port_app", shell=True, check=True)
        subprocess.run("docker rmi -f marioutsa/kube-wrong-port-app", shell=True, check=True)
        subprocess.run("docker rmi -f kube-wrong-port-app", shell=True, check=True)

        os.remove(f"{filepath}/{testEnvName}/{testEnvName}.yaml")
        os.remove(f"{filepath}/{testEnvName}/server.py")
        os.remove(f"{filepath}/{testEnvName}/Dockerfile")

        shutil.copyfile(f"{filepath}/{testEnvName}/backup_yaml.yaml", f"{filepath}/{testEnvName}/{testEnvName}.yaml")        
        shutil.copyfile(f"{filepath}/{testEnvName}/backup_server.py", f"{filepath}/{testEnvName}/server.py")        
        shutil.copyfile(f"{filepath}/{testEnvName}/backup_Dockerfile", f"{filepath}/{testEnvName}/Dockerfile")        

        subprocess.run(f"kubectl delete -f ./troubleshooting/{testEnvName}/{testEnvName}.yaml", shell=True, check=True)
    elif testEnvName == "port_mismatch":
        subprocess.run("docker stop port_mismatch_app", shell=True, check=True)
        subprocess.run("docker rm port_mismatch_app", shell=True, check=True)
        subprocess.run("docker rmi -f marioutsa/kube-port-mismatch-app", shell=True, check=True)
        subprocess.run("docker rmi -f kube-port-mismatch-app", shell=True, check=True)

        os.remove(f"{filepath}/{testEnvName}/{testEnvName}.yaml")
        os.remove(f"{filepath}/{testEnvName}/app_service.yaml")
        os.remove(f"{filepath}/{testEnvName}/server.py")
        os.remove(f"{filepath}/{testEnvName}/Dockerfile")

        shutil.copyfile(f"{filepath}/{testEnvName}/backup_yaml.yaml", f"{filepath}/{testEnvName}/{testEnvName}.yaml")   
        shutil.copyfile(f"{filepath}/{testEnvName}/backup_app_service.yaml", f"{filepath}/{testEnvName}/app_service.yaml")     
        shutil.copyfile(f"{filepath}/{testEnvName}/backup_server.py", f"{filepath}/{testEnvName}/server.py")        
        shutil.copyfile(f"{filepath}/{testEnvName}/backup_Dockerfile", f"{filepath}/{testEnvName}/Dockerfile")        

        subprocess.run(f"kubectl delete -f ./troubleshooting/{testEnvName}/{testEnvName}.yaml", shell=True, check=True)
        subprocess.run(f"kubectl delete -f ./troubleshooting/{testEnvName}/app_service.yaml", shell=True, check=True)

    elif testEnvName == "incorrect_selector":

        subprocess.run("docker stop incorrect_selector_app", shell=True, check=True)
        subprocess.run("docker rm incorrect_selector_app", shell=True, check=True)
        subprocess.run("docker rmi -f marioutsa/kube-incorrect-selector-app", shell=True, check=True)
        subprocess.run("docker rmi -f kube-incorrect-selector-app", shell=True, check=True)

        os.remove(f"{filepath}/{testEnvName}/{testEnvName}.yaml")
        os.remove(f"{filepath}/{testEnvName}/app_service.yaml")
        os.remove(f"{filepath}/{testEnvName}/server.py")
        os.remove(f"{filepath}/{testEnvName}/Dockerfile")

        shutil.copyfile(f"{filepath}/{testEnvName}/backup_yaml.yaml", f"{filepath}/{testEnvName}/{testEnvName}.yaml")   
        shutil.copyfile(f"{filepath}/{testEnvName}/backup_app_service.yaml", f"{filepath}/{testEnvName}/app_service.yaml")     
        shutil.copyfile(f"{filepath}/{testEnvName}/backup_server.py", f"{filepath}/{testEnvName}/server.py")        
        shutil.copyfile(f"{filepath}/{testEnvName}/backup_Dockerfile", f"{filepath}/{testEnvName}/Dockerfile")        

        subprocess.run(f"kubectl delete -f ./troubleshooting/{testEnvName}/{testEnvName}.yaml", shell=True, check=True)
        subprocess.run(f"kubectl delete -f ./troubleshooting/{testEnvName}/app_service.yaml", shell=True, check=True)


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
    file_path = Path("~").expanduser() / "KubeLLM/debug_assistant_latest/result_logs/result_logs_agents_rag_memory.txt"
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

