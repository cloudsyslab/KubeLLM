from main import allStepsAtOnce, stepByStep, singleAgentApproach
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import time
import datetime
from pathlib import Path
from teardown import TEARDOWN_CONFIG, backup_environment, teardown_environment

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
    """Backward-compatible wrapper around teardown.backup_environment()."""
    backup_environment(testEnvName)


def tearDownEnviornment(testEnvName):
    """Backward-compatible wrapper around teardown.teardown_environment()."""
    teardown_environment(testEnvName)

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
