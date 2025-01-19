from phi.assistant import Assistant
from phi.agent import Agent as StepAgent
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
from utils import traverseRelevantFiles, identifyLLM, withTimeout
import re
import timeout_decorator

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
        self.debugStatus = None

    def prepareAgent(self):
        """ Prepare the debug assistant based on the config file """
        try:
            
            model = identifyLLM(self.agentProperties)
            
            self.agent = Assistant(
                model=model,
                tools=[ShellTools()], 
                debug_mode=True,
                instructions=[x for x in self.agentProperties["instructions"]],
                show_tool_calls=True,
                read_chat_history=True,
                # tool_call_limit=1
                markdown=True,
                guidelines=[x for x in self.agentProperties["guidelines"]]
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

    @timeout_decorator.timeout(480)
    @withTimeout(False)
    def askQuestion(self):
        """ Ask the formatted prepared question to the debug agent """
        try:
            

            prompt = f'Perform the action suggested here: \n{self.agentAPIResponse}\n'
            prompt += f"\nThe relevant configuration file is located in this path: {self.config['test-directory']+self.config['yaml-file-name']}\n"
            prompt += "You can update these files if necessary. If any files are updated, make sure to delete and reapply the configuration file.\n"

            response = "".join(self.agent.run(prompt))

            if "<|ERROR|>" in response or "<|FAILED|>" in response:
                self.debugStatus = False
                return False
            elif "<|SOLVED|>" in response:
                self.debugStatus = True
                return True
            else:
                self.debugStatus = False
                return False

        except Exception as e:
            print(f"Error asking question to debug agent: {e}")
            sys.exit()


class AgentDebugStepByStep(Agent):
    def __init__(self, agentType, config):
        super().__init__(agentType, config)
        self.agentAPIResponse = None
        self.debugStatus = None

    def prepareAgent(self):
        """ Prepare the debug assistant based on the config file """
        try:
            model = identifyLLM(self.agentProperties)
            self.agent = Assistant(
                model=model,
                tools=[ShellTools()], 
                debug_mode=True,
                show_tool_calls=True,
                markdown=True,
                instructions=[x for x in self.agentProperties["instructions"]],
                guidelines=[x for x in self.agentProperties["guidelines"]]
            )
        except Exception as e:
            print(f"Error preparing debug agent: {e}")
            sys.exit()

    def preparePrompt(self):
        """ Prepare the debug agent prompt """
        try:

            self.prompt = f"Troubleshoot the Kubernetes issue described: {self.config['knowledge-prompt']['problem-desc']}"

            for relevantFileType in ["deployment", "application", "service", "dockerfile"]:
                self.prompt = traverseRelevantFiles(self.config, relevantFileType, self.prompt)

            self.prompt += "Use `kubectl` commands to gather information, and provide a series of shell commands for the user to resolve the issue."

        except Exception as e:
            print(f"Error creating debug agent prompt: {e}")
            sys.exit()

    def formProblemSolvingSteps(self):
        """ From the resonse generate a list of steps that the debug agent will execute one by one """
        self.steps = []

        try:    
            knowledgeAIRespnseString = str(self.agentAPIResponse)

            bashCommands = re.findall(r"``bash\\n(.*?)\\n```", knowledgeAIRespnseString, re.DOTALL)
            bashCommandsList = [cmd.strip() for cmd in bashCommands]
            
            self.steps = bashCommandsList

        except Exception as e:
            print(f"Failed to generate steps to problem: {e}")
            sys.exit()

    @timeout_decorator.timeout(480)
    @withTimeout(False)
    def executeProblemSteps(self):
        """ Once we have formed all of the steps based on the knowledge agent, then we can start to execute each step one by one """
        try:            
            numSteps = len(self.steps)
            for i, step in enumerate(self.steps, start=1):
                
                prompt = f'Perform the action suggested here: \n{step}\n'
                prompt += f"\nThe relevant configuration file is located in this path: {self.config['test-directory']+self.config['yaml-file-name']}\n"
                prompt += "You can update these files if necessary. If any files are updated, make sure to delete and reapply the configuration file.\n"
                prompt += f"\nThis is step {i} out of {numSteps}."
                
                response = "".join(self.agent.run(prompt))

                if "<|ERROR|>" in response or "<|FAILED|>" in response:
                    self.debugStatus = False
                    return False
                elif "<|SOLVED|>" in response:
                    self.debugStatus = True
                    return True
                else:
                    self.debugStatus = False
                    return False

        except Exception as e:
            print(f"Failed to execute problem steps : {e}")
            sys.exit()




