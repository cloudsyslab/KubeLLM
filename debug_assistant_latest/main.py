from agents import AgentAPI, AgentDebug
from utils import readTheJSONConfigFile, setUpEnvironment


def getAgents(config):
    apiAgent = AgentAPI("api-agent" , config)
    debugAgent = AgentDebug("debug-agent" , config)
    return apiAgent, debugAgent

def run():
    config = readTheJSONConfigFile()
    setUpEnvironment(config)
    apiAgent, debugAgent = getAgents(config)

    apiAgent.setupAgent()
    debugAgent.setupAgent()

    apiAgent.askQuestion()

    debugAgent.agentAPIResponse = apiAgent.response
    debugAgent.askQuestion()

    print("=================================================")
    print("                   FINISHED                      ")
    print("=================================================")


if __name__ == "__main__":
    run()




    



