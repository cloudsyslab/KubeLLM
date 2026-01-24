"""
Test discovery module for KubeLLM test runner.

Provides functions to enumerate test cases from the troubleshooting/ directory
and match test names against glob patterns.
"""

import fnmatch
from pathlib import Path
from typing import List, Optional

# Script directory - all paths relative to this
SCRIPT_DIR = Path(__file__).parent.absolute()
TROUBLESHOOTING_DIR = SCRIPT_DIR / "troubleshooting"


def list_test_cases() -> List[str]:
    """
    List all available test cases from the troubleshooting/ directory.

    A test case is identified by having a config_step.json file in its directory.

    Returns:
        Sorted list of test case names
    """
    if not TROUBLESHOOTING_DIR.exists():
        raise FileNotFoundError(
            f"Troubleshooting directory not found: {TROUBLESHOOTING_DIR}\n"
            f"Expected structure: <repo-root>/debug_assistant_latest/troubleshooting/"
        )

    test_cases = []
    for item in TROUBLESHOOTING_DIR.iterdir():
        if item.is_dir():
            config_file = item / "config_step.json"
            if config_file.exists():
                test_cases.append(item.name)

    return sorted(test_cases)


def match_pattern(pattern: str, test_cases: Optional[List[str]] = None) -> List[str]:
    """
    Match test case names against a pattern.

    Supports:
    - 'all' - returns all test cases
    - Glob patterns like 'port_*', 'wrong_*'
    - Comma-separated patterns: 'port_*,wrong_*'
    - Exact names: 'wrong_port'

    Args:
        pattern: Pattern string to match against
        test_cases: Optional list of test cases to match against.
                   If None, uses list_test_cases()

    Returns:
        Sorted list of matching test case names
    """
    if test_cases is None:
        test_cases = list_test_cases()

    if pattern.lower() == "all":
        return sorted(test_cases)

    # Handle comma-separated patterns
    patterns = [p.strip() for p in pattern.split(",")]

    matched = set()
    for p in patterns:
        for tc in test_cases:
            if fnmatch.fnmatch(tc, p):
                matched.add(tc)

    return sorted(matched)


def get_config_path(test_name: str) -> Path:
    """
    Get the path to a test case's config_step.json file.

    Args:
        test_name: Name of the test case

    Returns:
        Path to the config_step.json file

    Raises:
        FileNotFoundError: If the test case or config file doesn't exist
    """
    config_path = TROUBLESHOOTING_DIR / test_name / "config_step.json"
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found for test case '{test_name}': {config_path}"
        )
    return config_path


def validate_test_case(test_name: str) -> bool:
    """
    Validate that a test case exists and has required files.

    Args:
        test_name: Name of the test case

    Returns:
        True if valid, raises exception otherwise
    """
    test_dir = TROUBLESHOOTING_DIR / test_name
    if not test_dir.exists():
        raise FileNotFoundError(f"Test case directory not found: {test_dir}")

    config_path = test_dir / "config_step.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    return True


def get_test_info(test_name: str) -> dict:
    """
    Get basic information about a test case.

    Args:
        test_name: Name of the test case

    Returns:
        Dictionary with test case info
    """
    import json

    config_path = get_config_path(test_name)
    with open(config_path) as f:
        config = json.load(f)

    return {
        "name": test_name,
        "config_path": str(config_path),
        "test_directory": config.get("test-directory", ""),
        "yaml_file": config.get("yaml-file-name", ""),
        "problem_desc": config.get("knowledge-prompt", {}).get("problem-desc", "")[:100],
        "debug_model": config.get("debug-agent", {}).get("model", ""),
        "api_model": config.get("api-agent", {}).get("model", ""),
    }


if __name__ == "__main__":
    # Quick test of the module
    print("Available test cases:")
    for tc in list_test_cases():
        print(f"  - {tc}")

    print("\nPattern matching tests:")
    print(f"  'port_*': {match_pattern('port_*')}")
    print(f"  'wrong_*': {match_pattern('wrong_*')}")
    print(f"  'all': {match_pattern('all')}")
