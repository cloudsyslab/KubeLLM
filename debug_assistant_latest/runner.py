#!/usr/bin/env python3
"""
KubeLLM Test Runner — thin shim over ``cli`` / ``executor`` / ``parallel`` / ``diagnostics``.

Preserves ``python runner.py`` and stable ``debug_assistant_latest.runner`` imports for tests
and documentation.

Usage:
    python3 runner.py --list                           # List available test cases
    python3 runner.py wrong_port                       # Run single test
    python3 runner.py --run-many "port_*" --jobs 4    # Run pattern in parallel
    python3 runner.py wrong_port --debug-model gpt-4o # With config override
"""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
REPO_ROOT = SCRIPT_DIR.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from debug_assistant_latest.cli import (  # noqa: E402
    _apply_repeat_overrides,
    _build_repeat_payload,
    _repeat_iteration_worker,
    _run_repeat_queue,
    cmd_compare,
    cmd_list,
    main,
)
from debug_assistant_latest.diagnostics import (  # noqa: E402
    cmd_dashboard,
    cmd_diagnose,
    cmd_diagnose_last,
    cmd_latest_run,
    get_latest_run_dir,
)
from debug_assistant_latest.executor import (  # noqa: E402
    TestResult,
    _best_effort_configure_console_streams,
    _build_failed_result,
    _display_path,
    _extract_execution_result,
    _has_ground_truth_config,
    _maybe_run_preflight,
    _print_run_footer,
    _read_error_context,
    _result_status,
    _run_preflight_result,
    _run_selected_preflight,
    _safe_flush_stream,
    _safe_write_to_stream,
    _summarize_preflight_failure,
    _write_text_log,
    cmd_run_many,
    cmd_run_single,
    get_output_dir,
    get_timestamp_id,
    resolve_rag_api_url_for_args,
    result_to_summary,
    run_single_test,
    run_single_test_in_process,
)
from debug_assistant_latest.parallel import (  # noqa: E402
    PARALLEL_TEST_TIMEOUT,
    Process,
    Queue,
    _worker_wrapper,
    run_tests_parallel,
)
from preflight import print_preflight_result, run_preflight  # noqa: E402
from report import (  # noqa: E402
    generate_aggregate_report,
    print_console_summary,
    save_aggregate_report,
    save_run_config,
    save_test_summary,
)

__all__ = [
    "PARALLEL_TEST_TIMEOUT",
    "Process",
    "Queue",
    "TestResult",
    "_apply_repeat_overrides",
    "_best_effort_configure_console_streams",
    "_build_failed_result",
    "_build_repeat_payload",
    "_display_path",
    "_extract_execution_result",
    "_has_ground_truth_config",
    "_maybe_run_preflight",
    "_print_run_footer",
    "_read_error_context",
    "_repeat_iteration_worker",
    "_result_status",
    "_run_preflight_result",
    "_run_repeat_queue",
    "_run_selected_preflight",
    "_safe_flush_stream",
    "_safe_write_to_stream",
    "_summarize_preflight_failure",
    "_worker_wrapper",
    "_write_text_log",
    "cmd_dashboard",
    "cmd_diagnose",
    "cmd_diagnose_last",
    "cmd_latest_run",
    "cmd_compare",
    "cmd_list",
    "cmd_preflight",
    "cmd_run_many",
    "cmd_run_single",
    "generate_aggregate_report",
    "get_latest_run_dir",
    "get_output_dir",
    "get_timestamp_id",
    "main",
    "print_console_summary",
    "print_preflight_result",
    "resolve_rag_api_url_for_args",
    "result_to_summary",
    "run_preflight",
    "run_single_test",
    "run_single_test_in_process",
    "run_tests_parallel",
    "save_aggregate_report",
    "save_run_config",
    "save_test_summary",
]

if __name__ == "__main__":
    sys.exit(main())
