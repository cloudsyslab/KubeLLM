import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from data_analysis.run_paired_campaign import (
    MINIMUM_ATTEMPT_FREE_BYTES,
    MINIMUM_STARTUP_FREE_BYTES,
    PILOT_MAX_SCHEDULED_ATTEMPTS,
    PILOT_STARTUP_FREE_BYTES,
    RUNNER,
    _build_command,
    _candidate_orders,
    _cost_success_frontier,
    _model_summary,
    _attempt_disk_stop_reason,
    _startup_disk_error,
    _storage_policy,
    _write_report,
)


class PairedCampaignTests(unittest.TestCase):
    def test_storage_guard_enforces_startup_and_between_attempt_floors(self):
        self.assertIsNone(_startup_disk_error(MINIMUM_STARTUP_FREE_BYTES))
        self.assertIn(
            "20.00 GB required",
            _startup_disk_error(MINIMUM_STARTUP_FREE_BYTES - 1),
        )
        self.assertIsNone(_startup_disk_error(PILOT_STARTUP_FREE_BYTES, PILOT_STARTUP_FREE_BYTES))
        self.assertIn(
            "12.00 GB required",
            _startup_disk_error(PILOT_STARTUP_FREE_BYTES - 1, PILOT_STARTUP_FREE_BYTES),
        )
        self.assertIsNone(_attempt_disk_stop_reason(MINIMUM_ATTEMPT_FREE_BYTES, "attempt-2"))
        self.assertIn(
            "attempt-2",
            _attempt_disk_stop_reason(MINIMUM_ATTEMPT_FREE_BYTES - 1, "attempt-2"),
        )

    def test_pilot_storage_policy_is_explicit_and_capped(self):
        standard = _storage_policy(False, 486)
        pilot = _storage_policy(True, PILOT_MAX_SCHEDULED_ATTEMPTS)

        self.assertEqual(standard["profile"], "standard")
        self.assertEqual(standard["minimum_startup_free_bytes"], MINIMUM_STARTUP_FREE_BYTES)
        self.assertIsNone(standard["maximum_scheduled_attempts"])
        self.assertEqual(pilot["profile"], "pilot_18")
        self.assertEqual(pilot["minimum_startup_free_bytes"], PILOT_STARTUP_FREE_BYTES)
        self.assertEqual(pilot["minimum_before_attempt_free_bytes"], MINIMUM_ATTEMPT_FREE_BYTES)
        self.assertEqual(pilot["maximum_scheduled_attempts"], PILOT_MAX_SCHEDULED_ATTEMPTS)
        with self.assertRaisesRegex(ValueError, "limited to 18 scheduled candidate attempts"):
            _storage_policy(True, PILOT_MAX_SCHEDULED_ATTEMPTS + 1)

    def test_report_records_storage_headroom_for_each_attempt(self):
        config = {
            "campaign_id": "storage-test",
            "cases": ["case-a"],
            "plan_replicates": 1,
            "gpu_cost_assumptions": {},
            "disk_guard": {
                "profile": "pilot_18",
                "minimum_startup_free_bytes": MINIMUM_STARTUP_FREE_BYTES,
                "minimum_before_attempt_free_bytes": MINIMUM_ATTEMPT_FREE_BYTES,
                "maximum_scheduled_attempts": PILOT_MAX_SCHEDULED_ATTEMPTS,
            },
        }
        attempt = {
            "debug_model": "model-a",
            "test_name": "case-a",
            "ground_truth_passed": True,
            "effective_cost_with_shared_knowledge_call": 1.0,
            "storage_free_before_bytes": MINIMUM_STARTUP_FREE_BYTES,
            "storage_free_after_bytes": MINIMUM_ATTEMPT_FREE_BYTES,
        }
        with TemporaryDirectory() as directory:
            root = Path(directory)
            _write_report(root, config, [attempt], ["model-a"], None)
            report = (root / "campaign_report.json").read_text(encoding="utf-8")
            markdown = (root / "campaign_report.md").read_text(encoding="utf-8")

        self.assertIn('"storage_free_before_bytes": 20000000000', report)
        self.assertIn('"storage_free_after_bytes": 10000000000', report)
        self.assertIn("## Storage measurements", markdown)
        self.assertIn("20.00 GB", markdown)
        self.assertIn("10.00 GB", markdown)

    def test_summary_reports_pooled_and_equal_task_success_and_full_shared_cost(self):
        rows = [
            {
                "debug_model": "model-a",
                "test_name": "case-a",
                "ground_truth_passed": True,
                "effective_cost_with_shared_knowledge_call": 3.0,
            },
            {
                "debug_model": "model-a",
                "test_name": "case-a",
                "ground_truth_passed": False,
                "effective_cost_with_shared_knowledge_call": 6.0,
            },
            {
                "debug_model": "model-a",
                "test_name": "case-b",
                "ground_truth_passed": True,
                "effective_cost_with_shared_knowledge_call": 9.0,
            },
            {
                "debug_model": "model-a",
                "test_name": "case-c",
                "ground_truth_passed": None,
                "effective_cost_with_shared_knowledge_call": 12.0,
            },
        ]

        summary = _model_summary(rows, ["model-a", "model-b"])
        self.assertEqual(summary[0]["attempts_with_ground_truth"], 3)
        self.assertAlmostEqual(summary[0]["pooled_ground_truth_success_rate"], 2 / 3)
        self.assertAlmostEqual(summary[0]["equal_task_ground_truth_success_rate"], 0.75)
        self.assertAlmostEqual(summary[0]["mean_effective_cost_with_shared_knowledge_call"], 7.5)
        # Failed and unknown attempts still consumed their full pipeline cost.
        self.assertAlmostEqual(summary[0]["mean_effective_cost_per_success"], 15.0)
        self.assertAlmostEqual(summary[0]["total_effective_cost_with_shared_knowledge_call"], 30.0)
        self.assertEqual(summary[1]["attempts_with_ground_truth"], 0)

    def test_command_uses_canonical_runner_and_capture_replay_flag(self):
        command = _build_command(
            test_name="port_mismatch",
            debug_model="candidate-z",
            run_dir=Path("/tmp/campaign/run-1"),
            artifact_path=Path("/tmp/campaign/plan.txt"),
            mode="replay",
            api_model="fixed-api",
            verification_model="fixed-verifier",
            lab_config=Path("/tmp/private-lane.json"),
        )
        self.assertEqual(Path(command[1]), RUNNER)
        self.assertIn("candidate-z", command)
        self.assertIn("--replay-knowledge-response", command)
        self.assertIn("fixed-api", command)
        self.assertIn("fixed-verifier", command)
        self.assertIn("/tmp/private-lane.json", command)

    def test_local_candidate_command_opts_into_debug_entry_warmup(self):
        command = _build_command(
            test_name="port_mismatch",
            debug_model="glm-4.7-flash:latest",
            run_dir=Path("/tmp/campaign/run-2"),
            artifact_path=Path("/tmp/campaign/plan.txt"),
            mode="replay",
            api_model=None,
            verification_model=None,
            lab_config=None,
            warmup_digest="a" * 64,
            warmup_allow_models=["glm-4.7-flash:latest", "nemotron-cascade-2:30b"],
            warmup_keep_alive="10m",
        )

        self.assertIn("--ollama-debug-warmup", command)
        self.assertIn("--ollama-debug-warmup-digest", command)
        self.assertIn("a" * 64, command)
        self.assertIn("glm-4.7-flash:latest,nemotron-cascade-2:30b", command)
        self.assertIn("10m", command)

    def test_cost_frontier_requires_complete_ground_truth_coverage(self):
        rows = [
            {
                "debug_model": "cheap",
                "test_name": "case-a",
                "ground_truth_passed": True,
                "effective_cost_with_shared_knowledge_call": 1.0,
            },
            {
                "debug_model": "cheap",
                "test_name": "case-b",
                "ground_truth_passed": None,
                "effective_cost_with_shared_knowledge_call": 1.0,
            },
            {
                "debug_model": "reliable",
                "test_name": "case-a",
                "ground_truth_passed": True,
                "effective_cost_with_shared_knowledge_call": 4.0,
            },
            {
                "debug_model": "reliable",
                "test_name": "case-b",
                "ground_truth_passed": True,
                "effective_cost_with_shared_knowledge_call": 4.0,
            },
        ]
        summary = _model_summary(rows, ["cheap", "reliable"], ["case-a", "case-b"], 1)
        frontier = _cost_success_frontier(summary, thresholds=(0.8, 1.0))
        self.assertEqual(frontier[0]["lowest_mean_cost_model"], "reliable")
        self.assertEqual(frontier[1]["lowest_mean_cost_model"], "reliable")

    def test_candidate_capture_order_is_balanced_and_deterministic(self):
        cases = ["case-a", "case-b"]
        models = ["model-a", "model-b", "model-c"]
        first = _candidate_orders(cases, 3, models, 17)
        second = _candidate_orders(cases, 3, models, 17)
        self.assertEqual(first, second)
        self.assertEqual(
            {order[0] for order in first.values()},
            set(models),
        )
        self.assertTrue(all(set(order) == set(models) for order in first.values()))


if __name__ == "__main__":
    unittest.main()
