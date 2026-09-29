#!/usr/bin/env python3
"""Parallel test execution with per-process workers, queues, and hard timeouts."""

import json
import queue
import time
import traceback
from datetime import datetime
from multiprocessing import Process, Queue
from pathlib import Path
from typing import Any, Dict, List, Optional

from debug_assistant_latest.executor import (
    TestResult,
    _has_ground_truth_config,
    result_to_summary,
    run_single_test,
    run_single_test_in_process,
)
from debug_assistant_latest.provenance import build_environment_context
from debug_assistant_latest.report import save_test_summary

# Per-test timeout for parallel execution (seconds)
PARALLEL_TEST_TIMEOUT = 600


def _write_run_control(
    output_dir: Path,
    planned_names: List[str],
    results: List[TestResult],
    *,
    status: str,
    stop_reason: Optional[str] = None,
    in_progress: Optional[List[str]] = None,
) -> None:
    completed = {result.test_name for result in results}
    active = set(in_progress or ()) - completed
    control = {
        "status": status,
        "stop_reason": stop_reason,
        "planned_count": len(planned_names),
        "completed_count": len(completed),
        "planned_test_names": planned_names,
        "completed_test_names": [name for name in planned_names if name in completed],
        "in_progress_test_names": [name for name in planned_names if name in active],
        "unstarted_test_names": [name for name in planned_names if name not in completed and name not in active],
        "updated_at": datetime.now().isoformat(),
    }
    path = output_dir / "run_control.json"
    temporary_path = path.with_suffix(".json.tmp")
    with temporary_path.open("w", encoding="utf-8") as stream:
        json.dump(control, stream, indent=2)
    temporary_path.replace(path)


def _record_result(
    result: TestResult,
    results: List[TestResult],
    *,
    test_names: List[str],
    technique: str,
    overrides: dict,
    output_dir: Path,
    status: str,
    stop_reason: Optional[str] = None,
    in_progress: Optional[List[str]] = None,
) -> None:
    results.append(result)
    save_test_summary(result_to_summary(result, technique, overrides), result.log_dir)
    _write_run_control(
        output_dir,
        test_names,
        results,
        status=status,
        stop_reason=stop_reason,
        in_progress=in_progress,
    )


def _worker_wrapper(
    result_queue: Queue,
    test_name: str,
    technique: str,
    overrides: dict,
    output_dir: Path,
    teardown_after_run: bool,
    run_uuid: str,
    run_id: str,
    environment_context: Optional[Dict[str, Any]],
) -> None:
    """
    Worker wrapper that runs a test and puts the result in a Queue.

    This allows the parent process to enforce a hard timeout by terminating
    the worker process if it exceeds the limit.
    """
    try:
        result = run_single_test_in_process(
            test_name,
            technique,
            overrides,
            output_dir,
            teardown_after_run,
            run_uuid=run_uuid,
            run_id=run_id,
            environment_context=environment_context,
        )
        result_queue.put(("success", result))
    except Exception as e:
        result_queue.put(("error", (test_name, str(e), traceback.format_exc())))


def run_tests_parallel(
    test_names: List[str],
    technique: str,
    overrides: dict,
    output_dir: Path,
    max_workers: int = 1,
    teardown_after_run: bool = False,
    run_uuid: str = "",
    run_id: str = "",
    environment_context: Optional[Dict[str, Any]] = None,
    parallel_timeout_s: int = PARALLEL_TEST_TIMEOUT,
) -> List[TestResult]:
    """
    Run multiple tests in parallel with hard per-test timeout.

    Uses one ``multiprocessing.Process`` per active test with a result ``Queue``
    so workers can be terminated on timeout (``concurrent.futures`` does not
    support hard kills the same way).

    Args:
        test_names: List of test case names to run
        technique: Execution technique (allStepsAtOnce, stepByStep, singleAgent, knowledgeAgentOnly)
        overrides: Config overrides to apply
        output_dir: Base output directory for this run
        max_workers: Maximum number of parallel workers
        teardown_after_run: Run teardown after test completes

    Returns:
        List of TestResult objects
    """
    if technique == "knowledgeAgentOnly" and max_workers > 1:
        raise ValueError(
            "knowledgeAgentOnly requires serial execution because the RAG API keeps one shared assistant session."
        )

    results = []
    gt_configured_by_test = {
        test_name: _has_ground_truth_config(test_name, overrides) for test_name in test_names
    }
    seq_runtime_context = None
    if run_uuid or run_id or environment_context is not None:
        seq_runtime_context = {
            "run_uuid": run_uuid,
            "run_id": run_id,
            "environment_context": environment_context if environment_context is not None else build_environment_context(),
        }

    if max_workers == 1:
        # Sequential execution
        _write_run_control(output_dir, test_names, results, status="running")
        for name in test_names:
            _write_run_control(
                output_dir,
                test_names,
                results,
                status="running",
                in_progress=[name],
            )
            try:
                result = run_single_test(
                    name,
                    technique,
                    overrides,
                    output_dir,
                    verbose=True,
                    teardown_after_run=teardown_after_run,
                    runtime_context=seq_runtime_context,
                )
            except KeyboardInterrupt:
                now = datetime.now().isoformat()
                result = TestResult(
                    test_name=name,
                    success=False,
                    verified=None,
                    debug_self_report=None,
                    duration_s=0.0,
                    error="Interrupted by user before case completion",
                    metrics={},
                    log_dir=output_dir / name,
                    started_at=now,
                    finished_at=now,
                    ground_truth_configured=gt_configured_by_test.get(name, False),
                    architecture_outcome="interrupted" if technique == "knowledgeAgentOnly" else None,
                    interrupted=True,
                )
                _record_result(
                    result,
                    results,
                    test_names=test_names,
                    technique=technique,
                    overrides=overrides,
                    output_dir=output_dir,
                    status="interrupted",
                    stop_reason="keyboard_interrupt",
                )
                break

            if result.interrupted:
                status, reason = "interrupted", "keyboard_interrupt"
            elif result.teardown_failed:
                status, reason = "stopped_cleanup_failure", result.teardown_error
            else:
                status, reason = "running", None
            _record_result(
                result,
                results,
                test_names=test_names,
                technique=technique,
                overrides=overrides,
                output_dir=output_dir,
                status=status,
                stop_reason=reason,
            )
            if result.interrupted or result.teardown_failed:
                break
        else:
            _write_run_control(output_dir, test_names, results, status="completed")
    else:
        # Parallel execution with hard per-test timeout
        print(f"Running {len(test_names)} tests with {max_workers} workers...")
        print(f"Hard timeout: {parallel_timeout_s}s per test")
        print("WARNING: Parallel execution may cause K8s resource conflicts if tests")
        print("         use overlapping resource names. Use --jobs 1 for isolation.")
        print()

        # Track active processes: {test_name: (process, queue, start_time)}
        active: Dict[str, tuple] = {}
        pending = list(test_names)
        _write_run_control(output_dir, test_names, results, status="running")
        halt_reason = None

        while pending or active:
            # Launch new processes up to max_workers
            while pending and len(active) < max_workers and halt_reason is None:
                test_name = pending.pop(0)
                result_queue = Queue()
                proc = Process(
                    target=_worker_wrapper,
                    args=(
                        result_queue,
                        test_name,
                        technique,
                        overrides,
                        output_dir,
                        teardown_after_run,
                        run_uuid,
                        run_id,
                        environment_context,
                    ),
                )
                proc.start()
                active[test_name] = (proc, result_queue, time.perf_counter())

            # Check for completed or timed-out processes
            completed = []
            previous_result_count = len(results)
            for test_name, (proc, result_queue, start_time) in active.items():
                elapsed = time.perf_counter() - start_time

                if not proc.is_alive():
                    # Process finished - collect result
                    try:
                        # Use get with short timeout to avoid race with empty()
                        status_type, payload = result_queue.get(timeout=1.0)
                        if status_type == "success":
                            result = payload
                            results.append(result)
                            status = "PASS" if result.success else ("ERROR" if result.error else "FAIL")
                            print(f"[{status}] {test_name} ({result.duration_s:.1f}s)")
                            if result.teardown_failed:
                                halt_reason = result.teardown_error or f"teardown failed for {test_name}"
                            elif result.interrupted:
                                halt_reason = "keyboard_interrupt"
                        else:
                            # Error during execution
                            _, err_msg, _ = payload
                            print(f"[ERROR] {test_name}: {err_msg}")
                            results.append(
                                TestResult(
                                    test_name=test_name,
                                    success=False,
                                    verified=None,
                                    debug_self_report=None,
                                    duration_s=elapsed,
                                    error=f"Worker error: {err_msg}",
                                    metrics={},
                                    log_dir=output_dir / test_name,
                                    started_at=datetime.now().isoformat(),
                                    finished_at=datetime.now().isoformat(),
                                    ground_truth_configured=gt_configured_by_test.get(test_name, False),
                                )
                            )
                    except queue.Empty:
                        # Process ended but no result (crash)
                        print(f"[ERROR] {test_name}: Worker crashed without result")
                        results.append(
                            TestResult(
                                test_name=test_name,
                                success=False,
                                verified=None,
                                debug_self_report=None,
                                duration_s=elapsed,
                                error="Worker crashed without result",
                                metrics={},
                                log_dir=output_dir / test_name,
                                started_at=datetime.now().isoformat(),
                                finished_at=datetime.now().isoformat(),
                                ground_truth_configured=gt_configured_by_test.get(test_name, False),
                            )
                        )
                    finally:
                        proc.join(timeout=1)
                        # Cleanup queue to prevent resource leaks
                        result_queue.close()
                        result_queue.cancel_join_thread()
                        completed.append(test_name)

                elif elapsed > parallel_timeout_s:
                    # Hard timeout - terminate the process
                    print(f"[TIMEOUT] {test_name}: Exceeded {parallel_timeout_s}s, terminating...")
                    proc.terminate()
                    proc.join(timeout=5)
                    if proc.is_alive():
                        proc.kill()
                        proc.join(timeout=1)

                    # Cleanup queue to prevent resource leaks
                    result_queue.close()
                    result_queue.cancel_join_thread()

                    # Log timeout to per-test stderr.log
                    log_dir = output_dir / test_name
                    log_dir.mkdir(parents=True, exist_ok=True)
                    stderr_log = log_dir / "stderr.log"
                    with open(stderr_log, "a", encoding="utf-8") as f:
                        f.write(f"\n\n[TIMEOUT] Test exceeded {parallel_timeout_s}s and was terminated.\n")

                    results.append(
                        TestResult(
                            test_name=test_name,
                            success=False,
                            verified=None,
                            debug_self_report=None,
                            duration_s=elapsed,
                            error=f"Timeout: exceeded {parallel_timeout_s}s",
                            metrics={},
                            log_dir=log_dir,
                            started_at=datetime.now().isoformat(),
                            finished_at=datetime.now().isoformat(),
                            ground_truth_configured=gt_configured_by_test.get(test_name, False),
                        )
                    )

                    # Teardown after timeout kill
                    if teardown_after_run:
                        teardown_failed = False
                        teardown_error = None
                        teardown_recoveries = []
                        try:
                            from teardown import teardown_environment

                            teardown_recoveries = teardown_environment(test_name)
                        except Exception as td_err:
                            teardown_failed = True
                            teardown_error = str(td_err)
                            with open(stderr_log, "a", encoding="utf-8") as f:
                                f.write(f"\n[WARNING] Post-timeout teardown failed: {td_err}\n")
                        results[-1].teardown_attempted = True
                        results[-1].teardown_failed = teardown_failed
                        results[-1].teardown_error = teardown_error
                        results[-1].teardown_recoveries = teardown_recoveries
                        if teardown_failed:
                            halt_reason = teardown_error or f"teardown failed for {test_name}"

                    completed.append(test_name)

            # Remove completed tests from active
            for test_name in completed:
                del active[test_name]

            for result in results[previous_result_count:]:
                save_test_summary(result_to_summary(result, technique, overrides), result.log_dir)
            if halt_reason is None and not pending and not active:
                control_status = "completed"
            elif halt_reason is not None:
                control_status = "stopped_cleanup_failure" if halt_reason != "keyboard_interrupt" else "interrupted"
            else:
                control_status = "running"
            _write_run_control(
                output_dir,
                test_names,
                results,
                status=control_status,
                stop_reason=halt_reason,
                in_progress=list(active),
            )

            if halt_reason is not None and not active:
                break

            # Brief sleep to avoid busy-waiting
            if active:
                time.sleep(0.5)

    return results
