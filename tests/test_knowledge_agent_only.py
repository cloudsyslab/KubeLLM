import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
DEBUG_DIR = REPO_ROOT / "debug_assistant_latest"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(DEBUG_DIR))

from assistant import BetterShellTools as AssistantBetterShellTools
from assistant import _output_instructions, _output_tools, guidelines, instructions
import api_server
from debug_assistant_latest import rag_api
from debug_assistant_latest.better_shell import BetterShellTools, ShellCommandResult
from debug_assistant_latest.knowledge_agent_only import (
    MAX_KNOWLEDGE_EXECUTION_SECONDS,
    KnowledgePlanError,
    execute_knowledge_plan,
    parse_knowledge_plan,
)
from debug_assistant_latest.ground_truth import GroundTruthResult
from debug_assistant_latest import executor


def _plan(*commands):
    return {
        "schema_version": "1",
        "actions": [
            {"tool": "run_shell_command", "arguments": {"command": command}}
            for command in commands
        ],
    }


class FakeShell:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def run_shell_command_result(self, command, *, timeout_s):
        self.calls.append((command, timeout_s))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def _shell_result(command, status="success", **kwargs):
    return ShellCommandResult(command=command, status=status, **kwargs)


class KnowledgePlanParserTests(unittest.TestCase):
    def test_parses_exact_json_and_preserves_literal_command(self):
        raw = '{"schema_version":"1","actions":[{"tool":"run_shell_command","arguments":{"command":"  kubectl get pods -o wide  "}}]}'

        plan = parse_knowledge_plan(raw)

        self.assertEqual(plan["actions"][0]["arguments"]["command"], "  kubectl get pods -o wide  ")

    def test_rejects_non_json_prose_fences_and_duplicate_keys(self):
        valid = json.dumps(_plan("kubectl get pods"))
        invalid_responses = [
            "Here is the plan: " + valid,
            "```json\n" + valid + "\n```",
            '{"schema_version":"1","schema_version":"1","actions":[]}',
        ]
        for response in invalid_responses:
            with self.subTest(response=response):
                with self.assertRaises(KnowledgePlanError):
                    parse_knowledge_plan(response)

    def test_rejects_schema_drift_empty_command_and_more_than_twenty_actions(self):
        invalid_plans = [
            {"schema_version": "1", "actions": [], "notes": "extra"},
            {"schema_version": "1", "actions": [{"tool": "other", "arguments": {"command": "x"}}]},
            _plan("   "),
            _plan(*[f"kubectl get pods --field-selector={index}" for index in range(21)]),
        ]
        for plan in invalid_plans:
            with self.subTest(plan=plan):
                with self.assertRaises(KnowledgePlanError):
                    parse_knowledge_plan(json.dumps(plan))


class DeterministicExecutionTests(unittest.TestCase):
    def test_executes_in_order_without_rewriting_and_applies_limits(self):
        plan = _plan("  kubectl get pods  ", "kubectl describe pod/demo")
        shell = FakeShell(
            [
                _shell_result("  kubectl get pods  ", stdout="pods\n"),
                _shell_result("kubectl describe pod/demo", stdout="details\n"),
            ]
        )

        report = execute_knowledge_plan(plan, shell)

        self.assertEqual([call[0] for call in shell.calls], ["  kubectl get pods  ", "kubectl describe pod/demo"])
        self.assertTrue(all(timeout <= 120 for _, timeout in shell.calls))
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["completed_action_count"], 2)
        self.assertEqual(report["actions"][0]["result"]["stdout"], "pods\n")

    def test_stops_after_nonzero_exit_or_blocked_action(self):
        failures = [
            _shell_result("kubectl apply -f x.yaml", status="exit_error", exit_code=1, stderr="bad manifest"),
            _shell_result("kubectl port-forward pod/demo 80:80", status="blocked", blocked_reason="blocked"),
        ]
        for first in failures:
            with self.subTest(status=first.status):
                shell = FakeShell([first])
                report = execute_knowledge_plan(
                    _plan(first.command, "kubectl get pods"),
                    shell,
                )

                self.assertEqual(report["status"], "action_failed")
                self.assertEqual(len(shell.calls), 1)
                self.assertEqual(report["actions"][1]["status"], "skipped")

    def test_distinguishes_executor_exceptions_and_stops_remaining_actions(self):
        shell = FakeShell([OSError("subprocess unavailable")])

        report = execute_knowledge_plan(_plan("kubectl get pods", "kubectl describe pod/demo"), shell)

        self.assertEqual(report["status"], "execution_error")
        self.assertEqual(report["actions"][0]["status"], "execution_error")
        self.assertEqual(report["actions"][1]["status"], "skipped")

    def test_exhausted_total_budget_skips_without_invoking_shell(self):
        shell = FakeShell([])

        with patch("debug_assistant_latest.knowledge_agent_only.time.monotonic", side_effect=[0, 2, 2]):
            report = execute_knowledge_plan(_plan("kubectl get pods"), shell, total_timeout_s=1)

        self.assertEqual(report["status"], "action_failed")
        self.assertEqual(report["actions"][0]["status"], "skipped")
        self.assertEqual(shell.calls, [])

    def test_execution_budgets_cannot_be_expanded_beyond_contract(self):
        shell = FakeShell([])
        with self.assertRaises(ValueError):
            execute_knowledge_plan(_plan("kubectl get pods"), shell, total_timeout_s=MAX_KNOWLEDGE_EXECUTION_SECONDS + 1)
        with self.assertRaises(ValueError):
            execute_knowledge_plan(_plan("kubectl get pods"), shell, command_timeout_s=121)
        self.assertEqual(shell.calls, [])

    def test_better_shell_structured_path_passes_exact_command_and_returns_exit_status(self):
        tool = BetterShellTools(phase="debug")
        command = "  printf 'literal  spaces'  "
        fake_process = SimpleNamespace(stdout="out", stderr="warning", returncode=2)

        with patch("subprocess.run", return_value=fake_process) as run_mock, patch(
            "debug_assistant_latest.better_shell.os.name", "posix"
        ):
            result = tool.run_shell_command_result(command, timeout_s=17)

        self.assertEqual(run_mock.call_args.args[0], command)
        self.assertTrue(run_mock.call_args.kwargs["shell"])
        self.assertEqual(run_mock.call_args.kwargs["timeout"], 17.0)
        self.assertEqual(result.status, "exit_error")
        self.assertEqual(result.exit_code, 2)
        self.assertEqual(result.stdout, "out")
        self.assertEqual(result.stderr, "warning")


class KnowledgePlanOutputModeTests(unittest.TestCase):
    def test_default_prompt_is_unchanged_and_plan_mode_only_replaces_format_contract(self):
        default_instructions, default_guidelines, default_markdown = _output_instructions("default")
        plan_instructions, plan_guidelines, plan_markdown = _output_instructions("knowledge_plan")

        self.assertIs(default_instructions, instructions)
        self.assertIs(default_guidelines, guidelines)
        self.assertTrue(default_markdown)
        self.assertEqual(plan_instructions[0], instructions[0])
        self.assertIn('"schema_version":"1"', plan_instructions[1])
        self.assertNotIn("Think harder", " ".join(plan_instructions + plan_guidelines))
        self.assertFalse(any("```bash" in item for item in plan_instructions + plan_guidelines))
        self.assertFalse(any(item.startswith("Don't worry too much") for item in plan_guidelines))
        self.assertFalse(plan_markdown)
        self.assertEqual(_output_tools("knowledge_plan"), [])
        self.assertIsInstance(_output_tools("default")[0], AssistantBetterShellTools)

    def test_client_sends_plan_mode_only_when_requested(self):
        with patch.object(rag_api, "_request", return_value={"status": "Agent initialized"}) as request:
            rag_api.initialize_assistant("test-model", output_mode="knowledge_plan")
            self.assertEqual(request.call_args.kwargs["data"]["output_mode"], "knowledge_plan")

            rag_api.initialize_assistant("test-model")
            self.assertNotIn("output_mode", request.call_args.kwargs["data"])

    def test_api_server_rebuilds_assistant_when_output_mode_changes(self):
        session = api_server.session_state
        session.reset_run()
        fake_assistant = SimpleNamespace(create_session=lambda: "plan-run")
        embedder_config = SimpleNamespace(model="embedder", provider="openai")

        try:
            with patch.object(api_server, "resolve_embedder_config", return_value=embedder_config), patch.object(
                api_server, "get_rag_assistant", return_value=fake_assistant
            ) as build_assistant:
                response = asyncio.run(
                    api_server.initialize_assistant(
                        llm_model="test-model",
                        embeddings_model="embedder",
                        embeddings_provider="openai",
                        output_mode="knowledge_plan",
                    )
                )

            self.assertEqual(response["status"], "Agent initialized")
            self.assertEqual(build_assistant.call_args.kwargs["output_mode"], "knowledge_plan")
            self.assertEqual(session.output_mode, "knowledge_plan")
            self.assertEqual(session.rag_assistant_run_id, "plan-run")
        finally:
            session.reset_run()


class KnowledgeAgentOnlyFlowTests(unittest.TestCase):
    def test_verification_is_fallback_evaluator_when_ground_truth_is_not_configured(self):
        cases = [
            (True, "completed_solved", True),
            (False, "completed_unsolved", False),
            (None, "verification_error", False),
        ]

        for verified, expected_outcome, expected_success in cases:
            with self.subTest(verified=verified):
                outcome, success, report = executor._finalize_knowledge_agent_only(
                    architecture_outcome="pending_ground_truth",
                    report={"verification": {"status": "verified" if verified is True else "failed" if verified is False else "verification_error"}},
                    ground_truth_configured=False,
                    ground_truth_passed=None,
                    verified=verified,
                )
                self.assertEqual(outcome, expected_outcome)
                self.assertEqual(success, expected_success)
                self.assertEqual(report["ground_truth"]["status"], "not_run")

    def test_pipeline_verifies_deterministic_transcript_and_writes_stage_artifacts(self):
        import main

        raw_response = json.dumps(_plan("kubectl get pods"))
        config = {"test-name": "unit-case", "verification-agent": {"model": "verifier"}}
        shell_result = _shell_result("kubectl get pods", stdout="pod/demo Running\n")
        shell = FakeShell([shell_result])

        class FakeAgentAPI:
            def __init__(self, *_args, **_kwargs):
                self.agentProperties = {"model": "knowledge"}
                self.response = ""

            def setupAgent(self):
                return None

        def run_api(_config, _context, api_agent):
            api_agent.response = raw_response
            return {"model": "knowledge", "duration_s": 0.01}

        def verify(_config, _context, verification_proxy, *, debug_metrics):
            self.assertIsNone(debug_metrics)
            transcript = json.loads(verification_proxy.response)
            self.assertEqual(transcript["actions"][0]["command"], "kubectl get pods")
            self.assertEqual(transcript["actions"][0]["result"]["stdout"], "pod/demo Running\n")
            self.assertIsNone(getattr(verification_proxy, "debugStatus", None))
            return {"model": "verifier"}, True

        with tempfile.TemporaryDirectory() as tmpdir, patch.object(main, "_load_runtime_config", return_value=config), patch.object(
            main, "setUpEnvironment"
        ), patch.object(main, "AgentAPI", FakeAgentAPI), patch.object(main, "_run_api_phase", side_effect=run_api), patch.object(
            main, "build_tool_kwargs", return_value={}
        ), patch.object(main, "BetterShellTools", return_value=shell), patch.object(
            main, "_run_verification_phase_after_debug", side_effect=verify
        ):
            result = main.knowledgeAgentOnly(
                "unused.json",
                runtime_context={"log_dir": tmpdir},
            )

            self.assertTrue(result["status"])
            self.assertIsNone(result["debug_metrics"])
            self.assertEqual(result["architecture_outcome"], "pending_ground_truth")
            self.assertEqual((Path(tmpdir) / "knowledge_response.raw.txt").read_text(), raw_response)
            self.assertTrue((Path(tmpdir) / "knowledge_plan.json").exists())
            self.assertEqual(result["knowledge_execution"]["execution"]["status"], "completed")

    def test_verification_still_runs_when_knowledge_agent_setup_fails(self):
        import main

        config = {"test-name": "unit-case", "api-agent": {"model": "knowledge"}}
        verifier_calls = []

        def verify(_config, _context, verification_proxy, *, debug_metrics):
            verifier_calls.append((verification_proxy.response, debug_metrics))
            return {"model": "verifier"}, None

        with tempfile.TemporaryDirectory() as tmpdir, patch.object(main, "_load_runtime_config", return_value=config), patch.object(
            main, "AgentAPI", side_effect=RuntimeError("agent construction failed")
        ), patch.object(main, "setUpEnvironment"), patch.object(
            main, "_run_verification_phase_after_debug", side_effect=verify
        ), patch.object(main, "store_metrics_entry"):
            result = main.knowledgeAgentOnly("unused.json", runtime_context={"log_dir": tmpdir})

        self.assertEqual(result["architecture_outcome"], "knowledge_generation_error")
        self.assertEqual(len(verifier_calls), 1)
        self.assertIsNone(verifier_calls[0][1])
        self.assertIn('"failure_stage": "knowledge_generation_error"', verifier_calls[0][0])
        self.assertIsNone(result["status"])

    def test_runner_still_runs_ground_truth_after_contract_failure_and_reports_both(self):
        import main

        report = {
            "technique": "knowledgeAgentOnly",
            "architecture_outcome": "contract_error",
            "knowledge_generation": {"status": "success"},
            "contract": {"status": "contract_error", "error": "not JSON"},
            "execution": {"status": "not_started", "actions": []},
            "verification": {"status": "verified", "error": None},
            "ground_truth": {"status": "pending"},
        }
        config = {"test-name": "unit-case", "ground-truth": {"checks": [{}]}}
        ground_truth_result = GroundTruthResult(test_name="unit-case", passed=True)

        with tempfile.TemporaryDirectory() as tmpdir, patch.object(
            executor, "get_config_path", return_value=Path(tmpdir) / "config.json"
        ), patch.object(executor, "load_config_with_overrides", return_value=config), patch.object(
            executor, "save_effective_config"
        ), patch.object(main, "knowledgeAgentOnly", return_value={
            "status": False,
            "api_metrics": {"model": "knowledge"},
            "debug_metrics": None,
            "verification_metrics": {"model": "verifier"},
            "architecture_outcome": "contract_error",
            "knowledge_execution": report,
        }), patch.object(
            executor, "run_ground_truth_checks", return_value=ground_truth_result
        ) as ground_truth_mock, patch.object(
            executor, "save_ground_truth_result"
        ), patch("teardown.cleanup_transient_k8s_resources"), patch("teardown.cleanup_test_pods"):
            result = executor.run_single_test(
                "unit-case",
                "knowledgeAgentOnly",
                {},
                Path(tmpdir),
                verbose=False,
            )

            ground_truth_mock.assert_called_once_with(config)
            self.assertTrue(result.ground_truth_passed)
            self.assertFalse(result.success)  # A malformed architecture plan remains a POC failure.
            self.assertEqual(result.architecture_outcome, "contract_error")
            self.assertIn("knowledge_execution.json", {path.name for path in result.log_dir.iterdir()})
            summary = executor.result_to_summary(result, "knowledgeAgentOnly", {}).to_dict()
            self.assertEqual(summary["architecture_outcome"], "contract_error")
            self.assertTrue(summary["ground_truth_passed"])


if __name__ == "__main__":
    unittest.main()
