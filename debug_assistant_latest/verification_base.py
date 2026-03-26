import re

from agent_base import Agent
from agent_helpers import build_llm_agent, build_tool_kwargs
from better_shell import BetterShellTools
from ground_truth import run_all_checks
from prompt_helpers import TOOL_USAGE_RULES, extract_metrics, get_case_specific_guidance
from runtime_progress import (
    BlockedCommandThresholdError,
    get_wrong_port_verification_commands,
    is_wrong_port_windows_case,
)
from timeout_helpers import timeout as TIMEOUT_DECORATOR, withTimeout

STATUS_MAP = {True: 1, False: 0, None: -1}


def _run_wrong_port_windows_verification(config, runtime_context):
    tool = BetterShellTools(**build_tool_kwargs(runtime_context, phase="verification"))
    transcript = []

    for command in get_wrong_port_verification_commands(config):
        try:
            output = tool.run_shell_command(command=command)
        except BlockedCommandThresholdError as exc:
            transcript.append(f"$ {command}\nError: {exc}".strip())
            return False, "\n\n".join(transcript + ["<|FAILED|>"])

        transcript.append(f"$ {command}\n{output}".strip())
        if isinstance(output, str) and output.startswith("Error:"):
            return False, "\n\n".join(transcript + ["<|FAILED|>"])

    gt_result = run_all_checks(config)
    if gt_result and gt_result.passed:
        return True, "\n\n".join(transcript + ["wrong_port deterministic ground truth passed", "<|VERIFIED|>"])
    return False, "\n\n".join(transcript + ["wrong_port deterministic ground truth failed", "<|FAILED|>"])


def parse_verification_status(report: str):
    report = report or ""

    if re.search(r"<\|\s*VERIFIED\s*\|>", report) or "<|VERIFIED|>" in report:
        return True
    if re.search(r"<\|\s*FAILED\s*\|>", report) or "<|FAILED|>" in report:
        return False
    if re.search(r"<\|\s*VERIFICATION_ERROR\s*\|>", report) or "<|VERIFICATION_ERROR|>" in report:
        return None
    return None


def print_verification_status(status):
    if status is True:
        print("\n" + "=" * 80)
        print("VERIFICATION STATUS: ✓ VERIFIED")
        print("The issue has been completely resolved")
        print("=" * 80 + "\n")
    elif status is False:
        print("\n" + "=" * 80)
        print("VERIFICATION STATUS: ✗ FAILED")
        print("The issue has NOT been fixed")
        print("=" * 80 + "\n")
    else:
        print("\n" + "=" * 80)
        print("VERIFICATION STATUS: ? UNKNOWN")
        print("No verification status token found in response")
        print("=" * 80 + "\n")

class VerificationAgentBase(Agent):
    include_duration_cost = False

    def __init__(self, agentType, config):
        super().__init__(agentType, config)
        self.verificationStatus = None
        self.verificationReport = None

    def prepareAgent(self):
        try:
            props = self.agentProperties or {}
            model_name = props.get("model", "gpt-4o")
            temperature = props.get("temperature", 0.3)
            instructions = props.get("instructions", self.default_instructions)
            guidelines = props.get("guidelines", self.default_guidelines)

            self.agent = build_llm_agent(
                model_name,
                instructions=instructions,
                guidelines=guidelines,
                temperature=temperature,
                tool_kwargs=build_tool_kwargs(self.runtime_context, phase="verification"),
            )
        except Exception as e:
            raise RuntimeError(f"Error preparing verification agent: {e}") from e

    def preparePrompt(self):
        raise NotImplementedError

    @withTimeout(None)
    @TIMEOUT_DECORATOR(480)
    def askQuestion(self):
        try:
            if is_wrong_port_windows_case(self.config):
                self.verificationStatus, self.verificationReport = _run_wrong_port_windows_verification(
                    self.config,
                    self.runtime_context,
                )
                print_verification_status(self.verificationStatus)
                return {
                    "test_case": self.config["test-name"],
                    "model": self.config["verification-agent"].get("model"),
                    "agent_type": "verification",
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "task_status": STATUS_MAP.get(self.verificationStatus, -1),
                    "duration_s": 0,
                    "cost": 0,
                }

            prompt = self.prompt
            prompt += "\n" + TOOL_USAGE_RULES
            prompt += get_case_specific_guidance(self.config)
            prompt += "\n\n=== CRITICAL: USE EXACT TOKENS ===\n"
            prompt += "You MUST conclude with EXACTLY one of these three tokens:\n"
            prompt += "1. <|VERIFIED|> if the issue has been completely resolved\n"
            prompt += "2. <|FAILED|> if the issue has NOT been fixed\n"
            prompt += "3. <|VERIFICATION_ERROR|> if you encountered errors during verification\n\n"
            prompt += "DO NOT make up your own tokens like <|FIX_VERIFIED_FAILED|> or anything else.\n"
            prompt += "Use ONLY: <|VERIFIED|>, <|FAILED|>, or <|VERIFICATION_ERROR|>\n"

            response = self.agent.run(prompt)
            self.verificationReport = response.content
            self.verificationStatus = parse_verification_status(self.verificationReport)
            print_verification_status(self.verificationStatus)

            return extract_metrics(
                response,
                test_case=self.config["test-name"],
                agent_type="verification",
                task_status=STATUS_MAP.get(self.verificationStatus, -1),
                include_duration_cost=self.include_duration_cost,
            )
        except BlockedCommandThresholdError as e:
            print(f"Verification aborted after repeated blocked commands: {e}")
            self.verificationStatus = False
            return {
                "test_case": self.config["test-name"],
                "model": self.config["verification-agent"].get("model"),
                "agent_type": "verification",
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "task_status": 0,
                "duration_s": 0,
                "cost": 0,
            }
        except Exception as e:
            print(f"Error during verification: {e}")
            self.verificationStatus = None
            return {
                "test_case": self.config["test-name"],
                "model": self.config["verification-agent"].get("model"),
                "agent_type": "verification",
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "task_status": -1,
                "duration_s": 0,
                "cost": 0,
            }
