import asyncio
import json
import argparse
import os
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import inspect

import requests
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
DEBUG_DIR = REPO_ROOT / "debug_assistant_latest"

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(DEBUG_DIR))

if not hasattr(inspect, "getargspec"):
    inspect.getargspec = inspect.getfullargspec

from debug_assistant_latest.config_merge import (
    apply_runner_llm_env_defaults,
    load_config_with_overrides,
    merge_config_overrides,
)
from debug_assistant_latest.ground_truth import (
    CheckStatus,
    GroundTruthResult,
    execute_command,
    run_all_checks,
    run_check,
    save_ground_truth_result,
    validate_ground_truth_config,
)
from debug_assistant_latest.report import AgentMetrics, TestSummary, generate_aggregate_report, load_test_summary
from debug_assistant_latest.cli import (
    _apply_repeat_overrides,
    _build_repeat_payload,
    _run_repeat_queue,
    _verification_temperature_issues,
    main as cli_main,
)
from debug_assistant_latest.executor import (
    TestResult,
    _best_effort_configure_console_streams,
    _extract_execution_result,
    _safe_flush_stream,
    _safe_write_to_stream,
    cmd_run_single,
    result_to_summary,
)
from debug_assistant_latest import executor
from debug_assistant_latest import teardown
from debug_assistant_latest.test_discovery import list_test_cases
import assistant
import api_server
from api_server_support import SessionState, knowledge_table_name
import api_server_support
import runtime_config
import timeout_helpers
import debug_assistant_latest.agent_helpers as agent_helpers
import debug_assistant_latest.prompt_helpers as prompt_helpers
from debug_assistant_latest import rag_api
from debug_assistant_latest import rag_server_config
from debug_assistant_latest.better_shell import BetterShellTools
from debug_assistant_latest.api_agents import AgentAPI
from runtime_progress import BlockedCommandThresholdError, ProgressWriter
from debug_assistant_latest.verification_base import parse_verification_status, print_verification_status
from debug_assistant_latest.verification_agents import AgentVerification_v2


class FakeEmbedder:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.preflight_calls = []

    def get_embedding_and_usage(self, text):
        self.preflight_calls.append(text)
        return [0.1, 0.2], {"total_tokens": 1}

    def __getitem__(self, key):
        return self.kwargs[key]


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

    def test_apply_runner_llm_env_defaults_use_ollama_fills_unset_fields(self):
        import argparse

        args = argparse.Namespace(
            api_model=None,
            debug_model=None,
            verification_model=None,
            embedder=None,
            embedder_provider=None,
        )
        with patch.dict(
            os.environ,
            {
                "KUBELLM_USE_OLLAMA": "1",
                "KUBELLM_OLLAMA_CHAT_MODEL": "llama3.2:3b",
                "KUBELLM_OLLAMA_EMBEDDER": "nomic-embed-text",
            },
            clear=False,
        ):
            apply_runner_llm_env_defaults(args)
        self.assertEqual(args.api_model, "llama3.2:3b")
        self.assertEqual(args.debug_model, "llama3.2:3b")
        self.assertEqual(args.verification_model, "llama3.2:3b")
        self.assertEqual(args.embedder, "nomic-embed-text")
        self.assertEqual(args.embedder_provider, "ollama")

    def test_apply_runner_llm_env_defaults_cli_wins_over_use_ollama(self):
        import argparse

        args = argparse.Namespace(
            api_model="custom-api",
            debug_model=None,
            verification_model=None,
            embedder=None,
            embedder_provider=None,
        )
        with patch.dict(
            os.environ,
            {
                "KUBELLM_USE_OLLAMA": "1",
                "KUBELLM_OLLAMA_CHAT_MODEL": "llama3.2:3b",
                "KUBELLM_OLLAMA_EMBEDDER": "nomic-embed-text",
            },
            clear=False,
        ):
            apply_runner_llm_env_defaults(args)
        self.assertEqual(args.api_model, "custom-api")
        self.assertEqual(args.debug_model, "llama3.2:3b")

    def test_apply_runner_llm_env_defaults_per_field_env(self):
        import argparse

        args = argparse.Namespace(
            api_model=None,
            debug_model=None,
            verification_model=None,
            embedder=None,
            embedder_provider=None,
        )
        with patch.dict(
            os.environ,
            {
                "KUBELLM_USE_OLLAMA": "",
                "KUBELLM_DEBUG_MODEL": "mistral:7b",
                "KUBELLM_EMBEDDER_PROVIDER": "ollama",
            },
            clear=False,
        ):
            apply_runner_llm_env_defaults(args)
        self.assertEqual(args.debug_model, "mistral:7b")
        self.assertEqual(args.embedder_provider, "ollama")


class RagServerConfigTests(unittest.TestCase):
    def test_resolve_client_base_url_defaults_to_shared_local_port(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(rag_server_config.resolve_client_base_url(), "http://127.0.0.1:18000")

    def test_resolve_client_base_url_uses_server_port_when_url_unset(self):
        with patch.dict(os.environ, {"RAG_SERVER_PORT": "8123"}, clear=True):
            self.assertEqual(rag_server_config.resolve_client_base_url(), "http://127.0.0.1:8123")

    def test_resolve_client_base_url_prefers_explicit_url(self):
        with patch.dict(os.environ, {"RAG_API_URL": "http://env-host:9000"}, clear=True):
            self.assertEqual(
                rag_server_config.resolve_client_base_url("http://cli-host:7000/"),
                "http://cli-host:7000",
            )


class RuntimeConfigTests(unittest.TestCase):
    def test_build_chat_model_openai_path_skips_gemini_and_ollama_imports(self):
        imported_modules = []

        def fake_import(module_name):
            imported_modules.append(module_name)
            if module_name == "phi.model.openai":
                return types.SimpleNamespace(OpenAIChat=lambda **kwargs: kwargs)
            if module_name in {"phi.model.google", "phi.model.ollama"}:
                raise AssertionError(f"Unexpected import: {module_name}")
            raise AssertionError(f"Unexpected module import request: {module_name}")

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False), patch(
            "runtime_config.importlib.import_module", side_effect=fake_import
        ):
            model = runtime_config.build_chat_model("gpt-5-mini", temperature=0.4)

        self.assertEqual(model["id"], "gpt-5-mini")
        self.assertEqual(model["temperature"], 0.4)
        self.assertEqual(imported_modules, ["phi.model.openai"])

    def test_build_chat_model_ollama_path_skips_openai_and_gemini_imports(self):
        imported_modules = []

        def fake_import(module_name):
            imported_modules.append(module_name)
            if module_name == "phi.model.ollama":
                return types.SimpleNamespace(Ollama=lambda **kwargs: kwargs)
            if module_name in {"phi.model.openai", "phi.model.google"}:
                raise AssertionError(f"Unexpected import: {module_name}")
            raise AssertionError(f"Unexpected module import request: {module_name}")

        with patch.dict(os.environ, {}, clear=True), patch(
            "runtime_config.importlib.import_module", side_effect=fake_import
        ):
            model = runtime_config.build_chat_model("llama3.1:8b")

        self.assertEqual(model["id"], "llama3.1:8b")
        self.assertEqual(imported_modules, ["phi.model.ollama"])

    def test_build_embedder_openai_path_skips_ollama_imports(self):
        imported_modules = []

        def fake_import(module_name):
            imported_modules.append(module_name)
            if module_name == "phi.embedder.openai":
                return types.SimpleNamespace(OpenAIEmbedder=lambda **kwargs: kwargs)
            if module_name == "phi.embedder.ollama":
                raise AssertionError(f"Unexpected import: {module_name}")
            raise AssertionError(f"Unexpected module import request: {module_name}")

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False), patch(
            "runtime_config.importlib.import_module", side_effect=fake_import
        ):
            embedder = runtime_config.build_embedder("text-embedding-3-small")

        self.assertEqual(embedder["model"], "text-embedding-3-small")
        self.assertEqual(embedder["dimensions"], 1536)
        self.assertEqual(imported_modules, ["phi.embedder.openai"])

    def test_build_resolved_embedder_keeps_successful_openai(self):
        imported_modules = []

        def fake_import(module_name):
            imported_modules.append(module_name)
            if module_name == "phi.embedder.openai":
                return types.SimpleNamespace(OpenAIEmbedder=FakeEmbedder)
            if module_name == "phi.embedder.ollama":
                raise AssertionError(f"Unexpected import: {module_name}")
            raise AssertionError(f"Unexpected module import request: {module_name}")

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False), patch(
            "runtime_config.importlib.import_module", side_effect=fake_import
        ):
            resolved = runtime_config.build_resolved_embedder("text-embedding-3-small", provider="openai")

        self.assertEqual((resolved.config.provider, resolved.config.model), ("openai", "text-embedding-3-small"))
        self.assertEqual(resolved.embedder.preflight_calls, [runtime_config.EMBEDDER_PREFLIGHT_TEXT])
        self.assertEqual(imported_modules, ["phi.embedder.openai"])

    def test_build_resolved_embedder_surfaces_openai_quota_error_without_ollama_imports(self):
        imported_modules = []

        class QuotaEmbedder(FakeEmbedder):
            def get_embedding_and_usage(self, text):
                raise RuntimeError("Error code: 429 - insufficient_quota")

        def fake_import(module_name):
            imported_modules.append(module_name)
            if module_name == "phi.embedder.openai":
                return types.SimpleNamespace(OpenAIEmbedder=QuotaEmbedder)
            if module_name == "phi.embedder.ollama":
                raise AssertionError(f"Unexpected import: {module_name}")
            raise AssertionError(f"Unexpected module import request: {module_name}")

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False), patch(
            "runtime_config.importlib.import_module", side_effect=fake_import
        ):
            with self.assertRaisesRegex(RuntimeError, "insufficient_quota"):
                runtime_config.build_resolved_embedder("text-embedding-3-small", provider="openai")

        self.assertEqual(imported_modules, ["phi.embedder.openai"])

    def test_build_resolved_embedder_does_not_hide_non_quota_errors(self):
        class AuthErrorEmbedder(FakeEmbedder):
            def get_embedding_and_usage(self, text):
                raise RuntimeError("401 invalid api key")

        def fake_import(module_name):
            if module_name == "phi.embedder.openai":
                return types.SimpleNamespace(OpenAIEmbedder=AuthErrorEmbedder)
            if module_name == "phi.embedder.ollama":
                raise AssertionError(f"Unexpected import: {module_name}")
            raise AssertionError(f"Unexpected module import request: {module_name}")

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False), patch(
            "runtime_config.importlib.import_module", side_effect=fake_import
        ):
            with self.assertRaisesRegex(RuntimeError, "401 invalid api key"):
                runtime_config.build_resolved_embedder("text-embedding-3-small", provider="openai")

    def test_all_troubleshooting_openai_embedder_configs_resolve_to_openai(self):
        config_paths = sorted((DEBUG_DIR / "troubleshooting").glob("*/config_step.json"))
        openai_embedder_configs = []
        for config_path in config_paths:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            api_agent = config.get("api-agent", {})
            if api_agent.get("embedder-provider") == "openai":
                openai_embedder_configs.append((config_path, api_agent.get("embedder")))

        self.assertGreater(len(openai_embedder_configs), 0)
        for config_path, embedder_model in openai_embedder_configs:
            with self.subTest(config=config_path.name):
                resolved = runtime_config.resolve_embedder_config(embedder_model, provider="openai")
                self.assertEqual((resolved.provider, resolved.model), ("openai", embedder_model))

    def test_resolve_embedder_config_defaults_by_chat_provider(self):
        openai_config = runtime_config.resolve_embedder_config(chat_model_name="gpt-5-mini")
        ollama_config = runtime_config.resolve_embedder_config(chat_model_name="llama3.1:8b")

        self.assertEqual((openai_config.provider, openai_config.model), ("openai", "text-embedding-3-small"))
        self.assertEqual((ollama_config.provider, ollama_config.model), ("ollama", "nomic-embed-text"))

    def test_resolve_embedder_config_requires_explicit_provider_for_gemini(self):
        with self.assertRaisesRegex(ValueError, "Gemini"):
            runtime_config.resolve_embedder_config(chat_model_name="gemini-1.5-pro")

    def test_db_url_uses_psycopg2_driver_consistently(self):
        self.assertEqual(runtime_config.DB_URL, runtime_config.DB_URL_PSYCOPG2)
        self.assertTrue(runtime_config.DB_URL.startswith("postgresql+psycopg2://"))

    def test_resolve_db_url_uses_workspace_override(self):
        override = "postgresql+psycopg2://ai:ai@localhost:5533/ai"
        with patch.dict(os.environ, {runtime_config.DB_URL_ENV: override}):
            self.assertEqual(runtime_config.resolve_db_url(), override)

    def test_resolve_db_url_uses_default_for_empty_override(self):
        with patch.dict(os.environ, {runtime_config.DB_URL_ENV: "  "}):
            self.assertEqual(runtime_config.resolve_db_url(), runtime_config.DEFAULT_DB_URL_PSYCOPG2)


class TimeoutHelperTests(unittest.TestCase):
    def test_timeout_unblocks_caller_on_windows(self):
        def target():
            time.sleep(0.2)
            return "ok"

        fake_module = types.SimpleNamespace(timeout=MagicMock(), TimeoutError=RuntimeError)

        with patch.object(timeout_helpers, "timeout_decorator", fake_module), patch("timeout_helpers.os.name", "nt"):
            decorated = timeout_helpers.timeout(0.01)(target)
            started = time.perf_counter()
            with self.assertRaises(timeout_helpers.TimeoutError):
                decorated()
            elapsed = time.perf_counter() - started

        self.assertLess(elapsed, 0.1)

    def test_timeout_uses_signals_off_windows(self):
        fake_decorator = object()
        fake_timeout = MagicMock(return_value=fake_decorator)
        fake_module = types.SimpleNamespace(timeout=fake_timeout, TimeoutError=RuntimeError)

        with patch.object(timeout_helpers, "timeout_decorator", fake_module), patch("timeout_helpers.os.name", "posix"):
            result = timeout_helpers.timeout(480)

        fake_timeout.assert_called_once_with(480, use_signals=True)
        self.assertIs(result, fake_decorator)


class AgentHelperTests(unittest.TestCase):
    def test_build_llm_agent_disables_debug_logs_by_default_on_windows(self):
        fake_factory = MagicMock(return_value="agent")

        with patch.object(agent_helpers, "llmAgent", fake_factory), patch.object(
            agent_helpers, "build_model", return_value="model"
        ), patch.object(agent_helpers, "BetterShellTools", return_value="tool"), patch(
            "debug_assistant_latest.agent_helpers.os.name", "nt"
        ), patch.dict(os.environ, {}, clear=False):
            result = agent_helpers.build_llm_agent("gpt-5-mini", ["i"], ["g"])

        self.assertEqual(result, "agent")
        self.assertFalse(fake_factory.call_args.kwargs["debug_mode"])
        self.assertFalse(fake_factory.call_args.kwargs["show_tool_calls"])

    def test_build_llm_agent_allows_windows_debug_override(self):
        fake_factory = MagicMock(return_value="agent")

        with patch.object(agent_helpers, "llmAgent", fake_factory), patch.object(
            agent_helpers, "build_model", return_value="model"
        ), patch.object(agent_helpers, "BetterShellTools", return_value="tool"), patch(
            "debug_assistant_latest.agent_helpers.os.name", "nt"
        ), patch.dict(os.environ, {"KUBELLM_AGENT_DEBUG_LOGS": "1"}, clear=False):
            agent_helpers.build_llm_agent("gpt-5-mini", ["i"], ["g"])

        self.assertTrue(fake_factory.call_args.kwargs["debug_mode"])
        self.assertTrue(fake_factory.call_args.kwargs["show_tool_calls"])


class PromptHelperTests(unittest.TestCase):
    def _load_troubleshooting_config(self, test_name):
        case_dir = DEBUG_DIR / "troubleshooting" / test_name
        config = json.loads((case_dir / "config_step.json").read_text(encoding="utf-8"))
        config["test-directory"] = str(case_dir) + "/"
        return config

    def test_get_tool_usage_rules_adds_windows_guidance(self):
        with patch("debug_assistant_latest.prompt_helpers.os.name", "nt"):
            rules = prompt_helpers.get_tool_usage_rules()

        self.assertIn("PowerShell-compatible", rules)
        self.assertIn("ownerReferences[0]", rules)
        self.assertIn("kubectl port-forward", rules)

    def test_get_tool_usage_rules_includes_generic_reachability_guidance(self):
        with patch("debug_assistant_latest.prompt_helpers.os.name", "posix"):
            rules = prompt_helpers.get_tool_usage_rules()

        self.assertIn("kubectl port-forward", rules)
        self.assertIn("background verification", rules)
        self.assertIn("kubectl logs -f", rules)
        self.assertIn("kubectl get -w", rules)
        self.assertIn("if a Service exists", rules)
        self.assertIn("kubectl exec", rules)

    def test_api_prompt_includes_generic_tool_usage_rules_on_linux(self):
        config = {
            "api-agent": {},
            "knowledge-prompt": {
                "problem-desc": "pod cannot be reached",
                "system-prompt": "Give specific commands.",
            },
            "test-directory": str(DEBUG_DIR / "troubleshooting" / "wrong_port"),
            "relevant-files": {
                "deployment": [],
                "application": [],
                "service": [],
                "dockerfile": False,
            },
        }
        agent = AgentAPI("api-agent", config)

        with patch("debug_assistant_latest.prompt_helpers.os.name", "posix"):
            agent.preparePrompt()

        self.assertIn("Do not use `kubectl port-forward`", agent.prompt)
        self.assertIn("if a Service exists", agent.prompt)
        self.assertIn("kubectl exec", agent.prompt)

    def test_api_prompt_includes_global_durable_fix_guidance_without_ground_truth_leakage(self):
        config = {
            "api-agent": {},
            "knowledge-prompt": {
                "problem-desc": "pod cannot be reached",
                "system-prompt": "Give specific commands.",
            },
            "test-directory": str(DEBUG_DIR / "troubleshooting" / "wrong_port"),
            "relevant-files": {
                "deployment": [],
                "application": [],
                "service": [],
                "dockerfile": False,
            },
        }
        agent = AgentAPI("api-agent", config)

        agent.preparePrompt()

        self.assertIn("Prefer durable fixes", agent.prompt)
        self.assertIn("running container", agent.prompt)
        self.assertIn("source-of-truth configuration", agent.prompt)
        self.assertIn("Do not skip a visible source/config mismatch", agent.prompt)
        self.assertNotIn("ground-truth", agent.prompt)
        self.assertNotIn("port_aligned", agent.prompt)

    def test_api_prompt_includes_profile_generic_minikube_image_guidance(self):
        config = {
            "api-agent": {},
            "knowledge-prompt": {
                "problem-desc": "pod cannot be reached",
                "system-prompt": "Give specific commands.",
            },
            "test-directory": str(DEBUG_DIR / "troubleshooting" / "wrong_port"),
            "relevant-files": {
                "deployment": [],
                "application": [],
                "service": [],
                "dockerfile": False,
            },
        }
        agent = AgentAPI("api-agent", config)

        agent.preparePrompt()

        self.assertIn("Minikube Image Guidance", agent.prompt)
        self.assertIn("MINIKUBE_PROFILE", agent.prompt)
        self.assertIn('minikube -p "$PROFILE" image build', agent.prompt)
        self.assertIn("Do not recommend `docker push`", agent.prompt)
        self.assertNotIn("plama", agent.prompt)

    def test_no_service_deployment_gets_verification_guidance(self):
        guidance = prompt_helpers.get_case_specific_guidance(
            self._load_troubleshooting_config("wrong_port"), phase="verification"
        )

        self.assertIn("intentionally has no Kubernetes Service", guidance)
        self.assertIn("Absence of a Service is not a failure", guidance)
        self.assertIn("old ReplicaSet pods in Terminating state are acceptable", guidance)
        self.assertIn("current Deployment pod template", guidance)

    def test_no_service_pod_variant_gets_no_service_guidance_only(self):
        guidance = prompt_helpers.get_case_specific_guidance(
            self._load_troubleshooting_config("wrong_port_9090"), phase="verification"
        )

        self.assertIn("intentionally has no Kubernetes Service", guidance)
        self.assertIn("Service endpoints", guidance)
        self.assertNotIn("DEPLOYMENT ROLLOUT", guidance)

    def test_unrelated_case_gets_no_case_specific_guidance(self):
        config = {"test-name": "port_mismatch", "relevant-files": {"service": ["service.yaml"]}}

        self.assertEqual(prompt_helpers.get_case_specific_guidance(config, phase="verification"), "")

    def test_case_specific_guidance_is_verification_only(self):
        config = self._load_troubleshooting_config("wrong_port")

        self.assertEqual(prompt_helpers.get_case_specific_guidance(config), "")

    def test_verification_prompt_includes_scenario_guidance(self):
        config = self._load_troubleshooting_config("wrong_port")
        agent = AgentVerification_v2("verification-agent", config)
        captured = {}

        agent.preparePrompt()

        class FakeAgent:
            def run(self, prompt):
                captured["prompt"] = prompt
                return types.SimpleNamespace(content="<|VERIFIED|>", metrics={}, model="fake")

        agent.agent = FakeAgent()
        agent.askQuestion()
        prompt = captured["prompt"]

        self.assertIn("configured access path for this scenario is reachable", prompt)
        self.assertIn("Only if a Service manifest exists", prompt)
        self.assertIn("Absence of a Service is not a failure", prompt)
        self.assertIn("old ReplicaSet pods in Terminating state are acceptable", prompt)


class AgentAPIMetricsTests(unittest.TestCase):
    def test_ask_question_returns_api_metrics_and_preserves_response_text(self):
        config = {
            "test-name": "wrong_port",
            "api-agent": {"model": "gpt-4o"},
        }
        agent = AgentAPI("api-agent", config)
        agent.prompt = "diagnose"

        with patch(
            "debug_assistant_latest.api_agents.ask_question",
            return_value={
                "response": "fix the manifest",
                "metrics": {
                    "model": "gpt-4o-mini",
                    "input_tokens": 12,
                    "output_tokens": 7,
                    "total_tokens": 19,
                },
            },
        ):
            metrics = agent.askQuestion()

        self.assertEqual(agent.response, "fix the manifest")
        self.assertEqual(
            metrics,
            {
                "test_case": "wrong_port",
                "model": "gpt-4o-mini",
                "agent_type": "api",
                "input_tokens": 12,
                "output_tokens": 7,
                "total_tokens": 19,
                "task_status": 1,
            },
        )

    def test_ask_question_defaults_missing_usage_to_zero(self):
        config = {
            "test-name": "wrong_port",
            "api-agent": {"model": "gpt-4o"},
        }
        agent = AgentAPI("api-agent", config)
        agent.prompt = "diagnose"

        with patch(
            "debug_assistant_latest.api_agents.ask_question",
            return_value={"response": "fix the manifest"},
        ):
            metrics = agent.askQuestion()

        self.assertEqual(agent.response, "fix the manifest")
        self.assertEqual(metrics["model"], "gpt-4o")
        self.assertEqual(metrics["input_tokens"], 0)
        self.assertEqual(metrics["output_tokens"], 0)
        self.assertEqual(metrics["total_tokens"], 0)
        self.assertEqual(metrics["agent_type"], "api")


class BetterShellTests(unittest.TestCase):
    def test_run_shell_command_exposes_string_command_schema(self):
        tool = BetterShellTools()

        parameters = tool.functions["run_shell_command"].parameters

        self.assertEqual(parameters["type"], "object")
        self.assertEqual(parameters["required"], ["command"])
        self.assertEqual(parameters["properties"]["command"]["type"], "string")
        self.assertNotIn("args", parameters["properties"])

    def test_run_shell_command_uses_powershell_on_windows(self):
        tool = BetterShellTools()
        fake_result = types.SimpleNamespace(stdout="ok\n", returncode=0)

        with patch("subprocess.run", return_value=fake_result) as run_mock, patch(
            "debug_assistant_latest.better_shell.os.name", "nt"
        ):
            output = tool.run_shell_command("Get-Location")

        self.assertEqual(output, "ok\n")
        args, kwargs = run_mock.call_args
        self.assertEqual(args[0][:3], ["powershell", "-NoProfile", "-Command"])
        self.assertFalse(kwargs["shell"])
        self.assertEqual(kwargs["encoding"], "utf-8")
        self.assertEqual(kwargs["errors"], "replace")
        self.assertEqual(kwargs["timeout"], 120)

    def test_run_shell_command_allows_direct_powershell_edit_on_windows(self):
        tool = BetterShellTools()
        fake_result = types.SimpleNamespace(stdout="", stderr="", returncode=0)
        command = (
            "(Get-Content 'C:\\repo\\wrong_port.yaml') "
            "-replace 'containerPort: 8000','containerPort: 8765' | "
            "Set-Content 'C:\\repo\\wrong_port.yaml'"
        )

        with patch("subprocess.run", return_value=fake_result) as run_mock, patch(
            "debug_assistant_latest.better_shell.os.name", "nt"
        ):
            output = tool.run_shell_command(command)

        self.assertEqual(output, "")
        run_mock.assert_called_once()

    def test_run_shell_command_blocks_known_bad_windows_pattern_with_actionable_error(self):
        tool = BetterShellTools()
        command = "kubectl port-forward pod/kube-wrong-port 8765:8765 & sleep 1; curl -s http://localhost:8765 | head -n 5"

        with patch("debug_assistant_latest.better_shell.os.name", "nt"):
            output = tool.run_shell_command(command)

        self.assertIn("Error:", output)
        self.assertIn("kubectl exec", output)
        self.assertIn("kubectl get", output)

    def test_run_shell_command_blocks_port_forward_for_debug_phase_on_linux(self):
        tool = BetterShellTools(phase="debug")
        command = "kubectl port-forward pod/kube-wrong-port 8765:8765"

        with patch("debug_assistant_latest.better_shell.os.name", "posix"), patch(
            "subprocess.run"
        ) as run_mock:
            output = tool.run_shell_command(command)

        self.assertIn("Error:", output)
        self.assertIn("kubectl port-forward", output)
        self.assertIn("kubectl exec", output)
        run_mock.assert_not_called()

    def test_run_shell_command_blocks_background_verification_for_verification_phase_on_linux(self):
        tool = BetterShellTools(phase="verification")
        command = "kubectl port-forward pod/kube-wrong-port 8765:8765 & sleep 1; curl -s http://localhost:8765/"

        with patch("debug_assistant_latest.better_shell.os.name", "posix"), patch(
            "subprocess.run"
        ) as run_mock:
            output = tool.run_shell_command(command)

        self.assertIn("Error:", output)
        self.assertIn("kubectl port-forward", output)
        run_mock.assert_not_called()

    def test_run_shell_command_allows_default_linux_tool_behavior_for_same_string(self):
        tool = BetterShellTools()
        fake_result = types.SimpleNamespace(stdout="ok\n", stderr="", returncode=0)
        command = "kubectl port-forward pod/kube-wrong-port 8765:8765"

        with patch("debug_assistant_latest.better_shell.os.name", "posix"), patch(
            "subprocess.run", return_value=fake_result
        ) as run_mock:
            output = tool.run_shell_command(command)

        self.assertEqual(output, "ok\n")
        run_mock.assert_called_once()

    def test_run_shell_command_raises_after_repeated_blocked_commands(self):
        tool = BetterShellTools(phase="debug", blocked_threshold=3)
        command = "kubectl port-forward pod/kube-wrong-port 8765:8765"

        with patch("debug_assistant_latest.better_shell.os.name", "posix"):
            self.assertIn("Error:", tool.run_shell_command(command))
            self.assertIn("Error:", tool.run_shell_command(command))
            with self.assertRaises(BlockedCommandThresholdError):
                tool.run_shell_command(command)

    def test_run_shell_command_resets_blocked_counter_after_allowed_command(self):
        tool = BetterShellTools(phase="debug", blocked_threshold=3)
        blocked = "kubectl port-forward pod/kube-wrong-port 8765:8765"
        fake_result = types.SimpleNamespace(stdout="ok\n", stderr="", returncode=0)

        with patch("debug_assistant_latest.better_shell.os.name", "posix"), patch(
            "subprocess.run", return_value=fake_result
        ):
            self.assertIn("Error:", tool.run_shell_command(blocked))
            self.assertEqual(tool.run_shell_command("Get-Location"), "ok\n")

        self.assertEqual(tool._consecutive_blocked, 0)

    def test_run_shell_command_accepts_dict_command_payload(self):
        tool = BetterShellTools()
        fake_result = types.SimpleNamespace(stdout="ok\n", stderr="", returncode=0)

        with patch("subprocess.run", return_value=fake_result) as run_mock, patch(
            "debug_assistant_latest.better_shell.os.name", "nt"
        ):
            output = tool.run_shell_command({"command": "Get-Location"})

        self.assertEqual(output, "ok\n")
        args, kwargs = run_mock.call_args
        self.assertEqual(args[0][:3], ["powershell", "-NoProfile", "-Command"])
        self.assertEqual(args[0][-1], "Get-Location")
        self.assertFalse(kwargs["shell"])

    def test_run_shell_command_processed_entrypoint_accepts_legacy_command_payload(self):
        tool = BetterShellTools()
        fake_result = types.SimpleNamespace(stdout="ok\n", stderr="", returncode=0)
        function = tool.functions["run_shell_command"]
        function.process_entrypoint()

        with patch("subprocess.run", return_value=fake_result) as run_mock, patch(
            "debug_assistant_latest.better_shell.os.name", "nt"
        ):
            output = function.entrypoint(command={"command": "Get-Location"})

        self.assertEqual(output, "ok\n")
        args, kwargs = run_mock.call_args
        self.assertEqual(args[0][-1], "Get-Location")
        self.assertFalse(kwargs["shell"])

    def test_run_shell_command_returns_actionable_error_for_non_command_payload(self):
        tool = BetterShellTools()

        with patch("debug_assistant_latest.better_shell.os.name", "nt"):
            output = tool.run_shell_command({"type": "string"})

        self.assertIn("Error:", output)
        self.assertIn("literal shell command string", output)

    def test_build_llm_agent_ollama_request_kwargs_include_shell_tool_schema(self):
        agent = agent_helpers.build_llm_agent("llama3.1:8b", ["i"], ["g"])

        agent.update_model()
        tools = agent.model.request_kwargs["tools"]

        self.assertEqual(len(tools), 1)
        parameters = tools[0]["function"]["parameters"]
        self.assertEqual(parameters["properties"]["command"]["type"], "string")
        self.assertEqual(parameters["required"], ["command"])
        self.assertNotIn("args", parameters["properties"])


class RunnerStreamTests(unittest.TestCase):
    def test_safe_write_to_stream_replaces_unencodable_console_text(self):
        class FakeStream:
            encoding = "cp1252"

            def __init__(self):
                self.writes = []

            def write(self, data):
                data.encode(self.encoding)
                self.writes.append(data)

            def flush(self):
                return None

        stream = FakeStream()
        _safe_write_to_stream(stream, "step -> next \u2192 done")

        self.assertEqual(stream.writes, ["step -> next ? done"])

    def test_safe_flush_stream_swallows_oserror(self):
        class FakeStream:
            def flush(self):
                raise OSError("bad handle")

        _safe_flush_stream(FakeStream())

    def test_best_effort_configure_console_streams_reconfigures_streams(self):
        stdout_stream = MagicMock()
        stderr_stream = MagicMock()

        with patch("sys.stdout", stdout_stream), patch("sys.stderr", stderr_stream):
            _best_effort_configure_console_streams()

        stdout_stream.reconfigure.assert_called_once_with(encoding="utf-8", errors="replace")
        stderr_stream.reconfigure.assert_called_once_with(encoding="utf-8", errors="replace")


class ProgressWriterTests(unittest.TestCase):
    def test_progress_writer_serializes_concurrent_jsonl_writes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = ProgressWriter(Path(tmpdir) / "progress.log")

            def emit(prefix):
                for index in range(20):
                    writer.write_event("thread_event", prefix=prefix, index=index)

            threads = [threading.Thread(target=emit, args=(name,)) for name in ("a", "b", "c")]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            writer.close()

            lines = (Path(tmpdir) / "progress.log").read_text(encoding="utf-8").splitlines()

        self.assertEqual(len(lines), 60)
        records = [json.loads(line) for line in lines]
        self.assertEqual(sorted(record["seq"] for record in records), list(range(1, 61)))


class AssistantIntegrationTests(unittest.TestCase):
    def test_get_rag_assistant_openai_path_works_without_ollama_imports(self):
        imported_modules = []

        def fake_import(module_name):
            imported_modules.append(module_name)
            if module_name == "phi.model.openai":
                return types.SimpleNamespace(OpenAIChat=lambda **kwargs: {"kind": "chat", **kwargs})
            if module_name == "phi.embedder.openai":
                return types.SimpleNamespace(OpenAIEmbedder=FakeEmbedder)
            if module_name in {"phi.model.ollama", "phi.embedder.ollama", "phi.model.google"}:
                raise AssertionError(f"Unexpected import: {module_name}")
            raise AssertionError(f"Unexpected module import request: {module_name}")

        fake_agent = types.SimpleNamespace()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False), patch(
            "runtime_config.importlib.import_module", side_effect=fake_import
        ), patch.object(assistant, "AgentKnowledge", return_value="knowledge"), patch.object(
            assistant, "PgVector", return_value="pgvector"
        ) as pgvector_mock, patch.object(assistant, "PgAgentStorage", return_value="storage"), patch.object(
            assistant, "BetterShellTools", return_value="tool"
        ), patch.object(assistant, "Agent", return_value=fake_agent):
            result = assistant.get_rag_assistant(
                llm_model="gpt-5-mini",
                embeddings_model="text-embedding-3-small",
                embeddings_provider="openai",
            )

        self.assertIs(result, fake_agent)
        self.assertIn("phi.model.openai", imported_modules)
        self.assertIn("phi.embedder.openai", imported_modules)
        self.assertTrue(all("ollama" not in name for name in imported_modules))
        self.assertEqual(pgvector_mock.call_args.kwargs["table_name"], "local_rag_documents_text-embedding-3-small")

    def test_get_rag_assistant_ollama_path_works_without_openai_env_or_imports(self):
        imported_modules = []

        def fake_import(module_name):
            imported_modules.append(module_name)
            if module_name == "phi.model.ollama":
                return types.SimpleNamespace(Ollama=lambda **kwargs: {"kind": "chat", **kwargs})
            if module_name == "phi.embedder.ollama":
                return types.SimpleNamespace(OllamaEmbedder=FakeEmbedder)
            if module_name in {"phi.model.openai", "phi.embedder.openai", "phi.model.google"}:
                raise AssertionError(f"Unexpected import: {module_name}")
            raise AssertionError(f"Unexpected module import request: {module_name}")

        fake_agent = types.SimpleNamespace()
        with patch.dict(os.environ, {}, clear=True), patch(
            "runtime_config.importlib.import_module", side_effect=fake_import
        ), patch.object(assistant, "AgentKnowledge", return_value="knowledge"), patch.object(
            assistant, "PgVector", return_value="pgvector"
        ) as pgvector_mock, patch.object(assistant, "PgAgentStorage", return_value="storage"), patch.object(
            assistant, "BetterShellTools", return_value="tool"
        ), patch.object(assistant, "Agent", return_value=fake_agent):
            result = assistant.get_rag_assistant(
                llm_model="llama3.1:8b",
                embeddings_model="nomic-embed-text",
                embeddings_provider="ollama",
            )

        self.assertIs(result, fake_agent)
        self.assertEqual(imported_modules, ["phi.model.ollama", "phi.embedder.ollama"])
        self.assertEqual(pgvector_mock.call_args.kwargs["table_name"], "local_rag_documents_nomic-embed-text")

    def test_get_rag_assistant_surfaces_openai_embedder_quota_without_ollama_imports(self):
        imported_modules = []

        class QuotaEmbedder(FakeEmbedder):
            def get_embedding_and_usage(self, text):
                raise RuntimeError("Error code: 429 - insufficient_quota")

        def fake_import(module_name):
            imported_modules.append(module_name)
            if module_name == "phi.model.openai":
                return types.SimpleNamespace(OpenAIChat=lambda **kwargs: {"kind": "chat", **kwargs})
            if module_name == "phi.embedder.openai":
                return types.SimpleNamespace(OpenAIEmbedder=QuotaEmbedder)
            if module_name == "phi.embedder.ollama":
                raise AssertionError(f"Unexpected import: {module_name}")
            if module_name in {"phi.model.ollama", "phi.model.google"}:
                raise AssertionError(f"Unexpected import: {module_name}")
            raise AssertionError(f"Unexpected module import request: {module_name}")

        fake_agent = types.SimpleNamespace()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False), patch(
            "runtime_config.importlib.import_module", side_effect=fake_import
        ), patch.object(assistant, "AgentKnowledge", return_value="knowledge"), patch.object(
            assistant, "PgVector", return_value="pgvector"
        ) as pgvector_mock, patch.object(assistant, "PgAgentStorage", return_value="storage"), patch.object(
            assistant, "BetterShellTools", return_value="tool"
        ), patch.object(assistant, "Agent", return_value=fake_agent):
            with self.assertRaisesRegex(RuntimeError, "insufficient_quota"):
                assistant.get_rag_assistant(
                    llm_model="gpt-5-mini",
                    embeddings_model="text-embedding-3-small",
                    embeddings_provider="openai",
                )

        pgvector_mock.assert_not_called()
        self.assertEqual(imported_modules, ["phi.model.openai", "phi.embedder.openai"])


class GroundTruthTests(unittest.TestCase):
    def test_execute_command_uses_direct_argv_on_windows_for_jsonpath(self):
        fake_result = types.SimpleNamespace(stdout="True\n", stderr="", returncode=0)
        command = "kubectl get pod test -o jsonpath='{.status.conditions[?(@.type==\"Ready\")].status}'"

        with patch("subprocess.run", return_value=fake_result) as run_mock, patch(
            "debug_assistant_latest.ground_truth.os.name", "nt"
        ):
            output, exit_code, error = execute_command(command)

        self.assertEqual((output, exit_code, error), ("True", 0, None))
        args, kwargs = run_mock.call_args
        self.assertEqual(
            args[0],
            ["kubectl", "get", "pod", "test", "-o", 'jsonpath={.status.conditions[?(@.type=="Ready")].status}'],
        )
        self.assertFalse(kwargs["shell"])
        self.assertEqual(kwargs["encoding"], "utf-8")
        self.assertEqual(kwargs["errors"], "replace")

    def test_execute_command_uses_powershell_on_windows_when_shell_is_required(self):
        fake_result = types.SimpleNamespace(stdout="clean\n", stderr="", returncode=0)
        command = "kubectl logs test 2>&1 | grep boom || echo clean"

        with patch("subprocess.run", return_value=fake_result) as run_mock, patch(
            "debug_assistant_latest.ground_truth.os.name", "nt"
        ):
            output, exit_code, error = execute_command(command)

        self.assertEqual((output, exit_code, error), ("clean", 0, None))
        args, kwargs = run_mock.call_args
        self.assertEqual(args[0][:3], ["powershell", "-NoProfile", "-Command"])
        self.assertFalse(kwargs["shell"])

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

    def test_run_check_fails_when_output_does_not_match_expect(self):
        cmd = f'"{sys.executable}" -c "print(1)"'
        result = run_check(
            {"name": "neg_expect", "cmd": cmd, "expect": "expected"},
            passed_checks=set(),
        )
        self.assertEqual(result.status, CheckStatus.FAIL)

    def test_run_all_checks_fails_when_a_check_fails(self):
        cmd = f'"{sys.executable}" -c "print(1)"'
        result = run_all_checks(
            {
                "test-name": "neg_suite",
                "ground-truth": {
                    "checks": [{"name": "c1", "cmd": cmd, "expect": "yes"}],
                },
            }
        )
        self.assertIsNotNone(result)
        self.assertFalse(result.passed)
        self.assertEqual(result.checks[0].status, CheckStatus.FAIL)

    def test_save_ground_truth_includes_schema_provenance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            res = GroundTruthResult(test_name="t", passed=True, checks=[], total_duration_ms=0)
            out = save_ground_truth_result(res, Path(tmpdir))
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertIn("ground_truth_schema_sha256", data)
            self.assertIn("ground_truth_schema_version", data)
            self.assertEqual(len(data["ground_truth_schema_sha256"]), 64)


class MainMetricsLineageTests(unittest.TestCase):
    def test_debug_timeout_metrics_include_run_lineage(self):
        from debug_assistant_latest import main as main_mod

        captured = []

        def capture(db, metrics, tsv):
            captured.append((dict(metrics), tsv))

        rc = {"run_uuid": "uu-1", "run_id": "rid-1", "log_dir": "/tmp/x"}
        config = {"test-name": "t1"}

        def run_obs(_rt, phase, action):
            if phase == "api":
                action()
                return {"model": "m-api", "input_tokens": 1, "output_tokens": 2, "total_tokens": 3}
            if phase == "debug":
                return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
            raise AssertionError(phase)

        mock_api = MagicMock()
        mock_api.agentProperties = {"model": "m-api"}
        with patch.object(main_mod, "store_metrics_entry", side_effect=capture), patch.object(
            main_mod, "_load_runtime_config", return_value=config
        ), patch.object(main_mod, "setUpEnvironment"), patch.object(
            main_mod, "AgentAPI", return_value=mock_api
        ), patch.object(main_mod, "AgentDebug") as dbg_cls, patch.object(
            main_mod, "_run_observed_phase", side_effect=run_obs
        ), patch.object(main_mod, "printFinishMessage"):
            dbg = MagicMock()
            dbg.agentProperties = {"model": "m1"}
            dbg._last_timeout = True
            dbg_cls.return_value = dbg
            main_mod.allStepsAtOnce(configFile="dummy.json", runtime_context=rc)

        self.assertEqual(len(captured), 2)
        by_agent = {metrics["agent_type"]: metrics for metrics, _ in captured}
        self.assertEqual(by_agent["api"].get("run_uuid"), "uu-1")
        self.assertEqual(by_agent["api"].get("run_id"), "rid-1")
        self.assertEqual(by_agent["debug"].get("run_uuid"), "uu-1")
        self.assertEqual(by_agent["debug"].get("run_id"), "rid-1")


class VerificationTemperatureLintTests(unittest.TestCase):
    def test_verification_temperature_issues_one_allowed(self):
        cfg = {"verification-agent": {"temperature": 1.0}}
        self.assertEqual(_verification_temperature_issues(cfg, allow_high=False), [])

    def test_verification_temperature_issues_above_one(self):
        cfg = {"verification-agent": {"temperature": 1.5}}
        issues = _verification_temperature_issues(cfg, allow_high=False)
        self.assertEqual(len(issues), 1)
        self.assertIn("1.0", issues[0])

    def test_verification_temperature_issues_allowed_when_flag_set(self):
        cfg = {"verification-agent": {"temperature": 2.0}}
        self.assertEqual(_verification_temperature_issues(cfg, allow_high=True), [])


class ExecutionResultExtractionTests(unittest.TestCase):
    def test_extract_execution_verification_unknown_yields_verified_none(self):
        payload = {
            "status": None,
            "api_metrics": {"task_status": 1, "total_tokens": 5},
            "debug_metrics": {"task_status": 1},
            "verification_metrics": {"task_status": 0, "total_tokens": 10},
        }
        success, verified, debug_self_report, metrics, derived = _extract_execution_result(payload)
        self.assertFalse(success)
        self.assertIsNone(verified)
        self.assertTrue(debug_self_report)
        self.assertIn("api", metrics)
        self.assertIn("verification", metrics)

    def test_extract_execution_verification_true_false_preserved(self):
        ok = {
            "status": True,
            "debug_metrics": {"task_status": 1},
            "verification_metrics": {"total_tokens": 1},
        }
        self.assertTrue(_extract_execution_result(ok)[1])
        bad = {
            "status": False,
            "debug_metrics": {"task_status": 1},
            "verification_metrics": {"total_tokens": 1},
        }
        self.assertFalse(_extract_execution_result(bad)[1])

    def test_result_to_summary_preserves_verified_none(self):
        result = TestResult(
            test_name="t1",
            success=False,
            verified=None,
            debug_self_report=True,
            duration_s=1.0,
            error=None,
            metrics={},
            log_dir=Path("/tmp/t1"),
            started_at="2026-01-01T00:00:00",
            finished_at="2026-01-01T00:00:01",
        )
        summary = result_to_summary(result, "allStepsAtOnce", {})
        self.assertIsNone(summary.verified)


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
                metrics={
                    "api": AgentMetrics(total_tokens=25, cost=0.25),
                    "debug_agent": AgentMetrics(total_tokens=100, cost=1.25),
                },
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
        self.assertEqual(aggregate.total_tokens, 175)
        self.assertEqual(aggregate.total_api_tokens, 25)
        self.assertEqual(aggregate.total_cost, 2.25)
        self.assertEqual(aggregate.total_api_cost, 0.25)
        self.assertEqual(aggregate.ground_truth_failed_tests, ["wrong_interface"])

    def test_generate_aggregate_report_counts_configured_gt_even_if_not_run(self):
        summaries = [
            TestSummary(
                test_name="wrong_port",
                technique="allStepsAtOnce",
                status="PASS",
                verified=True,
                ground_truth_passed=True,
                ground_truth_configured=True,
            ),
            TestSummary(
                test_name="worker_timeout",
                technique="allStepsAtOnce",
                status="ERROR",
                verified=None,
                ground_truth_passed=None,
                ground_truth_configured=True,
                error_message="Timeout: exceeded 600s",
            ),
        ]

        aggregate = generate_aggregate_report(summaries, run_config={}, run_id="run-gt-timeout")

        self.assertEqual(aggregate.ground_truth_passed, 1)
        self.assertEqual(aggregate.tests_with_ground_truth, 2)
        self.assertEqual(aggregate.ground_truth_rate, 50.0)
        self.assertEqual(aggregate.ground_truth_failed_tests, ["worker_timeout"])

    def test_generate_aggregate_report_counts_dict_backed_metrics(self):
        summaries = [
            TestSummary(
                test_name="wrong_port",
                technique="allStepsAtOnce",
                status="PASS",
                verified=True,
                metrics={
                    "api": {
                        "test_case": "wrong_port",
                        "model": "gpt-4o",
                        "agent_type": "api",
                        "input_tokens": 10,
                        "output_tokens": 15,
                        "total_tokens": 25,
                        "task_status": True,
                        "duration_s": 2.0,
                        "cost": 0.25,
                    },
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

        self.assertEqual(aggregate.total_tokens, 175)
        self.assertEqual(aggregate.total_api_tokens, 25)
        self.assertEqual(aggregate.total_cost, 2.25)
        self.assertEqual(aggregate.total_api_cost, 0.25)
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
        self.assertTrue(summary.ground_truth_configured)


class TeardownTests(unittest.TestCase):
    def test_all_runnable_fixture_baselines_match_working_fixtures(self):
        for test_name in list_test_cases():
            fixture_dir = teardown.TROUBLESHOOTING_DIR / test_name
            baseline_dir = teardown.FIXTURE_BASELINES_DIR / test_name
            self.assertTrue(baseline_dir.is_dir(), test_name)
            fixture_files = sorted(
                path.relative_to(fixture_dir)
                for path in fixture_dir.rglob("*")
                if path.is_file() and "__pycache__" not in path.parts
            )
            baseline_files = sorted(
                path.relative_to(baseline_dir)
                for path in baseline_dir.rglob("*")
                if path.is_file() and "__pycache__" not in path.parts
            )
            self.assertEqual(baseline_files, fixture_files, test_name)
            for relative_path in fixture_files:
                self.assertEqual(
                    (baseline_dir / relative_path).read_bytes(),
                    (fixture_dir / relative_path).read_bytes(),
                    f"{test_name}/{relative_path}",
                )

    def test_restore_fixture_baseline_replaces_modified_and_new_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_root = Path(tmpdir)
            case_dir = test_root / "wrong_port"
            baseline_root = Path(tmpdir) / "baselines"
            baseline_dir = baseline_root / "wrong_port"
            baseline_dir.mkdir(parents=True)
            (baseline_dir / "config_step.json").write_text('{"baseline": true}\n')
            (baseline_dir / "nested").mkdir()
            (baseline_dir / "nested" / "server.py").write_text("baseline\n")
            case_dir.mkdir()
            (case_dir / "config_step.json").write_text("modified\n")
            (case_dir / "created.txt").write_text("created\n")
            (case_dir / "created_dir").mkdir()
            (case_dir / "created_dir" / "child.txt").write_text("created\n")

            with patch.object(teardown, "TROUBLESHOOTING_DIR", test_root), patch.object(
                teardown, "FIXTURE_BASELINES_DIR", baseline_root
            ), patch.dict(
                teardown.TEARDOWN_CONFIG,
                {"wrong_port": {"docker_images": [], "k8s_manifests": []}},
                clear=False,
            ):
                teardown.restore_fixture_baseline("wrong_port")

            self.assertEqual((case_dir / "config_step.json").read_text(), '{"baseline": true}\n')
            self.assertEqual((case_dir / "nested" / "server.py").read_text(), "baseline\n")
            self.assertFalse((case_dir / "created.txt").exists())
            self.assertFalse((case_dir / "created_dir").exists())

    def test_restore_fixture_baseline_requires_baseline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_root = Path(tmpdir)
            case_dir = test_root / "wrong_port"
            case_dir.mkdir()

            with patch.object(teardown, "TROUBLESHOOTING_DIR", test_root), patch.object(
                teardown, "FIXTURE_BASELINES_DIR", Path(tmpdir) / "missing"
            ), patch.dict(
                teardown.TEARDOWN_CONFIG,
                {"wrong_port": {"docker_images": [], "k8s_manifests": []}},
                clear=False,
            ):
                with self.assertRaisesRegex(FileNotFoundError, "Fixture baseline not found"):
                    teardown.restore_fixture_baseline("wrong_port")

    def test_teardown_environment_restores_baseline_and_deletes_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_root = Path(tmpdir)
            case_dir = test_root / "wrong_port"
            case_dir.mkdir()
            (case_dir / "wrong_port.yaml").write_text("broken\n")
            baseline_root = Path(tmpdir) / "baselines"
            baseline_dir = baseline_root / "wrong_port"
            baseline_dir.mkdir(parents=True)
            (baseline_dir / "wrong_port.yaml").write_text("restored\n")

            recorded_calls = []

            def fake_run(*args, **kwargs):
                recorded_calls.append((args, kwargs))
                return None

            with patch.object(teardown, "TROUBLESHOOTING_DIR", test_root), patch.object(
                teardown, "FIXTURE_BASELINES_DIR", baseline_root
            ), patch(
                "debug_assistant_latest.teardown.subprocess.run", side_effect=fake_run
            ), patch.dict(
                teardown.TEARDOWN_CONFIG,
                {"wrong_port": {"docker_images": [], "k8s_manifests": ["{name}.yaml"]}},
                clear=False,
            ):
                teardown.teardown_environment("wrong_port")

            self.assertEqual((case_dir / "wrong_port.yaml").read_text(), "restored\n")
            self.assertTrue(any("kubectl" in call[0][0][0] for call in recorded_calls if call[0]))

    def test_cleanup_transient_k8s_resources_deletes_known_helper_resources(self):
        recorded_calls = []

        def fake_run(*args, **kwargs):
            recorded_calls.append((args, kwargs))
            completed = subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")
            if args and args[0] == ["kubectl", "get", "pods", "-n", "default", "-o", "name"]:
                completed.stdout = "\n".join(
                    [
                        "pod/curl-test2",
                        "pod/curl-check2",
                        "pod/net-test",
                        "pod/svc-test",
                        "pod/kube-wrong-port",
                    ]
                )
            return completed

        with patch("debug_assistant_latest.teardown.subprocess.run", side_effect=fake_run):
            teardown.cleanup_transient_k8s_resources()

        commands = [call[0][0] for call in recorded_calls]
        self.assertIn(
            ["kubectl", "delete", "pod", "curl-test", "-n", "default", "--ignore-not-found=true"],
            commands,
        )
        self.assertIn(
            ["kubectl", "delete", "service", "curl-test", "-n", "default", "--ignore-not-found=true"],
            commands,
        )
        self.assertIn(
            ["kubectl", "delete", "pod", "curl-check", "-n", "default", "--ignore-not-found=true"],
            commands,
        )
        self.assertIn(
            ["kubectl", "delete", "service", "curl-check", "-n", "default", "--ignore-not-found=true"],
            commands,
        )
        self.assertIn(
            ["kubectl", "delete", "pod", "curlcheck", "-n", "default", "--ignore-not-found=true"],
            commands,
        )
        self.assertIn(
            ["kubectl", "delete", "service", "curlcheck", "-n", "default", "--ignore-not-found=true"],
            commands,
        )
        self.assertIn(
            ["kubectl", "delete", "pod", "curl-test2", "-n", "default", "--ignore-not-found=true"],
            commands,
        )
        self.assertIn(
            ["kubectl", "delete", "pod", "curl-check2", "-n", "default", "--ignore-not-found=true"],
            commands,
        )
        self.assertIn(
            ["kubectl", "delete", "pod", "net-test", "-n", "default", "--ignore-not-found=true"],
            commands,
        )
        self.assertIn(
            ["kubectl", "delete", "pod", "svc-test", "-n", "default", "--ignore-not-found=true"],
            commands,
        )
        self.assertNotIn(
            ["kubectl", "delete", "pod", "kube-wrong-port", "-n", "default", "--ignore-not-found=true"],
            commands,
        )

    def test_cleanup_test_pods_deletes_all_pods_in_namespace(self):
        recorded_calls = []

        def fake_run(*args, **kwargs):
            recorded_calls.append((args, kwargs))
            return subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")

        with patch("debug_assistant_latest.teardown.subprocess.run", side_effect=fake_run):
            teardown.cleanup_test_pods("default")

        commands = [call[0][0] for call in recorded_calls]
        self.assertEqual(
            commands,
            [["kubectl", "delete", "pods", "--all", "-n", "default", "--ignore-not-found=true"]],
        )

class RunnerTests(unittest.TestCase):
    def test_removed_backup_flag_is_rejected(self):
        with patch.object(sys, "argv", ["runner.py", "--backup-before-run"]):
            with self.assertRaises(SystemExit) as error:
                cli_main()

        self.assertEqual(error.exception.code, 2)

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
            ground_truth_configured=True,
        )

        summary = result_to_summary(result, "allStepsAtOnce", {"debug-agent.model": "gpt-4o"})

        self.assertEqual(summary.status, "PASS")
        self.assertTrue(summary.verified)
        self.assertTrue(summary.ground_truth_passed)
        self.assertTrue(summary.ground_truth_configured)
        self.assertEqual(summary.metrics["debug_agent"].__class__.__name__, "AgentMetrics")
        self.assertEqual(summary.metrics["debug_agent"].cost, 1.0)
        self.assertEqual(summary.config_overrides_applied["debug-agent.model"], "gpt-4o")

    def test_run_single_test_cleans_transient_resources_before_ground_truth(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            events = []

            def fake_agent(**kwargs):
                events.append("agent")
                return {"status": True}

            def fake_cleanup():
                events.append("cleanup")

            def fake_pod_cleanup():
                events.append("pod_cleanup")

            def fake_ground_truth(config):
                events.append("ground_truth")
                return GroundTruthResult(test_name="svc_case", passed=True)

            config = {
                "ground-truth": {
                    "checks": [
                        {
                            "name": "dummy",
                            "cmd": "true",
                            "expect": "",
                        }
                    ]
                }
            }

            with patch("main.allStepsAtOnce", side_effect=fake_agent), patch(
                "teardown.cleanup_transient_k8s_resources", side_effect=fake_cleanup
            ), patch(
                "teardown.cleanup_test_pods", side_effect=fake_pod_cleanup
            ), patch("debug_assistant_latest.executor.get_config_path", return_value=Path("dummy.json")), patch(
                "debug_assistant_latest.executor.load_config_with_overrides", return_value=config
            ), patch("debug_assistant_latest.executor.save_effective_config"), patch(
                "debug_assistant_latest.executor.run_ground_truth_checks", side_effect=fake_ground_truth
            ), patch(
                "debug_assistant_latest.executor.save_ground_truth_result"
            ):
                result = executor.run_single_test(
                    "svc_case",
                    "allStepsAtOnce",
                    {},
                    Path(tmpdir),
                    verbose=False,
                )

            self.assertTrue(result.success)
            self.assertTrue(result.ground_truth_passed)
            self.assertEqual(events, ["cleanup", "agent", "cleanup", "ground_truth", "pod_cleanup"])

    def test_apply_repeat_overrides_forces_serial_teardown(self):
        args = argparse.Namespace(
            repeat=3,
            jobs=4,
            teardown_after_run=False,
        )

        repeat_active = _apply_repeat_overrides(args)

        self.assertTrue(repeat_active)
        self.assertEqual(args.jobs, 1)
        self.assertTrue(args.teardown_after_run)

    def test_build_repeat_payload_serializes_paths_and_sets_test_case(self):
        args = argparse.Namespace(
            output_dir=Path("/tmp/original"),
            test_case="wrong_port",
            repeat=2,
            jobs=1,
            teardown_after_run=True,
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
            with patch("debug_assistant_latest.cli.Process", FakeProcess), patch(
                "debug_assistant_latest.cli._repeat_iteration_worker", fake_worker
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
            with patch("debug_assistant_latest.cli.Process", FakeProcess), patch(
                "debug_assistant_latest.cli.Queue", FakeQueue
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
                embedder=None,
                embedder_provider=None,
                technique="allStepsAtOnce",
                teardown_after_run=False,
                minikube_profile=None,
                rag_api_url=None,
                skip_preflight=True,
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

            with patch("debug_assistant_latest.executor.collect_run_provenance", return_value={}), patch(
                "debug_assistant_latest.executor.build_environment_context",
                return_value={"platform": "linux", "python_version": "3.13.0", "kubectl_context": "test"},
            ), patch("debug_assistant_latest.executor.run_single_test", return_value=fake_result), patch(
                "debug_assistant_latest.executor.save_run_config"
            ) as save_run_config_mock, patch(
                "debug_assistant_latest.executor.save_test_summary"
            ) as save_test_summary_mock, patch(
                "debug_assistant_latest.executor.generate_aggregate_report",
                return_value=types.SimpleNamespace(passed=1, failed=0, errors=0),
            ) as generate_report_mock, patch(
                "debug_assistant_latest.executor.save_aggregate_report"
            ) as save_aggregate_mock, patch(
                "debug_assistant_latest.executor.print_console_summary"
            ) as print_console_mock:
                exit_code = cmd_run_single(args, "wrong_port")

            self.assertEqual(exit_code, 0)
            save_run_config_mock.assert_called_once()
            save_test_summary_mock.assert_called_once()
            generate_report_mock.assert_called_once()
            save_aggregate_mock.assert_called_once()
            print_console_mock.assert_called_once()

    def test_cmd_run_single_preflight_failure_writes_terminal_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            args = argparse.Namespace(
                output_dir=Path(tmpdir),
                debug_model=None,
                api_model=None,
                verification_model=None,
                embedder=None,
                embedder_provider=None,
                technique="allStepsAtOnce",
                teardown_after_run=False,
                minikube_profile="test-profile",
                rag_api_url=None,
                skip_preflight=False,
            )
            preflight_result = {
                "passed": False,
                "checks": [
                    {"name": "docker_engine", "passed": False, "message": "engine down"},
                    {"name": "cluster_access", "passed": False, "message": "kubectl get nodes failed"},
                ],
            }

            with patch("debug_assistant_latest.executor.collect_run_provenance", return_value={}), patch(
                "debug_assistant_latest.executor.build_environment_context",
                return_value={"platform": "linux", "python_version": "3.13.0", "kubectl_context": "test"},
            ), patch("debug_assistant_latest.executor.run_preflight", return_value=preflight_result), patch(
                "debug_assistant_latest.executor.print_preflight_result"
            ), patch(
                "debug_assistant_latest.executor.run_single_test"
            ) as run_single_mock, patch(
                "debug_assistant_latest.executor.print_console_summary"
            ):
                exit_code = cmd_run_single(args, "wrong_port")

            self.assertEqual(exit_code, 1)
            run_single_mock.assert_not_called()
            summary_path = Path(tmpdir) / "wrong_port" / "summary.json"
            aggregate_path = Path(tmpdir) / "aggregate.json"
            progress_path = Path(tmpdir) / "wrong_port" / "progress.log"
            self.assertTrue(summary_path.exists())
            self.assertTrue(aggregate_path.exists())
            self.assertTrue(progress_path.exists())

            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["status"], "ERROR")
            self.assertIn("Preflight failed", summary["error_message"])

            progress_events = [
                json.loads(line)["event"]
                for line in progress_path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertIn("preflight_end", progress_events)
            self.assertEqual(progress_events[-1], "run_end")


class ApiServerRouteTests(unittest.TestCase):
    def setUp(self):
        api_server.session_state.reset_run()

    def tearDown(self):
        api_server.session_state.reset_run()

    def test_initialize_route_returns_structured_json_error(self):
        client = TestClient(api_server.app)

        with patch("api_server.resolve_embedder_config", side_effect=RuntimeError("ollama package missing")):
            response = client.post("/initialize/", data={"llm_model": "llama3.1:8b"})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json()["detail"],
            "Could not initialize assistant: ollama package missing",
        )

    def test_initialize_route_records_requested_embedder_config(self):
        fake_agent = types.SimpleNamespace(
            create_session=MagicMock(return_value="run-1"),
        )

        with patch("api_server.get_rag_assistant", return_value=fake_agent):
            response = asyncio.run(
                api_server.initialize_assistant(
                    llm_model="gpt-5-mini",
                    embeddings_model="text-embedding-3-small",
                    embeddings_provider="openai",
                )
            )

        self.assertEqual(response, {"status": "Agent initialized"})
        self.assertEqual(api_server.session_state.embeddings_model, "text-embedding-3-small")
        self.assertEqual(api_server.session_state.embeddings_provider, "openai")

    def test_server_info_reports_version_and_signature(self):
        client = TestClient(api_server.app)

        response = client.get("/server_info/")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["api_version"], rag_server_config.RAG_API_VERSION)
        self.assertEqual(body["repo_signature"], rag_server_config.SERVER_REPO_SIGNATURE)
        self.assertTrue(body["module_path"].endswith("api_server.py"))

    def test_server_info_uses_startup_signature(self):
        with patch.object(rag_server_config, "SERVER_REPO_SIGNATURE", "signature-at-startup"):
            info = rag_server_config.build_server_info(module_path=REPO_ROOT / "api_server.py")

        self.assertEqual(info["repo_signature"], "signature-at-startup")

    def test_ask_route_returns_structured_json_error(self):
        client = TestClient(api_server.app)
        api_server.session_state.rag_assistant = types.SimpleNamespace(run=MagicMock(side_effect=RuntimeError("boom")))

        response = client.post("/ask/", data={"prompt": "hello"})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "Could not answer question: boom")

    def test_ask_route_returns_response_metrics(self):
        api_server.session_state.rag_assistant = types.SimpleNamespace(
            run=MagicMock(
                return_value=types.SimpleNamespace(
                    content="answer",
                    model="gpt-4o",
                    metrics={
                        "input_tokens": [10, 2],
                        "output_tokens": [3],
                        "total_tokens": [15],
                    },
                )
            )
        )
        api_server.session_state.llm_model = "gpt-4o"

        response = asyncio.run(api_server.ask_question(prompt="hello"))
        self.assertEqual(
            response,
            {
                "response": "answer",
                "metrics": {
                    "model": "gpt-4o",
                    "input_tokens": 12,
                    "output_tokens": 3,
                    "total_tokens": 15,
                },
            },
        )

    def test_ask_route_falls_back_to_message_metrics(self):
        api_server.session_state.rag_assistant = types.SimpleNamespace(
            run=MagicMock(
                return_value=types.SimpleNamespace(
                    content="answer",
                    model="gpt-4o",
                    metrics={},
                    messages=[
                        types.SimpleNamespace(role="user", metrics={"input_tokens": 999}),
                        types.SimpleNamespace(
                            role="assistant",
                            metrics={
                                "input_tokens": 20,
                                "output_tokens": 4,
                                "total_tokens": 24,
                            },
                        ),
                    ],
                )
            )
        )
        api_server.session_state.llm_model = "gpt-4o"

        response = asyncio.run(api_server.ask_question(prompt="hello"))

        self.assertEqual(
            response["metrics"],
            {
                "model": "gpt-4o",
                "input_tokens": 20,
                "output_tokens": 4,
                "total_tokens": 24,
            },
        )

    def test_ask_route_falls_back_to_model_metrics_delta(self):
        model = types.SimpleNamespace(
            metrics={
                "input_tokens": 100,
                "output_tokens": 10,
                "total_tokens": 110,
            }
        )

        def run(_prompt):
            model.metrics["input_tokens"] = 130
            model.metrics["output_tokens"] = 17
            model.metrics["total_tokens"] = 147
            return types.SimpleNamespace(content="answer", model="gpt-4o", metrics={})

        api_server.session_state.rag_assistant = types.SimpleNamespace(model=model, run=MagicMock(side_effect=run))
        api_server.session_state.llm_model = "gpt-4o"

        response = asyncio.run(api_server.ask_question(prompt="hello"))

        self.assertEqual(
            response["metrics"],
            {
                "model": "gpt-4o",
                "input_tokens": 30,
                "output_tokens": 7,
                "total_tokens": 37,
            },
        )

    def test_ask_route_defaults_missing_usage_to_zero(self):
        api_server.session_state.rag_assistant = types.SimpleNamespace(
            run=MagicMock(return_value=types.SimpleNamespace(content="answer", model="gpt-4o"))
        )
        api_server.session_state.llm_model = "gpt-4o"

        response = asyncio.run(api_server.ask_question(prompt="hello"))

        self.assertEqual(
            response["metrics"],
            {
                "model": "gpt-4o",
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            },
        )

    def test_clear_knowledge_base_is_idempotent_when_table_missing(self):
        client = TestClient(api_server.app)
        api_server.session_state.rag_assistant = object()
        api_server.session_state.embeddings_model = "text-embedding-3-small"

        fake_inspector = MagicMock()
        fake_inspector.has_table.return_value = False
        with patch("api_server.inspect", return_value=fake_inspector):
            response = client.post("/clear_knowledge_base/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "Knowledge base already empty",
                "table": "ai.local_rag_documents_text-embedding-3-small",
            },
        )

    def test_healthz_returns_ok_and_server_info(self):
        client = TestClient(api_server.app)
        response = client.get("/healthz/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["server_info"]["api_version"], rag_server_config.RAG_API_VERSION)

    def test_read_root_returns_html(self):
        client = TestClient(api_server.app)
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("content-type", ""))
        self.assertIn("Local RAG API", response.text)

    def test_chat_history_returns_session_messages(self):
        client = TestClient(api_server.app)
        response = client.get("/chat_history/")
        self.assertEqual(response.status_code, 200)
        messages = response.json()["messages"]
        self.assertTrue(messages)
        self.assertEqual(messages[0]["role"], "assistant")

    def test_new_run_resets_session(self):
        client = TestClient(api_server.app)
        api_server.session_state.rag_assistant = object()
        api_server.session_state.llm_model = "gpt-4o"
        response = client.post("/new_run/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "New run started"})
        self.assertIsNone(api_server.session_state.rag_assistant)
        self.assertIsNone(api_server.session_state.llm_model)

    def test_ask_requires_initialized_assistant(self):
        client = TestClient(api_server.app)
        response = client.post("/ask/", data={"prompt": "hello"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Agent not initialized")

    def test_upload_md_requires_initialized_assistant(self):
        client = TestClient(api_server.app)
        response = client.post(
            "/upload_md/",
            files={"file": ("x.md", b"# x", "text/markdown")},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Agent not initialized")

    def test_upload_pdf_requires_initialized_assistant(self):
        client = TestClient(api_server.app)
        response = client.post(
            "/upload_pdf/",
            files={"file": ("x.pdf", b"%PDF-1.4", "application/pdf")},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Agent not initialized")

    def test_add_url_requires_initialized_assistant(self):
        client = TestClient(api_server.app)
        response = client.post("/add_url/", data={"url": "https://example.com"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Agent not initialized")

    def test_add_url_requires_embeddings_model(self):
        client = TestClient(api_server.app)
        api_server.session_state.rag_assistant = object()
        api_server.session_state.embeddings_model = None
        response = client.post("/add_url/", data={"url": "https://example.com"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Embeddings model not initialized")

    def test_clear_knowledge_base_requires_embeddings_model(self):
        client = TestClient(api_server.app)
        api_server.session_state.rag_assistant = object()
        api_server.session_state.embeddings_model = None
        response = client.post("/clear_knowledge_base/")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Embeddings model not initialized")

    def test_add_url_success_calls_load_knowledge_document(self):
        api_server.session_state.rag_assistant = object()
        api_server.session_state.embeddings_model = "text-embedding-3-small"
        api_server.session_state.embeddings_provider = "openai"
        with patch("api_server.load_knowledge_document", return_value="local_rag_documents_text-embedding-3-small") as load_mock:
            response = asyncio.run(api_server.add_url(url="https://example.com/doc"))
        self.assertEqual(response["status"], "URL added")
        self.assertEqual(response["table"], "local_rag_documents_text-embedding-3-small")
        load_mock.assert_called_once_with(
            "https://example.com/doc",
            "local_rag_documents_text-embedding-3-small",
            "text-embedding-3-small",
            api_server.DB_URL,
            embeddings_provider="openai",
        )

    def test_upload_md_invokes_load_documents_when_reader_returns_docs(self):
        from phi.document import Document

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            def path_ctor(*parts):
                if len(parts) == 1 and isinstance(parts[0], str) and parts[0].startswith("./test_knowledge/"):
                    return tmp_path / parts[0].replace("./test_knowledge/", "")
                return Path(*parts)

            load_documents = MagicMock()
            api_server.session_state.rag_assistant = types.SimpleNamespace(
                knowledge=types.SimpleNamespace(load_documents=load_documents)
            )
            doc = Document(content="# Hello", meta_data={})
            with patch("api_server.Path", side_effect=path_ctor), patch("api_server.TextReader") as tr_mock:
                tr_mock.return_value.read.return_value = [doc]
                client = TestClient(api_server.app)
                response = client.post(
                    "/upload_md/",
                    files={"file": ("note.md", b"# Hello\n", "text/markdown")},
                )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "Markdown file uploaded")
            load_documents.assert_called_once()
            tr_mock.return_value.read.assert_called_once()
            read_path = tr_mock.return_value.read.call_args[0][0]
            self.assertEqual(read_path, tmp_path / "note.md")

    def test_upload_pdf_invokes_load_documents_when_reader_returns_docs(self):
        from phi.document import Document

        load_documents = MagicMock()
        api_server.session_state.rag_assistant = types.SimpleNamespace(
            knowledge=types.SimpleNamespace(load_documents=load_documents)
        )
        doc = Document(content="pdf text", meta_data={})
        with patch("api_server.PDFReader") as reader_mock:
            reader_mock.return_value.read.return_value = [doc]
            client = TestClient(api_server.app)
            response = client.post(
                "/upload_pdf/",
                files={"file": ("x.pdf", b"%PDF-1.4 fake", "application/pdf")},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "PDF uploaded")
        load_documents.assert_called_once()
        reader_mock.return_value.read.assert_called_once()

    def test_global_exception_handler_returns_json_detail(self):
        client = TestClient(api_server.app, raise_server_exceptions=False)
        with patch("api_server.build_server_info", side_effect=RuntimeError("kaput")):
            response = client.get("/healthz/")
        self.assertEqual(response.status_code, 500)
        self.assertIn("kaput", response.json()["detail"])


class RagApiTests(unittest.TestCase):
    def setUp(self):
        rag_api.reset_compatibility_cache()

    def tearDown(self):
        rag_api.reset_compatibility_cache()

    def _server_info_response(self, **overrides):
        response = MagicMock()
        response.ok = True
        payload = {
            "api_version": rag_server_config.RAG_API_VERSION,
            "repo_signature": rag_server_config.compute_repo_signature(),
            "server_pid": 123,
            "server_started_at": "2026-03-24T17:00:00+00:00",
            "module_path": "C:/repo/api_server.py",
        }
        payload.update(overrides)
        response.json.return_value = payload
        return response

    def test_initialize_assistant_surfaces_non_json_http_errors(self):
        class FakeResponse:
            status_code = 502
            text = "upstream failed hard"
            reason = "Bad Gateway"

            def raise_for_status(self):
                raise requests.HTTPError("boom", response=self)

            def json(self):
                raise ValueError("not json")

        with patch("debug_assistant_latest.rag_api.requests.get", return_value=self._server_info_response()), patch(
            "debug_assistant_latest.rag_api.requests.request", return_value=FakeResponse()
        ):
            with self.assertRaisesRegex(RuntimeError, "status 502: upstream failed hard"):
                rag_api.initialize_assistant("gpt-5-mini")

    def test_initialize_assistant_sends_embeddings_provider_when_configured(self):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"status": "ok"}

        with patch("debug_assistant_latest.rag_api.requests.get", return_value=self._server_info_response()), patch(
            "debug_assistant_latest.rag_api.requests.request", return_value=response
        ) as request_mock:
            payload = rag_api.initialize_assistant(
                "gpt-5-mini",
                embeddings_model="text-embedding-3-small",
                embeddings_provider="openai",
            )

        self.assertEqual(payload, {"status": "ok"})
        self.assertEqual(
            request_mock.call_args.kwargs["data"],
            {
                "llm_model": "gpt-5-mini",
                "embeddings_model": "text-embedding-3-small",
                "embeddings_provider": "openai",
            },
        )

    def test_initialize_assistant_rejects_incompatible_server_before_request(self):
        with patch(
            "debug_assistant_latest.rag_api.requests.get",
            return_value=self._server_info_response(repo_signature="stale-signature"),
        ), patch("debug_assistant_latest.rag_api.requests.request") as request_mock:
            with self.assertRaisesRegex(RuntimeError, "RAG API server mismatch detected"):
                rag_api.initialize_assistant("gpt-5-mini")

        request_mock.assert_not_called()

    def test_consecutive_api_calls_fetch_server_info_once_per_base_url(self):
        rag_api.reset_compatibility_cache()
        fixed_base = "http://127.0.0.1:8765"
        expected_info_url = f"{fixed_base}{rag_api.SERVER_INFO_PATH}"

        info_response = self._server_info_response()
        post_response = MagicMock()
        post_response.raise_for_status.return_value = None
        post_response.json.return_value = {"status": "ok"}

        get_urls = []

        def capture_get(url, **kwargs):
            get_urls.append(url)
            return info_response

        with patch.object(rag_api, "get_base_url", return_value=fixed_base), patch(
            "debug_assistant_latest.rag_api.requests.get", side_effect=capture_get
        ), patch("debug_assistant_latest.rag_api.requests.request", return_value=post_response):
            rag_api.initialize_assistant("gpt-5-mini")
            rag_api.ask_question("hello")

        info_gets = [u for u in get_urls if u == expected_info_url]
        self.assertEqual(len(info_gets), 1, f"expected one GET {expected_info_url}, got {get_urls}")


class SingleAgentTests(unittest.TestCase):
    def test_prepare_prompt_includes_shared_operational_guardrails(self):
        from debug_assistant_latest.debug_agents import SingleAgent

        config = {
            "debug-agent": {"instructions": [], "guidelines": []},
            "debug-prompt": {"additional-directions": "Reapply changed manifests."},
            "test-directory": str(DEBUG_DIR / "troubleshooting" / "wrong_port"),
            "yaml-file-name": "wrong_port.yaml",
            "relevant-files": {
                "deployment": [],
                "application": [],
                "service": [],
                "dockerfile": False,
            },
            "ground-truth": {"checks": [{"name": "port_aligned"}]},
        }

        agent = SingleAgent("single-agent", config)
        agent.prompt = "The pod cannot be reached. "
        agent.preparePrompt()

        self.assertIn("Do not use `kubectl port-forward`", agent.prompt)
        self.assertIn("Prefer durable fixes", agent.prompt)
        self.assertIn("Minikube Image Guidance", agent.prompt)
        self.assertIn("Reapply changed manifests.", agent.prompt)
        self.assertNotIn("ground-truth", agent.prompt)
        self.assertNotIn("port_aligned", agent.prompt)

    def test_prepare_agent_uses_configured_model_and_embedder_settings(self):
        from debug_assistant_latest.debug_agents import SingleAgent

        config = {
            "api-agent": {
                "model": "gpt-5-mini",
                "embedder": "text-embedding-3-small",
                "embedder-provider": "openai",
                "knowledge": ["https://example.com"],
            },
            "debug-agent": {
                "model": "gpt-5-nano",
                "instructions": [],
                "guidelines": [],
            },
            "debug-prompt": {"additional-directions": ""},
            "test-directory": "",
            "yaml-file-name": "wrong_port.yaml",
            "relevant-files": {
                "deployment": [],
                "application": [],
                "service": [],
                "dockerfile": False,
            },
        }

        agent = SingleAgent("single-agent", config)
        fake_llm_agent = object()
        resolved_embedder = runtime_config.ResolvedEmbedder(
            config=runtime_config.EmbedderConfig(model="text-embedding-3-small", provider="openai"),
            embedder="embedder",
        )
        with patch("debug_assistant_latest.debug_agents.build_model", return_value="model") as build_model_mock, patch(
            "debug_assistant_latest.debug_agents.build_resolved_embedder",
            return_value=resolved_embedder,
        ) as build_embedder_mock, patch(
            "debug_assistant_latest.debug_agents.PgVector", return_value="pgvector"
        ) as pgvector_mock, patch(
            "debug_assistant_latest.debug_agents.WebsiteKnowledgeBase", return_value="knowledge"
        ), patch("debug_assistant_latest.debug_agents.BetterShellTools", return_value="tool"), patch(
            "debug_assistant_latest.debug_agents.llmAgent", return_value=fake_llm_agent
        ):
            agent.prepareAgent()

        self.assertIs(agent.agent, fake_llm_agent)
        build_model_mock.assert_called_once_with("gpt-5-nano")
        build_embedder_mock.assert_called_once_with(
            embeddings_model="text-embedding-3-small",
            provider="openai",
            chat_model_name="gpt-5-nano",
        )
        self.assertEqual(pgvector_mock.call_args.kwargs["table_name"], "local_rag_documents_text-embedding-3-small")


class ApiServerSupportTests(unittest.TestCase):
    def test_session_state_reset_run_restores_default_message(self):
        session = SessionState()
        session.messages.append({"role": "user", "content": "hello"})
        session.rag_assistant = object()
        session.rag_assistant_run_id = "abc"

        session.reset_run()

        self.assertIsNone(session.rag_assistant)
        self.assertIsNone(session.rag_assistant_run_id)
        self.assertIsNone(session.llm_model)
        self.assertIsNone(session.embeddings_model)
        self.assertIsNone(session.embeddings_provider)
        self.assertEqual(session.messages, [{"role": "assistant", "content": "Upload a doc and ask me questions..."}])

    def test_knowledge_table_name_uses_embedding_model(self):
        self.assertEqual(knowledge_table_name("nomic-embed-text"), "local_rag_documents_nomic-embed-text")

    def test_load_knowledge_document_uses_shared_embedder_builder(self):
        from phi.document import Document

        fake_kb = MagicMock()
        fake_embedder = MagicMock()
        resolved_embedder = runtime_config.ResolvedEmbedder(
            config=runtime_config.EmbedderConfig(model="text-embedding-3-small", provider="openai"),
            embedder=fake_embedder,
        )

        with patch("api_server_support.build_resolved_embedder", return_value=resolved_embedder) as build_embedder_mock, patch(
            "api_server_support.scrape_url_to_document",
            return_value=Document(content="doc", meta_data={"source": "https://example.com"}),
        ), patch("phi.agent.AgentKnowledge", return_value=fake_kb), patch(
            "phi.vectordb.pgvector.PgVector", return_value="vector_db"
        ) as pgvector_mock:
            table_name = api_server_support.load_knowledge_document(
                "https://example.com",
                "local_rag_documents_text-embedding-3-small",
                "text-embedding-3-small",
                "postgresql://example",
                embeddings_provider="openai",
            )

        build_embedder_mock.assert_called_once_with("text-embedding-3-small", provider="openai")
        self.assertEqual(table_name, "local_rag_documents_text-embedding-3-small")
        self.assertEqual(pgvector_mock.call_args.kwargs["table_name"], "local_rag_documents_text-embedding-3-small")
        loaded_documents = fake_kb.load_documents.call_args.args[0]
        self.assertEqual(len(loaded_documents), 1)
        self.assertEqual(loaded_documents[0].content, "doc")
        self.assertTrue(fake_kb.load_documents.call_args.kwargs["upsert"])

    def test_load_knowledge_document_repeated_loads_use_upsert(self):
        from phi.document import Document

        fake_kb = MagicMock()
        resolved_embedder = runtime_config.ResolvedEmbedder(
            config=runtime_config.EmbedderConfig(model="text-embedding-3-small", provider="openai"),
            embedder=MagicMock(),
        )

        with patch("api_server_support.build_resolved_embedder", return_value=resolved_embedder), patch(
            "api_server_support.scrape_url_to_document",
            return_value=Document(content="doc", meta_data={"source": "https://example.com"}),
        ), patch("phi.agent.AgentKnowledge", return_value=fake_kb), patch(
            "phi.vectordb.pgvector.PgVector", return_value="vector_db"
        ):
            for _ in range(2):
                api_server_support.load_knowledge_document(
                    "https://example.com",
                    "local_rag_documents_text-embedding-3-small",
                    "text-embedding-3-small",
                    "postgresql://example",
                    embeddings_provider="openai",
                )

        self.assertEqual(fake_kb.load_documents.call_count, 2)
        self.assertTrue(all(call.kwargs["upsert"] for call in fake_kb.load_documents.call_args_list))

    def test_load_knowledge_document_surfaces_provider_preflight_error(self):
        with patch(
            "api_server_support.build_resolved_embedder",
            side_effect=RuntimeError("openai embedder failed preflight"),
        ):
            with self.assertRaisesRegex(RuntimeError, "openai embedder failed preflight"):
                api_server_support.load_knowledge_document(
                    "https://example.com",
                    "local_rag_documents_text-embedding-3-small",
                    "text-embedding-3-small",
                    "postgresql://example",
                    embeddings_provider="openai",
                )

    def test_load_knowledge_document_chunks_large_documents_before_load(self):
        from phi.document import Document

        fake_kb = MagicMock()
        fake_embedder = MagicMock()
        fake_embedder.get_embedding_and_usage.return_value = ([0.1, 0.2], {"total_tokens": 1})
        large_document = Document(
            content=("0123456789 " * 600),
            meta_data={"source": "https://example.com", "title": "Example"},
        )

        resolved_embedder = runtime_config.ResolvedEmbedder(
            config=runtime_config.EmbedderConfig(model="nomic-embed-text", provider="ollama"),
            embedder=fake_embedder,
        )

        with patch("api_server_support.build_resolved_embedder", return_value=resolved_embedder), patch(
            "api_server_support.scrape_url_to_document", return_value=large_document
        ), patch("phi.agent.AgentKnowledge", return_value=fake_kb), patch(
            "phi.vectordb.pgvector.PgVector", return_value="vector_db"
        ):
            api_server_support.load_knowledge_document(
                "https://example.com",
                "local_rag_documents_nomic-embed-text",
                "nomic-embed-text",
                "postgresql://example",
                embeddings_provider="ollama",
            )

        loaded_documents = fake_kb.load_documents.call_args.args[0]
        self.assertGreater(len(loaded_documents), 1)
        self.assertTrue(
            all(len(doc.content) <= api_server_support.EMBEDDING_CHUNK_SIZE_CHARS for doc in loaded_documents)
        )
        self.assertEqual(loaded_documents[0].meta_data["source"], "https://example.com")
        self.assertEqual(loaded_documents[0].meta_data["chunk_index"], 1)
        self.assertEqual(loaded_documents[-1].meta_data["chunk_count"], len(loaded_documents))


if __name__ == "__main__":
    unittest.main()
