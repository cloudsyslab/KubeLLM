from agent_base import Agent
from rag_api import (
    add_url,
    ask_question,
    clear_knowledge_base,
    initialize_assistant,
    start_new_run,
)
from utils import traverseRelevantFiles


class AgentAPI(Agent):
    def __init__(self, agentType, config):
        super().__init__(agentType, config)
        self.response = None

    def prepareAgent(self):
        """Prepare the API agent based on the config specifications."""
        try:
            if self.agentProperties["new-run"]:
                new_run_response = start_new_run()
                print("New Run Response:", new_run_response)

            initialize_response = initialize_assistant(
                self.agentProperties["model"],
                self.agentProperties["embedder"],
            )
            print("Initialize Response:", initialize_response)

            if self.agentProperties["clear-knowledge"]:
                clear_kb_response = clear_knowledge_base()
                print("Clear Knowledge Base Response:", clear_kb_response)

            for source in self.agentProperties.get("knowledge", []):
                add_url_response = add_url(source)
                print("Add URL Response:", add_url_response)

        except Exception as e:
            raise RuntimeError(f"Error preparing knowledge agent (API Agent): {e}") from e

    def preparePrompt(self):
        """Prepare the knowledge prompt according to the config file."""
        try:
            self.prompt = (
                self.prompt
                + " "
                + self.config["knowledge-prompt"]["problem-desc"]
                + " "
                + self.config["knowledge-prompt"]["system-prompt"]
            )

            for relevantFileType in ["deployment", "application", "service", "dockerfile"]:
                self.prompt = traverseRelevantFiles(self.config, relevantFileType, self.prompt)

        except Exception as e:
            raise RuntimeError(f"Error creating knowledge (API) agent prompt: {e}") from e

    def askQuestion(self):
        """Ask the formatted prepared question to the knowledge agent."""
        try:
            self.response = ask_question(self.prompt)
        except Exception as e:
            raise RuntimeError(f"Error asking question to knowledge agent: {e}") from e
