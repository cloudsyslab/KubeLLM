"""Static error-pattern catalog for run diagnosis."""

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class ErrorPattern:
    regex: str
    category_name: str
    actions: List[str]


ERROR_PATTERNS = [
    ErrorPattern(
        regex=r"timed out after \d+ seconds|timeout: exceeded \d+s|\[TIMEOUT\]|global timeout exceeded",
        category_name="TIMEOUT",
        actions=[
            "Inspect stdout.log to see which agent step stalled before the timeout.",
            "Check timeout settings and confirm the agent is not waiting on an interactive or streaming command.",
            "Re-run the case after fixing the stall source or use --diagnose-last to confirm the timeout class.",
        ],
    ),
    ErrorPattern(
        regex=r"debug agent timed out|verification agent timed out|agent execution exceeded 480s",
        category_name="LLM_STALL",
        actions=[
            "Inspect the last successful tool call in stdout.log to find the blocking operation.",
            "Check prompt/tool instructions for commands that can hang on Windows or wait for live output.",
            "Prefer non-interactive kubectl and HTTP calls and re-run after narrowing the stall point.",
        ],
    ),
    ErrorPattern(
        regex=r"ModuleNotFoundError|ImportError|No module named|Failed to import",
        category_name="IMPORT_ERROR",
        actions=[
            "Install the missing dependency from requirements.txt or fix the import path.",
            "Run python -m pytest tests/ -v after fixing imports to catch secondary breakage.",
            "If the import is optional, guard it behind provider-specific code paths.",
        ],
    ),
    ErrorPattern(
        regex=r"<\|\s*FAILED\s*\|>|VERIFICATION STATUS: .*FAILED|verified\": false",
        category_name="VERIFICATION_MISMATCH",
        actions=[
            "Read summary.json and stdout.log to compare the debug agent claim with the verification evidence.",
            "Inspect the manifest and cluster state directly with kubectl before changing prompts.",
            "Fix the underlying remediation logic rather than relaxing verification.",
        ],
    ),
    ErrorPattern(
        regex=r"GROUND TRUTH FAILED|ground_truth_passed\": false|Result: FAILED",
        category_name="GROUND_TRUTH_FAIL",
        actions=[
            "Open ground_truth.json or the ground-truth section in config_step.json to see which deterministic check failed.",
            "Fix the manifest or application behavior the check is asserting, then re-run the same test.",
            "Do not trust an LLM success report when ground truth fails.",
        ],
    ),
    ErrorPattern(
        regex=r"Teardown failed|Post-timeout teardown failed",
        category_name="TEARDOWN_FAIL",
        actions=[
            "Inspect stderr.log for the teardown stack trace and failed kubectl/docker command.",
            "Restore the environment manually if required before re-running the test.",
            "Fix teardown config or manifest naming so cleanup can complete deterministically.",
        ],
    ),
    ErrorPattern(
        regex=r"Config file not found|Unknown test case|Invalid test type|ground-truth\.|jsonschema|config_step\.json",
        category_name="CONFIG_ERROR",
        actions=[
            "Validate the selected test config and ground-truth schema before re-running.",
            "Check CLI arguments, config_step.json paths, and required config keys.",
            "Use runner.py --validate-ground-truth and --preflight to confirm the configuration is now valid.",
        ],
    ),
    ErrorPattern(
        regex=r"kubectl|CrashLoopBackOff|ImagePullBackOff|OOMKilled|connection refused|no matches for kind|pod .* not found|service .* not found|failed to create pod sandbox",
        category_name="K8S_ERROR",
        actions=[
            "Inspect stderr.log and kubectl describe output for the exact Kubernetes failure.",
            "Check manifest resource names, image availability, probes, ports, selectors, and pod events.",
            "Re-run ground truth after fixing the manifest or cluster-side issue.",
        ],
    ),
    ErrorPattern(
        regex=r"RAG API|Could not initialize assistant|Could not load knowledge base|repo signature|api_version",
        category_name="CONFIG_ERROR",
        actions=[
            "Confirm the RAG API server is running at the expected URL and matches the current repo.",
            "Check DB migrations and vector table health if add_url or initialize is failing.",
            "Restart the API server after dependency or code changes.",
        ],
    ),
    ErrorPattern(
        regex=r"sqlite|database is locked|database is busy",
        category_name="UNKNOWN",
        actions=[
            "Inspect metrics DB contention and re-run with fewer concurrent workers if needed.",
            "Check whether another process is holding the database open.",
        ],
    ),
]
