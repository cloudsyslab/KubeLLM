import re

from phi.agent import Agent as llmAgent
from phi.knowledge.website import WebsiteKnowledgeBase
from phi.storage.agent.postgres import PgAgentStorage
from phi.vectordb.pgvector import PgVector, SearchType

from agent_base import Agent
from agent_helpers import agent_debug_logging_enabled, build_llm_agent, build_model, build_tool_kwargs
from better_shell import BetterShellTools
from runtime_progress import BlockedCommandThresholdError
from runtime_config import DB_URL, build_embedder, resolve_embedder_config
from prompt_helpers import (
    TOOL_USAGE_RULES,
    append_relevant_files,
    classify_status_from_response,
    extract_metrics,
    get_case_specific_guidance,
)
from timeout_helpers import timeout, withTimeout


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
                tool_kwargs=build_tool_kwargs(self.runtime_context, phase="debug"),
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
            self.prompt += get_case_specific_guidance(self.config)
        except Exception as e:
            raise RuntimeError(f"Error creating debug agent prompt: {e}") from e

    @withTimeout(False)
    @timeout(480)
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
            prompt += get_case_specific_guidance(self.config)

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
        except BlockedCommandThresholdError as exc:
            self.response = f"{exc}\n<|FAILED|>"
            self.debugStatus = False
            return {
                "test_case": self.config["test-name"],
                "model": self.agentProperties.get("model"),
                "agent_type": "debug",
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "task_status": 0,
            }
        except Exception as e:
            raise RuntimeError(f"Error asking question to debug agent: {e}") from e


class AgentDebugStepByStep(Agent):
    def __init__(self, agentType, config):
        super().__init__(agentType, config)
        self.agentAPIResponse = None
        self.debugStatus = None
        self.response = None
        self.steps = []

    def prepareAgent(self):
        """Prepare the debug assistant based on the config file."""
        try:
            model_name = self.agentProperties["model"]
            self.agent = build_llm_agent(
                model_name,
                instructions=[x for x in self.agentProperties["instructions"]],
                guidelines=[x for x in self.agentProperties["guidelines"]],
                tool_kwargs=build_tool_kwargs(self.runtime_context, phase="debug"),
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
            self.prompt += get_case_specific_guidance(self.config)
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
    @timeout(480)
    def executeProblemSteps(self):
        """Execute each generated problem-solving step in order."""
        try:
            step_metrics = []
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
                prompt += get_case_specific_guidance(self.config)

                response = self.agent.run(prompt, return_response=True)
                response_content = response.content
                self.response = response_content
                self.debugStatus = classify_status_from_response(response_content)
                step_metrics.append(
                    extract_metrics(
                        response,
                        test_case=self.config["test-name"],
                        agent_type="debug",
                        task_status=int(self.debugStatus),
                    )
                )

            aggregate = {
                "test_case": self.config["test-name"],
                "model": "",
                "agent_type": "debug",
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "task_status": -1 if self.debugStatus is None else int(self.debugStatus),
            }
            for metrics in step_metrics:
                if metrics.get("model"):
                    aggregate["model"] = metrics["model"]
                aggregate["input_tokens"] += metrics.get("input_tokens", 0)
                aggregate["output_tokens"] += metrics.get("output_tokens", 0)
                aggregate["total_tokens"] += metrics.get("total_tokens", 0)
                aggregate["task_status"] = metrics.get("task_status", aggregate["task_status"])
            return aggregate
        except BlockedCommandThresholdError:
            self.debugStatus = False
            return {
                "test_case": self.config["test-name"],
                "model": self.agentProperties.get("model"),
                "agent_type": "debug",
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "task_status": 0,
            }
        except Exception as e:
            raise RuntimeError(f"Failed to execute problem steps: {e}") from e


class SingleAgent(Agent):
    def __init__(self, agentType, config):
        super().__init__(agentType, config)
        self.knowledgeResponse = None
        self.debugStatus = None
        self._resolved_debug_model_name = None

    def prepareAgent(self):
        """Prepare the single-agent workflow based on the config file."""
        try:
            single_agent_config = self.agentProperties or {}
            debug_agent_config = self.config.get("debug-agent", {})
            api_agent_config = self.config.get("api-agent", {})

            model_name = (
                single_agent_config.get("model")
                or debug_agent_config.get("model")
                or api_agent_config.get("model")
            )
            if not model_name:
                raise RuntimeError(
                    "SingleAgent requires a configured model in 'single-agent.model', "
                    "'debug-agent.model', or 'api-agent.model'."
                )

            model = build_model(model_name)
            self._resolved_debug_model_name = model_name
            embedder_config = resolve_embedder_config(
                embeddings_model=single_agent_config.get("embedder") or api_agent_config.get("embedder"),
                provider=single_agent_config.get("embedder-provider") or api_agent_config.get("embedder-provider"),
                chat_model_name=model_name,
            )
            embedder = build_embedder(embedder_config.model, provider=embedder_config.provider)

            knowledge_base = WebsiteKnowledgeBase(
                urls=api_agent_config.get("knowledge", []),
                max_links=10,
                vector_db=PgVector(
                    table_name=f"local_rag_documents_{embedder_config.model}",
                    db_url=DB_URL,
                    embedder=embedder,
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
            debug_logging = agent_debug_logging_enabled()
            tool_kwargs = build_tool_kwargs(self.runtime_context, phase="debug")

            self.agent = llmAgent(
                model=model,
                tools=[BetterShellTools(**tool_kwargs)],
                debug_mode=debug_logging,
                instructions=[x for x in self.config["debug-agent"]["instructions"]] + additionalInstructions,
                show_tool_calls=debug_logging,
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
            self.prompt += get_case_specific_guidance(self.config)
        except Exception as e:
            raise RuntimeError(f"Error creating debug agent prompt: {e}") from e

    @withTimeout(False)
    @timeout(480)
    def askQuestion(self):
        """Ask the formatted prepared question to the single agent."""
        try:
            response = self.agent.run(self.prompt, return_response=True)
            response_content = response.content
            self.knowledgeResponse = response_content
            self.debugStatus = classify_status_from_response(response_content)
            model_name = self._resolved_debug_model_name or (self.agentProperties or {}).get("model")
            if not model_name:
                model_name = self.config.get("debug-agent", {}).get("model")
            return extract_metrics(
                response,
                test_case=self.config["test-name"],
                agent_type="debug",
                task_status=int(self.debugStatus),
                model_override=model_name,
            )
        except BlockedCommandThresholdError as exc:
            self.knowledgeResponse = f"{exc}\n<|FAILED|>"
            self.debugStatus = False
            model_name = self._resolved_debug_model_name or (self.agentProperties or {}).get("model")
            if not model_name:
                model_name = self.config.get("debug-agent", {}).get("model")
            return {
                "test_case": self.config["test-name"],
                "model": model_name,
                "agent_type": "debug",
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "task_status": 0,
            }
        except Exception as e:
            raise RuntimeError(f"Error asking question to knowledge agent: {e}") from e
