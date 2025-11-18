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

STATUS_MAP = {
    True: 1,
    False: 0,
    None: -1
}

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
        self.response = None  # Store the debug agent's response for verification

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

    @withTimeout(False)
    @timeout_decorator.timeout(480)
    def askQuestion(self):
        """ Ask the formatted prepared question to the debug agent """
        try:
            prompt = f'Perform the actions suggested here: \n{self.agentAPIResponse}\n'
            prompt += f"\nThe relevant configuration file is located in this path: {self.config['test-directory']+self.config['yaml-file-name']}\n"
            prompt += "You can update these files if necessary. If any files are updated, make sure to delete and reapply the configuration file.\n"
            prompt += "Do not use live feed flags when checking the logs such as 'kubectl logs -f'\n"
            prompt += (
    "### Tool Usage Rules\n"
    "- Do not attempt many commands in one tool call.\n"
    "- Never repeat a tool call that has already been executed successfully in this run.\n"
    "- If you need the result of a previous tool call, use the provided output rather than re-invoking it.\n"
    "- Keep the tool call as simple as possible to avoid errors.\n"
    #"- After a successful tool call, decide the next step based solely on the tool’s output, not by re-issuing the same command.\n"
)

            response = self.agent.run(prompt, return_response=True)
            response_content = response.content
            
            # Store the response for verification agent
            self.response = response_content
            
            metrics = response.metrics or {}  # Fallback to empty dict if None
            input_tokens = sum(metrics.get("input_tokens", []))
            output_tokens = sum(metrics.get("output_tokens", []))
            total_tokens = sum(metrics.get("total_tokens", []))
            model_name = response.model  
            agent_type = 'debug'
            
            # SUCCESS or FAILURE should be determined by a verification agent
            # the following debugStatus is still useful to demonstrate the need for verification agent
            if "<|ERROR|>" in response_content or "<|FAILED|>" in response_content:
                self.debugStatus = False
            elif "<|SOLVED|>" in response_content:
                self.debugStatus = True
            else:
                self.debugStatus = False
            
            # Save metrics
            metrics_entry = {
                "test_case": self.config['test-name'],    
                "model": model_name,
                "agent_type": agent_type,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "task_status": int(self.debugStatus)
            }
            return metrics_entry
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

            bashCommands = re.findall(r"``bash\\n\s*(.*?)\\n\s*```", knowledgeAIRespnseString, re.DOTALL)
            bashCommandsList = [cmd.strip() for cmd in bashCommands]
            print(knowledgeAIRespnseString)
            print(bashCommands)
            print(bashCommandsList)
            self.steps = bashCommandsList

        except Exception as e:
            print(f"Failed to generate steps to problem: {e}")
            sys.exit()

    @withTimeout(False)
    @timeout_decorator.timeout(480)
    def executeProblemSteps(self):
        """ Once we have formed all of the steps based on the knowledge agent, then we can start to execute each step one by one """
        # Define tool usage rules once
        tool_rules = (
           "### Tool Usage Rules\n"
           "- Do not attempt many commands in one tool call.\n"
           "- Never repeat a tool call that has already been executed successfully in this run.\n"
           "- If you need the result of a previous tool call, use the provided output rather than re-invoking it.\n"
           "- After a successful tool call, decide the next step based solely on the tool’s output, not by re-issuing the same command.\n"
        )

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
                
                # Append the tool usage rules
                prompt += tool_rules

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


class AgentVerification_v2(Agent):
    """
    Verification agent that checks whether the debug agent successfully resolved the Kubernetes issue.
    This agent runs diagnostic commands to verify the actual state of the cluster and files.
    """

    def __init__(self, agentType, config):
        super().__init__(agentType, config)
        self.debugAgentResponse = None
        self.verificationStatus = None
        self.verificationReport = None
        
        # Default instructions 
        self.default_instructions = [
            "You are a verification agent tasked with verifying whether the described Kubernetes issue has been fixed.",
            "Run diagnostic commands to check the current state of the cluster.",
            "Always verify that the pods are running",
            "Since this Kubernetes cluster is running on Minikube, use the minikube service command to access services when appropriate."
            "Do not use live feed flags when checking the logs such as 'kubectl logs -f'",
            "If kubectl logs fails, wait 5-10 seconds and try again up to 3 times",
            "If logs are still unavailable after retries, you can still verify based on pod status and output of specific diagnostic command that will be provided to you",
            "Use <|VERIFIED|> if the pod is Running and the kubectl or minikube diagnostic commands indicate success, even if logs are temporarily unavailable)",
            "After completing verification, you must conclude with EXACTLY one of these tokens:",
            "- <|VERIFIED|> if the issue has been completely fixed",
            "- <|FAILED|> if the issue has NOT been fixed",
            "- <|VERIFICATION_ERROR|> only if you cannot check files or pod status at all",
            "DO NOT create your own tokens. Use ONLY the three tokens listed above."
        ]

        # Default guidelines
        self.default_guidelines = [
            "If pod logs are temporarily unavailable, this is acceptable",
            "The PRIMARY verification is: pod is Running and output of kubectl or minikube based diagnostic commands.",
            "Log verification is secondary - if unavailable, ignore it. You can verify without logs",
            "You MUST use one of the three specified tokens: <|VERIFIED|>, <|FAILED|>, or <|VERIFICATION_ERROR|>"
        ]

    def prepareAgent(self):
        """ Prepare the verification agent based on the config file """
        # agentProperties can be None if verification-agent is not in config - that's okay, we'll use defaults
        try:
            # Get model and temperature from config or use defaults
            if self.agentProperties:
                model_name = self.agentProperties.get("model", "gpt-4o")
                temperature = self.agentProperties.get("temperature", 0.3)
            else:
                model_name = "gpt-4o"
                temperature = 0.3
            
            if any(token in model_name for token in ['gpt', 'o3', 'o4', 'o1']):
                model = OpenAIChat(id=model_name, temperature=temperature)
            elif 'llama' in model_name:
                model = Ollama(id=model_name, temperature=temperature)
            elif 'gemini' in model_name:
                model = Gemini(id=model_name, temperature=temperature)
            else:
                raise Exception("Invalid model name provided for verification agent.")

            # Use config instructions/guidelines if provided, otherwise use defaults
            if self.agentProperties:
                instructions = self.agentProperties.get("instructions", self.default_instructions)
                guidelines = self.agentProperties.get("guidelines", self.default_guidelines)
            else:
                instructions = self.default_instructions
                guidelines = self.default_guidelines

            self.agent = llmAgent(
                model=model,
                tools=[BetterShellTools()], 
                debug_mode=True,
                instructions=instructions,
                show_tool_calls=True,
                markdown=True,
                guidelines=guidelines
            )
        except Exception as e:
            print(f"Error preparing verification agent: {e}")
            raise  # Re-raise the exception instead of sys.exit()

    def preparePrompt(self):
        """ Prepare the verification agent prompt - fully generic, no problem-specific config needed """
        try:
            # Start with the problem description
            
            self.prompt = f"""You are a precise Kubernetes Verification Agent. Your only goal is to determine, with evidence, whether the original problem described below has been fully resolved in the current cluster state.
            
            ### ORIGINAL PROBLEM TO VERIFY
            {self.config['knowledge-prompt']['problem-desc'].strip()}
            
            ### VERIFICATION RULES (STRICTLY FOLLOW)
            1. **Never assume** the problem is fixed. You must prove it with real commands and observed output.
            2. Always start verification using `kubectl` (never guess pod/service names).
            3. Use exact resource names extracted from the YAML manifests — do not invent them.
            4. If a command fails or a resource does not exist, clearly state that and do not proceed as if it succeeded.
            5. Only declare the issue resolved if all relevant pods are Running/Ready and the service (if applicable) is reachable from outside the cluster.
            
            ### RELEVANT MANIFESTS (use these to find exact names)
            """
            # Insert the actual file contents or summaries (better than just paths)
            for relevantFileType in ["deployment", "application", "service"]:
                self.prompt = traverseRelevantFiles(self.config, relevantFileType, self.prompt)  # prefer including YAML snippets
            
            self.prompt += f"""
            ### CURRENT CONTEXT
            - Working directory: {self.config['test-directory']}
            - Main configuration file: {self.config.get('yaml-file-name', 'N/A')}
            - Minikube profile: {self.config.get('minikube-profile', 'lamap')}
            
            ### STEP-BY-STEP VERIFICATION PROCEDURE (follow exactly in order)
            1. Run `kubectl get pods` → confirm all expected pods exist and are in Running state with 1/1 (or expected) ready containers.
            2. For each expected pod, run `kubectl describe pod <pod-name>` and check Events for errors (CrashLoopBackOff, ImagePullBackOff, OOM, etc.).
            3. If relevant service YAML exists, run `kubectl get service <service-name>` → confirm expected Service exists and has ClusterIP assigned.
            4. If a Service is running:
               - Run: `minikube -p {self.config.get('minikube-profile', 'minikube')} service <service-name> --url`
               - Take the URL(s) returned and test with `curl -v <url>` 
            5. If Ingress exists, get the ingress address and test the hostname/path with curl.
            """
        except Exception as e:
            print(f"Error creating verification agent prompt: {e}")
            sys.exit()

    @timeout_decorator.timeout(480)
    @withTimeout(None)
    def askQuestion(self):
        """ Ask the verification agent to verify the fix """
        try:
            prompt = self.prompt
            prompt += (
               "\n### TOOL USAGE RULES \n"
               "- Never repeat a tool call that has already been executed successfully in this run.\n"
               "- If you need the result of a previous tool call, use the provided output rather than re-invoking it.\n"
            )
            prompt += "\n\n=== CRITICAL: USE EXACT TOKENS ===\n"
            prompt += "You MUST conclude with EXACTLY one of these three tokens:\n"
            prompt += "1. <|VERIFIED|> if the issue has been completely resolved\n"
            prompt += "2. <|FAILED|> if the issue has NOT been fixed\n"
            prompt += "3. <|VERIFICATION_ERROR|> if you encountered errors during verification\n\n"
            prompt += "DO NOT make up your own tokens like <|FIX_VERIFIED_FAILED|> or anything else.\n"
            prompt += "Use ONLY: <|VERIFIED|>, <|FAILED|>, or <|VERIFICATION_ERROR|>\n"
            
            response = self.agent.run(prompt)
            self.verificationReport = response.content

            if "<|VERIFIED|>" in self.verificationReport:
                self.verificationStatus = True
                print("\n" + "="*80)
                print("VERIFICATION STATUS: ✓ VERIFIED")
                print("The issue has been completely resolved")
                print("="*80 + "\n")
            elif "<|FAILED|>" in self.verificationReport:
                self.verificationStatus = False
                print("\n" + "="*80)
                print("VERIFICATION STATUS: ✗ FAILED")
                print("The issue has NOT been fixed")
                print("="*80 + "\n")
            elif "<|VERIFICATION_ERROR|>" in self.verificationReport:
                self.verificationStatus = None
                print("\n" + "="*80)
                print("VERIFICATION STATUS: ⚠ ERROR")
                print("Encountered errors during verification")
                print("="*80 + "\n")
            else:
                self.verificationStatus = None
                print("\n" + "="*80)
                print("VERIFICATION STATUS: ? UNKNOWN")
                print("No verification status token found in response")
                print("="*80 + "\n")
            
            metrics = response.metrics or {}  # Fallback to empty dict if None
            input_tokens = sum(metrics.get("input_tokens", []))
            output_tokens = sum(metrics.get("output_tokens", []))
            total_tokens = sum(metrics.get("total_tokens", []))
            model_name = response.model
            agent_type = 'verification'
            
            # Save metrics
            metrics_entry = {
                "test_case": self.config['test-name'],
                "model": model_name,
                "agent_type": agent_type,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "task_status": STATUS_MAP.get(self.verificationStatus, -1),
                "duration_s": 0,
                "cost": 0
            }
            return metrics_entry

        except Exception as e:
            print(f"Error during verification: {e}")
            self.verificationStatus = None

            metrics_entry = {
                "test_case": self.config['test-name'],
                "model": self.config['verification-agent']['model'],
                "agent_type": 'verification',
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "task_status": -1,
                "duration_s": 0,
                "cost": 0
            }
            return metrics_entry

class AgentVerification_v1(Agent):
    """
    Verification agent that checks whether the debug agent successfully resolved the Kubernetes issue.
    This agent runs diagnostic commands to verify the actual state of the cluster and files.
    """

    def __init__(self, agentType, config):
        super().__init__(agentType, config)
        self.debugAgentResponse = None
        self.verificationStatus = None
        self.verificationReport = None
        
        # Default instructions 
        self.default_instructions = [
            "You are a verification agent tasked with verifying whether the debug agent successfully resolved the Kubernetes issue.",
            "Run diagnostic commands to check the current state of the cluster.",
            "Verify that the fixes claimed by the debug agent were actually applied.",
            "Always check the actual file contents using commands like 'cat' or 'grep'",
            "Do not use live feed flags when checking the logs such as 'kubectl logs -f'",
            "If kubectl logs fails, wait 5-10 seconds and try again up to 3 times",
            "If logs are still unavailable after retries, you can still verify based on file contents and pod status",
            "Use <|VERIFIED|> if the YAML file has the correct changes AND pod is Running (even if logs temporarily unavailable)",
            "After completing verification, you must conclude with EXACTLY one of these tokens:",
            "- <|VERIFIED|> if the issue has been completely fixed",
            "- <|FAILED|> if the issue has NOT been fixed",
            "- <|VERIFICATION_ERROR|> only if you cannot check files or pod status at all",
            "DO NOT create your own tokens. Use ONLY the three tokens listed above."
        ]

        # Default guidelines
        self.default_guidelines = [
            "Always verify the actual file contents to confirm changes were made",
            "Check pod status with kubectl get pods",
            "If pod logs are temporarily unavailable, this is acceptable - focus on file verification and pod status",
            "Verify the changes match what the debug agent claimed",
            "The PRIMARY verification is: Files have correct changes AND pod is Running",
            "Log verification is secondary - if unavailable, still verify based on files + pod status",
            "Do not assume the debug agent succeeded just because it said so",
            "Check the actual current state, not what was claimed",
            "If files are correct and pod is Running, you can conclude VERIFIED even without logs",
            "You MUST use one of the three specified tokens: <|VERIFIED|>, <|FAILED|>, or <|VERIFICATION_ERROR|>"
        ]

    def prepareAgent(self):
        """ Prepare the verification agent based on the config file """
        # agentProperties can be None if verification-agent is not in config - that's okay, we'll use defaults
        try:
            # Get model and temperature from config or use defaults
            if self.agentProperties:
                model_name = self.agentProperties.get("model", "gpt-4o")
                temperature = self.agentProperties.get("temperature", 0.3)
            else:
                model_name = "gpt-4o"
                temperature = 0.3
            
            if any(token in model_name for token in ['gpt', 'o3', 'o4', 'o1']):
                model = OpenAIChat(id=model_name, temperature=temperature)
            elif 'llama' in model_name:
                model = Ollama(id=model_name, temperature=temperature)
            elif 'gemini' in model_name:
                model = Gemini(id=model_name, temperature=temperature)
            else:
                raise Exception("Invalid model name provided for verification agent.")

            # Use config instructions/guidelines if provided, otherwise use defaults
            if self.agentProperties:
                instructions = self.agentProperties.get("instructions", self.default_instructions)
                guidelines = self.agentProperties.get("guidelines", self.default_guidelines)
            else:
                instructions = self.default_instructions
                guidelines = self.default_guidelines

            self.agent = llmAgent(
                model=model,
                tools=[BetterShellTools()], 
                debug_mode=True,
                instructions=instructions,
                show_tool_calls=True,
                markdown=True,
                guidelines=guidelines
            )
        except Exception as e:
            print(f"Error preparing verification agent: {e}")
            raise  # Re-raise the exception instead of sys.exit()

    def preparePrompt(self):
        """ Prepare the verification agent prompt - fully generic, no problem-specific config needed """
        try:
            # Start with the problem description
            self.prompt = "You are a verification agent. Your task is to verify whether the debug agent actually solved the Kubernetes issue.\n\n"
            
            self.prompt += f"=== ORIGINAL PROBLEM ===\n{self.config['knowledge-prompt']['problem-desc']}\n\n"
            
            # The key part: what did the debug agent claim?
            if self.debugAgentResponse:
                self.prompt += f"=== DEBUG AGENT'S RESPONSE ===\n{self.debugAgentResponse}\n\n"
            
            self.prompt += "=== YOUR VERIFICATION TASK ===\n"
            self.prompt += "1. Read the debug agent's response carefully\n"
            self.prompt += "2. Identify what changes it claims to have made\n"
            self.prompt += "3. Verify each claimed change is actually present in the system\n"
            self.prompt += "4. Check if the original problem is actually resolved\n"
            self.prompt += "5. Use kubectl commands and file inspection to verify the actual state\n\n"
            
            # Add context about relevant files
            self.prompt += "=== RELEVANT FILES (from configuration) ===\n"
            for relevantFileType in ["deployment", "application", "service"]:
                self.prompt = traverseRelevantFiles(self.config, relevantFileType, self.prompt)
            
            self.prompt += f"\nTest directory: {self.config['test-directory']}\n"
            self.prompt += f"Configuration file: {self.config.get('yaml-file-name', 'N/A')}\n\n"
            
            self.prompt += "=== VERIFICATION APPROACH ===\n"
            self.prompt += "- Check file contents match what debug agent claimed\n"
            self.prompt += "- Verify Kubernetes resources were actually modified/reapplied\n"
            self.prompt += "- Confirm pods are running (not in error states)\n"
            self.prompt += "- Test that the original problem symptom is gone\n"
            self.prompt += "- DO NOT trust claims without verification\n\n"
            
        except Exception as e:
            print(f"Error creating verification agent prompt: {e}")
            sys.exit()

    @timeout_decorator.timeout(480)
    @withTimeout(None)
    def askQuestion(self):
        """ Ask the verification agent to verify the fix """
        try:
            prompt = self.prompt
            prompt += "\n\n=== CRITICAL: USE EXACT TOKENS ===\n"
            prompt += "You MUST conclude with EXACTLY one of these three tokens:\n"
            prompt += "1. <|VERIFIED|> if the issue has been completely resolved\n"
            prompt += "2. <|FAILED|> if the issue has NOT been fixed\n"
            prompt += "3. <|VERIFICATION_ERROR|> if you encountered errors during verification\n\n"
            prompt += "DO NOT make up your own tokens like <|FIX_VERIFIED_FAILED|> or anything else.\n"
            prompt += "Use ONLY: <|VERIFIED|>, <|FAILED|>, or <|VERIFICATION_ERROR|>\n"
            
            response = self.agent.run(prompt)
            self.verificationReport = response.content

            if "<|VERIFIED|>" in self.verificationReport:
                self.verificationStatus = True
                print("\n" + "="*80)
                print("VERIFICATION STATUS: ✓ VERIFIED")
                print("The issue has been completely resolved")
                print("="*80 + "\n")
            elif "<|FAILED|>" in self.verificationReport:
                self.verificationStatus = False
                print("\n" + "="*80)
                print("VERIFICATION STATUS: ✗ FAILED")
                print("The issue has NOT been fixed")
                print("="*80 + "\n")
            elif "<|VERIFICATION_ERROR|>" in self.verificationReport:
                self.verificationStatus = None
                print("\n" + "="*80)
                print("VERIFICATION STATUS: ⚠ ERROR")
                print("Encountered errors during verification")
                print("="*80 + "\n")
            else:
                self.verificationStatus = None
                print("\n" + "="*80)
                print("VERIFICATION STATUS: ? UNKNOWN")
                print("No verification status token found in response")
                print("="*80 + "\n")
            
            metrics = response.metrics or {}  # Fallback to empty dict if None
            input_tokens = sum(metrics.get("input_tokens", []))
            output_tokens = sum(metrics.get("output_tokens", []))
            total_tokens = sum(metrics.get("total_tokens", []))
            model_name = response.model
            agent_type = 'verification'
            
            # Save metrics
            metrics_entry = {
                "test_case": self.config['test-name'],
                "model": model_name,
                "agent_type": agent_type,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "task_status": STATUS_MAP.get(self.verificationStatus, -1)
            }
            return metrics_entry

        except Exception as e:
            print(f"Error during verification: {e}")
            self.verificationStatus = None

            metrics_entry = {
                "test_case": self.config['test-name'],
                "model": self.config['verification-agent']['model'],
                "agent_type": 'verification',
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "task_status": -1
            }
            return metrics_entry        
