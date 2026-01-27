#!/usr/bin/env python3
"""
KubeLLM Test Runner - orchestrate Kubernetes troubleshooting tests.

This is the main CLI entrypoint for running tests with parallelism,
config overrides, and structured reporting.

Usage:
    python3 runner.py --list                           # List available test cases
    python3 runner.py wrong_port                       # Run single test
    python3 runner.py --run-many "port_*" --jobs 4    # Run pattern in parallel
    python3 runner.py wrong_port --debug-model gpt-4o # With config override
"""

import argparse
import json
import multiprocessing
import os
import queue
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass
from datetime import datetime
from io import StringIO
from multiprocessing import Process, Queue
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Per-test timeout for parallel execution (seconds)
PARALLEL_TEST_TIMEOUT = 600

# Script directory - all paths relative to this
SCRIPT_DIR = Path(__file__).parent.absolute()
REPO_ROOT = SCRIPT_DIR.parent

# Import local modules
from test_discovery import list_test_cases, match_pattern, get_config_path, get_test_info
from config_merge import (
    merge_config_overrides,
    build_overrides_from_args,
    load_config_with_overrides,
    save_effective_config,
    CLI_TO_CONFIG_MAP,
)
from report import (
    TestSummary,
    AgentMetrics,
    save_test_summary,
    generate_aggregate_report,
    save_aggregate_report,
    save_run_config,
    print_console_summary,
)


@dataclass
class TestResult:
    """Result of a single test execution."""
    test_name: str
    success: bool
    verified: bool
    debug_self_report: Optional[bool]
    duration_s: float
    error: Optional[str]
    metrics: Dict[str, Any]
    log_dir: Path
    started_at: str
    finished_at: str


def get_timestamp_id() -> str:
    """Generate a filesystem-safe timestamp ID for a run."""
    return datetime.now().strftime("%Y-%m-%dT%H-%M-%S")


def get_output_dir(run_id: str, base_dir: Optional[Path] = None) -> Path:
    """Get the output directory for a test run."""
    if base_dir:
        return base_dir
    return REPO_ROOT / ".local" / "test_runs" / run_id


def run_single_test_in_process(
    test_name: str,
    technique: str,
    overrides: dict,
    output_dir: Path,
    backup_before_run: bool = False,
    teardown_after_run: bool = False,
    forced_backup_warning: bool = False,
) -> TestResult:
    """
    Run a single test case - worker function for parallel execution.

    This function runs in a separate process and captures stdout/stderr.
    """
    log_dir = output_dir / test_name
    log_dir.mkdir(parents=True, exist_ok=True)

    stdout_log = log_dir / "stdout.log"
    stderr_log = log_dir / "stderr.log"

    # Log forced backup warning to per-test stderr.log
    if forced_backup_warning:
        with open(stderr_log, "a") as f:
            f.write("[WARNING] --teardown-after-run requires backup; auto-enabling --backup-before-run\n")

    started_at = datetime.now().isoformat()
    start_time = time.perf_counter()

    success = False
    verified = None
    debug_self_report = None
    error = None
    metrics = {}
    test_started = False  # Guard: only teardown if test actually started

    try:
        # Import here to avoid circular imports in worker process
        from main import allStepsAtOnce, stepByStep, singleAgentApproach
        from config_merge import load_config_with_overrides, save_effective_config
        from kube_test import backupEnviornment, tearDownEnviornment

        # Opt-in backup before run (fail fast if backup fails)
        if backup_before_run:
            try:
                backupEnviornment(test_name)
            except Exception as backup_err:
                error = f"Backup failed: {backup_err}"
                with open(stderr_log, "a") as f:
                    f.write(f"BACKUP FAILED:\n{traceback.format_exc()}")
                raise  # Abort test - don't proceed without backup

        config_path = get_config_path(test_name)
        config = load_config_with_overrides(config_path, overrides)

        # Save effective config for audit trail
        save_effective_config(config, log_dir / "config_effective.json")

        # Mark test as started (backup succeeded, about to run test)
        test_started = True

        # Capture stdout/stderr
        with open(stdout_log, "w") as stdout_f, open(stderr_log, "w") as stderr_f:
            # Redirect stdout/stderr
            old_stdout, old_stderr = sys.stdout, sys.stderr
            sys.stdout = stdout_f
            sys.stderr = stderr_f

            try:
                if technique == "allStepsAtOnce":
                    result = allStepsAtOnce(configFile=str(config_path), config_overrides=overrides)
                    # allStepsAtOnce runs verification agent, so verified = result
                    success = result is True
                    verified = result is True
                elif technique == "stepByStep":
                    result = stepByStep(configFile=str(config_path), config_overrides=overrides)
                    # stepByStep has no verification agent
                    success = result is True
                    verified = None  # No verification performed
                elif technique == "singleAgent":
                    result = singleAgentApproach(configFile=str(config_path), config_overrides=overrides)
                    # singleAgent has no verification agent
                    success = result is True
                    verified = None  # No verification performed
                else:
                    raise ValueError(f"Unknown technique: {technique}")
            finally:
                sys.stdout, sys.stderr = old_stdout, old_stderr

    except Exception as e:
        if error is None:  # Don't overwrite backup error
            error = str(e)
        with open(stderr_log, "a") as f:
            f.write(f"\n\nEXCEPTION:\n{traceback.format_exc()}")

    # Opt-in teardown after run (only if test started; log warnings to stderr.log)
    if teardown_after_run and test_started:
        try:
            tearDownEnviornment(test_name)
        except Exception as teardown_err:
            # Route warning to per-test stderr.log
            with open(stderr_log, "a") as f:
                f.write(f"\n\n[WARNING] Teardown failed for {test_name}: {teardown_err}\n")
                f.write(traceback.format_exc())

    duration = time.perf_counter() - start_time
    finished_at = datetime.now().isoformat()

    return TestResult(
        test_name=test_name,
        success=success,
        verified=verified,
        debug_self_report=debug_self_report,
        duration_s=duration,
        error=error,
        metrics=metrics,
        log_dir=log_dir,
        started_at=started_at,
        finished_at=finished_at,
    )


def run_single_test(
    test_name: str,
    technique: str,
    overrides: dict,
    output_dir: Path,
    verbose: bool = True,
    backup_before_run: bool = False,
    teardown_after_run: bool = False,
    forced_backup_warning: bool = False,
) -> TestResult:
    """
    Run a single test case (in the current process).

    For parallel execution, use run_tests_parallel() instead.
    """
    log_dir = output_dir / test_name
    log_dir.mkdir(parents=True, exist_ok=True)

    stdout_log = log_dir / "stdout.log"
    stderr_log = log_dir / "stderr.log"

    # Log forced backup warning to per-test stderr.log
    if forced_backup_warning:
        with open(stderr_log, "a") as f:
            f.write("[WARNING] --teardown-after-run requires backup; auto-enabling --backup-before-run\n")

    started_at = datetime.now().isoformat()
    start_time = time.perf_counter()

    success = False
    verified = None
    debug_self_report = None
    error = None
    metrics = {}
    test_started = False  # Guard: only teardown if test actually started

    if verbose:
        print(f"[RUNNING] {test_name} ({technique})")

    try:
        from main import allStepsAtOnce, stepByStep, singleAgentApproach
        from kube_test import backupEnviornment, tearDownEnviornment

        # Opt-in backup before run (fail fast if backup fails)
        if backup_before_run:
            if verbose:
                print(f"[BACKUP] Creating backup for {test_name}")
            try:
                backupEnviornment(test_name)
            except Exception as backup_err:
                error = f"Backup failed: {backup_err}"
                if verbose:
                    print(f"[ERROR] Backup failed for {test_name}: {backup_err}")
                with open(stderr_log, "a") as f:
                    f.write(f"BACKUP FAILED:\n{traceback.format_exc()}")
                raise  # Abort test - don't proceed without backup

        config_path = get_config_path(test_name)
        config = load_config_with_overrides(config_path, overrides)

        # Save effective config for audit trail
        save_effective_config(config, log_dir / "config_effective.json")

        # Mark test as started (backup succeeded, about to run test)
        test_started = True

        # For single test, we tee output to both console and file
        # Open log files for writing
        with open(stdout_log, "w") as stdout_f, open(stderr_log, "w") as stderr_f:
            # Create tee writers
            class TeeWriter:
                def __init__(self, *streams):
                    self.streams = streams

                def write(self, data):
                    for s in self.streams:
                        s.write(data)
                        s.flush()

                def flush(self):
                    for s in self.streams:
                        s.flush()

            old_stdout, old_stderr = sys.stdout, sys.stderr
            if verbose:
                sys.stdout = TeeWriter(old_stdout, stdout_f)
                sys.stderr = TeeWriter(old_stderr, stderr_f)
            else:
                sys.stdout = stdout_f
                sys.stderr = stderr_f

            try:
                if technique == "allStepsAtOnce":
                    result = allStepsAtOnce(configFile=str(config_path), config_overrides=overrides)
                    # allStepsAtOnce runs verification agent, so verified = result
                    success = result is True
                    verified = result is True
                elif technique == "stepByStep":
                    result = stepByStep(configFile=str(config_path), config_overrides=overrides)
                    # stepByStep has no verification agent
                    success = result is True
                    verified = None  # No verification performed
                elif technique == "singleAgent":
                    result = singleAgentApproach(configFile=str(config_path), config_overrides=overrides)
                    # singleAgent has no verification agent
                    success = result is True
                    verified = None  # No verification performed
                else:
                    raise ValueError(f"Unknown technique: {technique}")
            finally:
                sys.stdout, sys.stderr = old_stdout, old_stderr

    except Exception as e:
        if error is None:  # Don't overwrite backup error
            error = str(e)
        if verbose:
            print(f"[ERROR] {test_name}: {error}")
        with open(stderr_log, "a") as f:
            f.write(f"\n\nEXCEPTION:\n{traceback.format_exc()}")

    # Opt-in teardown after run (only if test started; log warnings to stderr.log)
    if teardown_after_run and test_started:
        try:
            if verbose:
                print(f"[TEARDOWN] Running teardown for {test_name}")
            tearDownEnviornment(test_name)
        except Exception as teardown_err:
            warning_msg = f"[WARNING] Teardown failed for {test_name}: {teardown_err}"
            if verbose:
                print(warning_msg, file=sys.stderr)
            # Also log to per-test stderr.log
            with open(stderr_log, "a") as f:
                f.write(f"\n\n{warning_msg}\n")
                f.write(traceback.format_exc())

    duration = time.perf_counter() - start_time
    finished_at = datetime.now().isoformat()

    status = "PASS" if success else ("ERROR" if error else "FAIL")
    if verbose:
        print(f"[{status}] {test_name} ({duration:.1f}s)")

    return TestResult(
        test_name=test_name,
        success=success,
        verified=verified,
        debug_self_report=debug_self_report,
        duration_s=duration,
        error=error,
        metrics=metrics,
        log_dir=log_dir,
        started_at=started_at,
        finished_at=finished_at,
    )


def _worker_wrapper(
    result_queue: Queue,
    test_name: str,
    technique: str,
    overrides: dict,
    output_dir: Path,
    backup_before_run: bool,
    teardown_after_run: bool,
    forced_backup_warning: bool,
) -> None:
    """
    Worker wrapper that runs a test and puts the result in a Queue.

    This allows the parent process to enforce a hard timeout by terminating
    the worker process if it exceeds the limit.
    """
    try:
        result = run_single_test_in_process(
            test_name, technique, overrides, output_dir,
            backup_before_run, teardown_after_run, forced_backup_warning,
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
    backup_before_run: bool = False,
    teardown_after_run: bool = False,
    forced_backup_warning: bool = False,
) -> List[TestResult]:
    """
    Run multiple tests in parallel with hard per-test timeout.

    Args:
        test_names: List of test case names to run
        technique: Execution technique (allStepsAtOnce, stepByStep, singleAgent)
        overrides: Config overrides to apply
        output_dir: Base output directory for this run
        max_workers: Maximum number of parallel workers
        backup_before_run: Create backup of test files before running
        teardown_after_run: Run teardown after test completes
        forced_backup_warning: If True, log warning about auto-enabled backup

    Returns:
        List of TestResult objects
    """
    results = []

    if max_workers == 1:
        # Sequential execution
        for name in test_names:
            result = run_single_test(
                name, technique, overrides, output_dir,
                verbose=True,
                backup_before_run=backup_before_run,
                teardown_after_run=teardown_after_run,
                forced_backup_warning=forced_backup_warning,
            )
            results.append(result)
    else:
        # Parallel execution with hard per-test timeout
        print(f"Running {len(test_names)} tests with {max_workers} workers...")
        print(f"Hard timeout: {PARALLEL_TEST_TIMEOUT}s per test")
        print("WARNING: Parallel execution may cause K8s resource conflicts if tests")
        print("         use overlapping resource names. Use --jobs 1 for isolation.")
        print()

        # Track active processes: {test_name: (process, queue, start_time)}
        active: Dict[str, tuple] = {}
        pending = list(test_names)

        while pending or active:
            # Launch new processes up to max_workers
            while pending and len(active) < max_workers:
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
                        backup_before_run,
                        teardown_after_run,
                        forced_backup_warning,
                    ),
                )
                proc.start()
                active[test_name] = (proc, result_queue, time.perf_counter())

            # Check for completed or timed-out processes
            completed = []
            for test_name, (proc, result_queue, start_time) in active.items():
                elapsed = time.perf_counter() - start_time

                if not proc.is_alive():
                    # Process finished - collect result
                    proc.join(timeout=1)
                    try:
                        # Use get with short timeout to avoid race with empty()
                        status_type, payload = result_queue.get(timeout=0.1)
                        if status_type == "success":
                            result = payload
                            results.append(result)
                            status = "PASS" if result.success else ("ERROR" if result.error else "FAIL")
                            print(f"[{status}] {test_name} ({result.duration_s:.1f}s)")
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
                            )
                        )
                    finally:
                        # Cleanup queue to prevent resource leaks
                        result_queue.close()
                        result_queue.cancel_join_thread()
                        completed.append(test_name)

                elif elapsed > PARALLEL_TEST_TIMEOUT:
                    # Hard timeout - terminate the process
                    print(f"[TIMEOUT] {test_name}: Exceeded {PARALLEL_TEST_TIMEOUT}s, terminating...")
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
                    with open(stderr_log, "a") as f:
                        f.write(f"\n\n[TIMEOUT] Test exceeded {PARALLEL_TEST_TIMEOUT}s and was terminated.\n")

                    results.append(
                        TestResult(
                            test_name=test_name,
                            success=False,
                            verified=None,
                            debug_self_report=None,
                            duration_s=elapsed,
                            error=f"Timeout: exceeded {PARALLEL_TEST_TIMEOUT}s",
                            metrics={},
                            log_dir=log_dir,
                            started_at=datetime.now().isoformat(),
                            finished_at=datetime.now().isoformat(),
                        )
                    )
                    completed.append(test_name)

            # Remove completed tests from active
            for test_name in completed:
                del active[test_name]

            # Brief sleep to avoid busy-waiting
            if active:
                time.sleep(0.5)

    return results


def result_to_summary(result: TestResult, technique: str, overrides: dict) -> TestSummary:
    """Convert a TestResult to a TestSummary for reporting."""
    status = "PASS" if result.success else ("ERROR" if result.error else "FAIL")

    return TestSummary(
        test_name=result.test_name,
        technique=technique,
        status=status,
        verified=result.verified,
        debug_self_report=result.debug_self_report,
        started_at=result.started_at,
        finished_at=result.finished_at,
        duration_s=result.duration_s,
        error_message=result.error,
        metrics=result.metrics,
        config_overrides_applied=overrides,
    )


def cmd_list(args):
    """Handle --list command."""
    test_cases = list_test_cases()

    if args.verbose:
        print(f"Available test cases ({len(test_cases)}):\n")
        for tc in test_cases:
            try:
                info = get_test_info(tc)
                print(f"  {tc}")
                print(f"    Debug model: {info['debug_model']}")
                print(f"    API model: {info['api_model']}")
                print(f"    Problem: {info['problem_desc']}...")
                print()
            except Exception as e:
                print(f"  {tc} (error loading info: {e})")
    else:
        print(f"Available test cases ({len(test_cases)}):")
        for tc in test_cases:
            print(f"  {tc}")

    return 0


def cmd_run_single(args, test_name: str):
    """Handle single test run."""
    run_id = get_timestamp_id()
    output_dir = get_output_dir(run_id, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    overrides = build_overrides_from_args(args)
    technique = args.technique
    backup_before_run = args.backup_before_run
    teardown_after_run = args.teardown_after_run
    forced_backup_warning = False

    # Enforce backup when teardown is enabled (prevent file loss)
    if teardown_after_run and not backup_before_run:
        backup_before_run = True
        forced_backup_warning = True
        print("[WARNING] --teardown-after-run requires backup; auto-enabling --backup-before-run")

    # Save run config
    run_config = {
        "test_names": [test_name],
        "technique": technique,
        "overrides": overrides,
        "jobs": 1,
        "run_id": run_id,
        "backup_before_run": backup_before_run,
        "teardown_after_run": teardown_after_run,
    }
    save_run_config(run_config, output_dir)

    print(f"Output directory: {output_dir}")
    print()

    wall_start = time.perf_counter()
    result = run_single_test(
        test_name, technique, overrides, output_dir,
        verbose=True,
        backup_before_run=backup_before_run,
        teardown_after_run=teardown_after_run,
        forced_backup_warning=forced_backup_warning,
    )
    wall_end = time.perf_counter()

    # Generate summary
    summary = result_to_summary(result, technique, overrides)
    save_test_summary(summary, result.log_dir)

    # Generate aggregate report (even for single test)
    aggregate = generate_aggregate_report(
        [summary], run_config, run_id, wall_clock_s=wall_end - wall_start
    )
    save_aggregate_report(aggregate, output_dir)
    print_console_summary(aggregate, output_dir)

    return 0 if result.success else 1


def cmd_run_many(args):
    """Handle --run-many command."""
    pattern = args.run_many
    matched = match_pattern(pattern)

    if not matched:
        print(f"No test cases match pattern: {pattern}")
        return 1

    if args.dry_run:
        print(f"Dry run - would execute {len(matched)} tests:")
        for tc in matched:
            print(f"  {tc}")
        return 0

    run_id = get_timestamp_id()
    output_dir = get_output_dir(run_id, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    overrides = build_overrides_from_args(args)
    technique = args.technique
    jobs = args.jobs
    backup_before_run = args.backup_before_run
    teardown_after_run = args.teardown_after_run
    forced_backup_warning = False

    # Enforce backup when teardown is enabled (prevent file loss)
    if teardown_after_run and not backup_before_run:
        backup_before_run = True
        forced_backup_warning = True
        print("[WARNING] --teardown-after-run requires backup; auto-enabling --backup-before-run")

    # Save run config
    run_config = {
        "pattern": pattern,
        "test_names": matched,
        "technique": technique,
        "overrides": overrides,
        "jobs": jobs,
        "run_id": run_id,
        "backup_before_run": backup_before_run,
        "teardown_after_run": teardown_after_run,
    }
    save_run_config(run_config, output_dir)

    print(f"Running {len(matched)} tests with {jobs} workers")
    print(f"Output directory: {output_dir}")
    print()

    wall_start = time.perf_counter()
    results = run_tests_parallel(
        matched, technique, overrides, output_dir, jobs,
        backup_before_run=backup_before_run,
        teardown_after_run=teardown_after_run,
        forced_backup_warning=forced_backup_warning,
    )
    wall_end = time.perf_counter()

    # Generate summaries
    summaries = []
    for result in results:
        summary = result_to_summary(result, technique, overrides)
        save_test_summary(summary, result.log_dir)
        summaries.append(summary)

    # Generate aggregate report
    aggregate = generate_aggregate_report(
        summaries, run_config, run_id, wall_clock_s=wall_end - wall_start
    )
    save_aggregate_report(aggregate, output_dir)
    print_console_summary(aggregate, output_dir)

    # Return non-zero if any test failed
    failed = sum(1 for r in results if not r.success)
    return 1 if failed > 0 else 0


def main():
    parser = argparse.ArgumentParser(
        description="KubeLLM Test Runner - orchestrate Kubernetes troubleshooting tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list                           List available test cases
  %(prog)s wrong_port                       Run single test
  %(prog)s --run-many "port_*" --jobs 4    Run matching tests in parallel
  %(prog)s wrong_port --debug-model gpt-4o Override debug agent model
        """,
    )

    # Positional argument for single test
    parser.add_argument(
        "test_case",
        nargs="?",
        help="Single test case name to run",
    )

    # List command
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available test cases",
    )

    # Multi-run
    parser.add_argument(
        "--run-many",
        metavar="PATTERN",
        help="Glob pattern or comma-separated test names. Use 'all' for all tests",
    )
    parser.add_argument(
        "--jobs", "-j",
        type=int,
        default=1,
        help="Number of parallel test workers (default: 1). "
             "WARNING: >1 may cause K8s resource conflicts between tests",
    )

    # Config overrides
    parser.add_argument(
        "--debug-model",
        dest="debug_model",
        help="Override debug-agent model",
    )
    parser.add_argument(
        "--api-model",
        dest="api_model",
        help="Override api-agent model",
    )
    parser.add_argument(
        "--verification-model",
        dest="verification_model",
        help="Override verification-agent model",
    )
    parser.add_argument(
        "--technique",
        choices=["allStepsAtOnce", "stepByStep", "singleAgent"],
        default="allStepsAtOnce",
        help="Execution technique (default: allStepsAtOnce)",
    )

    # Output control
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Custom output directory (default: .local/test_runs/<timestamp>)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be executed without running",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output",
    )

    # Backup/teardown hooks (opt-in)
    parser.add_argument(
        "--backup-before-run",
        action="store_true",
        help="Create backup of test files before running (opt-in)",
    )
    parser.add_argument(
        "--teardown-after-run",
        action="store_true",
        help="Run teardown after test completes (opt-in). Warnings emitted on failure.",
    )

    args = parser.parse_args()

    # Determine which command to run
    if args.list:
        return cmd_list(args)
    elif args.run_many:
        return cmd_run_many(args)
    elif args.test_case:
        # Validate test case exists
        available = list_test_cases()
        if args.test_case not in available:
            print(f"Unknown test case: {args.test_case}")
            print(f"Available: {', '.join(available)}")
            return 1
        return cmd_run_single(args, args.test_case)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
