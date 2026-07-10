import hashlib
import json
import sys
import os
from api_agents import AgentAPI
from debug_agents import AgentDebug, AgentDebugStepByStep, SingleAgent
from verification_agents import AgentVerification_v1, AgentVerification_v2
from utils import setUpEnvironment, printFinishMessage
from config_merge import load_config_with_overrides
from metrics_db import store_metrics_entry, calculate_cost, calculate_totals
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from runtime_progress import PhaseHeartbeat

# Use relative path from script location
SCRIPT_DIR = Path(__file__).parent.absolute()
db_path = str(SCRIPT_DIR.parent / "token_metrics.db")

# Validate that parent directory exists (should be repo root)
if not SCRIPT_DIR.parent.exists():
    raise FileNotFoundError(
        f"Repository root directory not found: {SCRIPT_DIR.parent}\n"
        f"This script should be run from within the repository structure."
    )


def _metrics_with_lineage(metrics: dict, runtime_context: Optional[Dict[str, Any]]) -> dict:
    """Attach run_uuid/run_id from runtime_context for SQLite joins to RUN_DIR artifacts."""
    out = dict(metrics)
    if runtime_context:
        ru = runtime_context.get("run_uuid")
        ri = runtime_context.get("run_id")
        if ru:
            out["run_uuid"] = ru
        if ri:
            out["run_id"] = ri
    return out


def _persist_verification_artifact(
    runtime_context: Optional[Dict[str, Any]],
    verification_agent,
) -> None:
    """Write verification_report.txt and small meta JSON under log_dir (ARCH-004)."""
    if not runtime_context:
        return
    raw = runtime_context.get("log_dir")
    if not raw:
        return
    log_dir = Path(raw)
    log_dir.mkdir(parents=True, exist_ok=True)
    body = getattr(verification_agent, "verificationReport", None) or ""
    status = getattr(verification_agent, "verificationStatus", None)
    enc = body.encode("utf-8", errors="replace")
    meta = {
        "verification_status": status,
        "content_sha256": hashlib.sha256(enc).hexdigest(),
        "content_length": len(enc),
    }
    with open(log_dir / "verification_report.meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    with open(log_dir / "verification_report.txt", "w", encoding="utf-8") as f:
        f.write(body)


def _load_runtime_config(config_file, config_overrides: Optional[Dict[str, Any]] = None) -> dict:
    """Load config and apply overrides using the shared config module."""
    if not config_file:
        raise ValueError("config_file is required")
    return load_config_with_overrides(Path(config_file), config_overrides)


def _status_to_task_status(status: Optional[bool]) -> int:
    if status is None:
        return -1
    return int(status)


def _default_metrics(config: dict, agent_type: str, model: Optional[str] = None, task_status: int = -1) -> dict:
    return {
        "test_case": config["test-name"],
        "model": model or "",
        "agent_type": agent_type,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "task_status": task_status,
    }


def _normalize_metrics(
    config: dict,
    metrics: Optional[dict],
    agent_type: str,
    model: Optional[str] = None,
    task_status: Optional[int] = None,
) -> dict:
    normalized = _default_metrics(config, agent_type, model=model, task_status=-1)
    if isinstance(metrics, dict):
        normalized.update(metrics)
    if task_status is not None:
        normalized["task_status"] = task_status
    if not normalized.get("model") and model:
        normalized["model"] = model
    return normalized


def _finalize_metrics(metrics: dict, duration_s: float) -> dict:
    metrics["duration_s"] = round(duration_s, 2)
    model_name = metrics.get("model")
    if model_name:
        metrics["cost"] = round(
            calculate_cost(
                model_name,
                metrics.get("input_tokens", 0),
                metrics.get("output_tokens", 0),
            ),
            4,
        )
    else:
        metrics["cost"] = 0.0
    return metrics


def _run_api_phase(
    config: dict,
    runtime_context: Optional[Dict[str, Any]],
    api_agent,
) -> dict:
    api_start_time = time.perf_counter()
    api_metrics = _run_observed_phase(runtime_context, "api", api_agent.askQuestion)
    api_end_time = time.perf_counter()
    api_metrics = _normalize_metrics(
        config,
        api_metrics,
        "api",
        model=api_agent.agentProperties.get("model") if api_agent.agentProperties else None,
        task_status=1,
    )
    _finalize_metrics(api_metrics, api_end_time - api_start_time)
    store_metrics_entry(
        db_path,
        _metrics_with_lineage(api_metrics, runtime_context),
        api_metrics.get("task_status"),
    )
    return api_metrics


def _write_progress(runtime_context: Optional[Dict[str, Any]], event: str, **fields: Any) -> None:
    if not runtime_context:
        return
    progress_writer = runtime_context.get("progress_writer")
    if progress_writer is None:
        return
    progress_writer.write_event(event, pid=os.getpid(), **fields)


def _run_observed_phase(runtime_context: Optional[Dict[str, Any]], phase: str, action):
    _write_progress(runtime_context, "phase_start", phase=phase)
    with PhaseHeartbeat(
        runtime_context.get("progress_writer") if runtime_context else None,
        phase,
        pid=os.getpid(),
    ):
        try:
            result = action()
        except Exception as exc:
            _write_progress(runtime_context, "phase_end", phase=phase, status="error", error=str(exc))
            raise
    _write_progress(runtime_context, "phase_end", phase=phase, status="ok")
    return result


def _debug_agent_transcript(debug_agent) -> str:
    for attr in ("response", "knowledgeResponse"):
        text = getattr(debug_agent, attr, None)
        if text:
            return str(text)
    return "Debug agent completed execution"


def _run_verification_phase_after_debug(
    config: dict,
    runtime_context: Optional[Dict[str, Any]],
    debug_agent,
    debug_metrics: dict,
) -> Optional[Tuple[dict, Any]]:
    """
    Run AgentVerification_v2 after the debug phase.
    Returns (verification_metrics, verification_status) or None if debug timed out (verification skipped).
    """
    if getattr(debug_agent, "_last_timeout", False):
        return None

    print("\n" + "=" * 80)
    print("STARTING VERIFICATION PHASE")
    print("=" * 80 + "\n")

    verification_agent = AgentVerification_v2("verification-agent", config)
    verification_agent.runtime_context = runtime_context or {}
    verification_agent.setupAgent()
    verification_agent.debugAgentResponse = _debug_agent_transcript(debug_agent)

    verification_start_time = time.perf_counter()
    verification_metrics = _run_observed_phase(runtime_context, "verification", verification_agent.askQuestion)
    verification_end_time = time.perf_counter()

    print(f"\nFinal Task Status: {'SUCCESS' if verification_agent.verificationStatus else 'FAILURE'}")
    print(f"Debug Agent Self-Report: {'SUCCESS' if debug_agent.debugStatus else 'FAILURE'}")
    print(
        f"Verification Agent Report: {'VERIFIED' if verification_agent.verificationStatus else 'FAILED' if verification_agent.verificationStatus is False else 'UNKNOWN'}\n"
    )

    v_props = getattr(verification_agent, "agentProperties", None) or config.get("verification-agent") or {}
    verification_metrics = _normalize_metrics(
        config,
        verification_metrics,
        "verification",
        model=v_props.get("model"),
        task_status=-1 if getattr(verification_agent, "_last_timeout", False) else None,
    )
    _finalize_metrics(verification_metrics, verification_end_time - verification_start_time)
    # Debug row: task_status_verified mirrors debug self-report (same layer as task_status).
    # Verification row: task_status_verified is the verification agent outcome.
    store_metrics_entry(
        db_path,
        _metrics_with_lineage(debug_metrics, runtime_context),
        debug_metrics.get("task_status"),
    )
    store_metrics_entry(
        db_path,
        _metrics_with_lineage(verification_metrics, runtime_context),
        verification_metrics.get("task_status"),
    )
    _persist_verification_artifact(runtime_context, verification_agent)

    return verification_metrics, verification_agent.verificationStatus


def allStepsAtOnce(
    configFile=None,
    config_overrides: Optional[Dict[str, Any]] = None,
    runtime_context: Optional[Dict[str, Any]] = None,
):
    """
        This function will run the knowledge agent and debug agent.
        When the debug agent receives the response from the knowledge
        agent, the debug agent will run all the commands all at once.

        Approach by: William Clifford

        Args:
            configFile: Path to config_step.json file
            config_overrides: Optional dict of dotted-path overrides
                              e.g. {"debug-agent.model": "gpt-4o"}
    """

    # Read config to initialize environment
    config = _load_runtime_config(configFile, config_overrides)
    _write_progress(runtime_context, "setup_start", test_name=config.get("test-name"))
    try:
        setUpEnvironment(config)
    except Exception as exc:
        _write_progress(runtime_context, "setup_end", test_name=config.get("test-name"), status="error", error=str(exc))
        raise
    _write_progress(runtime_context, "setup_end", test_name=config.get("test-name"), status="ok")
    # Initialize needed LLMs
    apiAgent = AgentAPI("api-agent" , config)
    debugAgent = AgentDebug("debug-agent" , config)
    debugAgent.runtime_context = runtime_context or {}
    #set up the LLMs
    apiAgent.setupAgent()
    debugAgent.setupAgent()

    #Run the LLMs as needed
    api_metrics = _run_api_phase(config, runtime_context, apiAgent)
    debugAgent.agentAPIResponse = apiAgent.response
    debug_start_time = time.perf_counter()
    debug_metrics = _run_observed_phase(runtime_context, "debug", debugAgent.askQuestion)
    debug_end_time = time.perf_counter()
    debug_metrics = _normalize_metrics(
        config,
        debug_metrics,
        "debug",
        model=debugAgent.agentProperties.get("model") if debugAgent.agentProperties else None,
        task_status=-1 if getattr(debugAgent, "_last_timeout", False) else _status_to_task_status(debugAgent.debugStatus),
    )
    _finalize_metrics(debug_metrics, debug_end_time - debug_start_time)

    if getattr(debugAgent, "_last_timeout", False):
        print("\nDebug agent timed out. Skipping verification phase.\n")
        store_metrics_entry(
            db_path,
            _metrics_with_lineage(debug_metrics, runtime_context),
            debug_metrics.get("task_status"),
        )
        printFinishMessage()
        return {
            "status": False,
            "api_metrics": api_metrics,
            "debug_metrics": debug_metrics,
            "verification_metrics": None,
        }

    verification_out = _run_verification_phase_after_debug(
        config, runtime_context, debugAgent, debug_metrics
    )
    assert verification_out is not None
    verification_metrics, verification_status = verification_out
    printFinishMessage()

    return {
        "status": verification_status,
        "api_metrics": api_metrics,
        "debug_metrics": debug_metrics,
        "verification_metrics": verification_metrics,
    }

def stepByStep(
    configFile=None,
    config_overrides: Optional[Dict[str, Any]] = None,
    runtime_context: Optional[Dict[str, Any]] = None,
):
    """
        This function will run the knowledge and debug agent.
        The knowledge agent will return the response with steps to run
        with a bash script for each step nicely formatted for the debug agent
        to then breakdown the steps and run it step by step, while trying to
        fix issues with each step if any.

        Approach by: Aaron Perez

        Args:
            configFile: Path to config_step.json file
            config_overrides: Optional dict of dotted-path overrides
    """
    # Read config to initialize environment
    config = _load_runtime_config(configFile, config_overrides)
    _write_progress(runtime_context, "setup_start", test_name=config.get("test-name"))
    try:
        setUpEnvironment(config)
    except Exception as exc:
        _write_progress(runtime_context, "setup_end", test_name=config.get("test-name"), status="error", error=str(exc))
        raise
    _write_progress(runtime_context, "setup_end", test_name=config.get("test-name"), status="ok")
    # Initialize needed LLMs
    apiAgent = AgentAPI("api-agent" , config)
    debugAgent = AgentDebugStepByStep("debug-agent", config)
    debugAgent.runtime_context = runtime_context or {}
    #set up the LLMs
    apiAgent.setupAgent()
    debugAgent.setupAgent()

    #Run the LLMs as needed
    api_metrics = _run_api_phase(config, runtime_context, apiAgent)
    debugAgent.agentAPIResponse = apiAgent.response
    debugAgent.formProblemSolvingSteps()
    debug_start_time = time.perf_counter()
    debug_metrics = _run_observed_phase(runtime_context, "debug", debugAgent.executeProblemSteps)
    debug_end_time = time.perf_counter()
    debug_metrics = _normalize_metrics(
        config,
        debug_metrics,
        "debug",
        model=debugAgent.agentProperties.get("model") if debugAgent.agentProperties else None,
        task_status=-1 if getattr(debugAgent, "_last_timeout", False) else _status_to_task_status(debugAgent.debugStatus),
    )
    _finalize_metrics(debug_metrics, debug_end_time - debug_start_time)

    if getattr(debugAgent, "_last_timeout", False):
        store_metrics_entry(
            db_path,
            _metrics_with_lineage(debug_metrics, runtime_context),
            debug_metrics.get("task_status"),
        )
        printFinishMessage()
        return {
            "status": False,
            "api_metrics": api_metrics,
            "debug_metrics": debug_metrics,
            "verification_metrics": None,
        }

    verification_out = _run_verification_phase_after_debug(
        config, runtime_context, debugAgent, debug_metrics
    )
    assert verification_out is not None
    verification_metrics, verification_status = verification_out
    printFinishMessage()

    return {
        "status": verification_status,
        "api_metrics": api_metrics,
        "debug_metrics": debug_metrics,
        "verification_metrics": verification_metrics,
    }


def singleAgentApproach(
    configFile=None,
    config_overrides: Optional[Dict[str, Any]] = None,
    runtime_context: Optional[Dict[str, Any]] = None,
):
    """
        This function will run a single agent which will do the
        reasoning on top of the actioning

        Args:
            configFile: Path to config_step.json file
            config_overrides: Optional dict of dotted-path overrides
    """
    # Read config to initialize environment
    config = _load_runtime_config(configFile, config_overrides)
    _write_progress(runtime_context, "setup_start", test_name=config.get("test-name"))
    try:
        setUpEnvironment(config)
    except Exception as exc:
        _write_progress(runtime_context, "setup_end", test_name=config.get("test-name"), status="error", error=str(exc))
        raise
    _write_progress(runtime_context, "setup_end", test_name=config.get("test-name"), status="ok")
    # Initialize needed LLMs
    agent = SingleAgent("single-agent", config)
    agent.runtime_context = runtime_context or {}
    #set up the LLMs
    agent.setupAgent()

    #Run the LLMs as needed
    debug_start_time = time.perf_counter()
    debug_metrics = _run_observed_phase(runtime_context, "debug", agent.askQuestion)
    debug_end_time = time.perf_counter()
    debug_model = getattr(agent, "_resolved_debug_model_name", None) or (
        agent.agentProperties.get("model") if agent.agentProperties else None
    )
    debug_metrics = _normalize_metrics(
        config,
        debug_metrics,
        "debug",
        model=debug_model,
        task_status=-1 if getattr(agent, "_last_timeout", False) else _status_to_task_status(agent.debugStatus),
    )
    _finalize_metrics(debug_metrics, debug_end_time - debug_start_time)

    if getattr(agent, "_last_timeout", False):
        store_metrics_entry(
            db_path,
            _metrics_with_lineage(debug_metrics, runtime_context),
            debug_metrics.get("task_status"),
        )
        printFinishMessage()
        return {
            "status": False,
            "debug_metrics": debug_metrics,
            "verification_metrics": None,
        }

    verification_out = _run_verification_phase_after_debug(config, runtime_context, agent, debug_metrics)
    assert verification_out is not None
    verification_metrics, verification_status = verification_out
    printFinishMessage()

    return {
        "status": verification_status,
        "debug_metrics": debug_metrics,
        "verification_metrics": verification_metrics,
    }


def run(debugType, configFile, config_overrides: Optional[Dict[str, Any]] = None, runtime_context: Optional[Dict[str, Any]] = None):
    if debugType == "allStepsAtOnce":
        return allStepsAtOnce(configFile, config_overrides=config_overrides, runtime_context=runtime_context)
    if debugType == "stepByStep":
        return stepByStep(configFile, config_overrides=config_overrides, runtime_context=runtime_context)
    if debugType == "singleAgent":
        return singleAgentApproach(configFile, config_overrides=config_overrides, runtime_context=runtime_context)
    return None

if __name__ == "__main__":
    if (len(sys.argv) < 2):
        print('Usage: python3 main.py <config_file> [test_type]')
        print('Available test types: allStepsAtOnce, stepByStep, singleAgent (default: allStepsAtOnce)')
        sys.exit(1)

    configFile = sys.argv[1]
    
    # Get test type from second argument, default to "allStepsAtOnce"
    testType = sys.argv[2] if len(sys.argv) > 2 else "allStepsAtOnce"
    
    # Validate test type
    validTestTypes = ["allStepsAtOnce", "stepByStep", "singleAgent"]
    if testType not in validTestTypes:
        print(f'Invalid test type: {testType}')
        print(f'Available test types: {", ".join(validTestTypes)}')
        sys.exit(1)
    
    if os.path.exists(configFile):
        run(testType, configFile)
    else:
        print (f'{configFile} does not exist')




    
