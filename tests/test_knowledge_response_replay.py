import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from debug_assistant_latest import main


class KnowledgeResponseArtifactTests(unittest.TestCase):
    def test_round_trip_records_hashes_and_rejects_prompt_or_case_mismatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "plan.txt"
            artifact = main._save_knowledge_response_artifact(
                path,
                response="Apply this patch.",
                prompt="Fix case A",
                test_name="case_a",
                api_model="knowledge-model",
                runtime_context={"run_id": "run-1", "run_uuid": "uuid-1"},
            )

            replayed = main._load_knowledge_response_artifact(
                path, prompt="Fix case A", test_name="case_a"
            )
            self.assertEqual(replayed["response"], "Apply this patch.")
            self.assertEqual(replayed["response_sha256"], artifact["response_sha256"])
            self.assertEqual(replayed["source_run_id"], "run-1")
            with self.assertRaisesRegex(ValueError, "prompt fingerprint"):
                main._load_knowledge_response_artifact(
                    path, prompt="Fix a different case", test_name="case_a"
                )
            with self.assertRaisesRegex(ValueError, "belongs to"):
                main._load_knowledge_response_artifact(
                    path, prompt="Fix case A", test_name="case_b"
                )

    def test_round_trip_rejects_modified_response_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "plan.txt"
            main._save_knowledge_response_artifact(
                path,
                response="Original response",
                prompt="Prompt",
                test_name="case_a",
                api_model="knowledge-model",
                runtime_context=None,
            )
            with self.assertRaises(FileExistsError):
                main._save_knowledge_response_artifact(
                    path,
                    response="Replacement response",
                    prompt="Prompt",
                    test_name="case_a",
                    api_model="knowledge-model",
                    runtime_context=None,
                )
            path.write_text("Modified response", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "checksum"):
                main._load_knowledge_response_artifact(
                    path, prompt="Prompt", test_name="case_a"
                )

    def test_round_trip_rejects_modified_prompt_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "plan.txt"
            main._save_knowledge_response_artifact(
                path,
                response="Response",
                prompt="Prompt",
                test_name="case_a",
                api_model="knowledge-model",
                runtime_context=None,
            )
            metadata_path = path.with_suffix(path.suffix + ".json")
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["prompt"] = "Modified metadata prompt"
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "prompt artifact checksum"):
                main._load_knowledge_response_artifact(path, prompt="Prompt", test_name="case_a")

    def test_all_steps_replay_skips_knowledge_agent_setup_and_query(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact_path = Path(temp_dir) / "plan.txt"
            main._save_knowledge_response_artifact(
                artifact_path,
                response="Use the exact captured plan.",
                prompt="Stable prompt",
                test_name="case_a",
                api_model="knowledge-model",
                runtime_context={"run_id": "capture-run"},
            )

            class FakeAPI:
                def __init__(self, _agent_type, _config):
                    self.agentProperties = {"model": "knowledge-model"}
                    self.response = None
                    self.prompt = ""

                def preparePrompt(self):
                    self.prompt = "Stable prompt"

                def setupAgent(self):
                    raise AssertionError("Replay must not initialize or query the KnowledgeAgent")

            class FakeDebug:
                def __init__(self, _agent_type, _config):
                    self.agentProperties = {"model": "debug-model"}
                    self.debugStatus = True
                    self._last_timeout = False
                    self.agentAPIResponse = None

                def setupAgent(self):
                    return None

                def askQuestion(self):
                    self.observed_response = self.agentAPIResponse
                    return {"model": "debug-model", "input_tokens": 2, "output_tokens": 3}

            fake_debug = FakeDebug("debug-agent", {})

            def observed_phase(_runtime, phase, action):
                self.assertEqual(phase, "debug")
                action()
                return {"model": "debug-model", "input_tokens": 2, "output_tokens": 3}

            with patch.object(main, "_load_runtime_config", return_value={"test-name": "case_a"}), patch.object(
                main, "setUpEnvironment"
            ), patch.object(main, "AgentAPI", FakeAPI), patch.object(
                main, "AgentDebug", return_value=fake_debug
            ), patch.object(
                main,
                "_run_api_phase",
                side_effect=AssertionError("Replay must not call the KnowledgeAgent"),
            ), patch.object(main, "_run_observed_phase", side_effect=observed_phase), patch.object(
                main,
                "_run_verification_phase_after_debug",
                return_value=({"model": "verification-model", "cost": 0.0}, True),
            ), patch.object(main, "printFinishMessage"):
                result = main.allStepsAtOnce(
                    configFile="unused.json",
                    runtime_context={
                        "log_dir": str(Path(temp_dir) / "replay-run"),
                        "replay_knowledge_response_path": str(artifact_path),
                    },
                )

            self.assertTrue(result["status"])
            self.assertEqual(fake_debug.observed_response, "Use the exact captured plan.")
            self.assertEqual(result["api_metrics"]["total_tokens"], 0)
            self.assertTrue((Path(temp_dir) / "replay-run" / "knowledge_response.txt").exists())
            meta = json.loads(
                (Path(temp_dir) / "replay-run" / "knowledge_response.meta.json").read_text(encoding="utf-8")
            )
            self.assertEqual(meta["mode"], "replay")


if __name__ == "__main__":
    unittest.main()
