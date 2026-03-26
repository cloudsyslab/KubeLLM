import os
import sys
from pathlib import Path

# Add repo root to path so runtime_config can be imported
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from phi.agent import Agent as llmAgent
except ImportError:
    llmAgent = None
from better_shell import BetterShellTools
from runtime_config import build_chat_model as build_model


def agent_debug_logging_enabled() -> bool:
    override = os.getenv("KUBELLM_AGENT_DEBUG_LOGS")
    if override is not None:
        return override.strip().lower() in {"1", "true", "yes", "on"}
    return os.name != "nt"


def build_tool_kwargs(runtime_context=None, phase=None):
    runtime_context = runtime_context or {}
    kwargs = {
        "progress_writer": runtime_context.get("progress_writer"),
        "phase": phase,
    }
    if phase in {"debug", "verification"}:
        kwargs["blocked_threshold"] = runtime_context.get("blocked_threshold", 3)
    if phase == "debug" and runtime_context.get("success_probe") is not None:
        kwargs["success_probe"] = runtime_context["success_probe"]
    return {key: value for key, value in kwargs.items() if value is not None}


def build_llm_agent(model_name, instructions, guidelines, temperature=None, tool_kwargs=None, **extra_kwargs):
    if llmAgent is None:
        raise RuntimeError("phi is required to build the LLM agent; install the phi package first.")
    model = build_model(model_name, temperature=temperature)
    debug_logging = agent_debug_logging_enabled()
    return llmAgent(
        model=model,
        tools=[BetterShellTools(**(tool_kwargs or {}))],
        debug_mode=debug_logging,
        instructions=instructions,
        show_tool_calls=debug_logging,
        markdown=True,
        guidelines=guidelines,
        **extra_kwargs,
    )
