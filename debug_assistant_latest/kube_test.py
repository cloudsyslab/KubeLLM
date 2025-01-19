from main import allStepsAtOnce, stepByStep
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import time


def selectTestFunc(testName):
    """ return the test function based on the test name given """
    if testName == "allStepsAtOnce":
        return allStepsAtOnce
    elif testName == "stepByStep":
        return stepByStep
    else:
        return None

def runSingleTest(testFunc, configFile):
    """ Run the test and collect the results from the run """
    startTime = time.time()
    result = testFunc(configFile = configFile)
    endTime = time.time()
    totalTime = endTime - startTime

    return {"TimeTaken":totalTime,"Result":result}

def run():
    """ main runner function which is responsilbe for setting up and running all tests """
    numTests = 10
    testName = "stepByStep"
    testFunc = selectTestFunc(testName)
    configFile = "/home/mario/KubeLLM_latest/KubeLLM-main/debug_assistant_latest/troubleshooting/readiness_failure/config_step.json"
    allTestResults = {}
    if testFunc:
        for testNumber in range(numTests):
            print(f"Running Test Number : {testNumber}")
            testResults = runSingleTest(testFunc, configFile)
            allTestResults[testNumber] = testResults

        allTestResultsDF = pd.DataFrame(allTestResults).T
        
        print("Finished All Tests!")
        print(allTestResultsDF)
    else:
        print(f"Could not find test : {testName}")


if __name__ == "__main__":
    run()

