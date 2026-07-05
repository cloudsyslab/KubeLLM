import re

from agent_base import Agent
from agent_helpers import build_llm_agent, build_tool_kwargs
from prompt_helpers import TOOL_USAGE_RULES, extract_metrics, get_case_specific_guidance
from runtime_progress import BlockedCommandThresholdError
from timeout_helpers import timeout as TIMEOUT_DECORATOR, withTimeout

STATUS_MAP = {True: 1, False: 0, None: -1}

_RELAXED_STATUS_LABEL_RE = re.compile(
    r"(?im)^\s*(?:#+\s*)?(?:final\s+)?(?:verification\s+)?"
    r"(?:status|result|conclusion)\s*[:=-]\s*"
    r"(?P<status>verification[_ -]?error|unknown|unable to verify|cannot verify|"
    r"not verified|not fixed|unresolved|failed|failure|broken|"
    r"verified|passed|success|fixed|resolved)\b"
)

_STANDALONE_STATUS_RE = re.compile(
    r"(?i)^(?:verification[_ -]?error|unknown|unable to verify|cannot verify|"
    r"not verified|not fixed|unresolved|failed|failure|broken|"
    r"verified|passed|success|fixed|resolved)$"
)


def _status_word_to_value(status_word: str):
    normalized = re.sub(r"[\s_-]+", " ", status_word.strip().lower())
    if normalized in {"verified", "passed", "success", "fixed", "resolved"}:
        return True
    if normalized in {"failed", "failure", "broken", "not verified", "not fixed", "unresolved"}:
        return False
    return None


def parse_verification_status(report: str):
    report = report or ""

    if re.search(r"<\|\s*VERIFIED\s*\|>", report) or "<|VERIFIED|>" in report:
        return True
    if re.search(r"<\|\s*FAILED\s*\|>", report) or "<|FAILED|>" in report:
        return False
    if re.search(r"<\|\s*VERIFICATION_ERROR\s*\|>", report) or "<|VERIFICATION_ERROR|>" in report:
        return None

    relaxed_matches = list(_RELAXED_STATUS_LABEL_RE.finditer(report))
    if relaxed_matches:
        return _status_word_to_value(relaxed_matches[-1].group("status"))

    nonempty_lines = [line.strip().strip("*`").strip() for line in report.splitlines() if line.strip()]
    if nonempty_lines:
        standalone = _STANDALONE_STATUS_RE.fullmatch(nonempty_lines[-1])
        if standalone:
            return _status_word_to_value(standalone.group(0))

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
            temperature = props.get("temperature", 1)
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
