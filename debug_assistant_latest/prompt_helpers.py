import os

RELEVANT_FILE_TYPES = ["deployment", "application", "service", "dockerfile"]
BASE_TOOL_USAGE_RULES = (
    "### Tool Usage Rules\n"
    "- Do not attempt many commands in one tool call.\n"
    "- Never repeat a tool call that has already been executed successfully in this run.\n"
    "- If you need the result of a previous tool call, use the provided output rather than re-invoking it.\n"
    "- Keep the tool call as simple as possible to avoid errors.\n"
    "- Do not run long-lived or background commands such as `kubectl port-forward`, `Start-Process`, or `kubectl logs -f`; prefer single-shot commands that exit on their own.\n"
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


def get_case_specific_guidance(config):
    if config.get("test-name") != "wrong_port":
        return ""

    return (
        "### wrong_port Guidance\n"
        "- This scenario is a bare Pod with no Service. Do not use `minikube service`, `kubectl port-forward`, or background verification commands.\n"
        "- Preferred verification path: inspect the manifest, wait for `pod/kube-wrong-port` to become Ready, then use `kubectl exec kube-wrong-port -- python3 -c \"import urllib.request; print(urllib.request.urlopen('http://localhost:8765/').getcode())\"`.\n"
        "- Once all three are true, stop debugging and report success: the pod is Ready, `containerPort` is `8765`, and the in-pod HTTP check returns `200`.\n"
    )


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


def extract_metrics(response, test_case, agent_type, task_status, include_duration_cost=False):
    metrics = response.metrics or {}
    entry = {
        "test_case": test_case,
        "model": response.model,
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
