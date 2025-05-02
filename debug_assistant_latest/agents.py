from phi.assistant import Assistant
from phi.agent import Agent as llmAgent
from phi.llm.openai import OpenAIChat
from phi.model.google import Gemini
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
from better_shell import BetterShellTools
from phi.model.openai import OpenAIChat
from phi.model.ollama import Ollama



from phi.agent import AgentKnowledge
from phi.vectordb.pgvector import PgVector, SearchType
from phi.storage.agent.postgres import PgAgentStorage
from phi.knowledge.website import WebsiteKnowledgeBase


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
            
            initialize_response = initialize_assistant(self.agentProperties["model"], self.agentProperties["embedder"] )
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
            #print("RAG assistant Response:", self.response)
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
            
            model_name = self.agentProperties["model"]
            if any(token in model_name for token in ['gpt', 'o3', 'o4', 'o1']):
                model = OpenAIChat(id=model_name)
            elif 'llama' in model_name:
                model = Ollama(id=model_name)
            elif 'gemini' in model_name:
                model = Gemini(id=model_name)
            else:
                raise Exception("Invalid model name provided.")

            self.agent = llmAgent(
                model=model,
                tools=[BetterShellTools()], 
                debug_mode=True,
                instructions=[x for x in self.agentProperties["instructions"]],
                show_tool_calls=True,
                #read_chat_history=True,
                # tool_call_limit=1
                markdown=True,
                guidelines=[x for x in self.agentProperties["guidelines"]]
                #add_history_to_messages=True,
                #num_history_responses=3
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
            prompt += "Do not use live feed flags when checking the logs such as 'kubectl logs -f'"
            response = self.agent.run(prompt)
            response = response.content

            if "<|ERROR|>" in response or "<|FAILED|>" in response:
                self.debugStatus = False
            elif "<|SOLVED|>" in response:
                self.debugStatus = True
            else:
                self.debugStatus = False
            return
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

            model_name = self.agentProperties["model"]
            if any(token in model_name for token in ['gpt', 'o3', 'o4', 'o1']):
                model = OpenAIChat(id=model_name)
            elif 'llama' in model_name:
                model = Ollama(id=model_name)
            elif 'gemini' in model_name:
                model = Gemini(id=model_name)
            else:
                raise Exception("Invalid model name provided.")
            
            #model = Gemini(id="gemini-1.5-flash")
            #OpenAIChat(id="gpt-4o")
            #OpenAIChat(id="o3-mini")
            #Ollama(id="llama3.3")
            #OpenAIChat(id="gpt-4o")

            self.agent = llmAgent(
                model=model,
                tools=[BetterShellTools()], 
                debug_mode=True,
                show_tool_calls=True,
                markdown=True,
                instructions=[x for x in self.agentProperties["instructions"]],
                guidelines=[x for x in self.agentProperties["guidelines"]]
                #add_history_to_messages=True,
                #num_history_responses=3
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
                prompt += f'If you struggle within one of the steps try to figure out the solution until you see the pod running fine with kubectl describe.'
                prompt += f"\nThe relevant configuration file is located in this path: {self.config['test-directory']+self.config['yaml-file-name']}\n"
                prompt += "You can update these files if necessary. If any files are updated, make sure to delete and reapply the configuration file.\n"
                prompt += "If you need to update a pod then use kubectl replace --force [POD_NAME]"
                prompt += f"\nThis is step {i} out of {numSteps}."
                prompt += "Do not use live feed flags when checking the logs such as 'kubectl logs -f'"

                response = self.agent.run(prompt)
                response = response.content


                if "<|ERROR|>" in response or "<|FAILED|>" in response:
                    self.debugStatus = False
                elif "<|SOLVED|>" in response:
                    self.debugStatus = True
                else:
                    self.debugStatus = False
                    
        except Exception as e:
            print(f"Failed to execute problem steps : {e}")
            sys.exit()

class SingleAgent(Agent):
    def __init__(self, agentType, config):
        super().__init__(agentType, config)
        self.knowledgeResponse = None
        self.debugStatus = None

    def prepareAgent(self):
        """ Prepare the debug assistant based on the config file """
        try:
            
            model = OpenAIChat(id="o3-mini")
            #OpenAIChat(id="gpt-4o")
            #OpenAIChat(id="gpt-4o")
            #Ollama(id="llama3.3")
            #OpenAIChat(id="o3-mini")
            #Gemini(id="gemini-1.5-flash")
            
            knowledge_base = WebsiteKnowledgeBase(
                urls=self.config["api-agent"].get("knowledge", []),
                # Number of links to follow from the seed URLs
                max_links=10,
                # Table name: ai.website_documents
                vector_db=PgVector(
                    table_name="ai.local_rag_documents_singleAgent",
                    db_url="postgresql+psycopg://ai:ai@localhost:5532/ai",
                ),
            )


            additionalInstructions = ["Carefully read the information the user provided.", 
                                      "Run diagnostic commands yourself, then use the output to further help you.", 
                                      "Do not use live feed flags when checking the logs such as 'kubectl logs -f'",
                                      "Do not use commands that would open an editor like 'kubectl edit'",
                                      "DO NOT BY ANY MEANS USE kubectl edit"
                                    ]
            
            
            additionalGuidelines = [ "You will run the commands as Instructed! Please feel free to change it if necessary and if it makes sense to! You will solve the issue and run the commands!", 
                                    "When writing out your commands, use the real name of the Kubernetes resource instead of placeholder names. For example, if your command is `kubectl get pods -n <namespace>`, run `kubectl get namespaces` first to get available namespaces.", 
                                    "Do not use live feed flags when checking the logs such as 'kubectl logs -f'", 
                                    "When executing the shell commands please feel free to figure out whether or not it the command worked.",
                                    "Do not use commands that would open an editor like 'kubectl edit'",
                                    "DO NOT BY ANY MEANS USE kubectl edit"
                                    ]

            self.agent = llmAgent(
                model=model,
                tools=[BetterShellTools()], 
                debug_mode=True,
                instructions=[x for x in self.config["debug-agent"]["instructions"]] + additionalInstructions,
                show_tool_calls=True,
                #read_chat_history=True,
                #tool_call_limit=1,
                markdown=True,
                guidelines=[x for x in self.config["debug-agent"]["guidelines"]] + additionalGuidelines,
                knowledge=knowledge_base,
                search_knowledge=True,
                prevent_hallucinations=True,
                description="You are an AI called 'RAGit'. You come up with commands and execute them step by step in order to fix kubernetes issues.",
                task="Proivde the automated assistance in fixing kubernetes issues by executing commands that are relevant to the problem."
                #add_history_to_messages=True,
                #num_history_responses=3
            )
        except Exception as e:
            print(f"Error preparing debug agent: {e}")
            sys.exit()

    def preparePrompt(self):
        """ Prepare the debug agent prompt """
        try:
            for relevantFileType in ["deployment", "application", "service", "dockerfile"]:
                self.prompt = traverseRelevantFiles(self.config, relevantFileType, self.prompt)

            self.prompt = f"{self.prompt} " +" "+ self.config["debug-prompt"]["additional-directions"]
        
            self.prompt += f'Perform the actions that seem to be the most applicable in the current step'
            self.prompt += f"\nThe relevant configuration file is located in this path: {self.config['test-directory']+self.config['yaml-file-name']}\n"
            self.prompt += "You can update these files if necessary. If any files are updated, make sure to delete and reapply the configuration file.\n"
            self.prompt += "Do not use live feed flags when checking the logs such as 'kubectl logs -f'"
            self.prompt += "Do not use commands that would open an editor like 'kubectl edit'"
            self.prompt += "You will run the commands as Instructed! Please feel free to change it if necessary and if it makes sense to! You will solve the issue and run the commands!"
            self.prompt += "DO NOT BY ANY MEANS USE kubectl edit"
        except Exception as e:
            print(f"Error creating debug agent prompt: {e}")
            sys.exit()


    def askQuestion(self):
        """ Ask the formatted prepared question to the knowledge (API) agent """
        try:
            response = self.agent.run(self.prompt)
            response = response.content

            if "<|SOLVED|>" in response:
                self.debugStatus = True
            elif "<|ERROR|>" in response or "<|FAILED|>" in response:
                self.debugStatus = False
            return
            
        except Exception as e:
            print(f"Error asking question to knowledge agent: {e}")
            sys.exit()
