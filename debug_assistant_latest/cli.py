#!/usr/bin/env python3
"""CLI argument parsing, command dispatch, and repeat-queue orchestration."""

import argparse
import json
import os
import queue
import sys
import time
from datetime import datetime
from multiprocessing import Process, Queue
from pathlib import Path
from typing import List, Optional, Tuple

# Bootstrap paths before other local imports
from debug_assistant_latest.executor import (
    REPO_ROOT,
    _best_effort_configure_console_streams,
    cmd_run_many,
    cmd_run_single,
    get_timestamp_id,
    _run_selected_preflight,
)
from rag_server_config import RAG_API_URL_ENV

from config_merge import apply_runner_llm_env_defaults, load_config_with_overrides
from ground_truth import (
    format_results as format_ground_truth_results,
    run_all_checks as run_ground_truth_checks,
    save_ground_truth_result,
    validate_ground_truth_config,
)
from test_discovery import get_config_path, get_test_info, list_test_cases, match_pattern

from debug_assistant_latest.compare_runs import cmd_compare
from debug_assistant_latest.diagnostics import (
    cmd_dashboard,
    cmd_diagnose,
    cmd_diagnose_last,
    cmd_latest_run,
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


def cmd_preflight(args):
    test_names = None
    if args.run_many:
        test_names = match_pattern(args.run_many)
        if not test_names:
            print(f"No test cases match pattern: {args.run_many}")
            return 1
    elif args.test_case:
        available = list_test_cases()
        if args.test_case not in available:
            print(f"Unknown test case: {args.test_case}")
            print(f"Available: {', '.join(available)}")
            return 1
        test_names = [args.test_case]

    return _run_selected_preflight(args, test_names)


def cmd_validate_ground_truth(args):
    """Handle --validate-ground-truth command."""
    test_cases = list_test_cases()
    errors_found = False

    print(f"Validating ground truth configs for {len(test_cases)} test cases...\n")

    for tc in test_cases:
        config_path = get_config_path(tc)
        try:
            config = load_config_with_overrides(config_path, {})
            gt_errors = validate_ground_truth_config(config)

            if gt_errors:
                print(f"[INVALID] {tc}:")
                for err in gt_errors:
                    print(f"          {err}")
                errors_found = True
            elif config.get("ground-truth"):
                checks = config["ground-truth"].get("checks", [])
                print(f"[OK]      {tc} ({len(checks)} checks)")
            else:
                print(f"[NONE]    {tc} (no ground-truth configured)")
        except Exception as e:
            print(f"[ERROR]   {tc}: {e}")
            errors_found = True

    print()
    if errors_found:
        print("Validation FAILED - fix errors above")
        return 1
    else:
        print("Validation PASSED")
        return 0


def cmd_verify_only(args, test_name: str):
    """Handle --verify-only command - run ground truth checks without agents."""
    config_path = get_config_path(test_name)
    config = load_config_with_overrides(config_path, {})

    if not config.get("ground-truth"):
        print(f"No ground-truth configured for {test_name}")
        return 1

    print(f"Running ground truth verification for {test_name}...")

    gt_result = run_ground_truth_checks(config)
    if gt_result:
        print(format_ground_truth_results(gt_result))

        # Save results if output-dir specified
        if args.output_dir:
            output_dir = args.output_dir / test_name
            save_ground_truth_result(gt_result, output_dir)
            print(f"Results saved to: {output_dir}/ground_truth.json")

        return 0 if gt_result.passed else 1
    else:
        print("Ground truth verification failed to run")
        return 1


def _apply_repeat_overrides(args):
    """
    When --repeat N (N>1) is set, enforce serial execution with teardown.

    Mutates args in place and prints warnings about overridden flags.
    Returns True if repeat mode is active.
    """
    if args.repeat < 1:
        print("[ERROR] --repeat must be >= 1")
        sys.exit(1)

    if args.repeat == 1:
        return False

    if args.jobs != 1:
        print(f"[WARNING] --repeat forces --jobs 1 (was {args.jobs})")
        args.jobs = 1

    if not args.teardown_after_run:
        print("[WARNING] --repeat forces --teardown-after-run")
        args.teardown_after_run = True

    if not args.backup_before_run:
        print("[WARNING] --repeat forces --backup-before-run (required by teardown)")
        args.backup_before_run = True

    return True


def _repeat_iteration_worker(result_queue, payload):
    """
    Spawn-safe worker for a single repeat iteration.

    Receives a plain-dict *payload* (fully picklable) and reconstructs a
    fresh argparse.Namespace per iteration so there are no shared-state
    side-effects.  The payload always contains a base_output_dir so
    iter_dir is deterministic (no filesystem-mtime heuristics).

    Puts ("ok", exit_code, output_dir_str) or ("error", msg, output_dir_str)
    onto *result_queue*.
    """
    mode = payload["mode"]
    iteration = payload["iteration"]
    base_run_id = payload["base_run_id"]
    base_output_dir = payload["base_output_dir"]  # always set in repeat mode
    args_dict = payload["args"]

    # Build a fresh Namespace from the serialised args
    iter_args = argparse.Namespace(**args_dict)
    # Tests (and minimal callers) may omit parser-derived fields; mirror CLI defaults.
    _repeat_iter_defaults = {
        "technique": "allStepsAtOnce",
        "debug_model": None,
        "api_model": None,
        "verification_model": None,
        "embedder": None,
        "embedder_provider": None,
        "minikube_profile": None,
        "rag_api_url": None,
        "skip_preflight": False,
        "backup_before_run": True,
        "teardown_after_run": True,
        "jobs": 1,
        "dry_run": False,
        "verbose": False,
        "repeat": 1,
        "stall_limit_s": 900,
    }
    for _key, _val in _repeat_iter_defaults.items():
        if not hasattr(iter_args, _key):
            setattr(iter_args, _key, _val)

    # Per-iteration output dir nested under the queue directory
    queue_dir = Path(base_output_dir) / base_run_id
    iter_dir = queue_dir / f"iter-{iteration:03d}"
    iter_args.output_dir = iter_dir
    output_dir_str = str(iter_dir)

    try:
        if mode == "single":
            exit_code = cmd_run_single(iter_args, payload["test_case"])
        else:
            exit_code = cmd_run_many(iter_args)
        result_queue.put(("ok", exit_code, output_dir_str))
    except Exception as exc:
        result_queue.put(("error", str(exc), output_dir_str))


def _build_repeat_payload(args, mode, iteration, base_run_id, base_output_dir):
    """
    Build a picklable payload dict for _repeat_iteration_worker.

    Converts args to a plain dict, replacing Path values with strings
    so the payload survives pickle (spawn start-method).
    """
    args_dict = {}
    for k, v in vars(args).items():
        args_dict[k] = v.as_posix() if isinstance(v, Path) else v
    # output_dir will be overridden by the worker; set to None to be explicit
    args_dict["output_dir"] = None

    payload = {
        "mode": mode,
        "iteration": iteration,
        "base_run_id": base_run_id,
        "base_output_dir": base_output_dir.as_posix() if isinstance(base_output_dir, Path) else str(base_output_dir),
        "args": args_dict,
    }
    if mode == "single":
        payload["test_case"] = args.test_case
    return payload


def _run_repeat_queue(args, mode, base_run_id, base_output_dir):
    """
    Run iterations serially with a hard-kill stall watchdog.

    Each iteration runs in a child process (multiprocessing.Process) using
    the spawn-safe _repeat_iteration_worker.  If an iteration exceeds
    --stall-limit-s the process is terminated (SIGTERM), given 5 s to
    clean up, then killed (SIGKILL).  The queue stops on stall.

    Writes queue_summary.json and prints a queue summary at the end.
    Returns a non-zero exit code if any iteration failed or stalled.
    """
    total = args.repeat
    stall_limit = args.stall_limit_s
    # (iteration, exit_code | None, duration_s, output_dir_str)
    results: List[Tuple[int, Optional[int], float, str]] = []

    print(f"[REPEAT] Queue: {total} iteration(s), stall limit {stall_limit}s")
    print()

    queue_started_at = datetime.now().isoformat()
    queue_start = time.perf_counter()

    for i in range(1, total + 1):
        iter_start = time.perf_counter()
        print(f"{'=' * 60}")
        print(f"[REPEAT] Iteration {i}/{total}")
        print(f"{'=' * 60}")

        payload = _build_repeat_payload(args, mode, i, base_run_id, base_output_dir)
        result_q = Queue()
        proc = Process(
            target=_repeat_iteration_worker,
            args=(result_q, payload),
        )
        proc.start()

        # Wait for the process with stall timeout
        proc.join(timeout=stall_limit)
        iter_duration = time.perf_counter() - iter_start

        if proc.is_alive():
            # Stall detected — hard-kill the iteration
            print()
            print(f"[STALL] Iteration {i} exceeded stall limit of {stall_limit}s — terminating process.")
            proc.terminate()
            proc.join(timeout=5)
            if proc.is_alive():
                print("[STALL] Process did not exit after SIGTERM, sending SIGKILL.")
                proc.kill()
                proc.join(timeout=2)
                if proc.is_alive():
                    print(f"[WARNING] Process {proc.pid} still alive after SIGKILL — may need manual cleanup.")

            # Cleanup queue resources
            result_q.close()
            result_q.cancel_join_thread()

            # Output dir for this iteration (always deterministic)
            iter_out = str(Path(base_output_dir) / base_run_id / f"iter-{i:03d}")

            results.append((i, None, iter_duration, iter_out))
            print("[STALL] Aborting queue — no further iterations will run.")
            break

        # Process finished — collect result from queue (retry up to 5 times)
        exit_code = 1
        output_dir_str = ""
        got_result = False
        for _attempt in range(5):
            try:
                status_type, ec_or_msg, out_dir = result_q.get(timeout=1.0)
                output_dir_str = out_dir
                if status_type == "ok":
                    exit_code = ec_or_msg if ec_or_msg is not None else 1
                else:
                    print(f"[ERROR] Iteration {i} raised: {ec_or_msg}")
                    exit_code = 1
                got_result = True
                break
            except queue.Empty:
                continue
        if not got_result:
            print(f"[ERROR] Iteration {i}: worker finished but produced no result")
            exit_code = 1

        # Cleanup queue resources
        proc.join(timeout=1)
        result_q.close()
        result_q.cancel_join_thread()

        results.append((i, exit_code, iter_duration, output_dir_str))
        print()

    # Queue summary (console)
    queue_duration = time.perf_counter() - queue_start
    queue_finished_at = datetime.now().isoformat()
    print()
    print(f"{'=' * 60}")
    print(f"[REPEAT] Queue summary ({len(results)}/{total} iterations)")
    print(f"{'=' * 60}")
    passed = sum(1 for _, ec, _, _ in results if ec == 0)
    failed = sum(1 for _, ec, _, _ in results if ec is not None and ec != 0)
    stalled = sum(1 for _, ec, _, _ in results if ec is None)
    for iteration, ec, dur, _ in results:
        tag = "PASS" if ec == 0 else ("STALL" if ec is None else "FAIL")
        print(f"  Iteration {iteration}: {tag} ({dur:.1f}s)")
    print()
    print(f"  Passed: {passed}  Failed: {failed}  Stalled: {stalled}")
    print(f"  Total wall clock: {queue_duration:.1f}s")

    # Write queue_summary.json
    summary_obj = {
        "queue_id": base_run_id,
        "total_iterations": total,
        "completed_iterations": len(results),
        "stall_limit_s": stall_limit,
        "started_at": queue_started_at,
        "finished_at": queue_finished_at,
        "results": [],
    }
    for iteration, ec, dur, out_dir in results:
        tag = "PASS" if ec == 0 else ("STALL" if ec is None else "FAIL")
        summary_obj["results"].append(
            {
                "iteration": iteration,
                "status": tag,
                "duration_s": round(dur, 2),
                "output_dir": out_dir,
            }
        )

    # Write summary in the queue-scoped directory alongside iteration dirs
    summary_dir = Path(base_output_dir) / base_run_id
    summary_dir.mkdir(parents=True, exist_ok=True)
    summary_path = summary_dir / "queue_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary_obj, f, indent=2)
    print(f"\n  Queue summary written to: {summary_path}")

    # Return non-zero if any iteration failed/stalled
    if failed > 0 or stalled > 0:
        return 1
    return 0


def main():
    _best_effort_configure_console_streams()

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
        "--list",
        "-l",
        action="store_true",
        help="List available test cases",
    )
    parser.add_argument(
        "--latest-run",
        action="store_true",
        help="Print the most recent run directory and exit",
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Run structured preflight checks and exit",
    )
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        help="Skip automatic preflight checks before executing tests",
    )
    parser.add_argument(
        "--diagnose",
        type=Path,
        metavar="RUN_DIR",
        help="Diagnose a specific run directory",
    )
    parser.add_argument(
        "--diagnose-last",
        action="store_true",
        help="Diagnose the most recent diagnosable run directory",
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Show a simple dashboard over historical run data",
    )
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("RUN1", "RUN2"),
        help="Compare two run directories: full paths or run IDs under .local/test_runs/",
    )

    # Multi-run
    parser.add_argument(
        "--run-many",
        metavar="PATTERN",
        help="Glob pattern or comma-separated test names. Use 'all' for all tests",
    )
    parser.add_argument(
        "--jobs",
        "-j",
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
        "--embedder",
        dest="embedder",
        help="Override api-agent embedder model",
    )
    parser.add_argument(
        "--embedder-provider",
        dest="embedder_provider",
        choices=["openai", "ollama"],
        help="Override api-agent embedder provider",
    )
    parser.add_argument(
        "--technique",
        choices=["allStepsAtOnce", "stepByStep", "singleAgent"],
        default="allStepsAtOnce",
        help="Execution technique (default: allStepsAtOnce)",
    )
    parser.add_argument(
        "--minikube-profile",
        dest="minikube_profile",
        default=None,
        help="Override minikube profile name. Only applied when explicitly set.",
    )
    parser.add_argument(
        "--rag-api-url",
        dest="rag_api_url",
        default=None,
        help=(
            "Override the RAG API base URL for this run. "
            "Precedence: --rag-api-url > RAG_API_URL env/.env > http://127.0.0.1:RAG_SERVER_PORT"
        ),
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
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )

    # Backup/teardown hooks (on by default for benchmark integrity)
    parser.add_argument(
        "--backup-before-run",
        action="store_true",
        default=True,
        help="Create backup of test files before running (default: on)",
    )
    parser.add_argument(
        "--no-backup-before-run",
        dest="backup_before_run",
        action="store_false",
        help="Disable backup of test files before running",
    )
    parser.add_argument(
        "--teardown-after-run",
        action="store_true",
        default=True,
        help="Run teardown after test completes (default: on). Runs after ground truth.",
    )
    parser.add_argument(
        "--no-teardown",
        dest="teardown_after_run",
        action="store_false",
        help="Disable teardown after test completes",
    )

    # Ground truth verification
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Run only ground truth verification (no agent execution)",
    )
    parser.add_argument(
        "--validate-ground-truth",
        action="store_true",
        help="Validate ground truth configs without executing (schema check only)",
    )

    # Serial repeat queue
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        metavar="N",
        help="Run the test(s) N times serially. Forces --teardown-after-run and --jobs 1.",
    )
    parser.add_argument(
        "--stall-limit-s",
        type=int,
        default=900,
        metavar="SECONDS",
        help="Abort repeat queue if no run completes within this many seconds (default: 900).",
    )

    args = parser.parse_args()
    if args.rag_api_url:
        os.environ[RAG_API_URL_ENV] = args.rag_api_url

    applied_llm = apply_runner_llm_env_defaults(args)
    if applied_llm and (args.test_case or args.run_many):
        print("[INFO] LLM defaults from environment:", "; ".join(applied_llm))

    # Determine which command to run
    if args.list:
        return cmd_list(args)

    if args.latest_run:
        return cmd_latest_run(args)

    if args.preflight:
        return cmd_preflight(args)

    if args.validate_ground_truth:
        return cmd_validate_ground_truth(args)

    if args.diagnose:
        return cmd_diagnose(args, args.diagnose)

    if args.diagnose_last:
        return cmd_diagnose_last(args)

    if args.dashboard:
        return cmd_dashboard(args)

    if args.compare:
        return cmd_compare(args)

    if args.verify_only:
        if not args.test_case:
            print("Error: --verify-only requires a test case name")
            return 1
        available = list_test_cases()
        if args.test_case not in available:
            print(f"Unknown test case: {args.test_case}")
            print(f"Available: {', '.join(available)}")
            return 1
        return cmd_verify_only(args, args.test_case)

    # Apply repeat overrides before dispatching
    repeat_active = _apply_repeat_overrides(args)

    if args.run_many:
        if repeat_active:
            if args.dry_run:
                matched = match_pattern(args.run_many)
                if not matched:
                    print(f"No test cases match pattern: {args.run_many}")
                    return 1
                print(f"Dry run - would execute {len(matched)} tests x {args.repeat} iterations:")
                for tc in matched:
                    print(f"  {tc}")
                print(f"\nRepeat: {args.repeat} iterations, stall limit: {args.stall_limit_s}s")
                return 0

            base_run_id = get_timestamp_id()
            # Always provide a base_output_dir so iter dirs are deterministic
            base_output_dir = args.output_dir if args.output_dir else REPO_ROOT / ".local" / "test_runs"
            return _run_repeat_queue(args, "many", base_run_id, base_output_dir)
        return cmd_run_many(args)
    elif args.test_case:
        # Validate test case exists
        available = list_test_cases()
        if args.test_case not in available:
            print(f"Unknown test case: {args.test_case}")
            print(f"Available: {', '.join(available)}")
            return 1
        if repeat_active:
            if args.dry_run:
                print(f"Dry run - would execute: {args.test_case} x {args.repeat} iterations")
                print(f"\nRepeat: {args.repeat} iterations, stall limit: {args.stall_limit_s}s")
                return 0

            base_run_id = get_timestamp_id()
            # Always provide a base_output_dir so iter dirs are deterministic
            base_output_dir = args.output_dir if args.output_dir else REPO_ROOT / ".local" / "test_runs"
            return _run_repeat_queue(args, "single", base_run_id, base_output_dir)
        return cmd_run_single(args, args.test_case)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
