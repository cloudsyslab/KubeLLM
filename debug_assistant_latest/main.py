from agents import AgentAPI, AgentDebug, AgentDebugStepByStep, SingleAgent
from utils import readTheJSONConfigFile, setUpEnvironment, printFinishMessage
import sys, os
from metrics_db import store_metrics_entry, calculate_cost, calculate_totals

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
    metrics = debugAgent.askQuestion()

    # call the verificaiton agent to determine SUCCESS or FAILURE
    #-----------------------------------#
    task_status = True 

    #-----------------------------------#
    
    # Calculate the cost
    cost = calculate_cost(metrics.get("model"), metrics.get("input_tokens"), metrics.get("output_tokens"))

    # Store metrics entry into the database
    db_path = os.path.expanduser("~/KubeLLM/token_metrics.db")

    store_metrics_entry(
        db_path, metrics.get('test_case'), metrics.get("model"),
        metrics.get("input_tokens"), metrics.get("output_tokens"), 
        metrics.get("total_tokens"), int(task_status), cost
    )

    
    printFinishMessage()

    return debugAgent.debugStatus

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




    



