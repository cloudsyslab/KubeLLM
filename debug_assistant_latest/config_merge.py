"""
Config merge module for KubeLLM test runner.

Provides functions to merge CLI overrides into test configuration
without modifying the original JSON files.
"""

import copy
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


# Mapping from CLI argument names to config dotted paths
CLI_TO_CONFIG_MAP = {
    "debug_model": "debug-agent.model",
    "api_model": "api-agent.model",
    "verification_model": "verification-agent.model",
    "embedder": "api-agent.embedder",
    "minikube_profile": "minikube-profile",
}


def merge_config_overrides(base_config: dict, overrides: dict) -> dict:
    """
    Merge CLI overrides into config without mutating original.

    Args:
        base_config: Original configuration dictionary
        overrides: Dictionary of dotted-path keys to values
                   e.g. {"debug-agent.model": "gpt-4o"}

    Returns:
        New config dictionary with overrides applied
    """
    merged = copy.deepcopy(base_config)

    for dotted_key, value in overrides.items():
        if value is None:
            continue

        keys = dotted_key.split(".")
        target = merged
        for k in keys[:-1]:
            target = target.setdefault(k, {})
        target[keys[-1]] = value

    return merged


def build_overrides_from_args(args) -> dict:
    """
    Build config overrides dictionary from argparse namespace.

    Args:
        args: argparse.Namespace with CLI arguments

    Returns:
        Dictionary of dotted-path config overrides
    """
    overrides = {}
    for cli_arg, config_path in CLI_TO_CONFIG_MAP.items():
        value = getattr(args, cli_arg, None)
        if value is not None:
            overrides[config_path] = value
    return overrides


def load_config_with_overrides(config_path: Path, overrides: Optional[dict] = None) -> dict:
    """
    Load a config file and apply overrides.

    Args:
        config_path: Path to config_step.json
        overrides: Optional dictionary of dotted-path config overrides

    Returns:
        Merged configuration dictionary
    """
    with open(config_path) as f:
        config = json.load(f)

    # Derive test-directory from config file location if empty
    if not config.get("test-directory") or config.get("test-directory") == "":
        config_dir = Path(config_path).parent.absolute()
        config["test-directory"] = str(config_dir) + "/"

    if overrides:
        config = merge_config_overrides(config, overrides)

    return config


def save_effective_config(config: dict, output_path: Path) -> None:
    """
    Save the effective (merged) configuration for audit trail.

    Args:
        config: Merged configuration dictionary
        output_path: Path to save the effective config
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(config, f, indent=2)


def get_override_summary(overrides: dict) -> str:
    """
    Get a human-readable summary of applied overrides.

    Args:
        overrides: Dictionary of applied overrides

    Returns:
        Formatted string of overrides
    """
    if not overrides:
        return "No overrides applied"

    lines = ["Config overrides:"]
    for key, value in sorted(overrides.items()):
        lines.append(f"  {key}: {value}")
    return "\n".join(lines)


if __name__ == "__main__":
    # Quick test of the module
    test_config = {
        "api-agent": {"model": "gpt-5-mini", "embedder": "nomic-embed-text"},
        "debug-agent": {"model": "gpt-5-nano", "instructions": []},
        "test-name": "test_case",
    }

    overrides = {
        "debug-agent.model": "gpt-4o",
        "api-agent.model": "gpt-5-mini",
    }

    merged = merge_config_overrides(test_config, overrides)

    print("Original config:")
    print(json.dumps(test_config, indent=2))
    print("\nOverrides:")
    print(json.dumps(overrides, indent=2))
    print("\nMerged config:")
    print(json.dumps(merged, indent=2))
