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


def build_llm_agent(model_name, instructions, guidelines, temperature=None, **extra_kwargs):
    if llmAgent is None:
        raise RuntimeError("phi is required to build the LLM agent; install the phi package first.")
    model = build_model(model_name, temperature=temperature)
    return llmAgent(
        model=model,
        tools=[BetterShellTools()],
        debug_mode=True,
        instructions=instructions,
        show_tool_calls=True,
        markdown=True,
        guidelines=guidelines,
        **extra_kwargs,
    )
