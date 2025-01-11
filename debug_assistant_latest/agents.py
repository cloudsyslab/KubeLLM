from phi.assistant import Assistant
from phi.llm.openai import OpenAIChat
from phi.llm.ollama import Ollama
from phi.tools.shell import ShellTools
from phi.tools.duckduckgo import DuckDuckGo
from phi.llm.ollama import OllamaTools
import requests
import rag_api
import json
import sys
import os
import subprocess

from utils import traverseRelevantFiles, identifyLLM
from rag_api import (
    BASE_URL,
    initialize_assistant,
    ask_question,
    add_url,
    upload_pdf,
    clear_knowledge_base,
    get_chat_history,
    start_new_run
)

class Agent():
    def __init__(self, agentType, config):
        self.agentProperties = config.get(agentType, None)
        self.config = config
        self.agent = None
        self.prompt = ""

    def prepareAgent(self):
        """ Prepare the assistant based on the config file """
        pass

    def preparePrompt(self):
        """ Prepare the prompt according to the config file """
        pass

    def askQuestion(self):
        """ Ask the formatted prepared question to the agent """
        pass

    def setupAgent(self):
        self.prepareAgent()
        self.preparePrompt()

class AgentAPI(Agent):
    def __init__(self, agentType, config):
        super().__init__(agentType, config)
        self.response = None

    def prepareAgent(self):
        """ Prepare the API Agent based on the config specifications """
        try:
            if self.agentProperties["new-run"]:
                new_run_response = start_new_run()
                print("New Run Response:", new_run_response)

            initialize_response = initialize_assistant(self.agentProperties["model"], self.agentProperties["embedder"])
            print("Initialize Response:", initialize_response)

            if self.agentProperties["clear-knowledge"]:
                clear_kb_response = clear_knowledge_base()
                print("Clear Knowledge Base Response:", clear_kb_response)
            
            for source in self.agentProperties.get("knowledge", []):
                add_url_response = add_url(source)
                print("Add URL Response:", add_url_response)
            
        except Exception as e:
            print(f"Error preparing knowledge agent (API Agent): {e}")
            sys.exit()

    def preparePrompt(self):
        """ Prepare the knowledge prompt according to the config file """
        try:
            self.prompt = self.prompt +" "+ self.config["knowledge-prompt"]["problem-desc"] +" "+ self.config["knowledge-prompt"]["system-prompt"]

            for relevantFileType in ["deployment", "application", "service", "dockerfile"]:
                self.prompt = traverseRelevantFiles(self.config, relevantFileType, self.prompt)

        except Exception as e:
            print(f"Error creating knowledge (API) agent prompt: {e}")
            sys.exit()

    def askQuestion(self):
        """ Ask the formatted prepared question to the knowledge (API) agent """
        try:
            self.response = ask_question(self.prompt)
            print("RAG assistant Response:", self.response)
        except Exception as e:
            print(f"Error asking question to knowledge agent: {e}")
            sys.exit()


class AgentDebug(Agent):
    def __init__(self, agentType, config):
        super().__init__(agentType, config)
        self.agentAPIResponse = None

    def prepareAgent(self):
        """ Prepare the debug assistant based on the config file """
        preparedDebugAssistant = None
        try:
            
            model = identifyLLM(self.agentProperties)
            
            self.agent = Assistant(
                llm=model,
                tools=[ShellTools()], 
                debug_mode=True,
                instructions=[x for x in self.agentProperties["instructions"]],
                show_tool_calls=True,
                read_chat_history=True,
                # tool_call_limit=1
            )
        except Exception as e:
            print(f"Error preparing debug agent: {e}")
            sys.exit()

    def preparePrompt(self):
        """ Prepare the debug agent prompt """
        try:
            for relevantFileType in ["deployment", "application", "service", "dockerfile"]:
                self.prompt = traverseRelevantFiles(self.config, relevantFileType, self.prompt)

            self.prompt = f"{self.prompt} Take the actions provided here: {str(self.agentAPIResponse)}. " +" "+ self.config["debug-prompt"]["additional-directions"]
        except Exception as e:
            print(f"Error creating debug agent prompt: {e}")
            sys.exit()

    def askQuestion(self):
        """ Ask the formatted prepared question to the debug agent """
        try:
            self.agent.print_response(self.prompt)
        except Exception as e:
            print(f"Error asking question to debug agent: {e}")
            sys.exit()


