class Agent:
    def __init__(self, agentType, config):
        self.agentProperties = config.get(agentType, None)
        self.config = config
        self.agent = None
        self.prompt = ""
        self.runtime_context = {}

    def prepareAgent(self):
        """Prepare the assistant based on the config file."""
        raise NotImplementedError

    def preparePrompt(self):
        """Prepare the prompt according to the config file."""
        raise NotImplementedError

    def askQuestion(self):
        """Ask the formatted prepared question to the agent."""
        raise NotImplementedError

    def setupAgent(self):
        self.prepareAgent()
        self.preparePrompt()
