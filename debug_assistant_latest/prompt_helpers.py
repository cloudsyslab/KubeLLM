import os
import re
from pathlib import Path

RELEVANT_FILE_TYPES = ["deployment", "application", "service", "dockerfile"]
BASE_TOOL_USAGE_RULES = (
    "### Tool Usage Rules\n"
    "- Do not attempt many commands in one tool call.\n"
    "- Never repeat a tool call that has already been executed successfully in this run.\n"
    "- If you need the result of a previous tool call, use the provided output rather than re-invoking it.\n"
    "- Keep the tool call as simple as possible to avoid errors.\n"
    "- Do not run long-lived or background commands such as `kubectl port-forward`, `Start-Process`, or `kubectl logs -f`; prefer single-shot commands that exit on their own.\n"
    "- Do not use `kubectl port-forward`, background verification, `kubectl logs -f`, or `kubectl get -w`.\n"
    "- For reachability checks, use the access path defined by the scenario: if a Service exists, verify via Service/endpoints/service-routed access; if no Service exists, use bounded direct checks such as `kubectl exec` with an in-container one-shot HTTP request.\n"
    "- Prefer one-shot application checks such as `kubectl exec <pod> -- python3 -c \"import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:<port>/').getcode())\"` when Python is available in the container.\n"
)

WINDOWS_RUNTIME_GUIDANCE = (
    "### Windows Runtime Rules\n"
    "- This run is on Windows. Use PowerShell-compatible commands and Windows file paths.\n"
    "- Do not use bash-only tools or syntax such as `sed -i`, `ls -la`, chained `pwd; ...`, or `/dev/null` redirection.\n"
    "- Prefer PowerShell or `python -c` one-liners for file edits on the exact Windows path provided.\n"
    "- Do not use `kubectl port-forward`, `kubectl logs -f`, `kubectl get -w`, or `Start-Process` for verification; use direct one-shot commands instead.\n"
    "- Do not use Unix-style background verification such as `& sleep ...; curl ... | head ...`.\n"
    "- If the manifest under test is a bare `Pod`, inspect and update that Pod directly. Do not query `.metadata.ownerReferences[0]` or assume a Deployment exists.\n"
)


def get_runtime_execution_guidance():
    if os.name == "nt":
        return WINDOWS_RUNTIME_GUIDANCE
    return ""


def get_tool_usage_rules():
    return BASE_TOOL_USAGE_RULES + get_runtime_execution_guidance()


TOOL_USAGE_RULES = get_tool_usage_rules()


def get_case_specific_guidance(config, *, phase=None):
    if phase != "verification":
        return ""

    guidance = []

    if _scenario_has_no_service(config):
        guidance.append(
            "### SCENARIO-SPECIFIC VERIFICATION GUIDANCE\n"
            "- This scenario intentionally has no Kubernetes Service. Absence of a Service is not a failure.\n"
            "- Do not verify this scenario via `minikube service`, external URL, Service existence, or Service endpoints.\n"
            "- Verify the configured direct-access success criteria instead: resource readiness, expected container port, and in-pod/local HTTP response on the intended port.\n"
        )

    if _primary_manifest_is_deployment(config):
        guidance.append(
            "### DEPLOYMENT ROLLOUT VERIFICATION GUIDANCE\n"
            "- For Deployment rollouts, old ReplicaSet pods in Terminating state are acceptable after rollout.\n"
            "- Do not fail verification solely because an old ReplicaSet pod is Terminating.\n"
            "- Verify `kubectl rollout status`, the current Deployment pod template, and a responding selected current pod.\n"
        )

    return "\n".join(guidance)


def _scenario_has_no_service(config):
    relevant_files = config.get("relevant-files") or {}
    return relevant_files.get("service") == []


def _primary_manifest_is_deployment(config):
    for path in _manifest_paths(config):
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if re.search(r"(?m)^\s*kind:\s*Deployment\s*$", content):
            return True
    return False


def _manifest_paths(config):
    test_dir = _test_directory(config)
    names = []

    yaml_file_name = config.get("yaml-file-name")
    if yaml_file_name:
        names.append(yaml_file_name)

    relevant_files = config.get("relevant-files") or {}
    deployment_files = relevant_files.get("deployment") or []
    if isinstance(deployment_files, str):
        deployment_files = [deployment_files]
    names.extend(deployment_files)

    paths = []
    seen = set()
    for name in names:
        path = Path(name)
        if not path.is_absolute():
            path = test_dir / path
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        paths.append(resolved)
    return paths


def _test_directory(config):
    test_dir = config.get("test-directory")
    if test_dir:
        path = Path(test_dir)
        if path.is_absolute():
            return path
        return Path(__file__).resolve().parent.parent / path

    test_name = config.get("test-name")
    if test_name:
        return Path(__file__).resolve().parent / "troubleshooting" / test_name

    return Path.cwd()


def append_relevant_files(config, prompt, file_types=None):
    from utils import traverseRelevantFiles

    for relevant_file_type in file_types or RELEVANT_FILE_TYPES:
        prompt = traverseRelevantFiles(config, relevant_file_type, prompt)
    return prompt


def classify_status_from_response(response_content):
    if "<|ERROR|>" in response_content or "<|FAILED|>" in response_content:
        return False
    if "<|SOLVED|>" in response_content:
        return True
    return False


def extract_metrics(
    response,
    test_case,
    agent_type,
    task_status,
    include_duration_cost=False,
    *,
    model_override=None,
):
    metrics = response.metrics or {}
    entry = {
        "test_case": test_case,
        "model": model_override if model_override is not None else response.model,
        "agent_type": agent_type,
        "input_tokens": sum(metrics.get("input_tokens", [])),
        "output_tokens": sum(metrics.get("output_tokens", [])),
        "total_tokens": sum(metrics.get("total_tokens", [])),
        "task_status": task_status,
    }
    if include_duration_cost:
        entry["duration_s"] = 0
        entry["cost"] = 0
    return entry
