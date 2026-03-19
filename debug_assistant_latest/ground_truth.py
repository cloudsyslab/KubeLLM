"""
Ground Truth Verification Module for KubeLLM

Provides deterministic, LLM-independent verification of Kubernetes fixes.
Each test case can define verification commands that prove the specific
issue was fixed, not just that the pod is running.

Key features:
- Polling with configurable intervals for K8s eventual consistency
- Multiple comparison operators (exact, contains, regex, numeric, exit code)
- Check dependencies (skip if prerequisite failed)
- Structured results with PASS/FAIL/ERROR/SKIP status
"""

import json
import re
import subprocess
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


GROUND_TRUTH_SCHEMA_PATH = Path(__file__).with_name("ground_truth.schema.json")


class CheckStatus(Enum):
    """Status of a ground truth check."""
    PASS = "PASS"      # Check succeeded - assertion matched
    FAIL = "FAIL"      # Check ran but assertion did not match
    ERROR = "ERROR"    # Command failed to execute (timeout, kubectl error, etc.)
    SKIP = "SKIP"      # Skipped due to dependency failure


@dataclass
class CheckResult:
    """Result of a single ground truth check."""
    name: str
    status: CheckStatus
    expected: str
    actual: str
    attempts: int = 1
    duration_ms: int = 0
    error: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "name": self.name,
            "status": self.status.value,
            "expected": self.expected,
            "actual": self.actual,
            "attempts": self.attempts,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "description": self.description,
        }


@dataclass
class GroundTruthResult:
    """Aggregate result of all ground truth checks for a test case."""
    test_name: str
    passed: bool
    checks: List[CheckResult] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
    total_duration_ms: int = 0
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.summary:
            self.summary = {s.value: 0 for s in CheckStatus}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "test_name": self.test_name,
            "passed": self.passed,
            "checks": [c.to_dict() for c in self.checks],
            "summary": self.summary,
            "total_duration_ms": self.total_duration_ms,
            "timestamp": self.timestamp,
        }


def load_ground_truth(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract ground-truth section from test config.

    Args:
        config: Test configuration dict (from config_step.json)

    Returns:
        ground-truth dict if present, None otherwise
    """
    return config.get("ground-truth")


def execute_command(cmd: str, timeout_s: float = 30) -> tuple[str, int, Optional[str]]:
    """Execute a shell command and return (stdout, exit_code, error).

    Args:
        cmd: Shell command to execute
        timeout_s: Command timeout in seconds

    Returns:
        Tuple of (stdout, exit_code, error_message)
        - stdout: Command output (stripped)
        - exit_code: Process exit code
        - error_message: Error string if command failed, None otherwise
    """
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        return (
            result.stdout.strip(),
            result.returncode,
            (result.stderr.strip() or None) if result.returncode != 0 else None
        )
    except subprocess.TimeoutExpired:
        return ("", -1, f"Command timed out after {timeout_s}s")
    except Exception as e:
        return ("", -1, str(e))


def matches_expectation(output: str, exit_code: int, check: Dict[str, Any]) -> bool:
    """Check if command output matches the expected value.

    Args:
        output: Command stdout (stripped)
        exit_code: Command exit code
        check: Check definition with expect_* field

    Returns:
        True if output matches expectation, False otherwise
    """
    if "expect" in check:
        return output == check["expect"]

    if "expect_contains" in check:
        return check["expect_contains"] in output

    if "expect_regex" in check:
        pattern = check["expect_regex"]
        return bool(re.search(pattern, output))

    if "expect_gte" in check:
        try:
            actual_num = float(output)
            expected_num = float(check["expect_gte"])
            return actual_num >= expected_num
        except (ValueError, TypeError):
            return False

    if "expect_exit" in check:
        return exit_code == check["expect_exit"]

    if "expect_empty" in check and check["expect_empty"]:
        return output == ""

    return False


def get_expected_str(check: Dict[str, Any]) -> str:
    """Get human-readable expected value from check definition."""
    if "expect" in check:
        return check["expect"]
    if "expect_contains" in check:
        return f"contains '{check['expect_contains']}'"
    if "expect_regex" in check:
        return f"matches /{check['expect_regex']}/"
    if "expect_gte" in check:
        return f">= {check['expect_gte']}"
    if "expect_exit" in check:
        return f"exit code {check['expect_exit']}"
    if "expect_empty" in check:
        return "(empty)"
    return "(unknown)"


def build_global_timeout_result(
    check: Dict[str, Any],
    expected: str,
    description: Optional[str],
    attempts: int,
    duration_ms: int,
    actual: str = "(not executed)",
    global_timeout_s: Optional[float] = None,
) -> CheckResult:
    """Build a consistent timeout result when the global budget is exhausted."""
    timeout_label = f" ({global_timeout_s}s)" if global_timeout_s is not None else ""
    return CheckResult(
        name=check["name"],
        status=CheckStatus.ERROR,
        expected=expected,
        actual=actual,
        attempts=attempts,
        duration_ms=duration_ms,
        error=f"Global timeout exceeded{timeout_label}",
        description=description,
    )


def run_check(
    check: Dict[str, Any],
    passed_checks: set,
    deadline_at: Optional[float] = None,
    global_timeout_s: Optional[float] = None,
) -> CheckResult:
    """Execute a single ground truth check with optional polling.

    Args:
        check: Check definition dict
        passed_checks: Set of check names that have passed (for dependencies)
        deadline_at: Absolute monotonic deadline for the overall ground-truth run
        global_timeout_s: Configured global timeout used for user-facing error text

    Returns:
        CheckResult with status and details
    """
    name = check["name"]
    cmd = check["cmd"]
    description = check.get("description")
    max_attempts = check.get("max_attempts", 1)
    poll_interval = check.get("poll_interval_s", 0)
    timeout_s = check.get("timeout_s", 30)
    depends_on = check.get("depends_on", [])
    expected_str = get_expected_str(check)
    expect_exit = "expect_exit" in check

    # Check dependencies
    for dep in depends_on:
        if dep not in passed_checks:
            return CheckResult(
                name=name,
                status=CheckStatus.SKIP,
                expected=expected_str,
                actual=f"skipped (dependency '{dep}' did not pass)",
                attempts=0,
                duration_ms=0,
                description=description,
            )

    start_time = time.monotonic()
    last_output = ""
    last_error = None
    last_exit_code = 0

    def duration_ms() -> int:
        return int((time.monotonic() - start_time) * 1000)

    def remaining_budget_s() -> Optional[float]:
        if deadline_at is None:
            return None
        return deadline_at - time.monotonic()

    for attempt in range(1, max_attempts + 1):
        remaining = remaining_budget_s()
        if remaining is not None and remaining <= 0:
            return build_global_timeout_result(
                check,
                expected_str,
                description,
                attempts=attempt - 1,
                duration_ms=duration_ms(),
                actual=last_output or "(no output)",
                global_timeout_s=global_timeout_s,
            )

        command_timeout_s = timeout_s if remaining is None else min(timeout_s, remaining)
        output, exit_code, error = execute_command(cmd, command_timeout_s)
        last_output = output
        last_error = error
        last_exit_code = exit_code

        try:
            matched = matches_expectation(output, exit_code, check)
        except re.error as exc:
            return CheckResult(
                name=name,
                status=CheckStatus.ERROR,
                expected=expected_str,
                actual=output or "(no output)",
                attempts=attempt,
                duration_ms=duration_ms(),
                error=f"Invalid expect_regex: {exc}",
                description=description,
            )

        if matched and (error is None or expect_exit):
            return CheckResult(
                name=name,
                status=CheckStatus.PASS,
                expected=expected_str,
                actual=output,
                attempts=attempt,
                duration_ms=duration_ms(),
                description=description,
            )

        remaining = remaining_budget_s()
        if remaining is not None and remaining <= 0:
            return build_global_timeout_result(
                check,
                expected_str,
                description,
                attempts=attempt,
                duration_ms=duration_ms(),
                actual=last_output or "(no output)",
                global_timeout_s=global_timeout_s,
            )

        if attempt < max_attempts and poll_interval > 0:
            sleep_s = poll_interval if remaining is None else min(poll_interval, max(0.0, remaining))
            if sleep_s <= 0:
                return build_global_timeout_result(
                    check,
                    expected_str,
                    description,
                    attempts=attempt,
                    duration_ms=duration_ms(),
                    actual=last_output or "(no output)",
                    global_timeout_s=global_timeout_s,
                )
            time.sleep(sleep_s)

    total_duration_ms = duration_ms()

    # Determine if ERROR or FAIL
    if expect_exit:
        if last_error and last_exit_code == -1:
            return CheckResult(
                name=name,
                status=CheckStatus.ERROR,
                expected=expected_str,
                actual=last_output or "(no output)",
                attempts=max_attempts,
                duration_ms=total_duration_ms,
                error=last_error,
                description=description,
            )
        return CheckResult(
            name=name,
            status=CheckStatus.FAIL,
            expected=expected_str,
            actual=last_output,
            attempts=max_attempts,
            duration_ms=total_duration_ms,
            description=description,
        )

    if last_error:
        return CheckResult(
            name=name,
            status=CheckStatus.ERROR,
            expected=expected_str,
            actual=last_output or "(no output)",
            attempts=max_attempts,
            duration_ms=total_duration_ms,
            error=last_error,
            description=description,
        )
    else:
        return CheckResult(
            name=name,
            status=CheckStatus.FAIL,
            expected=expected_str,
            actual=last_output,
            attempts=max_attempts,
            duration_ms=total_duration_ms,
            description=description,
        )


def run_all_checks(config: Dict[str, Any]) -> Optional[GroundTruthResult]:
    """Execute all ground truth checks for a test case.

    Args:
        config: Test configuration dict with ground-truth section

    Returns:
        GroundTruthResult with all check results, or None if no ground-truth defined
    """
    gt_config = load_ground_truth(config)
    if not gt_config:
        return None

    test_name = config.get("test-name", "unknown")
    checks_config = gt_config.get("checks", [])
    global_timeout = gt_config.get("timeout_seconds")

    results: List[CheckResult] = []
    passed_checks: set = set()
    summary = {s.value: 0 for s in CheckStatus}
    start_time = time.monotonic()
    deadline_at = start_time + global_timeout if global_timeout is not None else None

    for check_def in checks_config:
        # Enforce global timeout if configured
        if deadline_at is not None and time.monotonic() >= deadline_at:
            result = build_global_timeout_result(
                check_def,
                get_expected_str(check_def),
                check_def.get("description"),
                attempts=0,
                duration_ms=0,
                global_timeout_s=global_timeout,
            )
            results.append(result)
            summary[result.status.value] += 1
            continue

        result = run_check(
            check_def,
            passed_checks,
            deadline_at=deadline_at,
            global_timeout_s=global_timeout,
        )
        results.append(result)
        summary[result.status.value] += 1

        if result.status == CheckStatus.PASS:
            passed_checks.add(result.name)

    total_duration_ms = int((time.monotonic() - start_time) * 1000)
    all_passed = summary[CheckStatus.PASS.value] == len(results) and len(results) > 0

    return GroundTruthResult(
        test_name=test_name,
        passed=all_passed,
        checks=results,
        summary=summary,
        total_duration_ms=total_duration_ms,
    )


def format_results(result: GroundTruthResult) -> str:
    """Format ground truth results for console output.

    Args:
        result: GroundTruthResult to format

    Returns:
        Human-readable string representation
    """
    lines = []
    lines.append(f"\n{'='*60}")
    lines.append(f"GROUND TRUTH VERIFICATION: {result.test_name}")
    lines.append(f"{'='*60}")

    for check in result.checks:
        status_icon = {
            CheckStatus.PASS: "[PASS]",
            CheckStatus.FAIL: "[FAIL]",
            CheckStatus.ERROR: "[ERR ]",
            CheckStatus.SKIP: "[SKIP]",
        }[check.status]

        attempts_str = f" ({check.attempts} attempts)" if check.attempts > 1 else ""
        lines.append(f"{status_icon} {check.name}{attempts_str}")

        if check.description:
            lines.append(f"       {check.description}")

        if check.status != CheckStatus.PASS:
            lines.append(f"       Expected: {check.expected}")
            lines.append(f"       Actual:   {check.actual}")
            if check.error:
                lines.append(f"       Error:    {check.error}")

    lines.append(f"{'-'*60}")
    summary_str = ", ".join(f"{k}: {v}" for k, v in result.summary.items() if v > 0)
    status_str = "PASSED" if result.passed else "FAILED"
    lines.append(f"Result: {status_str} | {summary_str} | {result.total_duration_ms}ms")
    lines.append(f"{'='*60}\n")

    return "\n".join(lines)


def save_ground_truth_result(result: GroundTruthResult, output_dir: Path) -> Path:
    """Save ground truth results to JSON file.

    Args:
        result: GroundTruthResult to save
        output_dir: Directory to save ground_truth.json

    Returns:
        Path to saved file
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "ground_truth.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, indent=2)

    return output_file


def _load_ground_truth_schema() -> Dict[str, Any]:
    """Load the checked-in ground-truth schema used by preflight validation."""
    with open(GROUND_TRUTH_SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def _format_schema_error(error: Any) -> str:
    """Format a jsonschema validation error with a stable dotted path."""
    path_parts = [str(part) for part in error.absolute_path]
    path = ".".join(path_parts) if path_parts else "ground-truth"
    return f"{path}: {error.message}"


def validate_ground_truth_config(config: Dict[str, Any]) -> List[str]:
    """Validate ground-truth section of a config without executing commands.

    Args:
        config: Test configuration dict

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    gt = config.get("ground-truth")

    if not gt:
        return []  # No ground-truth section is valid (optional)

    if not isinstance(gt, dict):
        errors.append("ground-truth must be an object")
        return errors

    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        errors.append("ground-truth schema validation unavailable: missing 'jsonschema' dependency")
        return errors

    try:
        schema = _load_ground_truth_schema()
    except Exception as exc:
        errors.append(f"failed to load ground-truth schema: {exc}")
        return errors

    validator = Draft202012Validator(schema)
    schema_errors = sorted(
        (error for error in validator.iter_errors(config) if error.validator != "oneOf"),
        key=lambda err: (tuple(str(part) for part in err.absolute_path), err.message),
    )
    for error in schema_errors:
        errors.append(_format_schema_error(error))

    checks = gt.get("checks")
    if not checks:
        errors.append("ground-truth.checks is required")
        return list(dict.fromkeys(errors))

    if not isinstance(checks, list):
        errors.append("ground-truth.checks must be an array")
        return list(dict.fromkeys(errors))

    seen_names = set()
    for i, check in enumerate(checks):
        prefix = f"checks[{i}]"

        if not isinstance(check, dict):
            errors.append(f"{prefix}: must be an object")
            continue

        name = check.get("name")
        if not name:
            errors.append(f"{prefix}: 'name' is required")
        elif not re.match(r"^[a-z][a-z0-9_]*$", name):
            errors.append(f"{prefix}: 'name' must be snake_case (got '{name}')")
        elif name in seen_names:
            errors.append(f"{prefix}: duplicate name '{name}'")
        else:
            seen_names.add(name)

        if not check.get("cmd"):
            errors.append(f"{prefix}: 'cmd' is required")

        # Check that exactly one expect_* field is present
        expect_fields = [
            "expect", "expect_contains", "expect_regex",
            "expect_gte", "expect_exit", "expect_empty"
        ]
        found = [f for f in expect_fields if f in check]
        if len(found) == 0:
            errors.append(f"{prefix}: one of {expect_fields} is required")
        elif len(found) > 1:
            errors.append(f"{prefix}: only one expect_* field allowed (found: {found})")

        if "expect_regex" in check and isinstance(check["expect_regex"], str):
            try:
                re.compile(check["expect_regex"])
            except re.error as exc:
                errors.append(f"{prefix}: invalid expect_regex '{check['expect_regex']}': {exc}")

        # Validate depends_on references
        depends_on = check.get("depends_on", [])
        for dep in depends_on:
            if dep not in seen_names:
                errors.append(f"{prefix}: depends_on '{dep}' not defined (must appear earlier)")

    return list(dict.fromkeys(errors))
