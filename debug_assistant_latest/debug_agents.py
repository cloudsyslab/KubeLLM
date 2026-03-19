import re

import timeout_decorator
from phi.agent import Agent as llmAgent
from phi.knowledge.website import WebsiteKnowledgeBase
from phi.storage.agent.postgres import PgAgentStorage
from phi.vectordb.pgvector import PgVector, SearchType

from agent_base import Agent
from agent_helpers import build_llm_agent, build_model
from better_shell import BetterShellTools
from prompt_helpers import (
    TOOL_USAGE_RULES,
    append_relevant_files,
    classify_status_from_response,
    extract_metrics,
)
from utils import withTimeout


class AgentDebug(Agent):
    def __init__(self, agentType, config):
        super().__init__(agentType, config)
        self.agentAPIResponse = None
        self.debugStatus = None
        self.response = None

    def prepareAgent(self):
        """Prepare the debug assistant based on the config file."""
        try:
            model_name = self.agentProperties["model"]
            self.agent = build_llm_agent(
                model_name,
                instructions=[x for x in self.agentProperties["instructions"]],
                guidelines=[x for x in self.agentProperties["guidelines"]],
            )
        except Exception as e:
            raise RuntimeError(f"Error preparing debug agent: {e}") from e

    def preparePrompt(self):
        """Prepare the debug agent prompt."""
        try:
            self.prompt = append_relevant_files(self.config, self.prompt)
            self.prompt = (
                f"{self.prompt} Take the actions provided here: {str(self.agentAPIResponse)}. "
                + " "
                + self.config["debug-prompt"]["additional-directions"]
            )
        except Exception as e:
            raise RuntimeError(f"Error creating debug agent prompt: {e}") from e

    @withTimeout(False)
    @timeout_decorator.timeout(480)
    def askQuestion(self):
        """Ask the formatted prepared question to the debug agent."""
        try:
            prompt = f"Perform the actions suggested here: \n{self.agentAPIResponse}\n"
            prompt += (
                "\nThe relevant configuration file is located in this path: "
                f"{self.config['test-directory'] + self.config['yaml-file-name']}\n"
            )
            prompt += "You can update these files if necessary. If any files are updated, make sure to delete and reapply the configuration file.\n"
            prompt += "Do not use live feed flags when checking the logs such as 'kubectl logs -f'\n"
            prompt += TOOL_USAGE_RULES

            response = self.agent.run(prompt, return_response=True)
            response_content = response.content
            self.response = response_content
            self.debugStatus = classify_status_from_response(response_content)
            return extract_metrics(
                response,
                test_case=self.config["test-name"],
                agent_type="debug",
                task_status=int(self.debugStatus),
            )
        except Exception as e:
            raise RuntimeError(f"Error asking question to debug agent: {e}") from e


class AgentDebugStepByStep(Agent):
    def __init__(self, agentType, config):
        super().__init__(agentType, config)
        self.agentAPIResponse = None
        self.debugStatus = None

    def prepareAgent(self):
        """Prepare the debug assistant based on the config file."""
        try:
            model_name = self.agentProperties["model"]
            self.agent = build_llm_agent(
                model_name,
                instructions=[x for x in self.agentProperties["instructions"]],
                guidelines=[x for x in self.agentProperties["guidelines"]],
            )
        except Exception as e:
            raise RuntimeError(f"Error preparing debug agent: {e}") from e

    def preparePrompt(self):
        """Prepare the debug agent prompt."""
        try:
            self.prompt = (
                "Troubleshoot the Kubernetes issue described: "
                f"{self.config['knowledge-prompt']['problem-desc']}"
            )
            self.prompt = append_relevant_files(self.config, self.prompt)
            self.prompt += "Use `kubectl` commands to gather information, and provide a series of shell commands for the user to resolve the issue."
        except Exception as e:
            raise RuntimeError(f"Error creating debug agent prompt: {e}") from e

    def formProblemSolvingSteps(self):
        """Generate a list of steps that the debug agent will execute one by one."""
        self.steps = []

        try:
            knowledge_response_string = str(self.agentAPIResponse)
            bash_commands = re.findall(r"``bash\\n\s*(.*?)\\n\s*```", knowledge_response_string, re.DOTALL)
            bash_commands_list = [cmd.strip() for cmd in bash_commands]
            print(knowledge_response_string)
            print(bash_commands)
            print(bash_commands_list)
            self.steps = bash_commands_list
        except Exception as e:
            raise RuntimeError(f"Failed to generate steps to problem: {e}") from e

    @withTimeout(False)
    @timeout_decorator.timeout(480)
    def executeProblemSteps(self):
        """Execute each generated problem-solving step in order."""
        try:
            numSteps = len(self.steps)
            for i, step in enumerate(self.steps, start=1):
                prompt = f"Perform the action suggested here: \n{step}\n"
                prompt += "If you struggle within one of the steps try to figure out the solution until you see the pod running fine with kubectl describe."
                prompt += (
                    "\nThe relevant configuration file is located in this path: "
                    f"{self.config['test-directory'] + self.config['yaml-file-name']}\n"
                )
                prompt += "You can update these files if necessary. If any files are updated, make sure to delete and reapply the configuration file.\n"
                prompt += "If you need to update a pod then use kubectl replace --force [POD_NAME]"
                prompt += f"\nThis is step {i} out of {numSteps}."
                prompt += "Do not use live feed flags when checking the logs such as 'kubectl logs -f'"
                prompt += TOOL_USAGE_RULES

                response = self.agent.run(prompt)
                response = response.content
                self.debugStatus = classify_status_from_response(response)
        except Exception as e:
            raise RuntimeError(f"Failed to execute problem steps: {e}") from e


class SingleAgent(Agent):
    def __init__(self, agentType, config):
        super().__init__(agentType, config)
        self.knowledgeResponse = None
        self.debugStatus = None

    def prepareAgent(self):
        """Prepare the single-agent workflow based on the config file."""
        try:
            model = build_model("o3-mini")

            knowledge_base = WebsiteKnowledgeBase(
                urls=self.config["api-agent"].get("knowledge", []),
                max_links=10,
                vector_db=PgVector(
                    table_name="ai.local_rag_documents_singleAgent",
                    db_url="postgresql+psycopg://ai:ai@localhost:5532/ai",
                ),
            )

            additionalInstructions = [
                "Carefully read the information the user provided.",
                "Run diagnostic commands yourself, then use the output to further help you.",
                "Do not use live feed flags when checking the logs such as 'kubectl logs -f'",
                "Do not use commands that would open an editor like 'kubectl edit'",
                "DO NOT BY ANY MEANS USE kubectl edit",
            ]

            additionalGuidelines = [
                "You will run the commands as Instructed! Please feel free to change it if necessary and if it makes sense to! You will solve the issue and run the commands!",
                "When writing out your commands, use the real name of the Kubernetes resource instead of placeholder names. For example, if your command is `kubectl get pods -n <namespace>`, run `kubectl get namespaces` first to get available namespaces.",
                "Do not use live feed flags when checking the logs such as 'kubectl logs -f'",
                "When executing the shell commands please feel free to figure out whether or not it the command worked.",
                "Do not use commands that would open an editor like 'kubectl edit'",
                "DO NOT BY ANY MEANS USE kubectl edit",
            ]

            self.agent = llmAgent(
                model=model,
                tools=[BetterShellTools()],
                debug_mode=True,
                instructions=[x for x in self.config["debug-agent"]["instructions"]] + additionalInstructions,
                show_tool_calls=True,
                markdown=True,
                guidelines=[x for x in self.config["debug-agent"]["guidelines"]] + additionalGuidelines,
                knowledge=knowledge_base,
                search_knowledge=True,
                prevent_hallucinations=True,
                description="You are an AI called 'RAGit'. You come up with commands and execute them step by step in order to fix kubernetes issues.",
                task="Proivde the automated assistance in fixing kubernetes issues by executing commands that are relevant to the problem.",
            )
        except Exception as e:
            raise RuntimeError(f"Error preparing debug agent: {e}") from e

    def preparePrompt(self):
        """Prepare the single-agent prompt."""
        try:
            self.prompt = append_relevant_files(self.config, self.prompt)
            self.prompt = f"{self.prompt} " + " " + self.config["debug-prompt"]["additional-directions"]
            self.prompt += "Perform the actions that seem to be the most applicable in the current step"
            self.prompt += (
                "\nThe relevant configuration file is located in this path: "
                f"{self.config['test-directory'] + self.config['yaml-file-name']}\n"
            )
            self.prompt += "You can update these files if necessary. If any files are updated, make sure to delete and reapply the configuration file.\n"
            self.prompt += "Do not use live feed flags when checking the logs such as 'kubectl logs -f'"
            self.prompt += "Do not use commands that would open an editor like 'kubectl edit'"
            self.prompt += "You will run the commands as Instructed! Please feel free to change it if necessary and if it makes sense to! You will solve the issue and run the commands!"
            self.prompt += "DO NOT BY ANY MEANS USE kubectl edit"
        except Exception as e:
            raise RuntimeError(f"Error creating debug agent prompt: {e}") from e

    def askQuestion(self):
        """Ask the formatted prepared question to the single agent."""
        try:
            response = self.agent.run(self.prompt)
            response = response.content
            self.debugStatus = classify_status_from_response(response)
            return
        except Exception as e:
            raise RuntimeError(f"Error asking question to knowledge agent: {e}") from e
