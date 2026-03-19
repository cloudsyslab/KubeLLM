import json
import argparse
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import inspect

REPO_ROOT = Path(__file__).resolve().parents[1]
DEBUG_DIR = REPO_ROOT / "debug_assistant_latest"

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(DEBUG_DIR))

if not hasattr(inspect, "getargspec"):
    inspect.getargspec = inspect.getfullargspec

from debug_assistant_latest.config_merge import load_config_with_overrides, merge_config_overrides
from debug_assistant_latest.ground_truth import CheckStatus, run_all_checks, run_check, validate_ground_truth_config
from debug_assistant_latest.report import AgentMetrics, TestSummary, generate_aggregate_report, load_test_summary
from debug_assistant_latest.runner import (
    TestResult,
    _apply_repeat_overrides,
    _build_repeat_payload,
    _run_repeat_queue,
    cmd_run_single,
    result_to_summary,
)
from debug_assistant_latest import teardown
from api_server_support import SessionState, knowledge_table_name
from debug_assistant_latest.verification_base import parse_verification_status, print_verification_status


class ConfigMergeTests(unittest.TestCase):
    def test_merge_config_overrides_deep_merges_without_mutation(self):
        base = {"debug-agent": {"model": "gpt-5-nano"}, "nested": {"a": 1}}
        merged = merge_config_overrides(base, {"debug-agent.model": "gpt-4o", "nested.b": 2})

        self.assertEqual(base["debug-agent"]["model"], "gpt-5-nano")
        self.assertEqual(merged["debug-agent"]["model"], "gpt-4o")
        self.assertEqual(merged["nested"], {"a": 1, "b": 2})

    def test_load_config_with_overrides_derives_test_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config_step.json"
            config_path.write_text(json.dumps({"test-directory": "", "debug-agent": {"model": "gpt-5-nano"}}))

            config = load_config_with_overrides(config_path, {"debug-agent.model": "gpt-4o"})

            self.assertEqual(config["debug-agent"]["model"], "gpt-4o")
            self.assertTrue(config["test-directory"].startswith(tmpdir))


class GroundTruthTests(unittest.TestCase):
    def test_run_check_skips_when_dependency_missing(self):
        result = run_check(
            {
                "name": "service_ready",
                "cmd": "echo should_not_run",
                "expect": "ok",
                "depends_on": ["pod_ready"],
            },
            passed_checks=set(),
        )

        self.assertEqual(result.status, CheckStatus.SKIP)
        self.assertEqual(result.attempts, 0)

    def test_validate_ground_truth_config_rejects_duplicate_names(self):
        errors = validate_ground_truth_config(
            {
                "ground-truth": {
                    "checks": [
                        {"name": "pod_ready", "cmd": "echo 1", "expect": "1"},
                        {"name": "pod_ready", "cmd": "echo 2", "expect": "2"},
                    ]
                }
            }
        )

        self.assertTrue(any("duplicate name" in error for error in errors))

    def test_validate_ground_truth_config_enforces_schema_ranges_and_types(self):
        errors = validate_ground_truth_config(
            {
                "ground-truth": {
                    "timeout_seconds": 0,
                    "checks": [
                        {
                            "name": "bad_check",
                            "cmd": "echo bad",
                            "timeout_s": "30",
                            "expect_exit": 999,
                        }
                    ],
                }
            }
        )

        self.assertTrue(any("ground-truth.timeout_seconds" in error and "minimum of 1" in error for error in errors))
        self.assertTrue(any("ground-truth.checks.0.timeout_s" in error and "type 'number'" in error for error in errors))
        self.assertTrue(any("ground-truth.checks.0.expect_exit" in error and "maximum of 255" in error for error in errors))

    def test_validate_ground_truth_config_accepts_schema_valid_expect_fields(self):
        errors = validate_ground_truth_config(
            {
                "ground-truth": {
                    "timeout_seconds": 60,
                    "checks": [
                        {
                            "name": "exit_check",
                            "cmd": "echo ok",
                            "timeout_s": 30,
                            "expect_exit": 2,
                        }
                    ],
                }
            }
        )

        self.assertEqual(errors, [])

    def test_validate_ground_truth_config_rejects_malformed_expect_regex(self):
        errors = validate_ground_truth_config(
            {
                "ground-truth": {
                    "checks": [
                        {
                            "name": "regex_check",
                            "cmd": "echo value",
                            "expect_regex": "(",
                        }
                    ],
                }
            }
        )

        self.assertTrue(any("invalid expect_regex" in error for error in errors))

    def test_run_check_allows_expect_exit_with_stderr(self):
        cmd = f'"{sys.executable}" -c "import sys; sys.stderr.write(\'boom\\n\'); sys.exit(2)"'
        result = run_check(
            {
                "name": "expect_nonzero",
                "cmd": cmd,
                "expect_exit": 2,
            },
            passed_checks=set(),
        )

        self.assertEqual(result.status, CheckStatus.PASS)
        self.assertIsNone(result.error)

    def test_run_check_expect_exit_timeout_still_errors(self):
        cmd = f'"{sys.executable}" -c "import time; time.sleep(0.2)"'
        result = run_check(
            {
                "name": "expect_timeout",
                "cmd": cmd,
                "expect_exit": 2,
                "timeout_s": 0.05,
            },
            passed_checks=set(),
        )

        self.assertEqual(result.status, CheckStatus.ERROR)
        self.assertIn("timed out", result.error)

    def test_run_check_malformed_expect_regex_returns_error(self):
        cmd = f'"{sys.executable}" -c "print(\'value\')"'
        result = run_check(
            {
                "name": "bad_regex",
                "cmd": cmd,
                "expect_regex": "(",
            },
            passed_checks=set(),
        )

        self.assertEqual(result.status, CheckStatus.ERROR)
        self.assertIn("Invalid expect_regex", result.error)

    def test_run_all_checks_enforces_global_timeout_during_slow_check(self):
        cmd_slow = f'"{sys.executable}" -c "import time; time.sleep(0.2); print(\'done\')"'
        cmd_fast = f'"{sys.executable}" -c "print(\'later\')"'
        result = run_all_checks(
            {
                "test-name": "slow_case",
                "ground-truth": {
                    "timeout_seconds": 0.05,
                    "checks": [
                        {"name": "slow_check", "cmd": cmd_slow, "expect": "done", "timeout_s": 1},
                        {"name": "after_check", "cmd": cmd_fast, "expect": "later"},
                    ],
                },
            }
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.checks[0].status, CheckStatus.ERROR)
        self.assertIn("Global timeout exceeded", result.checks[0].error)
        self.assertEqual(result.checks[1].status, CheckStatus.ERROR)
        self.assertEqual(result.checks[1].actual, "(not executed)")


class ReportTests(unittest.TestCase):
    def test_generate_aggregate_report_tracks_ground_truth_and_costs(self):
        summaries = [
            TestSummary(
                test_name="wrong_port",
                technique="allStepsAtOnce",
                status="PASS",
                verified=True,
                ground_truth_passed=True,
                duration_s=10,
                metrics={"debug_agent": AgentMetrics(total_tokens=100, cost=1.25)},
            ),
            TestSummary(
                test_name="wrong_interface",
                technique="allStepsAtOnce",
                status="FAIL",
                verified=False,
                ground_truth_passed=False,
                duration_s=5,
                error_message="not fixed",
                metrics={"verification_agent": AgentMetrics(total_tokens=50, cost=0.75)},
            ),
        ]

        aggregate = generate_aggregate_report(summaries, run_config={}, run_id="run-1", wall_clock_s=20)

        self.assertEqual(aggregate.total_tests, 2)
        self.assertEqual(aggregate.passed, 1)
        self.assertEqual(aggregate.failed, 1)
        self.assertEqual(aggregate.ground_truth_passed, 1)
        self.assertEqual(aggregate.tests_with_ground_truth, 2)
        self.assertEqual(aggregate.total_tokens, 150)
        self.assertEqual(aggregate.total_cost, 2.0)
        self.assertEqual(aggregate.ground_truth_failed_tests, ["wrong_interface"])

    def test_generate_aggregate_report_counts_dict_backed_metrics(self):
        summaries = [
            TestSummary(
                test_name="wrong_port",
                technique="allStepsAtOnce",
                status="PASS",
                verified=True,
                metrics={
                    "debug_agent": {
                        "test_case": "wrong_port",
                        "model": "gpt-4o",
                        "agent_type": "debug",
                        "input_tokens": 60,
                        "output_tokens": 40,
                        "total_tokens": 100,
                        "task_status": True,
                        "duration_s": 3.5,
                        "cost": 1.25,
                    }
                },
            ),
            TestSummary(
                test_name="wrong_interface",
                technique="allStepsAtOnce",
                status="FAIL",
                verified=False,
                metrics={
                    "verification_agent": {
                        "test_case": "wrong_interface",
                        "model": "gpt-4o-mini",
                        "agent_type": "verification",
                        "input_tokens": 20,
                        "output_tokens": 30,
                        "total_tokens": 50,
                        "task_status": False,
                        "duration_s": 1.25,
                        "cost": 0.75,
                    }
                },
            ),
        ]

        aggregate = generate_aggregate_report(summaries, run_config={}, run_id="run-dict")

        self.assertEqual(aggregate.total_tokens, 150)
        self.assertEqual(aggregate.total_cost, 2.0)
        self.assertEqual(aggregate.total_debug_cost, 1.25)
        self.assertEqual(aggregate.total_verification_cost, 0.75)

    def test_load_test_summary_accepts_legacy_raw_metric_dicts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            summary_path = Path(tmpdir) / "summary.json"
            summary_path.write_text(
                json.dumps(
                    {
                        "test_name": "wrong_port",
                        "technique": "allStepsAtOnce",
                        "status": "PASS",
                        "verified": True,
                        "started_at": "2026-01-01T00:00:00",
                        "finished_at": "2026-01-01T00:00:01",
                        "duration_s": 1.0,
                        "error_message": None,
                        "metrics": {
                            "debug_agent": {
                                "test_case": "wrong_port",
                                "model": "gpt-4o",
                                "agent_type": "debug",
                                "input_tokens": 5,
                                "output_tokens": 10,
                                "total_tokens": 15,
                                "task_status": True,
                                "duration_s": 0.5,
                                "cost": 0.25,
                            }
                        },
                        "config_overrides_applied": {},
                        "ground_truth_passed": True,
                    }
                )
            )

            summary = load_test_summary(summary_path)

        self.assertIsInstance(summary.metrics["debug_agent"], AgentMetrics)
        self.assertEqual(summary.metrics["debug_agent"].total_tokens, 15)
        self.assertEqual(summary.metrics["debug_agent"].cost, 0.25)


class TeardownTests(unittest.TestCase):
    def test_backup_environment_creates_expected_backup_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_root = Path(tmpdir)
            case_dir = test_root / "wrong_port"
            case_dir.mkdir()
            (case_dir / "wrong_port.yaml").write_text("kind: Deployment\n")

            with patch.object(teardown, "TROUBLESHOOTING_DIR", test_root), patch.dict(
                teardown.TEARDOWN_CONFIG,
                {"wrong_port": {"docker_images": [], "restore_files": ["yaml"], "k8s_manifests": []}},
                clear=False,
            ):
                teardown.backup_environment("wrong_port")

            self.assertTrue((case_dir / "backup_yaml.yaml").exists())

    def test_teardown_environment_restores_backup_and_deletes_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_root = Path(tmpdir)
            case_dir = test_root / "wrong_port"
            case_dir.mkdir()
            (case_dir / "wrong_port.yaml").write_text("broken\n")
            (case_dir / "backup_yaml.yaml").write_text("restored\n")

            recorded_calls = []

            def fake_run(*args, **kwargs):
                recorded_calls.append((args, kwargs))
                return None

            with patch.object(teardown, "TROUBLESHOOTING_DIR", test_root), patch(
                "debug_assistant_latest.teardown.subprocess.run", side_effect=fake_run
            ), patch.dict(
                teardown.TEARDOWN_CONFIG,
                {"wrong_port": {"docker_images": [], "restore_files": ["yaml"], "k8s_manifests": ["{name}.yaml"]}},
                clear=False,
            ):
                teardown.teardown_environment("wrong_port")

            self.assertEqual((case_dir / "wrong_port.yaml").read_text(), "restored\n")
            self.assertTrue(any("kubectl" in call[0][0][0] for call in recorded_calls if call[0]))


class RunnerTests(unittest.TestCase):
    def test_result_to_summary_preserves_ground_truth_flag(self):
        result = TestResult(
            test_name="wrong_port",
            success=True,
            verified=True,
            debug_self_report=False,
            duration_s=12.3,
            error=None,
            metrics={"debug_agent": {"cost": 1.0}},
            log_dir=Path("/tmp/wrong_port"),
            started_at="2026-01-01T00:00:00",
            finished_at="2026-01-01T00:00:12",
            ground_truth_passed=True,
        )

        summary = result_to_summary(result, "allStepsAtOnce", {"debug-agent.model": "gpt-4o"})

        self.assertEqual(summary.status, "PASS")
        self.assertTrue(summary.verified)
        self.assertTrue(summary.ground_truth_passed)
        self.assertEqual(summary.metrics["debug_agent"].__class__.__name__, "AgentMetrics")
        self.assertEqual(summary.metrics["debug_agent"].cost, 1.0)
        self.assertEqual(summary.config_overrides_applied["debug-agent.model"], "gpt-4o")

    def test_apply_repeat_overrides_forces_serial_backup_and_teardown(self):
        args = argparse.Namespace(
            repeat=3,
            jobs=4,
            teardown_after_run=False,
            backup_before_run=False,
        )

        repeat_active = _apply_repeat_overrides(args)

        self.assertTrue(repeat_active)
        self.assertEqual(args.jobs, 1)
        self.assertTrue(args.teardown_after_run)
        self.assertTrue(args.backup_before_run)

    def test_build_repeat_payload_serializes_paths_and_sets_test_case(self):
        args = argparse.Namespace(
            output_dir=Path("/tmp/original"),
            test_case="wrong_port",
            repeat=2,
            jobs=1,
            teardown_after_run=True,
            backup_before_run=True,
        )

        payload = _build_repeat_payload(args, "single", 2, "run-123", Path("/tmp/runs"))

        self.assertEqual(payload["mode"], "single")
        self.assertEqual(payload["iteration"], 2)
        self.assertEqual(payload["base_run_id"], "run-123")
        self.assertEqual(payload["base_output_dir"], "/tmp/runs")
        self.assertEqual(payload["test_case"], "wrong_port")
        self.assertIsNone(payload["args"]["output_dir"])

    def test_run_repeat_queue_writes_summary_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_base = Path(tmpdir)
            args = argparse.Namespace(
                repeat=2,
                jobs=1,
                teardown_after_run=True,
                backup_before_run=True,
                stall_limit_s=5,
                output_dir=tmp_base / "runs",
                test_case="wrong_port",
            )

            def fake_worker(result_queue, payload):
                iter_dir = Path(payload["base_output_dir"]) / payload["base_run_id"] / f"iter-{payload['iteration']:03d}"
                result_queue.put(("ok", 0, str(iter_dir)))

            class FakeProcess:
                def __init__(self, target, args):
                    self.target = target
                    self.args = args
                    self._alive = False
                    self.pid = 42

                def start(self):
                    self._alive = True
                    try:
                        self.target(*self.args)
                    finally:
                        self._alive = False

                def join(self, timeout=None):
                    return

                def is_alive(self):
                    return self._alive

                def terminate(self):
                    self._alive = False

                def kill(self):
                    self._alive = False

            base_run_id = "repeat-123"
            with patch("debug_assistant_latest.runner.Process", FakeProcess), patch(
                "debug_assistant_latest.runner._repeat_iteration_worker", fake_worker
            ):
                exit_code = _run_repeat_queue(args, "single", base_run_id, tmp_base)

            self.assertEqual(exit_code, 0)
            summary_path = tmp_base / base_run_id / "queue_summary.json"
            self.assertTrue(summary_path.exists())
            summary = json.loads(summary_path.read_text())
            self.assertEqual(summary["completed_iterations"], args.repeat)
            self.assertTrue(all(result["status"] == "PASS" for result in summary["results"]))

    def test_run_repeat_queue_reports_stall(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_base = Path(tmpdir)
            args = argparse.Namespace(
                repeat=1,
                jobs=1,
                teardown_after_run=True,
                backup_before_run=True,
                stall_limit_s=5,
                output_dir=tmp_base / "runs",
                test_case="wrong_port",
            )

            class FakeProcess:
                def __init__(self, target, args):
                    self._alive = True

                def start(self):
                    pass

                def join(self, timeout=None):
                    pass

                def is_alive(self):
                    return self._alive

                def terminate(self):
                    self._alive = False

                def kill(self):
                    self._alive = False

            class FakeQueue:
                def close(self):
                    pass

                def cancel_join_thread(self):
                    pass

            base_run_id = "repeat-stall"
            with patch("debug_assistant_latest.runner.Process", FakeProcess), patch(
                "debug_assistant_latest.runner.Queue", FakeQueue
            ):
                exit_code = _run_repeat_queue(args, "single", base_run_id, tmp_base)

            self.assertEqual(exit_code, 1)
            summary_path = tmp_base / base_run_id / "queue_summary.json"
            self.assertTrue(summary_path.exists())
            summary = json.loads(summary_path.read_text())
            self.assertEqual(summary["completed_iterations"], 1)
            self.assertEqual(summary["results"][0]["status"], "STALL")

    def test_verification_status_helpers(self):
        self.assertTrue(parse_verification_status("Solved <|VERIFIED|>"))
        self.assertFalse(parse_verification_status("Still broken <|FAILED|>"))
        self.assertIsNone(parse_verification_status("Could not check <|VERIFICATION_ERROR|>"))
        self.assertIsNone(parse_verification_status("unknown"))

    def test_print_verification_status_outputs_token(self):
        with patch("builtins.print") as mock_print:
            print_verification_status(True)

        combined = "".join(call.args[0] for call in mock_print.call_args_list if call.args)
        self.assertIn("VERIFICATION STATUS: ✓ VERIFIED", combined)

    def test_cmd_run_single_writes_summary_flow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            args = argparse.Namespace(
                output_dir=Path(tmpdir),
                debug_model=None,
                api_model=None,
                verification_model=None,
                technique="allStepsAtOnce",
                backup_before_run=False,
                teardown_after_run=False,
                minikube_profile=None,
            )

            fake_result = TestResult(
                test_name="wrong_port",
                success=True,
                verified=True,
                debug_self_report=None,
                duration_s=1.0,
                error=None,
                metrics={},
                log_dir=Path(tmpdir) / "wrong_port",
                started_at="2026-01-01T00:00:00",
                finished_at="2026-01-01T00:00:01",
            )

            with patch("debug_assistant_latest.runner.run_single_test", return_value=fake_result), patch(
                "debug_assistant_latest.runner.save_run_config"
            ) as save_run_config_mock, patch(
                "debug_assistant_latest.runner.save_test_summary"
            ) as save_test_summary_mock, patch(
                "debug_assistant_latest.runner.generate_aggregate_report", return_value={"ok": True}
            ) as generate_report_mock, patch(
                "debug_assistant_latest.runner.save_aggregate_report"
            ) as save_aggregate_mock, patch(
                "debug_assistant_latest.runner.print_console_summary"
            ) as print_console_mock:
                exit_code = cmd_run_single(args, "wrong_port")

            self.assertEqual(exit_code, 0)
            save_run_config_mock.assert_called_once()
            save_test_summary_mock.assert_called_once()
            generate_report_mock.assert_called_once()
            save_aggregate_mock.assert_called_once()
            print_console_mock.assert_called_once()


class ApiServerSupportTests(unittest.TestCase):
    def test_session_state_reset_run_restores_default_message(self):
        session = SessionState()
        session.messages.append({"role": "user", "content": "hello"})
        session.rag_assistant = object()
        session.rag_assistant_run_id = "abc"

        session.reset_run()

        self.assertIsNone(session.rag_assistant)
        self.assertIsNone(session.rag_assistant_run_id)
        self.assertEqual(session.messages, [{"role": "assistant", "content": "Upload a doc and ask me questions..."}])

    def test_knowledge_table_name_uses_embedding_model(self):
        self.assertEqual(knowledge_table_name("nomic-embed-text"), "local_rag_documents_nomic-embed-text")


if __name__ == "__main__":
    unittest.main()
