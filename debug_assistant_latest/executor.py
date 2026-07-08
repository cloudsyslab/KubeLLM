#!/usr/bin/env python3
"""Single-test execution, TestResult, ground-truth hooks, and run orchestration."""

import shutil
import sys
import time
import traceback
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Script directory - all paths relative to this
SCRIPT_DIR = Path(__file__).parent.absolute()
REPO_ROOT = SCRIPT_DIR.parent

# Ensure REPO_ROOT and SCRIPT_DIR are in sys.path
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from test_discovery import get_config_path, get_test_info, list_test_cases, match_pattern
from config_merge import (
    build_overrides_from_args,
    load_config_with_overrides,
    save_effective_config,
)
from provenance import build_environment_context, collect_run_provenance
from report import (
    TestSummary,
    generate_aggregate_report,
    normalize_metrics_map,
    print_console_summary,
    save_aggregate_report,
    save_provenance,
    save_run_config,
    save_test_summary,
)
from ground_truth import (
    format_results as format_ground_truth_results,
    run_all_checks as run_ground_truth_checks,
    save_ground_truth_result,
)
from preflight import print_preflight_result, run_preflight
from rag_server_config import resolve_client_base_url
from runtime_progress import ProgressWriter


@dataclass
class TestResult:
    """Result of a single test execution."""

    test_name: str
    success: bool
    verified: Optional[bool]
    debug_self_report: Optional[bool]
    duration_s: float
    error: Optional[str]
    metrics: Dict[str, Any]
    log_dir: Path
    started_at: str
    finished_at: str
    ground_truth_passed: Optional[bool] = None  # None if GT did not run
    ground_truth_configured: bool = False
    environment_context: Optional[Dict[str, Any]] = None


def get_timestamp_id() -> str:
    """Generate a filesystem-safe timestamp ID for a run."""
    return datetime.now().strftime("%Y-%m-%dT%H-%M-%S")


def get_output_dir(run_id: str, base_dir: Optional[Path] = None) -> Path:
    """Get the output directory for a test run."""
    if base_dir:
        return base_dir
    return REPO_ROOT / ".local" / "test_runs" / run_id


def prune_old_test_runs(retain_n: int, current_run_dir: Optional[Path] = None) -> None:
    """Remove oldest directories under ``.local/test_runs``, keeping *retain_n* newest by mtime.

    Never deletes *current_run_dir* if it would fall in the removal set (fail-safe).
    """
    if retain_n <= 0:
        return
    base = REPO_ROOT / ".local" / "test_runs"
    if not base.is_dir():
        return
    children = [p for p in base.iterdir() if p.is_dir()]
    children.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    if len(children) <= retain_n:
        return
    victims = children[retain_n:]
    cur = current_run_dir.resolve() if current_run_dir else None
    for path in victims:
        if cur is not None and path.resolve() == cur:
            continue
        try:
            shutil.rmtree(path, ignore_errors=True)
        except OSError:
            pass


def resolve_rag_api_url_for_args(args) -> str:
    return resolve_client_base_url(getattr(args, "rag_api_url", None))


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def _best_effort_configure_console_streams() -> None:
    """Force UTF-8 console encoding when the active stream supports it."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


def _safe_write_to_stream(stream, data) -> None:
    """Best-effort stream write that never lets console encoding abort the run."""
    text = data if isinstance(data, str) else str(data)
    encoding = getattr(stream, "encoding", None) or "utf-8"
    try:
        safe_text = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
    except (LookupError, ValueError):
        safe_text = text.encode("utf-8", errors="replace").decode("utf-8", errors="replace")

    try:
        stream.write(safe_text)
    except (OSError, UnicodeError, ValueError):
        try:
            stream.write(safe_text.encode("ascii", errors="replace").decode("ascii"))
        except (OSError, UnicodeError, ValueError):
            return


def _safe_flush_stream(stream) -> None:
    try:
        stream.flush()
    except (OSError, ValueError):
        pass


def _has_ground_truth_config(test_name: str, overrides: dict) -> bool:
    """Best-effort check for whether a test case has deterministic GT configured."""
    try:
        config_path = get_config_path(test_name)
        config = load_config_with_overrides(config_path, overrides)
    except Exception:
        return False
    return bool(config.get("ground-truth"))


def _extract_execution_result(
    result: Any,
) -> tuple[bool, Optional[bool], Optional[bool], Dict[str, Any], Optional[str]]:
    if isinstance(result, dict):
        success = result.get("status") is True
        metrics: Dict[str, Any] = {}
        debug_metrics = result.get("debug_metrics")
        verification_metrics = result.get("verification_metrics")

        debug_self_report = None
        if isinstance(debug_metrics, dict):
            metrics["debug"] = debug_metrics
            task_status = debug_metrics.get("task_status")
            if task_status == 1:
                debug_self_report = True
            elif task_status == 0:
                debug_self_report = False

        if isinstance(verification_metrics, dict):
            metrics["verification"] = verification_metrics
            vstatus = result.get("status")
            if vstatus is True:
                verified = True
            elif vstatus is False:
                verified = False
            else:
                verified = None
        else:
            verified = None

        derived_error = None
        if not success and isinstance(debug_metrics, dict) and debug_metrics.get("task_status") == -1:
            derived_error = "Timeout: agent execution exceeded 480s"

        return success, verified, debug_self_report, metrics, derived_error

    success = result is True
    return success, success, None, {}, None


def _result_status(result: TestResult) -> str:
    error_text = (result.error or "").lower()
    if "timeout" in error_text:
        return "TIMEOUT"

    debug_metrics = result.metrics.get("debug") if isinstance(result.metrics, dict) else None
    if isinstance(debug_metrics, dict) and debug_metrics.get("task_status") == -1:
        return "TIMEOUT"

    return "PASS" if result.success else ("ERROR" if result.error else "FAIL")


def _read_error_context(log_dir: Path, line_limit: int = 20) -> Optional[str]:
    stderr_log = log_dir / "stderr.log"
    if not stderr_log.exists():
        return None

    lines = stderr_log.read_text(encoding="utf-8", errors="replace").splitlines()
    excerpt = "\n".join(lines[:line_limit]).strip()
    return excerpt or None


def _run_selected_preflight(args, test_names: Optional[List[str]]) -> int:
    result = run_preflight(
        test_names=test_names,
        overrides=build_overrides_from_args(args),
        rag_api_url=resolve_rag_api_url_for_args(args),
        minikube_profile=getattr(args, "minikube_profile", None),
    )
    print_preflight_result(result)
    return 0 if result["passed"] else 1


def _maybe_run_preflight(args, test_names: List[str]) -> int:
    if getattr(args, "skip_preflight", False):
        return 0

    exit_code = _run_selected_preflight(args, test_names)
    if exit_code != 0:
        print("[ERROR] Preflight failed. Re-run with --skip-preflight only if you understand the risk.")
    return exit_code


def _run_preflight_result(args, test_names: List[str]) -> Optional[dict]:
    if getattr(args, "skip_preflight", False):
        return None
    result = run_preflight(
        test_names=test_names,
        overrides=build_overrides_from_args(args),
        rag_api_url=resolve_rag_api_url_for_args(args),
        minikube_profile=getattr(args, "minikube_profile", None),
    )
    print_preflight_result(result)
    return result


def _summarize_preflight_failure(result: dict) -> str:
    failures = [check for check in result.get("checks", []) if not check.get("passed")]
    if not failures:
        return "Preflight failed"
    return "Preflight failed: " + "; ".join(
        f"{check.get('name')}: {check.get('message')}" for check in failures
    )


def _write_text_log(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _build_failed_result(
    test_name: str,
    log_dir: Path,
    error_message: str,
    overrides: Optional[dict] = None,
    environment_context: Optional[Dict[str, Any]] = None,
) -> TestResult:
    now = datetime.now().isoformat()
    return TestResult(
        test_name=test_name,
        success=False,
        verified=None,
        debug_self_report=None,
        duration_s=0.0,
        error=error_message,
        metrics={},
        log_dir=log_dir,
        started_at=now,
        finished_at=now,
        ground_truth_passed=None,
        ground_truth_configured=_has_ground_truth_config(test_name, overrides or {}),
        environment_context=environment_context,
    )


def _print_run_footer(output_dir: Path, summaries: List[TestSummary]) -> None:
    print(f"RUN_DIR: {_display_path(output_dir)}")
    for summary in sorted(summaries, key=lambda item: item.test_name):
        print(f"RESULT: {summary.test_name} {summary.status} {summary.duration_s:.2f}s")


def run_single_test_in_process(
    test_name: str,
    technique: str,
    overrides: dict,
    output_dir: Path,
    backup_before_run: bool = False,
    teardown_after_run: bool = False,
    forced_backup_warning: bool = False,
    run_uuid: str = "",
    run_id: str = "",
    environment_context: Optional[Dict[str, Any]] = None,
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
        with open(stderr_log, "a", encoding="utf-8") as f:
            f.write("[WARNING] --teardown-after-run requires backup; auto-enabling --backup-before-run\n")

    started_at = datetime.now().isoformat()
    start_time = time.perf_counter()

    success = False
    verified = None
    debug_self_report = None
    error = None
    metrics = {}
    test_started = False  # Guard: only teardown if test actually started
    ground_truth_passed = None
    ground_truth_configured = False

    try:
        # Import here to avoid circular imports in worker process
        from main import allStepsAtOnce, singleAgentApproach, stepByStep
        from config_merge import load_config_with_overrides, save_effective_config
        from teardown import (
            backup_environment,
            cleanup_test_pods,
            cleanup_transient_fixture_files,
            cleanup_transient_k8s_resources,
            teardown_environment,
        )

        config_path = get_config_path(test_name)
        config = load_config_with_overrides(config_path, overrides)
        ground_truth_configured = bool(config.get("ground-truth"))

        cleanup_transient_k8s_resources()

        # Opt-in backup before run (fail fast if backup fails)
        if backup_before_run:
            try:
                backup_environment(test_name)
            except Exception as backup_err:
                error = f"Backup failed: {backup_err}"
                with open(stderr_log, "a", encoding="utf-8") as f:
                    f.write(f"BACKUP FAILED:\n{traceback.format_exc()}")
                raise  # Abort test - don't proceed without backup

        # Save effective config for audit trail
        save_effective_config(config, log_dir / "config_effective.json")

        # Mark test as started (backup succeeded, about to run test)
        test_started = True

        from provenance import build_environment_context

        worker_runtime = {
            "log_dir": str(log_dir),
            "blocked_threshold": 3,
            "environment_context": environment_context
            if environment_context is not None
            else build_environment_context(),
        }
        if run_uuid:
            worker_runtime["run_uuid"] = run_uuid
        if run_id:
            worker_runtime["run_id"] = run_id

        # Capture stdout/stderr
        with open(stdout_log, "w", encoding="utf-8") as stdout_f, open(stderr_log, "w", encoding="utf-8") as stderr_f:
            # Redirect stdout/stderr
            old_stdout, old_stderr = sys.stdout, sys.stderr
            sys.stdout = stdout_f
            sys.stderr = stderr_f

            try:
                if technique == "allStepsAtOnce":
                    result = allStepsAtOnce(
                        configFile=str(config_path),
                        config_overrides=overrides,
                        runtime_context=worker_runtime,
                    )
                    success, verified, debug_self_report, metrics, derived_error = _extract_execution_result(result)
                    if error is None and derived_error:
                        error = derived_error
                elif technique == "stepByStep":
                    result = stepByStep(
                        configFile=str(config_path),
                        config_overrides=overrides,
                        runtime_context=worker_runtime,
                    )
                    success, verified, debug_self_report, metrics, derived_error = _extract_execution_result(result)
                    if error is None and derived_error:
                        error = derived_error
                elif technique == "singleAgent":
                    result = singleAgentApproach(
                        configFile=str(config_path),
                        config_overrides=overrides,
                        runtime_context=worker_runtime,
                    )
                    success, verified, debug_self_report, metrics, derived_error = _extract_execution_result(result)
                    if error is None and derived_error:
                        error = derived_error
                else:
                    raise ValueError(f"Unknown technique: {technique}")

                # Run ground truth verification if configured
                if ground_truth_configured:
                    print("\n" + "=" * 60)
                    print("Running ground truth verification...")
                    cleanup_transient_k8s_resources()
                    gt_result = run_ground_truth_checks(config)
                    if gt_result:
                        print(format_ground_truth_results(gt_result))
                        save_ground_truth_result(gt_result, log_dir)
                        ground_truth_passed = gt_result.passed
                        # GT failure overrides LLM success (deterministic > heuristic)
                        if not gt_result.passed:
                            success = False

            finally:
                sys.stdout, sys.stderr = old_stdout, old_stderr

    except Exception as e:
        if error is None:  # Don't overwrite backup error
            error = str(e)
        with open(stderr_log, "a", encoding="utf-8") as f:
            f.write(f"\n\nEXCEPTION:\n{traceback.format_exc()}")

    # Opt-in teardown after run (only if test started; log warnings to stderr.log)
    if teardown_after_run and test_started:
        try:
            teardown_environment(test_name)
        except Exception as teardown_err:
            # Route warning to per-test stderr.log
            with open(stderr_log, "a", encoding="utf-8") as f:
                f.write(f"\n\n[WARNING] Teardown failed for {test_name}: {teardown_err}\n")
                f.write(traceback.format_exc())

    if test_started:
        try:
            cleanup_test_pods()
        except Exception as pod_cleanup_err:
            with open(stderr_log, "a", encoding="utf-8") as f:
                f.write(f"\n\n[WARNING] Post-test pod cleanup failed for {test_name}: {pod_cleanup_err}\n")
                f.write(traceback.format_exc())

    if test_started:
        try:
            removed_fixture_files = cleanup_transient_fixture_files(test_name)
            if removed_fixture_files:
                with open(stderr_log, "a", encoding="utf-8") as f:
                    f.write("\n\n[CLEANUP] Removed transient fixture files:\n")
                    for path in removed_fixture_files:
                        f.write(f"  {path}\n")
        except Exception as cleanup_err:
            with open(stderr_log, "a", encoding="utf-8") as f:
                f.write(f"\n\n[WARNING] Transient fixture cleanup failed for {test_name}: {cleanup_err}\n")
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
        ground_truth_passed=ground_truth_passed,
        ground_truth_configured=ground_truth_configured,
        environment_context=environment_context,
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
    runtime_context: Optional[Dict[str, Any]] = None,
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
        with open(stderr_log, "a", encoding="utf-8") as f:
            f.write("[WARNING] --teardown-after-run requires backup; auto-enabling --backup-before-run\n")

    started_at = datetime.now().isoformat()
    start_time = time.perf_counter()

    success = False
    verified = None
    debug_self_report = None
    error = None
    metrics = {}
    test_started = False  # Guard: only teardown if test actually started
    ground_truth_passed = None
    ground_truth_configured = False
    runtime_context = dict(runtime_context or {})
    runtime_context.setdefault("blocked_threshold", 3)
    runtime_context["log_dir"] = str(log_dir)
    progress_writer = runtime_context.get("progress_writer")

    _best_effort_configure_console_streams()

    if verbose:
        print(f"[RUNNING] {test_name} ({technique})")
    if progress_writer:
        progress_writer.write_event(
            "test_start",
            test_name=test_name,
            technique=technique,
            output_dir=str(output_dir),
        )

    try:
        from main import allStepsAtOnce, singleAgentApproach, stepByStep
        from teardown import (
            backup_environment,
            cleanup_test_pods,
            cleanup_transient_fixture_files,
            cleanup_transient_k8s_resources,
            teardown_environment,
        )

        config_path = get_config_path(test_name)
        config = load_config_with_overrides(config_path, overrides)
        ground_truth_configured = bool(config.get("ground-truth"))

        cleanup_transient_k8s_resources()

        # Opt-in backup before run (fail fast if backup fails)
        if backup_before_run:
            if verbose:
                print(f"[BACKUP] Creating backup for {test_name}")
            try:
                backup_environment(test_name)
            except Exception as backup_err:
                error = f"Backup failed: {backup_err}"
                if verbose:
                    print(f"[ERROR] Backup failed for {test_name}: {backup_err}")
                with open(stderr_log, "a", encoding="utf-8") as f:
                    f.write(f"BACKUP FAILED:\n{traceback.format_exc()}")
                raise  # Abort test - don't proceed without backup

        # Save effective config for audit trail
        save_effective_config(config, log_dir / "config_effective.json")
        if progress_writer:
            progress_writer.write_event(
                "config_effective_saved",
                test_name=test_name,
                path=str(log_dir / "config_effective.json"),
            )

        # Mark test as started (backup succeeded, about to run test)
        test_started = True

        # For single test, we tee output to both console and file
        # Open log files for writing
        with open(stdout_log, "w", encoding="utf-8") as stdout_f, open(stderr_log, "w", encoding="utf-8") as stderr_f:
            # Create tee writers
            class TeeWriter:
                def __init__(self, *streams):
                    self.streams = streams

                @property
                def encoding(self):
                    if not self.streams:
                        return "utf-8"
                    return getattr(self.streams[0], "encoding", None) or "utf-8"

                def isatty(self):
                    if not self.streams:
                        return False
                    isatty = getattr(self.streams[0], "isatty", None)
                    return bool(callable(isatty) and isatty())

                def write(self, data):
                    for s in self.streams:
                        _safe_write_to_stream(s, data)
                        _safe_flush_stream(s)

                def flush(self):
                    for s in self.streams:
                        _safe_flush_stream(s)

            old_stdout, old_stderr = sys.stdout, sys.stderr
            if verbose:
                sys.stdout = TeeWriter(old_stdout, stdout_f)
                sys.stderr = TeeWriter(old_stderr, stderr_f)
            else:
                sys.stdout = stdout_f
                sys.stderr = stderr_f

            try:
                if technique == "allStepsAtOnce":
                    result = allStepsAtOnce(
                        configFile=str(config_path),
                        config_overrides=overrides,
                        runtime_context=runtime_context,
                    )
                    success, verified, debug_self_report, metrics, derived_error = _extract_execution_result(result)
                    if error is None and derived_error:
                        error = derived_error
                elif technique == "stepByStep":
                    result = stepByStep(
                        configFile=str(config_path),
                        config_overrides=overrides,
                        runtime_context=runtime_context,
                    )
                    success, verified, debug_self_report, metrics, derived_error = _extract_execution_result(result)
                    if error is None and derived_error:
                        error = derived_error
                elif technique == "singleAgent":
                    result = singleAgentApproach(
                        configFile=str(config_path),
                        config_overrides=overrides,
                        runtime_context=runtime_context,
                    )
                    success, verified, debug_self_report, metrics, derived_error = _extract_execution_result(result)
                    if error is None and derived_error:
                        error = derived_error
                else:
                    raise ValueError(f"Unknown technique: {technique}")

                # Run ground truth verification if configured
                if ground_truth_configured:
                    if progress_writer:
                        progress_writer.write_event("ground_truth_start", test_name=test_name)
                    print("\n" + "=" * 60)
                    print("Running ground truth verification...")
                    cleanup_transient_k8s_resources()
                    gt_result = run_ground_truth_checks(config)
                    if gt_result:
                        print(format_ground_truth_results(gt_result))
                        save_ground_truth_result(gt_result, log_dir)
                        ground_truth_passed = gt_result.passed
                        if not gt_result.passed:
                            success = False
                        if progress_writer:
                            progress_writer.write_event(
                                "ground_truth_end",
                                test_name=test_name,
                                passed=gt_result.passed,
                                summary=gt_result.summary,
                            )
                    elif progress_writer:
                        progress_writer.write_event("ground_truth_end", test_name=test_name, passed=None)

            finally:
                sys.stdout, sys.stderr = old_stdout, old_stderr

    except Exception as e:
        if error is None:  # Don't overwrite backup error
            error = str(e)
        if verbose:
            print(f"[ERROR] {test_name}: {error}")
        with open(stderr_log, "a", encoding="utf-8") as f:
            f.write(f"\n\nEXCEPTION:\n{traceback.format_exc()}")
        if progress_writer:
            progress_writer.write_event("test_error", test_name=test_name, error=error)

    # Opt-in teardown after run (only if test started; log warnings to stderr.log)
    if teardown_after_run and test_started:
        try:
            if verbose:
                print(f"[TEARDOWN] Running teardown for {test_name}")
            teardown_environment(test_name)
        except Exception as teardown_err:
            warning_msg = f"[WARNING] Teardown failed for {test_name}: {teardown_err}"
            if verbose:
                print(warning_msg, file=sys.stderr)
            # Also log to per-test stderr.log
            with open(stderr_log, "a", encoding="utf-8") as f:
                f.write(f"\n\n{warning_msg}\n")
                f.write(traceback.format_exc())

    if test_started:
        try:
            if verbose:
                print(f"[CLEANUP] Deleting remaining test pods")
            cleanup_test_pods()
        except Exception as pod_cleanup_err:
            warning_msg = f"[WARNING] Post-test pod cleanup failed for {test_name}: {pod_cleanup_err}"
            if verbose:
                print(warning_msg, file=sys.stderr)
            with open(stderr_log, "a", encoding="utf-8") as f:
                f.write(f"\n\n{warning_msg}\n")
                f.write(traceback.format_exc())

    if test_started:
        try:
            removed_fixture_files = cleanup_transient_fixture_files(test_name)
            if removed_fixture_files:
                if verbose:
                    print(f"[CLEANUP] Removed {len(removed_fixture_files)} transient fixture file(s)")
                with open(stderr_log, "a", encoding="utf-8") as f:
                    f.write("\n\n[CLEANUP] Removed transient fixture files:\n")
                    for path in removed_fixture_files:
                        f.write(f"  {path}\n")
        except Exception as cleanup_err:
            warning_msg = f"[WARNING] Transient fixture cleanup failed for {test_name}: {cleanup_err}"
            if verbose:
                print(warning_msg, file=sys.stderr)
            with open(stderr_log, "a", encoding="utf-8") as f:
                f.write(f"\n\n{warning_msg}\n")
                f.write(traceback.format_exc())

    duration = time.perf_counter() - start_time
    finished_at = datetime.now().isoformat()

    status = "PASS" if success else ("ERROR" if error else "FAIL")
    if verbose:
        print(f"[{status}] {test_name} ({duration:.1f}s)")
    if progress_writer:
        progress_writer.write_event(
            "test_end",
            test_name=test_name,
            status=status,
            duration_s=round(duration, 3),
            success=success,
            verified=verified,
            error=error,
        )

    env_ctx = runtime_context.get("environment_context") if runtime_context else None
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
        ground_truth_passed=ground_truth_passed,
        ground_truth_configured=ground_truth_configured,
        environment_context=env_ctx,
    )


def result_to_summary(result: TestResult, technique: str, overrides: dict) -> TestSummary:
    """Convert a TestResult to a TestSummary for reporting."""
    status = _result_status(result)

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
        error_context=_read_error_context(result.log_dir),
        metrics=normalize_metrics_map(result.metrics),
        config_overrides_applied=overrides,
        ground_truth_passed=result.ground_truth_passed,
        ground_truth_configured=result.ground_truth_configured,
        environment_context=result.environment_context,
    )


def cmd_run_single(args, test_name: str):
    """Handle single test run."""
    run_id = get_timestamp_id()
    run_uuid = str(uuid.uuid4())
    output_dir = get_output_dir(run_id, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rag_api_url = resolve_rag_api_url_for_args(args)
    log_dir = output_dir / test_name
    log_dir.mkdir(parents=True, exist_ok=True)

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
        "run_uuid": run_uuid,
        "backup_before_run": backup_before_run,
        "teardown_after_run": teardown_after_run,
        "rag_api_url": rag_api_url,
    }
    save_run_config(run_config, output_dir)
    prov_payload = collect_run_provenance(REPO_ROOT, rag_api_url)
    prov_payload["run_uuid"] = run_uuid
    prov_payload["run_id"] = run_id
    save_provenance(prov_payload, output_dir)
    env_ctx = build_environment_context()
    progress_writer = ProgressWriter(log_dir / "progress.log")
    progress_writer.write_event(
        "run_start",
        run_id=run_id,
        test_name=test_name,
        technique=technique,
        rag_api_url=rag_api_url,
        output_dir=str(output_dir),
    )

    print(f"Output directory: {output_dir}")
    print(f"RAG API URL: {rag_api_url}")
    print()

    wall_start = time.perf_counter()
    result = None

    try:
        if getattr(args, "skip_preflight", False):
            progress_writer.write_event("preflight_skipped", test_name=test_name)
            preflight_result = None
        else:
            progress_writer.write_event("preflight_start", test_name=test_name)
            preflight_result = _run_preflight_result(args, [test_name])
        if preflight_result is not None:
            if preflight_result["passed"]:
                progress_writer.write_event("preflight_end", test_name=test_name, status="ok")
            else:
                error_message = _summarize_preflight_failure(preflight_result)
                progress_writer.write_event(
                    "preflight_end",
                    test_name=test_name,
                    status="error",
                    error=error_message,
                )
                print("[ERROR] Preflight failed. Re-run with --skip-preflight only if you understand the risk.")
                _write_text_log(log_dir / "stdout.log", "")
                _write_text_log(log_dir / "stderr.log", error_message + "\n")
                result = _build_failed_result(
                    test_name, log_dir, error_message, overrides=overrides, environment_context=env_ctx
                )
        if result is None:
            result = run_single_test(
                test_name,
                technique,
                overrides,
                output_dir,
                verbose=True,
                backup_before_run=backup_before_run,
                teardown_after_run=teardown_after_run,
                forced_backup_warning=forced_backup_warning,
                runtime_context={
                    "progress_writer": progress_writer,
                    "blocked_threshold": 3,
                    "run_uuid": run_uuid,
                    "run_id": run_id,
                    "environment_context": env_ctx,
                },
            )
        wall_end = time.perf_counter()

        summary = result_to_summary(result, technique, overrides)
        save_test_summary(summary, result.log_dir)
        progress_writer.write_event(
            "summary_written",
            test_name=test_name,
            path=str(result.log_dir / "summary.json"),
            status=summary.status,
        )

        aggregate = generate_aggregate_report(
            [summary], run_config, run_id, wall_clock_s=wall_end - wall_start, run_uuid=run_uuid
        )
        save_aggregate_report(aggregate, output_dir)
        progress_writer.write_event(
            "aggregate_written",
            test_name=test_name,
            path=str(output_dir / "aggregate.json"),
            passed=aggregate.passed,
            failed=aggregate.failed,
            errors=aggregate.errors,
        )
        print_console_summary(aggregate, output_dir)
        _print_run_footer(output_dir, [summary])

        exit_code = 0 if result.success else 1
        progress_writer.write_event(
            "run_end",
            test_name=test_name,
            status=summary.status,
            exit_code=exit_code,
            duration_s=round(wall_end - wall_start, 3),
        )
        if exit_code == 0:
            prune_old_test_runs(getattr(args, "max_retained_runs", 0), output_dir)
        return exit_code
    except Exception as exc:
        progress_writer.write_event(
            "run_end",
            test_name=test_name,
            status="ERROR",
            exit_code=1,
            error=str(exc),
        )
        raise
    finally:
        progress_writer.close()


def cmd_run_many(args):
    """Handle --run-many command."""
    from debug_assistant_latest.parallel import PARALLEL_TEST_TIMEOUT, run_tests_parallel

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

    preflight_exit = _maybe_run_preflight(args, matched)
    if preflight_exit != 0:
        return preflight_exit

    run_id = get_timestamp_id()
    run_uuid = str(uuid.uuid4())
    output_dir = get_output_dir(run_id, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rag_api_url = resolve_rag_api_url_for_args(args)

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
        "run_uuid": run_uuid,
        "backup_before_run": backup_before_run,
        "teardown_after_run": teardown_after_run,
        "rag_api_url": rag_api_url,
    }
    save_run_config(run_config, output_dir)
    prov_payload = collect_run_provenance(REPO_ROOT, rag_api_url)
    prov_payload["run_uuid"] = run_uuid
    prov_payload["run_id"] = run_id
    save_provenance(prov_payload, output_dir)
    env_ctx = build_environment_context()

    print(f"Running {len(matched)} tests with {jobs} workers")
    print(f"Output directory: {output_dir}")
    print(f"RAG API URL: {rag_api_url}")
    print()

    wall_start = time.perf_counter()
    parallel_timeout = getattr(args, "parallel_timeout", None)
    if parallel_timeout is None:
        parallel_timeout = PARALLEL_TEST_TIMEOUT
    results = run_tests_parallel(
        matched,
        technique,
        overrides,
        output_dir,
        jobs,
        backup_before_run=backup_before_run,
        teardown_after_run=teardown_after_run,
        forced_backup_warning=forced_backup_warning,
        run_uuid=run_uuid,
        run_id=run_id,
        environment_context=env_ctx,
        parallel_timeout_s=parallel_timeout,
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
        summaries, run_config, run_id, wall_clock_s=wall_end - wall_start, run_uuid=run_uuid
    )
    save_aggregate_report(aggregate, output_dir)
    print_console_summary(aggregate, output_dir)
    _print_run_footer(output_dir, summaries)

    # Return non-zero if any test failed
    failed = sum(1 for r in results if not r.success)
    if failed == 0:
        prune_old_test_runs(getattr(args, "max_retained_runs", 0), output_dir)
    return 1 if failed > 0 else 0
