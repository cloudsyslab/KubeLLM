import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

from debug_assistant_latest import lab_context
from debug_assistant_latest import cli, teardown, utils


class LabContextTests(unittest.TestCase):
    def _write_lane(self, root: Path) -> Path:
        env_file = root / "services.env"
        env_file.write_text("KUBELLM_DB_URL=postgresql+psycopg2://lane:secret@127.0.0.1:5533/lane\n")
        env_file.chmod(0o600)
        kubeconfig = root / "lane.kubeconfig"
        kubeconfig.write_text("apiVersion: v1\n")
        kubeconfig.chmod(0o600)
        config = root / "lane.json"
        config.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "lane_id": "minh",
                    "minikube_profile": "minh-lane",
                    "minikube_container": "minh-lane",
                    "kubeconfig_path": str(kubeconfig),
                    "service_env_file": str(env_file),
                    "rag_api_url": "http://127.0.0.1:18001",
                    "pgvector_container": "kubellm-minh-pgvector",
                }
            )
        )
        config.chmod(0o600)
        return config

    def test_load_lane_requires_private_config_and_services(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = self._write_lane(root)
            loaded = lab_context.load_lane_config(config_path)
            self.assertEqual(loaded["minikube_profile"], "minh-lane")
            self.assertEqual(loaded["database_port"], 5533)

            config_path.chmod(0o644)
            with self.assertRaisesRegex(lab_context.LaneConfigurationError, "owner-only"):
                lab_context.load_lane_config(config_path)

    def test_load_lane_rejects_shared_service_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = self._write_lane(root)
            env_file = root / "services.env"
            env_file.write_text("KUBELLM_DB_URL=postgresql+psycopg2://lane:secret@localhost:5532/ai\n")
            env_file.chmod(0o600)
            with self.assertRaisesRegex(lab_context.LaneConfigurationError, "dedicated local"):
                lab_context.load_lane_config(config_path)

    def test_load_lane_rejects_shared_minikube_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = self._write_lane(root)
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["minikube_profile"] = "minikube"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            config_path.chmod(0o600)
            with self.assertRaisesRegex(lab_context.LaneConfigurationError, "dedicated profile"):
                lab_context.load_lane_config(config_path)

    def test_bootstrap_pins_profile_and_rejects_cli_override(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True):
            config_path = self._write_lane(Path(tmp))
            lane = lab_context.bootstrap_from_argv(["--lab-config", str(config_path)])
            self.assertEqual(lane["lane_id"], "minh")
            self.assertEqual(os.environ["MINIKUBE_PROFILE"], "minh-lane")
            self.assertEqual(os.environ["KUBECONFIG"], str(Path(tmp) / "lane.kubeconfig"))
            with self.assertRaisesRegex(lab_context.LaneConfigurationError, "conflicts"):
                lab_context.bootstrap_from_argv(
                    ["--lab-config", str(config_path), "--minikube-profile", "someone-elses-profile"]
                )

    def test_active_marker_without_selector_fails_closed(self):
        with patch.dict(os.environ, {"KUBELLM_LAB_ACTIVE": "1"}, clear=True):
            with self.assertRaisesRegex(lab_context.LaneConfigurationError, "KUBELLM_LAB_CONFIG"):
                lab_context.bootstrap_from_argv([])

    def test_agent_commands_cannot_redirect_lane_or_mutate_host_docker(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True):
            config_path = self._write_lane(Path(tmp))
            lab_context.bootstrap_from_argv(["--lab-config", str(config_path)])
            self.assertIsNotNone(lab_context.lane_command_block_reason("kubectl get pods --context someone-else"))
            self.assertIsNotNone(lab_context.lane_command_block_reason("docker rm -f container"))
            self.assertIsNotNone(lab_context.lane_command_block_reason("minikube -p other start"))
            self.assertIsNotNone(lab_context.lane_command_block_reason("minikube start"))
            self.assertIsNotNone(lab_context.lane_command_block_reason("minikube -p minh-lane start"))
            self.assertIsNone(lab_context.lane_command_block_reason("minikube -p minh-lane status"))

    def test_database_identity_omits_password_but_separates_lane_ports(self):
        first = lab_context.database_identity("postgresql+psycopg://lane:secret@localhost:5533/db")
        second = lab_context.database_identity("postgresql+psycopg://lane:other@localhost:5533/db")
        other_lane = lab_context.database_identity("postgresql+psycopg://lane:secret@localhost:5534/db")
        self.assertEqual(first, second)
        self.assertNotEqual(first, other_lane)
        self.assertNotIn("secret", first)

    def test_checked_in_build_tags_are_redirected_to_lane_image_build(self):
        config = {
            "_lane_local_images": ["never-pull:latest"],
            "setup-commands": [
                "bash -lc 'minikube image build -t app:latest; else docker build -t app:latest -f Dockerfile .'"
            ],
        }
        self.assertEqual(
            lab_context.configured_local_images(config),
            ["never-pull:latest", "app:latest"],
        )

    def test_lane_run_lock_rejects_concurrent_use(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True):
            config_path = self._write_lane(Path(tmp))
            lab_context.bootstrap_from_argv(["--lab-config", str(config_path)])
            lock_path = Path(tmp) / "lock" / "runner.lock"
            with patch.object(lab_context, "lane_lock_path", return_value=lock_path):
                with lab_context.LaneRunLock():
                    with self.assertRaisesRegex(lab_context.LaneConfigurationError, "Another experiment"):
                        with lab_context.LaneRunLock():
                            pass

    def test_lane_setup_replaces_checked_in_host_docker_builds(self):
        lane = {"minikube_profile": "minh-lane", "kubeconfig_path": "/tmp/lane.kubeconfig"}
        with patch.dict(os.environ, {"KUBELLM_LAB_ACTIVE": "1"}, clear=False), patch.object(
            lab_context, "active_lane_config", return_value=lane
        ), patch.object(lab_context, "assert_lane_target"), patch.object(
            lab_context, "prepare_lane_images"
        ) as prepare, patch.object(utils, "_local_never_pull_images", return_value=["case:latest"]), patch.object(
            utils, "validate_local_images_available"
        ), patch.object(utils.subprocess, "run") as run:
            utils.setUpEnvironment(
                {
                    "minikube-profile": "minh-lane",
                    "setup-commands": ["bash -lc 'minikube image build -t case:latest; else docker build -t case:latest'"],
                }
            )
        prepare.assert_called_once()
        self.assertEqual(prepare.call_args.args[0]["_lane_local_images"], ["case:latest"])
        run.assert_not_called()

    def test_lane_cli_routes_each_technique_through_same_guarded_entrypoint(self):
        seen = []
        for technique in ("allStepsAtOnce", "stepByStep", "singleAgent", "knowledgeAgentOnly"):
            with patch.object(cli.sys, "argv", ["runner.py", "wrong_port", "--technique", technique]), patch.object(
                cli, "is_lane_active", return_value=True
            ), patch.object(
                cli, "bootstrap_from_argv", return_value={"minikube_profile": "minh-lane", "rag_api_url": "http://127.0.0.1:18001"}
            ), patch.object(cli, "LaneRunLock", nullcontext), patch.object(
                cli, "list_test_cases", return_value=["wrong_port"]
            ), patch.object(cli, "cmd_run_single", side_effect=lambda args, _case: seen.append(args.technique) or 0):
                self.assertEqual(cli.main(), 0)
        self.assertEqual(seen, ["allStepsAtOnce", "stepByStep", "singleAgent", "knowledgeAgentOnly"])

    def test_runner_lane_dry_run_bootstraps_all_techniques_without_execution(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self._write_lane(Path(tmp))
            env = os.environ.copy()
            env.pop("KUBELLM_LAB_CONFIG", None)
            env.pop("KUBELLM_LAB_ACTIVE", None)
            for technique in ("allStepsAtOnce", "stepByStep", "singleAgent", "knowledgeAgentOnly"):
                proc = subprocess.run(
                    [
                        sys.executable,
                        str(repo / "debug_assistant_latest" / "runner.py"),
                        "--lab-config",
                        str(config_path),
                        "wrong_port",
                        "--technique",
                        technique,
                        "--dry-run",
                    ],
                    cwd=repo,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertIn(f"technique={technique}", proc.stdout)
                self.assertIn("lane=minh", proc.stdout)

    def test_single_case_dry_run_exits_before_runner_execution(self):
        with patch.object(cli.sys, "argv", ["runner.py", "wrong_port", "--dry-run"]), patch.object(
            cli, "is_lane_active", return_value=False
        ), patch.object(cli, "list_test_cases", return_value=["wrong_port"]), patch.object(
            cli, "cmd_run_single"
        ) as run_case:
            self.assertEqual(cli.main(), 0)
        run_case.assert_not_called()

    def test_lane_teardown_never_uses_host_docker_or_namespace_sweep(self):
        lane = {"minikube_profile": "minh-lane"}
        with tempfile.TemporaryDirectory() as tmp, patch.object(teardown, "is_lane_active", return_value=True), patch.object(
            teardown, "active_lane_config", return_value=lane
        ), patch.object(teardown, "assert_lane_target"), patch.object(
            teardown, "cleanup_transient_k8s_resources"
        ), patch.object(teardown, "FIXTURE_BASELINES_DIR", Path(tmp)), patch.object(
            teardown.subprocess, "run"
        ) as run:
            teardown.teardown_environment("wrong_interface")
        commands = [call.args[0] for call in run.call_args_list]
        self.assertTrue(any(command[:5] == ["minikube", "-p", "minh-lane", "image", "rm"] for command in commands))
        self.assertFalse(any(command and command[0] == "docker" for command in commands))
        self.assertFalse(any(command[:3] == ["kubectl", "delete", "pods"] and "--all" in command for command in commands))


if __name__ == "__main__":
    unittest.main()
