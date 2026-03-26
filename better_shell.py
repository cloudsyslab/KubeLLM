"""Compatibility shim for the updated shell toolkit implementation."""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
_DEBUG_DIR = _REPO_ROOT / "debug_assistant_latest"
if str(_DEBUG_DIR) not in sys.path:
    sys.path.insert(0, str(_DEBUG_DIR))

from debug_assistant_latest.better_shell import BetterShellTools

__all__ = ["BetterShellTools"]
