try:
    import timeout_decorator
except ImportError:  # pragma: no cover import-error
    timeout_decorator = None

from agent_base import Agent
from agent_helpers import build_llm_agent
from prompt_helpers import TOOL_USAGE_RULES, extract_metrics

STATUS_MAP = {True: 1, False: 0, None: -1}


def parse_verification_status(report: str):
    if "<|VERIFIED|>" in report:
        return True
    if "<|FAILED|>" in report:
        return False
    if "<|VERIFICATION_ERROR|>" in report:
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


if timeout_decorator:
    TIMEOUT_DECORATOR = timeout_decorator.timeout
    TimeoutError = timeout_decorator.TimeoutError
else:
    def _noop_timeout(_seconds):
        def decorator(func):
            return func
        return decorator

    TIMEOUT_DECORATOR = _noop_timeout

    class TimeoutError(Exception):
        pass


def withTimeout(default_value):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except TimeoutError:
                return default_value
        return wrapper
    return decorator

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
