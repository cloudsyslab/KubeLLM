from agents import AgentAPI, AgentDebug, AgentDebugStepByStep, SingleAgent, AgentVerification_v1, AgentVerification_v2
from utils import readTheJSONConfigFile, setUpEnvironment, printFinishMessage
import sys, os
from metrics_db import store_metrics_entry, calculate_cost, calculate_totals
import time
from pathlib import Path

# Use relative path from script location
SCRIPT_DIR = Path(__file__).parent.absolute()
db_path = str(SCRIPT_DIR.parent / "token_metrics.db")

# Validate that parent directory exists (should be repo root)
if not SCRIPT_DIR.parent.exists():
    raise FileNotFoundError(
        f"Repository root directory not found: {SCRIPT_DIR.parent}\n"
        f"This script should be run from within the repository structure."
    )

def allStepsAtOnce(configFile = None):
    """
        This function will run the knowledge agent and debug agent. 
        When the debug agent receives the response from the knowledge
        agent, the debug agent will run all the commands all at once.

        Approach by: William Clifford
    """

    #read config to initilize enviornment
    config = readTheJSONConfigFile(configFile = configFile)
    setUpEnvironment(config)
    #initilize needed LLMs
    apiAgent = AgentAPI("api-agent" , config)
    debugAgent = AgentDebug("debug-agent" , config)
    #set up the LLMs
    apiAgent.setupAgent()
    debugAgent.setupAgent()

    #Run the LLMs as needed
    apiAgent.askQuestion()
    debugAgent.agentAPIResponse = apiAgent.response
    debug_start_time = time.perf_counter()
    debug_metrics = debugAgent.askQuestion()
    debug_end_time = time.perf_counter()
    debug_duration_s = debug_end_time - debug_start_time

    # Calculate the cost
    debug_cost = calculate_cost(debug_metrics.get("model"), debug_metrics.get("input_tokens"), debug_metrics.get("output_tokens"))
    
    # call the verification agent to determine SUCCESS or FAILURE
    #-----------------------------------#
    print("\n" + "="*80)
    print("STARTING VERIFICATION PHASE")
    print("="*80 + "\n")
    
    verificationAgent = AgentVerification_v2("verification-agent", config)
    verificationAgent.setupAgent()
    
    # Pass the debug agent's response to the verification agent
    verificationAgent.debugAgentResponse = debugAgent.response if debugAgent.response else "Debug agent completed execution"
    
    # Run verification
    verification_start_time = time.perf_counter()
    verification_metrics = verificationAgent.askQuestion()
    verification_end_time = time.perf_counter()
    verification_duration_s = verification_end_time - verification_start_time
    
    # If verification returns None (error or unknown), fall back to debug agent's self-reported status
    #if verificationAgent.verificationStatus is None:
    #    print("⚠ Warning: Verification agent could not determine status. We consider the task FAILED.")
    #    task_status = False
    
    print(f"\nFinal Task Status: {'SUCCESS' if verificationAgent.verificationStatus else 'FAILURE'}")
    print(f"Debug Agent Self-Report: {'SUCCESS' if debugAgent.debugStatus else 'FAILURE'}")
    print(f"Verification Agent Report: {'VERIFIED' if verificationAgent.verificationStatus else 'FAILED' if verificationAgent.verificationStatus is False else 'UNKNOWN'}\n")

    #-----------------------------------#
    
    # Calculate the cost
    verification_cost = calculate_cost(verification_metrics.get("model"), verification_metrics.get("input_tokens"), verification_metrics.get("output_tokens"))

    # Update debug_metrics and verification_metrics
    debug_metrics["duration_s"] = round(debug_duration_s, 2)
    debug_metrics["cost"] = round(debug_cost, 4)
    verification_metrics["duration_s"] = round(verification_duration_s, 2)
    verification_metrics["cost"] = round(verification_cost, 4)

    # Store metrics entry into the database
    store_metrics_entry(db_path, debug_metrics, verification_metrics.get("task_status"))
    store_metrics_entry(db_path, verification_metrics, verification_metrics.get("task_status"))
    printFinishMessage()

    return verificationAgent.verificationStatus  # Return verification result instead of debug agent's self-report

def stepByStep( configFile = None ):
    """
        This function will run the knowledge and debug agent. 
        The knowledge agent will return the response with steps to run
        with a bash script for each step nicely formatted for the debug agent
        to then breakdown the steps and run it step by step, while trying to 
        fix issues with each step if any.

        Approach by: Aaron Perez
    """
    #read config to initilize enviornment
    config = readTheJSONConfigFile( configFile = configFile)
    setUpEnvironment(config)
    #initilize needed LLMs
    apiAgent = AgentAPI("api-agent" , config)
    debugAgent = AgentDebugStepByStep("debug-agent" , config)
    #set up the LLMs
    apiAgent.setupAgent()
    debugAgent.setupAgent()

    #Run the LLMs as needed
    apiAgent.askQuestion()
    debugAgent.agentAPIResponse = apiAgent.response
    debugAgent.formProblemSolvingSteps()
    debugAgent.executeProblemSteps()
    printFinishMessage()

    return debugAgent.debugStatus


def singleAgentApproach( configFile = None ):
    """
        This function will run a single agent which will do the
        reasoning on top of the actioning
    """
    #read config to initilize enviornment
    config = readTheJSONConfigFile( configFile = configFile)
    setUpEnvironment(config)
    #initilize needed LLMs
    agent = SingleAgent("single-agent", config)
    #set up the LLMs
    agent.setupAgent()

    #Run the LLMs as needed
    agent.askQuestion()
    #agent.knowledgeResponse
    #agent.takeAction()

    return agent.debugStatus


def run( debugType, configFile ):
    if debugType == "allStepsAtOnce":
        allStepsAtOnce(configFile)
    elif debugType == "stepByStep":
        stepByStep(configFile)
    elif debugType == "singleAgent":
        singleAgentApproach(configFile)
    return

if __name__ == "__main__":
    if (len(sys.argv) < 2):
        print('Usage: python3 main.py <config_file> [test_type]')
        print('Available test types: allStepsAtOnce, stepByStep, singleAgent (default: allStepsAtOnce)')
        sys.exit(1)

    configFile = sys.argv[1]
    
    # Get test type from second argument, default to "allStepsAtOnce"
    testType = sys.argv[2] if len(sys.argv) > 2 else "allStepsAtOnce"
    
    # Validate test type
    validTestTypes = ["allStepsAtOnce", "stepByStep", "singleAgent"]
    if testType not in validTestTypes:
        print(f'Invalid test type: {testType}')
        print(f'Available test types: {", ".join(validTestTypes)}')
        sys.exit(1)
    
    if os.path.exists(configFile):
        run(testType, configFile)
    else:
        print (f'{configFile} does not exist')




    



