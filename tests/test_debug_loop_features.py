import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
DEBUG_DIR = REPO_ROOT / "debug_assistant_latest"

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(DEBUG_DIR))

import debug_assistant_latest.main as legacy_main
import debug_assistant_latest.preflight as preflight
import debug_assistant_latest.utils as debug_utils
from debug_assistant_latest.dashboard import build_dashboard_data
from debug_assistant_latest.debug_agents import AgentDebugStepByStep, SingleAgent
from debug_assistant_latest.preflight import PreflightCheck
from debug_assistant_latest.result_interpreter import FailureCategory, interpret_run
from debug_assistant_latest.runner import TestResult, result_to_summary
from debug_assistant_latest.verification_base import parse_verification_status


FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"


def _response(*, content: str, model: str = "gpt-4o", input_tokens: int = 10, output_tokens: int = 5):
    total_tokens = input_tokens + output_tokens
    return types.SimpleNamespace(
        content=content,
        model=model,
        metrics={
            "input_tokens": [input_tokens],
            "output_tokens": [output_tokens],
            "total_tokens": [total_tokens],
        },
    )


def _write_run_fixture(
    root: Path,
    *,
    test_name: str = "wrong_port",
    status: str,
    error_message: str | None = None,
    verified: bool | None = None,
    ground_truth_passed: bool | None = None,
    stderr_text: str = "",
    stdout_text: str = "",
):
    root.mkdir(parents=True, exist_ok=True)
    test_dir = root / test_name
    test_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "test_name": test_name,
        "technique": "allStepsAtOnce",
        "status": status,
        "verified": verified,
        "debug_self_report": None,
        "ground_truth_passed": ground_truth_passed,
        "ground_truth_configured": ground_truth_passed is not None,
        "started_at": "2026-03-25T10:00:00",
        "finished_at": "2026-03-25T10:00:05",
        "duration_s": 5.0,
        "error_message": error_message,
        "error_context": None,
        "metrics": {},
        "config_overrides_applied": {},
    }
    (test_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (test_dir / "stderr.log").write_text(stderr_text, encoding="utf-8")
    (test_dir / "stdout.log").write_text(stdout_text, encoding="utf-8")

    aggregate = {
        "run_id": root.name,
        "generated_at": "2026-03-25T10:00:05",
        "run_config": {},
        "total_tests": 1,
        "passed": 1 if status == "PASS" else 0,
        "failed": 1 if status == "FAIL" else 0,
        "errors": 1 if status in ("ERROR", "TIMEOUT") else 0,
        "verified": 1 if verified is True else 0,
        "tests_with_verification": 1 if verified is not None else 0,
        "ground_truth_passed": 1 if ground_truth_passed is True else 0,
        "tests_with_ground_truth": 1 if ground_truth_passed is not None else 0,
        "pass_rate": 100.0 if status == "PASS" else 0.0,
        "verified_rate": 100.0 if verified is True else 0.0,
        "ground_truth_rate": 100.0 if ground_truth_passed is True else 0.0,
        "total_duration_s": 5.0,
        "wall_clock_s": 5.0,
        "total_cost": 0.0,
        "total_debug_cost": 0.0,
        "total_verification_cost": 0.0,
        "total_tokens": 0,
        "tests": [
            {
                "name": test_name,
                "status": status,
                "verified": verified,
                "ground_truth_passed": ground_truth_passed,
                "ground_truth_configured": ground_truth_passed is not None,
                "duration_s": 5.0,
                "error": error_message,
            }
        ],
        "failed_tests": [test_name] if status == "FAIL" else [],
        "error_tests": [test_name] if status in ("ERROR", "TIMEOUT") else [],
        "ground_truth_failed_tests": [test_name] if ground_truth_passed is False else [],
    }
    (root / "aggregate.json").write_text(json.dumps(aggregate, indent=2), encoding="utf-8")


class VerificationParsingTests(unittest.TestCase):
    def test_parse_verification_status_allows_relaxed_tokens(self):
        self.assertTrue(parse_verification_status("** <| VERIFIED |> **"))
        self.assertFalse(parse_verification_status("```text\n<| FAILED |>\n```"))
        self.assertIsNone(parse_verification_status("Result: <| VERIFICATION_ERROR |>"))

    def test_parse_verification_status_allows_labeled_plain_language_statuses(self):
        self.assertTrue(parse_verification_status("All checks passed.\nVERIFICATION STATUS: VERIFIED"))
        self.assertFalse(parse_verification_status("Curl still times out.\nResult: failed"))
        self.assertIsNone(parse_verification_status("Could not reach kubectl.\nConclusion: cannot verify"))

    def test_parse_verification_status_allows_standalone_final_status_line(self):
        self.assertTrue(parse_verification_status("The pod is Ready and curl returns 200.\nVERIFIED"))
        self.assertFalse(parse_verification_status("The service still times out.\nFAILED"))

    def test_parse_verification_status_ignores_unlabeled_body_mentions(self):
        self.assertIsNone(parse_verification_status("I checked whether the issue is verified, but need more data."))


class DebugAgentMetricsTests(unittest.TestCase):
    def test_step_by_step_aggregates_metrics_across_steps(self):
        config = {
            "test-name": "wrong_port",
            "knowledge-prompt": {"problem-desc": "desc"},
            "debug-agent": {"model": "gpt-4o", "instructions": [], "guidelines": []},
            "debug-prompt": {"additional-directions": ""},
            "test-directory": "C:/tmp/",
            "yaml-file-name": "wrong_port.yaml",
        }

        agent = AgentDebugStepByStep("debug-agent", config)
        agent.agent = MagicMock()
        agent.steps = ["step one", "step two"]
        agent.agent.run.side_effect = [
            _response(content="<|SOLVED|>", input_tokens=10, output_tokens=5),
            _response(content="<|SOLVED|>", input_tokens=20, output_tokens=15),
        ]

        metrics = agent.executeProblemSteps()

        self.assertEqual(metrics["input_tokens"], 30)
        self.assertEqual(metrics["output_tokens"], 20)
        self.assertEqual(metrics["total_tokens"], 50)
        self.assertEqual(metrics["task_status"], 1)

    def test_single_agent_returns_metrics(self):
        config = {
            "test-name": "wrong_port",
            "single-agent": {"model": "gpt-4o"},
            "debug-agent": {"instructions": [], "guidelines": []},
            "debug-prompt": {"additional-directions": ""},
            "test-directory": "C:/tmp/",
            "yaml-file-name": "wrong_port.yaml",
        }

        agent = SingleAgent("single-agent", config)
        agent.agent = MagicMock()
        agent.agent.run.return_value = _response(content="<|SOLVED|>", input_tokens=25, output_tokens=10)
        agent.prompt = "fix the pod"

        metrics = agent.askQuestion()

        self.assertEqual(metrics["input_tokens"], 25)
        self.assertEqual(metrics["output_tokens"], 10)
        self.assertEqual(metrics["total_tokens"], 35)
        self.assertEqual(metrics["task_status"], 1)
        self.assertTrue(agent.debugStatus)


class LegacyMainReturnShapeTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "test-name": "wrong_port",
            "api-agent": {"model": "gpt-4o"},
            "debug-agent": {"model": "gpt-4o", "instructions": [], "guidelines": []},
            "verification-agent": {"model": "gpt-4o"},
            "debug-prompt": {"additional-directions": ""},
            "knowledge-prompt": {"problem-desc": "desc"},
            "test-directory": "C:/tmp/",
            "yaml-file-name": "wrong_port.yaml",
        }

    def test_all_steps_at_once_returns_dict_shape(self):
        class FakeAPI:
            def __init__(self, agent_type, config):
                self.agentProperties = config["api-agent"]
                self.response = "fix it"

            def setupAgent(self):
                return None

            def askQuestion(self):
                return {
                    "test_case": "wrong_port",
                    "model": "gpt-4o",
                    "agent_type": "api",
                    "input_tokens": 2,
                    "output_tokens": 1,
                    "total_tokens": 3,
                    "task_status": 1,
                }

        class FakeDebug:
            def __init__(self, agent_type, config):
                self.agentProperties = config["debug-agent"]
                self.response = "done"
                self.debugStatus = True
                self._last_timeout = False
                self.agentAPIResponse = None

            def setupAgent(self):
                return None

            def askQuestion(self):
                return {
                    "test_case": "wrong_port",
                    "model": "gpt-4o",
                    "agent_type": "debug",
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "total_tokens": 15,
                    "task_status": 1,
                }

        class FakeVerification:
            def __init__(self, agent_type, config):
                self.agentProperties = config["verification-agent"]
                self.verificationStatus = True
                self.debugAgentResponse = None
                self._last_timeout = False

            def setupAgent(self):
                return None

            def askQuestion(self):
                return {
                    "test_case": "wrong_port",
                    "model": "gpt-4o",
                    "agent_type": "verification",
                    "input_tokens": 5,
                    "output_tokens": 5,
                    "total_tokens": 10,
                    "task_status": 1,
                    "duration_s": 0,
                    "cost": 0,
                }

        with patch.object(legacy_main, "_load_runtime_config", return_value=self.config), patch.object(
            legacy_main, "setUpEnvironment"
        ), patch.object(legacy_main, "printFinishMessage"), patch.object(
            legacy_main, "store_metrics_entry"
        ) as store_mock, patch.object(legacy_main, "AgentAPI", FakeAPI), patch.object(
            legacy_main, "AgentDebug", FakeDebug
        ), patch.object(
            legacy_main, "AgentVerification_v2", FakeVerification
        ):
            result = legacy_main.allStepsAtOnce("ignored.json")

        stored_agent_types = [call.args[1]["agent_type"] for call in store_mock.call_args_list]
        self.assertEqual(set(result.keys()), {"status", "api_metrics", "debug_metrics", "verification_metrics"})
        self.assertTrue(result["status"])
        self.assertIsInstance(result["api_metrics"], dict)
        self.assertIsInstance(result["debug_metrics"], dict)
        self.assertIsInstance(result["verification_metrics"], dict)
        self.assertIn("api", stored_agent_types)

    def test_all_steps_at_once_short_circuit_debug_still_runs_verification(self):
        class FakeAPI:
            def __init__(self, agent_type, config):
                self.agentProperties = config["api-agent"]
                self.response = "fix it"

            def setupAgent(self):
                return None

            def askQuestion(self):
                return {
                    "test_case": "wrong_port",
                    "model": "gpt-4o",
                    "agent_type": "api",
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "task_status": 1,
                }

        class FakeDebug:
            def __init__(self, agent_type, config):
                self.agentProperties = config["debug-agent"]
                self.response = "deterministic success"
                self.debugStatus = True
                self._last_timeout = False
                self.agentAPIResponse = None

            def setupAgent(self):
                return None

            def askQuestion(self):
                return {
                    "test_case": "wrong_port",
                    "model": "gpt-4o",
                    "agent_type": "debug",
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "task_status": 1,
                }

        class FakeVerification:
            instances = []

            def __init__(self, agent_type, config):
                self.agentProperties = config["verification-agent"]
                self.verificationStatus = True
                self.debugAgentResponse = None
                self._last_timeout = False
                FakeVerification.instances.append(self)

            def setupAgent(self):
                return None

            def askQuestion(self):
                return {
                    "test_case": "wrong_port",
                    "model": "gpt-4o",
                    "agent_type": "verification",
                    "input_tokens": 1,
                    "output_tokens": 1,
                    "total_tokens": 2,
                    "task_status": 1,
                    "duration_s": 0,
                    "cost": 0,
                }

        with patch.object(legacy_main, "_load_runtime_config", return_value=self.config), patch.object(
            legacy_main, "setUpEnvironment"
        ), patch.object(legacy_main, "printFinishMessage"), patch.object(
            legacy_main, "store_metrics_entry"
        ), patch.object(legacy_main, "AgentAPI", FakeAPI), patch.object(
            legacy_main, "AgentDebug", FakeDebug
        ), patch.object(
            legacy_main, "AgentVerification_v2", FakeVerification
        ):
            result = legacy_main.allStepsAtOnce("ignored.json")

        self.assertTrue(result["status"])
        self.assertEqual(len(FakeVerification.instances), 1)
        self.assertEqual(FakeVerification.instances[0].debugAgentResponse, "deterministic success")

    def test_step_by_step_returns_dict_shape(self):
        class FakeAPI:
            def __init__(self, agent_type, config):
                self.agentProperties = config["api-agent"]
                self.response = "fix it"

            def setupAgent(self):
                return None

            def askQuestion(self):
                return {
                    "test_case": "wrong_port",
                    "model": "gpt-4o",
                    "agent_type": "api",
                    "input_tokens": 2,
                    "output_tokens": 1,
                    "total_tokens": 3,
                    "task_status": 1,
                }

        class FakeDebug:
            def __init__(self, agent_type, config):
                self.agentProperties = config["debug-agent"]
                self.debugStatus = True
                self._last_timeout = False
                self.agentAPIResponse = None
                self.response = "debug trace"

            def setupAgent(self):
                return None

            def formProblemSolvingSteps(self):
                return None

            def executeProblemSteps(self):
                return {
                    "test_case": "wrong_port",
                    "model": "gpt-4o",
                    "agent_type": "debug",
                    "input_tokens": 3,
                    "output_tokens": 2,
                    "total_tokens": 5,
                    "task_status": 1,
                }

        class FakeVerification:
            instances = []
            verificationStatus = True

            def __init__(self, agent_type, config):
                FakeVerification.instances.append(self)

            def setupAgent(self):
                return None

            def askQuestion(self):
                return {
                    "test_case": "wrong_port",
                    "model": "gpt-4o",
                    "agent_type": "verification",
                    "input_tokens": 1,
                    "output_tokens": 1,
                    "total_tokens": 2,
                    "task_status": 1,
                }

        FakeVerification.instances.clear()

        with patch.object(legacy_main, "_load_runtime_config", return_value=self.config), patch.object(
            legacy_main, "setUpEnvironment"
        ), patch.object(legacy_main, "printFinishMessage"), patch.object(
            legacy_main, "store_metrics_entry"
        ) as store_mock, patch.object(legacy_main, "AgentAPI", FakeAPI), patch.object(
            legacy_main, "AgentDebugStepByStep", FakeDebug
        ), patch.object(legacy_main, "AgentVerification_v2", FakeVerification):
            result = legacy_main.stepByStep("ignored.json")

        stored_agent_types = [call.args[1]["agent_type"] for call in store_mock.call_args_list]
        self.assertEqual(set(result.keys()), {"status", "api_metrics", "debug_metrics", "verification_metrics"})
        self.assertTrue(result["status"])
        self.assertEqual(result["api_metrics"]["total_tokens"], 3)
        self.assertIsNotNone(result["verification_metrics"])
        self.assertEqual(result["debug_metrics"]["total_tokens"], 5)
        self.assertEqual(result["verification_metrics"]["total_tokens"], 2)
        self.assertEqual(len(FakeVerification.instances), 1)
        self.assertIn("api", stored_agent_types)

    def test_single_agent_returns_dict_shape(self):
        class FakeSingleAgent:
            def __init__(self, agent_type, config):
                self.agentProperties = {"model": "gpt-4o"}
                self.debugStatus = True
                self._last_timeout = False
                self.response = "single-agent trace"

            def setupAgent(self):
                return None

            def askQuestion(self):
                return {
                    "test_case": "wrong_port",
                    "model": "gpt-4o",
                    "agent_type": "debug",
                    "input_tokens": 7,
                    "output_tokens": 4,
                    "total_tokens": 11,
                    "task_status": 1,
                }

        class FakeVerification:
            instances = []
            verificationStatus = True

            def __init__(self, agent_type, config):
                FakeVerification.instances.append(self)

            def setupAgent(self):
                return None

            def askQuestion(self):
                return {
                    "test_case": "wrong_port",
                    "model": "gpt-4o",
                    "agent_type": "verification",
                    "input_tokens": 2,
                    "output_tokens": 1,
                    "total_tokens": 3,
                    "task_status": 1,
                }

        FakeVerification.instances.clear()

        with patch.object(legacy_main, "_load_runtime_config", return_value=self.config), patch.object(
            legacy_main, "setUpEnvironment"
        ), patch.object(legacy_main, "printFinishMessage"), patch.object(
            legacy_main, "store_metrics_entry"
        ), patch.object(legacy_main, "SingleAgent", FakeSingleAgent), patch.object(
            legacy_main, "AgentVerification_v2", FakeVerification
        ):
            result = legacy_main.singleAgentApproach("ignored.json")

        self.assertEqual(set(result.keys()), {"status", "debug_metrics", "verification_metrics"})
        self.assertTrue(result["status"])
        self.assertIsNotNone(result["verification_metrics"])
        self.assertEqual(result["debug_metrics"]["total_tokens"], 11)
        self.assertEqual(result["verification_metrics"]["total_tokens"], 3)
        self.assertEqual(len(FakeVerification.instances), 1)


class PreflightTests(unittest.TestCase):
    def test_db_connectivity_failure_is_reported(self):
        with patch.object(preflight, "create_engine", side_effect=RuntimeError("bad db")):
            check = preflight._check_db_connectivity()

        self.assertFalse(check.passed)
        self.assertIn("bad db", check.message)

    def test_rag_api_failure_is_reported(self):
        with patch.object(preflight.requests, "get", side_effect=requests.RequestException("down")):
            check = preflight._check_rag_api("http://127.0.0.1:8000")

        self.assertFalse(check.passed)
        self.assertIn("down", check.message)

    def test_missing_kubectl_is_reported(self):
        with patch.object(preflight.subprocess, "run", side_effect=FileNotFoundError()):
            check = preflight._check_kubectl()

        self.assertFalse(check.passed)
        self.assertIn("not installed", check.message)

    def test_run_preflight_returns_structured_json(self):
        checks = {
            "_check_python_imports": PreflightCheck("python_imports", True, "ok"),
            "_check_pytest_available": PreflightCheck("pytest", True, "ok"),
            "_check_db_connectivity": PreflightCheck("db_connectivity", True, "ok"),
            "_check_rag_api": PreflightCheck("rag_api", True, "ok"),
            "_check_kubectl": PreflightCheck("kubectl", True, "ok"),
            "_check_docker_engine": PreflightCheck("docker_engine", True, "ok"),
            "_check_minikube_status": PreflightCheck("minikube_status", True, "ok"),
            "_check_cluster_access": PreflightCheck("cluster_access", True, "ok"),
            "_check_config_validity": PreflightCheck("config_validity", True, "ok"),
        }

        with patch.object(preflight, "_check_python_imports", return_value=checks["_check_python_imports"]), patch.object(
            preflight, "_check_pytest_available", return_value=checks["_check_pytest_available"]
        ), patch.object(preflight, "_check_db_connectivity", return_value=checks["_check_db_connectivity"]), patch.object(
            preflight, "_check_rag_api", return_value=checks["_check_rag_api"]
        ), patch.object(preflight, "_check_kubectl", return_value=checks["_check_kubectl"]), patch.object(
            preflight, "_check_docker_engine", return_value=checks["_check_docker_engine"]
        ), patch.object(
            preflight, "_check_minikube_status", return_value=checks["_check_minikube_status"]
        ), patch.object(
            preflight, "_check_cluster_access", return_value=checks["_check_cluster_access"]
        ), patch.object(
            preflight, "_check_config_validity", return_value=checks["_check_config_validity"]
        ):
            result = preflight.run_preflight(test_names=["wrong_port"], overrides={}, rag_api_url="http://127.0.0.1:8000")

        self.assertTrue(result["passed"])
        self.assertEqual(
            [check["name"] for check in result["checks"]],
            [
                "python_imports",
                "pytest",
                "db_connectivity",
                "rag_api",
                "kubectl",
                "docker_engine",
                "minikube_status",
                "cluster_access",
                "config_validity",
            ],
        )


class SetupLocalImageValidationTests(unittest.TestCase):
    def _write_case(self, tmpdir: str, *, image_pull_policy: str = "Never"):
        case_dir = Path(tmpdir)
        manifest = case_dir / "case.yaml"
        manifest.write_text(
            "\n".join(
                [
                    "apiVersion: v1",
                    "kind: Pod",
                    "metadata:",
                    "  name: local-image-pod",
                    "spec:",
                    "  containers:",
                    "  - name: app",
                    "    image: local-app:latest",
                    f"    imagePullPolicy: {image_pull_policy}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return {
            "test-directory": str(case_dir),
            "yaml-file-name": "case.yaml",
            "relevant-files": {"deployment": ["case.yaml"]},
            "minikube-profile": "test-profile",
        }

    def test_validate_local_images_available_passes_when_image_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = self._write_case(tmpdir)
            completed = subprocess_result(0, stdout="docker.io/library/local-app:latest\n")

            with patch.object(debug_utils.subprocess, "run", return_value=completed) as run_mock:
                debug_utils.validate_local_images_available(config, attempts=1, delay_s=0)

            run_mock.assert_called_once()
            self.assertEqual(run_mock.call_args.args[0], ["minikube", "-p", "test-profile", "image", "ls"])

    def test_validate_local_images_available_fails_when_image_missing_after_retries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = self._write_case(tmpdir)
            completed = subprocess_result(0, stdout="docker.io/library/other-app:latest\n")

            with patch.object(debug_utils.subprocess, "run", return_value=completed) as run_mock:
                with self.assertRaisesRegex(RuntimeError, "local-app:latest"):
                    debug_utils.validate_local_images_available(config, attempts=2, delay_s=0)

            self.assertEqual(run_mock.call_count, 2)

    def test_validate_local_images_available_skips_non_never_pull_images(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = self._write_case(tmpdir, image_pull_policy="IfNotPresent")

            with patch.object(debug_utils.subprocess, "run") as run_mock:
                debug_utils.validate_local_images_available(config, attempts=1, delay_s=0)

            run_mock.assert_not_called()

    def test_set_up_environment_runs_setup_then_validates(self):
        config = {
            "setup-commands": ["echo setup"],
            "test-directory": str(Path.cwd()),
            "yaml-file-name": "",
        }

        with patch.object(debug_utils.subprocess, "run") as run_mock, patch.object(
            debug_utils, "validate_local_images_available"
        ) as validate_mock:
            debug_utils.setUpEnvironment(config)

        run_mock.assert_called_once()
        validate_mock.assert_called_once()

    def test_troubleshooting_minikube_image_builds_use_context_relative_dockerfile(self):
        bad_commands = []
        for config_path in (DEBUG_DIR / "troubleshooting").glob("*/config_step.json"):
            config = json.loads(config_path.read_text(encoding="utf-8"))
            for command in config.get("setup-commands", []):
                if "minikube" not in command or " image build " not in command:
                    continue
                minikube_branch = command.split("; else ", 1)[0]
                if " image build -t " not in minikube_branch or ":latest -f Dockerfile " not in minikube_branch:
                    bad_commands.append(f"{config_path}: missing explicit latest tag or context-relative Dockerfile")
                if " -f debug_assistant_latest/troubleshooting/" in minikube_branch:
                    bad_commands.append(f"{config_path}: minikube build uses repo-root Dockerfile path")

        self.assertEqual([], bad_commands)


def subprocess_result(returncode=0, stdout="", stderr=""):
    return types.SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


class ResultInterpreterTests(unittest.TestCase):
    def test_static_fixtures_cover_pass_gt_fail_and_timeout(self):
        cases = [
            ("run_pass", "PASS", FailureCategory.UNKNOWN),
            ("run_gt_fail", "FAIL", FailureCategory.GROUND_TRUTH_FAIL),
            ("run_timeout", "TIMEOUT", FailureCategory.TIMEOUT),
        ]

        for fixture_name, expected_status, expected_category in cases:
            with self.subTest(fixture_name=fixture_name):
                diagnosis = interpret_run(FIXTURES_DIR / fixture_name)
                self.assertEqual(diagnosis.status, expected_status)
                self.assertEqual(diagnosis.category, expected_category)

    def test_interpret_run_covers_all_failure_categories(self):
        scenarios = {
            FailureCategory.IMPORT_ERROR: {
                "status": "ERROR",
                "error_message": "ModuleNotFoundError: No module named 'openai'",
                "stderr_text": "ModuleNotFoundError: No module named 'openai'\n",
            },
            FailureCategory.LLM_STALL: {
                "status": "ERROR",
                "error_message": "debug agent timed out",
                "stderr_text": "debug agent timed out\n",
            },
            FailureCategory.VERIFICATION_MISMATCH: {
                "status": "FAIL",
                "verified": False,
                "error_message": "verification said failed",
            },
            FailureCategory.TEARDOWN_FAIL: {
                "status": "ERROR",
                "stderr_text": "[WARNING] Teardown failed for wrong_port: cleanup boom\n",
            },
            FailureCategory.CONFIG_ERROR: {
                "status": "ERROR",
                "error_message": "Unknown test case: wrong_port",
            },
            FailureCategory.K8S_ERROR: {
                "status": "ERROR",
                "stderr_text": "CrashLoopBackOff while starting pod\n",
            },
            FailureCategory.UNKNOWN: {
                "status": "ERROR",
                "error_message": "mystery failure",
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            for category, kwargs in scenarios.items():
                run_dir = Path(tmpdir) / category.value.lower()
                _write_run_fixture(run_dir, **kwargs)
                diagnosis = interpret_run(run_dir)
                self.assertEqual(diagnosis.category, category)


class RunnerSummaryTests(unittest.TestCase):
    def test_result_to_summary_includes_error_context_excerpt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "wrong_port"
            log_dir.mkdir()
            lines = [f"line {index}" for index in range(25)]
            (log_dir / "stderr.log").write_text("\n".join(lines), encoding="utf-8")

            result = TestResult(
                test_name="wrong_port",
                success=False,
                verified=None,
                debug_self_report=None,
                duration_s=1.0,
                error="Timeout: agent execution exceeded 480s",
                metrics={"debug": {"task_status": -1}},
                log_dir=log_dir,
                started_at="2026-01-01T00:00:00",
                finished_at="2026-01-01T00:00:01",
            )

            summary = result_to_summary(result, "stepByStep", {})

        self.assertEqual(summary.status, "TIMEOUT")
        self.assertEqual(summary.error_context, "\n".join(lines[:20]))


class DashboardTests(unittest.TestCase):
    def test_dashboard_summarizes_complete_runs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runs_root = Path(tmpdir)
            _write_run_fixture(runs_root / "run-1", status="PASS", verified=True, ground_truth_passed=True)
            _write_run_fixture(
                runs_root / "run-2",
                status="ERROR",
                error_message="Timeout: exceeded 600s",
                stderr_text="[TIMEOUT] Test exceeded 600s and was terminated.\n",
            )

            data = build_dashboard_data(runs_root)

        self.assertEqual(data["complete_runs"], 2)
        self.assertEqual(data["total_tests"], 2)
        self.assertEqual(data["pass_rate"], 50.0)
        self.assertEqual(data["most_failing_tests"][0][0], "wrong_port")


if __name__ == "__main__":
    unittest.main()
