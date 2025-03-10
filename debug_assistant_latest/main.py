from agents import AgentAPI, AgentDebug, AgentDebugStepByStep, SingleAgent
from utils import readTheJSONConfigFile, setUpEnvironment, printFinishMessage
import sys, os

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
    debugAgent.askQuestion()

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
        print ('config file not provided')
        sys.exit(1)

    configFile = sys.argv[1]
    if os.path.exists(configFile):
        run("allStepsAtOnce", configFile)
    else:
        print (f'{configFile} does not exist')




    



