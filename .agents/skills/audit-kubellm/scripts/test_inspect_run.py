from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from inspect_run import inspect


class RunInspectorTests(unittest.TestCase):
    def test_summary_exposes_allowlisted_invalid_knowledge_outcome(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            test_dir = root / "case"
            test_dir.mkdir()
            (test_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "technique": "stepByStep",
                        "status": "FAIL",
                        "architecture_outcome": "knowledge_output_invalid",
                    }
                ),
                encoding="utf-8",
            )

            report = inspect(root)

        self.assertEqual(
            report["artifacts"][0]["data"]["architecture_outcome"],
            "knowledge_output_invalid",
        )

    def test_knowledge_execution_exposes_statuses_and_counts_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "knowledge_execution.json").write_text(
                json.dumps(
                    {
                        "technique": "knowledgeAgentOnly",
                        "architecture_outcome": "execution_completed",
                        "knowledge_generation": {"status": "success", "error": "private"},
                        "contract": {"status": "valid", "error": "private"},
                        "execution": {
                            "status": "completed",
                            "planned_action_count": 1,
                            "completed_action_count": 1,
                            "failure_reason": "private",
                            "actions": [
                                {
                                    "id": "action-1",
                                    "tool": "run_shell_command",
                                    "status": "success",
                                    "command": "echo private-command-marker",
                                    "result": {"stdout": "private-output-marker"},
                                }
                            ],
                        },
                        "verification": {"status": "verified", "error": "private"},
                        "ground_truth": {"status": "passed", "passed": True},
                    }
                ),
                encoding="utf-8",
            )

            report = inspect(root)
            serialized = json.dumps(report)
            artifact = report["artifacts"][0]["data"]

            self.assertEqual(artifact["architecture_outcome"], "execution_completed")
            self.assertEqual(artifact["execution"]["action_statuses"], ["success"])
            self.assertEqual(artifact["ground_truth"], {"status": "passed", "passed": True})
            for private in ("private-command-marker", "private-output-marker", "private"):
                self.assertNotIn(private, serialized)

    def test_summary_projects_only_typed_fields_and_ignores_raw_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "private-parent-path-marker"
            nested.mkdir()
            (nested / "summary.json").write_text(
                json.dumps(
                    {
                        "technique": "knowledgeAgentOnly",
                        "status": "PASS",
                        "architecture_outcome": "execution_completed",
                        "test_name": "case_with_sensitive_payload",
                        "duration_s": 12.5,
                        "verified": True,
                        "ground_truth_passed": True,
                        "error_message": "private-error-marker",
                        "error_context": {"command": "private-command-marker"},
                        "output_dir": "/private/path-marker",
                        "metrics": {
                            "api": {"cost": 0.2, "total_tokens": 10, "model": "private-model-marker"},
                            "verification": {"duration_s": 1.5},
                        },
                    }
                ),
                encoding="utf-8",
            )
            (root / "stdout.log").write_text("private-stdout-marker", encoding="utf-8")
            (root / "progress.log").write_text("kubectl get pods private-progress-marker", encoding="utf-8")
            (root / "stderr.log").write_text("private-stderr-marker", encoding="utf-8")

            report = inspect(root)
            serialized = json.dumps(report)

            self.assertEqual(report["artifact_count"], 1)
            self.assertEqual(report["artifacts"][0]["data"]["status"], "PASS")
            self.assertEqual(report["artifacts"][0]["data"]["metrics"]["api"]["cost"], 0.2)
            for private in (
                "private-error-marker", "private-command-marker", "/private/path-marker",
                "private-model-marker", "private-stdout-marker", "private-progress-marker",
                "kubectl", "private-stderr-marker", "case_with_sensitive_payload",
                "private-parent-path-marker",
            ):
                self.assertNotIn(private, serialized)

    def test_aggregate_does_not_return_nested_configuration_or_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "aggregate.json").write_text(
                json.dumps(
                    {
                        "total_tests": 2,
                        "passed": 1,
                        "total_cost": 0.3,
                        "run_uuid": "private-id-marker",
                        "run_config": {"provider": "private-provider-marker"},
                        "tests": [{"output": "private-output-marker"}],
                    }
                ),
                encoding="utf-8",
            )

            report = inspect(root)
            serialized = json.dumps(report)

            self.assertEqual(report["artifacts"][0]["data"]["total_tests"], 2)
            self.assertEqual(report["artifacts"][0]["data"]["passed"], 1)
            for private in ("private-id-marker", "private-provider-marker", "private-output-marker"):
                self.assertNotIn(private, serialized)


if __name__ == "__main__":
    unittest.main()
