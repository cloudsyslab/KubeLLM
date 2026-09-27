import json
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
DEBUG_DIR = REPO_ROOT / "debug_assistant_latest"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(DEBUG_DIR))

import debug_assistant_latest.main as legacy_main
from debug_assistant_latest import cli as runner_cli
from debug_assistant_latest.api_agents import AgentAPI
from debug_assistant_latest.better_shell import ShellCommandResult
from debug_assistant_latest.compare_runs import _summary_row
from debug_assistant_latest.executor import _extract_execution_result, _technique_run_metadata
from debug_assistant_latest.report import AgentMetrics, TestSummary, generate_aggregate_report
from debug_assistant_latest.knowledge_plan import (
    KNOWLEDGE_PLAN_PROMPT,
    KnowledgePlanError,
    KnowledgePlanExecutor,
    PLAN_SCHEMA_VERSION,
    parse_knowledge_plan,
)


def _plan_payload(*steps):
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "reasoning_summary": "The manifest and application port disagree.",
        "steps": list(steps)
        or [
            {
                "id": "inspect",
                "command": "kubectl get pods",
                "timeout_seconds": 30,
                "expected_exit_codes": [0],
            }
        ],
    }


class KnowledgePlanParserTests(unittest.TestCase):
    def test_accepts_exact_v1_json(self):
        plan = parse_knowledge_plan(json.dumps(_plan_payload()))

        self.assertEqual(plan.schema_version, "1.0")
        self.assertEqual(plan.steps[0].id, "inspect")

    def test_rejects_markdown_wrapped_json_without_repair(self):
        response = f"```json\n{json.dumps(_plan_payload())}\n```"

        with self.assertRaisesRegex(KnowledgePlanError, "not strict JSON"):
            parse_knowledge_plan(response)

    def test_rejects_unknown_fields(self):
        payload = _plan_payload()
        payload["extra"] = True

        with self.assertRaisesRegex(KnowledgePlanError, "Additional properties"):
            parse_knowledge_plan(json.dumps(payload))

    def test_rejects_duplicate_json_keys(self):
        response = (
            '{"schema_version":"1.0","schema_version":"1.0",'
            '"reasoning_summary":"x","steps":[]}'
        )

        with self.assertRaisesRegex(KnowledgePlanError, "duplicate JSON key"):
            parse_knowledge_plan(response)

    def test_rejects_duplicate_step_ids(self):
        step = {
            "id": "same",
            "command": "true",
            "timeout_seconds": 10,
            "expected_exit_codes": [0],
        }

        with self.assertRaisesRegex(KnowledgePlanError, "must be unique"):
            parse_knowledge_plan(json.dumps(_plan_payload(step, dict(step))))

    def test_rejects_shell_branching_and_command_chaining(self):
        step = {
            "id": "branch",
            "command": "kubectl get pods && kubectl delete pod bad",
            "timeout_seconds": 10,
            "expected_exit_codes": [0],
        }

        with self.assertRaisesRegex(KnowledgePlanError, "unsupported shell control token"):
            parse_knowledge_plan(json.dumps(_plan_payload(step)))

    def test_rejects_command_substitution(self):
        step = {
            "id": "substitution",
            "command": "kubectl get pod $(kubectl get pods -o name)",
            "timeout_seconds": 10,
            "expected_exit_codes": [0],
        }

        with self.assertRaisesRegex(KnowledgePlanError, "unsupported command substitution"):
            parse_knowledge_plan(json.dumps(_plan_payload(step)))


class FakeShellTools:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def execute_shell_command(self, command, *, timeout_s):
        self.calls.append((command, timeout_s))
        return self.results.pop(0)


class KnowledgePlanExecutorTests(unittest.TestCase):
    def test_executes_each_step_once_in_order(self):
        plan = parse_knowledge_plan(
            json.dumps(
                _plan_payload(
                    {
                        "id": "one",
                        "command": "first",
                        "timeout_seconds": 10,
                        "expected_exit_codes": [0],
                    },
                    {
                        "id": "two",
                        "command": "second",
                        "timeout_seconds": 20,
                        "expected_exit_codes": [0, 2],
                    },
                )
            )
        )
        shell = FakeShellTools(
            [
                ShellCommandResult(command="first", exit_code=0),
                ShellCommandResult(command="second", exit_code=2, stderr="expected probe miss"),
            ]
        )

        report = KnowledgePlanExecutor(REPO_ROOT, shell_tools=shell).execute(plan)

        self.assertTrue(report.success)
        self.assertEqual(shell.calls, [("first", 10), ("second", 20)])
        self.assertEqual(report.completed_steps, 2)

    def test_stops_after_first_unexpected_exit(self):
        steps = [
            {
                "id": step_id,
                "command": command,
                "timeout_seconds": 10,
                "expected_exit_codes": [0],
            }
            for step_id, command in (("one", "first"), ("two", "second"), ("three", "third"))
        ]
        plan = parse_knowledge_plan(json.dumps(_plan_payload(*steps)))
        shell = FakeShellTools(
            [
                ShellCommandResult(command="first", exit_code=0),
                ShellCommandResult(command="second", exit_code=7, stderr="boom"),
                ShellCommandResult(command="third", exit_code=0),
            ]
        )

        report = KnowledgePlanExecutor(REPO_ROOT, shell_tools=shell).execute(plan)

        self.assertFalse(report.success)
        self.assertEqual(report.failure_category, "UNEXPECTED_EXIT")
        self.assertEqual(shell.calls, [("first", 10), ("second", 10)])

    def test_blocked_command_fails_closed(self):
        plan = parse_knowledge_plan(json.dumps(_plan_payload()))
        shell = FakeShellTools(
            [ShellCommandResult(command="kubectl get pods", blocked_reason="blocked by policy")]
        )

        report = KnowledgePlanExecutor(REPO_ROOT, shell_tools=shell).execute(plan)

        self.assertFalse(report.success)
        self.assertEqual(report.failure_category, "COMMAND_BLOCKED")

    def test_total_timeout_never_rounds_up_the_remaining_budget(self):
        plan = parse_knowledge_plan(
            json.dumps(
                _plan_payload(
                    {
                        "id": "bounded",
                        "command": "kubectl get pods",
                        "timeout_seconds": 10,
                        "expected_exit_codes": [0],
                    }
                )
            )
        )
        shell = FakeShellTools(
            [ShellCommandResult(command="kubectl get pods", timed_out=True, error="timed out")]
        )

        report = KnowledgePlanExecutor(
            REPO_ROOT,
            shell_tools=shell,
            total_timeout_s=0.25,
        ).execute(plan)

        self.assertEqual(report.failure_category, "TOTAL_TIMEOUT")
        self.assertGreater(shell.calls[0][1], 0)
        self.assertLessEqual(shell.calls[0][1], 0.25)

    def test_executor_phase_uses_the_existing_shell_safety_policy(self):
        from debug_assistant_latest.better_shell import BetterShellTools

        result = BetterShellTools(phase="executor").execute_shell_command(
            "kubectl port-forward service/example 8080:80"
        )

        self.assertIsNotNone(result.blocked_reason)
        self.assertIsNone(result.exit_code)


class KnowledgeAgentPromptTests(unittest.TestCase):
    def test_plan_contract_is_only_added_in_deterministic_mode(self):
        config = {
            "api-agent": {},
            "knowledge-prompt": {"problem-desc": "broken", "system-prompt": "help"},
            "test-directory": str(REPO_ROOT),
            "relevant-files": {
                "deployment": [],
                "application": [],
                "service": [],
                "dockerfile": False,
            },
        }
        regular = AgentAPI("api-agent", config)
        deterministic = AgentAPI("api-agent", config, deterministic_plan=True)

        regular.preparePrompt()
        deterministic.preparePrompt()

        self.assertNotIn("Deterministic execution plan contract", regular.prompt)
        self.assertIn(KNOWLEDGE_PLAN_PROMPT.strip(), deterministic.prompt)


class RunnerImportTests(unittest.TestCase):
    def test_runner_help_loads_with_repository_root_import_precedence(self):
        completed = subprocess.run(
            [sys.executable, str(DEBUG_DIR / "runner.py"), "--help"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("knowledgeAgentOnly", completed.stdout)

    def test_single_case_dry_run_never_dispatches_execution(self):
        argv = [
            str(DEBUG_DIR / "runner.py"),
            "wrong_port",
            "--technique",
            "knowledgeAgentOnly",
            "--dry-run",
        ]
        with patch.object(sys, "argv", argv), patch.object(
            runner_cli, "list_test_cases", return_value=["wrong_port"]
        ), patch.object(runner_cli, "cmd_run_single") as run_single:
            exit_code = runner_cli.main()

        self.assertEqual(exit_code, 0)
        run_single.assert_not_called()


class KnowledgeAgentOnlyFlowTests(unittest.TestCase):
    def test_flow_has_no_debug_model_and_preserves_verification(self):
        config = {
            "test-name": "wrong_port",
            "api-agent": {"model": "knowledge-model"},
            "verification-agent": {"model": "verification-model"},
        }
        plan_json = json.dumps(_plan_payload())

        class FakeAPI:
            instances = []

            def __init__(self, agent_type, supplied_config, *, deterministic_plan=False):
                self.agentProperties = supplied_config[agent_type]
                self.response = plan_json
                self.deterministic_plan = deterministic_plan
                self.__class__.instances.append(self)

            def setupAgent(self):
                return None

            def askQuestion(self):
                return {
                    "test_case": "wrong_port",
                    "model": "knowledge-model",
                    "agent_type": "api",
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "total_tokens": 15,
                    "task_status": 1,
                }

        class FakeVerification:
            calls = 0

            def __init__(self, agent_type, supplied_config):
                self.agentProperties = supplied_config[agent_type]
                self.verificationStatus = True
                self.verificationReport = "verified"
                self.runtime_context = {}
                self.debugAgentResponse = None

            def setupAgent(self):
                return None

            def askQuestion(self):
                self.__class__.calls += 1
                return {
                    "test_case": "wrong_port",
                    "model": "verification-model",
                    "agent_type": "verification",
                    "input_tokens": 4,
                    "output_tokens": 2,
                    "total_tokens": 6,
                    "task_status": 1,
                }

        class FakeExecutor:
            def __init__(self, *args, **kwargs):
                pass

            def execute(self, plan):
                return types.SimpleNamespace(
                    success=True,
                    failure_category=None,
                    to_dict=lambda: {
                        "schema_version": "1.0",
                        "success": True,
                        "duration_s": 0.01,
                        "completed_steps": 1,
                        "total_steps": 1,
                        "failure_category": None,
                        "failure_message": None,
                        "steps": [],
                    },
                )

        with tempfile.TemporaryDirectory() as tmpdir, patch.object(
            legacy_main, "_load_runtime_config", return_value=config
        ), patch.object(legacy_main, "setUpEnvironment"), patch.object(
            legacy_main, "AgentAPI", FakeAPI
        ), patch.object(
            legacy_main, "KnowledgePlanExecutor", FakeExecutor
        ), patch.object(
            legacy_main, "AgentVerification_v2", FakeVerification
        ), patch.object(
            legacy_main, "AgentDebug", side_effect=AssertionError("debug model must not be constructed")
        ), patch.object(
            legacy_main, "store_metrics_entry"
        ):
            result = legacy_main.knowledgeAgentOnly(
                "ignored.json",
                runtime_context={"log_dir": tmpdir},
            )

            self.assertTrue(FakeAPI.instances[0].deterministic_plan)
            self.assertEqual(FakeVerification.calls, 1)
            self.assertNotIn("debug_metrics", result)
            self.assertEqual(result["executor_metrics"]["total_tokens"], 0)
            self.assertTrue((Path(tmpdir) / "knowledge_plan.json").exists())
            self.assertTrue((Path(tmpdir) / "execution_results.json").exists())

            success, verified, debug_self_report, metrics, error = _extract_execution_result(result)
            self.assertTrue(success)
            self.assertTrue(verified)
            self.assertIsNone(debug_self_report)
            self.assertNotIn("debug", metrics)
            self.assertEqual(metrics["executor"]["total_tokens"], 0)
            self.assertIsNone(error)

    def test_invalid_plan_fails_closed_but_still_runs_verification(self):
        config = {
            "test-name": "wrong_port",
            "api-agent": {"model": "knowledge-model"},
            "verification-agent": {"model": "verification-model"},
        }

        class InvalidAPI:
            def __init__(self, agent_type, supplied_config, *, deterministic_plan=False):
                self.agentProperties = supplied_config[agent_type]
                self.response = "```json\n{}\n```"
                self.deterministic_plan = deterministic_plan

            def setupAgent(self):
                return None

            def askQuestion(self):
                return {"agent_type": "api", "task_status": 1}

        class FailingVerification:
            calls = 0

            def __init__(self, agent_type, supplied_config):
                self.agentProperties = supplied_config[agent_type]
                self.verificationStatus = False
                self.verificationReport = "not fixed"
                self.runtime_context = {}
                self.debugAgentResponse = None

            def setupAgent(self):
                return None

            def askQuestion(self):
                self.__class__.calls += 1
                return {"agent_type": "verification", "task_status": 0}

        with tempfile.TemporaryDirectory() as tmpdir, patch.object(
            legacy_main, "_load_runtime_config", return_value=config
        ), patch.object(legacy_main, "setUpEnvironment"), patch.object(
            legacy_main, "AgentAPI", InvalidAPI
        ), patch.object(
            legacy_main,
            "KnowledgePlanExecutor",
            side_effect=AssertionError("invalid plans must never reach execution"),
        ), patch.object(
            legacy_main, "AgentVerification_v2", FailingVerification
        ), patch.object(
            legacy_main, "AgentDebug", side_effect=AssertionError("debug model must not be constructed")
        ), patch.object(
            legacy_main, "store_metrics_entry"
        ):
            result = legacy_main.knowledgeAgentOnly(
                "ignored.json",
                runtime_context={"log_dir": tmpdir},
            )

            self.assertFalse(result["status"])
            self.assertFalse(result["plan_valid"])
            self.assertFalse(result["execution_status"])
            self.assertEqual(result["execution_failure_category"], "PLAN_INVALID")
            self.assertEqual(FailingVerification.calls, 1)
            self.assertTrue((Path(tmpdir) / "knowledge_plan_error.json").exists())
            self.assertFalse((Path(tmpdir) / "knowledge_plan.json").exists())
            self.assertFalse((Path(tmpdir) / "execution_results.json").exists())

    def test_schema_version_is_recorded_only_for_the_new_technique(self):
        self.assertEqual(
            _technique_run_metadata("knowledgeAgentOnly"),
            {"knowledge_plan_schema_version": PLAN_SCHEMA_VERSION},
        )
        self.assertEqual(_technique_run_metadata("allStepsAtOnce"), {})

    def test_aggregate_reports_executor_separately_from_debug(self):
        summary = TestSummary(
            test_name="wrong_port",
            technique="knowledgeAgentOnly",
            status="PASS",
            verified=True,
            metrics={
                "api": AgentMetrics(model="knowledge", total_tokens=20, cost=0.2),
                "executor": AgentMetrics(total_tokens=0, cost=0.0, duration_s=1.5),
                "verification": AgentMetrics(model="verifier", total_tokens=5, cost=0.05),
            },
        )

        aggregate = generate_aggregate_report([summary], {}, "run")

        self.assertEqual(aggregate.total_debug_tokens, 0)
        self.assertEqual(aggregate.total_debug_cost, 0.0)
        self.assertEqual(aggregate.total_executor_tokens, 0)
        self.assertEqual(aggregate.total_executor_cost, 0.0)
        self.assertEqual(aggregate.total_executor_duration_s, 1.5)

        row = _summary_row(summary)
        self.assertEqual(row["api_tokens"], 20)
        self.assertEqual(row["debug_tokens"], 0)
        self.assertEqual(row["executor_tokens"], 0)
        self.assertEqual(row["verification_tokens"], 5)
        self.assertEqual(row["total_tokens"], 25)
        self.assertEqual(row["executor_duration_s"], 1.5)


if __name__ == "__main__":
    unittest.main()
