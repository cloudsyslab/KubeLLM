RELEVANT_FILE_TYPES = ["deployment", "application", "service", "dockerfile"]
TOOL_USAGE_RULES = (
    "### Tool Usage Rules\n"
    "- Do not attempt many commands in one tool call.\n"
    "- Never repeat a tool call that has already been executed successfully in this run.\n"
    "- If you need the result of a previous tool call, use the provided output rather than re-invoking it.\n"
    "- Keep the tool call as simple as possible to avoid errors.\n"
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
