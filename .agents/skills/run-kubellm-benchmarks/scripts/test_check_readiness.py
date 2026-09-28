from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import check_readiness as readiness


def completed(argv, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(argv, returncode, stdout, stderr)


class ReadinessSafetyTests(unittest.TestCase):
    def context(self, root: Path) -> readiness.Readiness:
        return readiness.Readiness(root, "wrong_port", "auto", "check-only", False)

    def test_missing_and_placeholder_provider_keys_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp))
            ctx.effective = {"providers": ["openai"]}
            ctx.runtime_env.pop("OPENAI_API_KEY", None)
            readiness.required_provider_variables(ctx)
            self.assertEqual(ctx.checks[-1].status, "fail")

            ctx.checks.clear()
            ctx.runtime_env["OPENAI_API_KEY"] = "your_openai_api_key_here"
            readiness.required_provider_variables(ctx)
            self.assertEqual(ctx.checks[-1].status, "fail")

    def test_invalid_live_key_is_redacted_and_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp))
            fake_key = "invalid-key-material"
            ctx.runtime_env["OPENAI_API_KEY"] = fake_key
            ctx.secret_values.append(fake_key)
            ctx.effective = {
                "providers": ["openai"],
                "models": [{"role": "api-agent", "provider": "openai", "model": "gpt-test"}],
            }
            with mock.patch.object(readiness, "http_status", return_value=(False, "HTTP 401")):
                readiness.live_provider_probe(ctx)
            self.assertEqual(ctx.checks[-1].status, "fail")
            self.assertNotIn(fake_key, json.dumps(ctx.report()))

    def test_stale_kubeconfig_certificate_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            kubeconfig = root / "config"
            kubeconfig.write_text("apiVersion: v1\n", encoding="utf-8")
            ctx = self.context(root)

            def fake_run(argv, **kwargs):
                if "view" in argv:
                    return completed(argv, 1, "", "view failed")
                return completed(argv, 1, "", "x509: certificate signed by unknown authority")

            with mock.patch.object(readiness, "run", side_effect=fake_run):
                ok, _, message = readiness.inspect_kubeconfig(ctx, kubeconfig)
            self.assertFalse(ok)
            self.assertIn("certificate", message)

    def test_incompatible_foreign_rag_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp))
            ctx.effective = {
                "rag_api_url": "http://127.0.0.1:18000",
                "rag_api_version": "expected",
                "rag_signature": "expected-signature",
            }
            payload = {
                "api_version": "old",
                "repo_signature": "foreign-signature",
                "repo_root": "/foreign/KubeLLM",
                "module_path": "/foreign/KubeLLM/api_server.py",
            }
            with mock.patch.object(readiness, "fetch_json", return_value=(payload, "ok")):
                readiness.check_rag(ctx)
            self.assertEqual(ctx.checks[-1].status, "fail")
            self.assertIn("incompatible", ctx.checks[-1].message)

    def test_lane_accepts_matching_rag_service_from_another_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp))
            database_url = "postgresql://lane:secret@127.0.0.1:5533/lane"
            database_identity = readiness.lane_database_identity(database_url)
            ctx.runtime_env["KUBELLM_DB_URL"] = database_url
            ctx.lane = {"lane_id": "minh", "rag_api_url": "http://127.0.0.1:18004", "rag_port": 18004}
            ctx.effective = {
                "rag_api_url": "http://127.0.0.1:18004",
                "rag_api_version": "version",
                "rag_signature": "same-code",
            }
            payload = {
                "api_version": "version",
                "repo_signature": "same-code",
                "repo_root": "/another/checkout",
                "server_port": 18004,
                "server_bind_host": "127.0.0.1",
                "database_identity": database_identity,
            }
            with mock.patch.object(readiness, "fetch_json", return_value=(payload, "ok")):
                readiness.check_rag(ctx)

            self.assertEqual(ctx.checks[-1].status, "pass")
            self.assertIn("checkout path is informational", ctx.checks[-1].message)

    def test_lane_rejects_matching_rag_code_when_database_identity_differs(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp))
            ctx.runtime_env["KUBELLM_DB_URL"] = "postgresql://lane:secret@127.0.0.1:5533/lane"
            ctx.lane = {"lane_id": "minh", "rag_api_url": "http://127.0.0.1:18004", "rag_port": 18004}
            ctx.effective = {
                "rag_api_url": "http://127.0.0.1:18004",
                "rag_api_version": "version",
                "rag_signature": "same-code",
            }
            payload = {
                "api_version": "version",
                "repo_signature": "same-code",
                "repo_root": "/another/checkout",
                "server_port": 18004,
                "server_bind_host": "127.0.0.1",
                "database_identity": "wrong-lane-database",
            }
            with mock.patch.object(readiness, "fetch_json", return_value=(payload, "ok")):
                readiness.check_rag(ctx)

            self.assertEqual(ctx.checks[-1].status, "fail")
            self.assertIn("database identity", ctx.checks[-1].message)

    def test_feature_branch_and_dirty_tree_do_not_block_personal_lane(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / ".git").mkdir()
            runner = root / readiness.RUNNER
            runner.parent.mkdir(parents=True)
            runner.write_text("", encoding="utf-8")
            ctx = self.context(root)

            def fake_run(argv, **kwargs):
                text = " ".join(argv)
                if "--show-toplevel" in argv:
                    return completed(argv, stdout=str(root) + "\n")
                if argv[-3:] == ["remote", "get-url", "origin"]:
                    return completed(argv, stdout="https://github.com/cloudsyslab/KubeLLM.git\n")
                if argv[-2:] == ["branch", "--show-current"]:
                    return completed(argv, stdout="poc/lab-isolation\n")
                if "status" in argv:
                    return completed(argv, stdout=" M debug_assistant_latest/troubleshooting/case/file\n")
                self.fail(f"unhandled git command: {text}")

            with mock.patch.object(readiness, "run", side_effect=fake_run):
                readiness.check_repo(ctx)
            checks = {check.name: check for check in ctx.checks}
            self.assertEqual(checks["repository_identity"].status, "pass")
            self.assertEqual(checks["repository_identity"].details["branch"], "poc/lab-isolation")
            self.assertEqual(len(checks["repository_identity"].details["dirty_paths"]), 1)

    def test_missing_dependencies_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "requirements.lock").write_text("pytest==1.2.3\n", encoding="utf-8")
            ctx = self.context(root)
            readiness.check_venv(ctx)
            checks = {check.name: check for check in ctx.checks}
            self.assertEqual(checks["virtual_environment"].status, "fail")

    def test_stopped_workspace_owned_pgvector_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            ctx = self.context(root)
            payload = {
                "Config": {
                    "Labels": {"io.kubellm.repo": str(root)},
                    "Image": "phidata/pgvector:16",
                },
                "State": {"Running": False},
            }

            def fake_run(argv, **kwargs):
                if "ps" in argv:
                    return completed(argv, stdout="kubellm-minh-pgvector\n")
                return completed(argv, stdout=json.dumps(payload))

            with mock.patch.object(readiness, "run", side_effect=fake_run):
                ok, _, _ = readiness.inspect_pgvector_owner(ctx)
            self.assertFalse(ok)

    def test_pgvector_lane_label_and_target_name_allow_another_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp))
            ctx.lane = {"lane_id": "minh", "pgvector_container": "kubellm-minh-pgvector"}
            ctx.runtime_env["KUBELLM_DB_URL"] = "postgresql://lane:secret@127.0.0.1:5533/lane"
            payload = {
                "Config": {
                    "Labels": {
                        "io.kubellm.repo": "/another/checkout",
                        "io.kubellm.lane": "minh",
                    },
                    "Image": "phidata/pgvector:16",
                },
                "State": {"Running": True},
            }

            def fake_run(argv, **kwargs):
                if argv[:2] == ["docker", "ps"]:
                    return completed(argv, stdout="kubellm-minh-pgvector\n")
                return completed(argv, stdout=json.dumps(payload))

            with mock.patch.object(readiness, "run", side_effect=fake_run):
                ok, details, _ = readiness.inspect_pgvector_owner(ctx)

            self.assertTrue(ok)
            self.assertEqual(details["owner_lane"], "minh")

    def test_pgvector_from_another_lane_still_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp))
            ctx.lane = {"lane_id": "minh", "pgvector_container": "kubellm-minh-pgvector"}
            ctx.runtime_env["KUBELLM_DB_URL"] = "postgresql://lane:secret@127.0.0.1:5533/lane"
            payload = {
                "Config": {"Labels": {"io.kubellm.repo": str(ctx.repo), "io.kubellm.lane": "another-lane"}},
                "State": {"Running": True},
            }

            def fake_run(argv, **kwargs):
                if argv[:2] == ["docker", "ps"]:
                    return completed(argv, stdout="kubellm-minh-pgvector\n")
                return completed(argv, stdout=json.dumps(payload))

            with mock.patch.object(readiness, "run", side_effect=fake_run):
                ok, _, message = readiness.inspect_pgvector_owner(ctx)

            self.assertFalse(ok)
            self.assertIn("foreign or ambiguous", message)

    def test_stopped_workspace_rag_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp))
            ctx.effective = {
                "rag_api_url": "http://127.0.0.1:18000",
                "rag_api_version": "version",
                "rag_signature": "signature",
            }
            with mock.patch.object(readiness, "fetch_json", return_value=(None, "ConnectionRefusedError")):
                readiness.check_rag(ctx)
            self.assertEqual(ctx.checks[-1].status, "fail")

    def test_env_template_never_activates_placeholder_secret(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            example = root / ".env.example"
            destination = root / ".env"
            example.write_text(
                "OPENAI_API_KEY=your_openai_api_key_here\nRAG_SERVER_PORT=18000\n",
                encoding="utf-8",
            )
            readiness.prepare_env_template(example, destination)
            values = readiness.parse_env_file(destination)
            self.assertNotIn("OPENAI_API_KEY", values)
            self.assertEqual(values["RAG_SERVER_PORT"], "18000")

    def test_safe_single_dry_run_contract_is_recognized(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cli = root / "debug_assistant_latest" / "cli.py"
            cli.parent.mkdir(parents=True)
            cli.write_text(
                "def main():\n"
                "    args = parser.parse_args()\n"
                "    if args.test_case:\n"
                "        if args.dry_run:\n"
                "            print('Dry run')\n"
                "            return 0\n"
                "        return cmd_run_single(args, args.test_case)\n",
                encoding="utf-8",
            )
            self.assertTrue(readiness.single_dry_run_is_safe(root))

    def test_check_only_directory_probe_does_not_create_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "not-created" / "services"
            ok, _ = readiness.writable_directory(target)
            self.assertTrue(ok)
            self.assertFalse(target.exists())

    def test_missing_lane_config_blocks_without_contacting_runner_or_services(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ctx = readiness.Readiness(
                root, "wrong_port", "auto", "check-only", False, root / "missing-lane.json"
            )
            with mock.patch.object(readiness, "run") as run_cmd, mock.patch.object(
                readiness, "check_runner_static_gates"
            ) as static_gates, mock.patch.object(readiness, "check_pgvector") as pgvector:
                report = readiness.execute(ctx)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertTrue(ctx.report_path.is_file())
            self.assertFalse(ctx.services_dir.exists())
            run_cmd.assert_not_called()
            static_gates.assert_not_called()
            pgvector.assert_not_called()

    def test_lane_config_is_never_guessed_from_personal_defaults(self):
        with mock.patch.dict(readiness.os.environ, {"KUBELLM_LAB_CONFIG": ""}):
            args = readiness.build_parser().parse_args([])
            self.assertIsNone(args.lab_config)
            with tempfile.TemporaryDirectory() as tmp:
                ctx = readiness.Readiness(Path(tmp), "wrong_port", "auto", "check-only", False, args.lab_config)
                readiness.load_lane_config(ctx)
                self.assertEqual(ctx.checks[-1].name, "lab_lane_config")
                self.assertEqual(ctx.checks[-1].status, "fail")
                self.assertIn("--lab-config", ctx.checks[-1].message)

    def test_check_only_does_not_write_lab_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = readiness.Readiness(Path(tmp), "wrong_port", "auto", "check-only", False)
            readiness.write_lab_env(ctx)
            self.assertFalse(ctx.services_dir.exists())

    def test_runner_command_always_passes_selected_lane_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lane_path = root / "minh.json"
            ctx = readiness.Readiness(root, "wrong_port", "auto", "check-only", False, lane_path)
            ctx.lane = {"lane_id": "minh"}
            with mock.patch.object(readiness, "run", return_value=completed([], stdout="ok")) as run_cmd:
                rc, stdout, _ = readiness.runner_command(ctx, "list", ["--list"])
            self.assertEqual((rc, stdout), (0, "ok"))
            self.assertIn("--lab-config", run_cmd.call_args.args[0])
            self.assertIn(str(lane_path.resolve()), run_cmd.call_args.args[0])

    def test_repair_safe_accepts_only_a_healthy_owned_minikube_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ctx = readiness.Readiness(root, "wrong_port", "auto", "repair-safe", False)
            ctx.lane = {
                "minikube_profile": "minh-lane",
                "minikube_container": "minh-lane",
            }
            payload = {
                "Config": {"Labels": {
                    "created_by.minikube.sigs.k8s.io": "true",
                    "name.minikube.sigs.k8s.io": "minh-lane",
                }},
                "State": {"Running": True},
            }

            def fake_run(argv, **kwargs):
                if argv[:4] == ["minikube", "-p", "minh-lane", "status"]:
                    return completed(argv, stdout="Running\n")
                if argv[:2] == ["docker", "inspect"]:
                    return completed(argv, stdout=json.dumps(payload))
                self.fail(f"unexpected command: {argv}")

            with mock.patch.object(readiness, "run", side_effect=fake_run) as run_cmd:
                self.assertTrue(readiness.repair_minikube_profile(ctx))
            self.assertEqual(ctx.repairs[-1].status, "pass")
            self.assertFalse(any("start" in call.args[0] for call in run_cmd.call_args_list))

    def test_repair_safe_refuses_foreign_container_at_selected_node_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ctx = readiness.Readiness(root, "wrong_port", "auto", "repair-safe", False)
            ctx.lane = {
                "minikube_profile": "minh-lane",
                "minikube_container": "minh-lane",
            }
            foreign = {
                "Config": {"Labels": {
                    "created_by.minikube.sigs.k8s.io": "true",
                    "name.minikube.sigs.k8s.io": "researcher-lane",
                }},
                "State": {"Running": False},
            }

            def fake_run(argv, **kwargs):
                if argv[:4] == ["minikube", "-p", "minh-lane", "status"]:
                    return completed(argv, 1)
                if argv[:2] == ["docker", "inspect"]:
                    return completed(argv, stdout=json.dumps(foreign))
                self.fail(f"unexpected command: {argv}")

            with mock.patch.object(readiness, "run", side_effect=fake_run) as run_cmd:
                self.assertFalse(readiness.repair_minikube_profile(ctx))
            self.assertEqual(ctx.repairs[-1].status, "fail")
            self.assertIn("foreign or ambiguous", ctx.repairs[-1].message)
            self.assertFalse(any("start" in call.args[0] for call in run_cmd.call_args_list))

    def test_repair_safe_refuses_minikube_start_below_docker_space_floor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ctx = readiness.Readiness(root, "wrong_port", "auto", "repair-safe", False)
            kubeconfig = root / "private" / "lane.kubeconfig"
            ctx.lane = {
                "minikube_profile": "minh-lane",
                "minikube_container": "minh-lane",
                "kubeconfig_path": str(kubeconfig),
            }

            def fake_run(argv, **kwargs):
                if argv[:4] == ["minikube", "-p", "minh-lane", "status"]:
                    return completed(argv, 1)
                if argv[:2] == ["docker", "inspect"]:
                    return completed(argv, 1, stderr="No such object")
                if argv[:3] == ["docker", "info", "--format"]:
                    return completed(argv, stdout=str(root))
                self.fail(f"unexpected command: {argv}")

            with mock.patch.object(readiness, "run", side_effect=fake_run) as run_cmd, mock.patch.object(
                readiness.shutil, "disk_usage", return_value=SimpleNamespace(free=readiness.MIN_DOCKER_FREE_BYTES - 1)
            ):
                self.assertFalse(readiness.repair_minikube_profile(ctx))
            self.assertEqual(ctx.repairs[-1].status, "fail")
            self.assertIn("at least 20 GiB", ctx.repairs[-1].message)
            self.assertFalse(any("start" in call.args[0] for call in run_cmd.call_args_list))

    def test_repair_safe_starts_only_selected_profile_after_safety_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ctx = readiness.Readiness(root, "wrong_port", "auto", "repair-safe", False)
            kubeconfig = root / "private" / "lane.kubeconfig"
            ctx.lane = {
                "minikube_profile": "minh-lane",
                "minikube_container": "minh-lane",
                "kubeconfig_path": str(kubeconfig),
            }
            state = {"started": False}
            payload = {
                "Config": {"Labels": {
                    "created_by.minikube.sigs.k8s.io": "true",
                    "name.minikube.sigs.k8s.io": "minh-lane",
                }},
                "State": {"Running": True},
            }

            def fake_run(argv, **kwargs):
                if argv[:4] == ["minikube", "-p", "minh-lane", "status"]:
                    return completed(argv, stdout="Running\n") if state["started"] else completed(argv, 1)
                if argv[:2] == ["docker", "inspect"]:
                    return completed(argv, stdout=json.dumps(payload)) if state["started"] else completed(argv, 1)
                if argv[:3] == ["docker", "info", "--format"]:
                    return completed(argv, stdout=str(root))
                if argv[:4] == ["minikube", "-p", "minh-lane", "start"]:
                    state["started"] = True
                    return completed(argv)
                self.fail(f"unexpected command: {argv}")

            with mock.patch.object(readiness, "run", side_effect=fake_run) as run_cmd, mock.patch.object(
                readiness.shutil, "disk_usage", return_value=SimpleNamespace(free=readiness.MIN_DOCKER_FREE_BYTES)
            ):
                self.assertTrue(readiness.repair_minikube_profile(ctx))
            starts = [call.args[0] for call in run_cmd.call_args_list if "start" in call.args[0]]
            self.assertEqual(starts, [["minikube", "-p", "minh-lane", "start", "--driver=docker", "--keep-context"]])
            self.assertEqual(ctx.repairs[-1].status, "pass")


if __name__ == "__main__":
    unittest.main()
