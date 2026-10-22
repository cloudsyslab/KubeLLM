import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from debug_assistant_latest.executor import _run_ground_truth_checkpoint
from debug_assistant_latest.ground_truth import GroundTruthResult
from debug_assistant_latest.report import TestSummary as SummaryRecord
from debug_assistant_latest.report import load_test_summary, save_test_summary


class GroundTruthCheckpointTests(unittest.TestCase):
    def test_named_checkpoints_are_saved_without_overwriting_each_other(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            result = GroundTruthResult(test_name="case-a", passed=True)
            with patch("debug_assistant_latest.executor.run_ground_truth_checks", return_value=result):
                after_debug = _run_ground_truth_checkpoint(
                    {"ground-truth": {"checks": []}}, log_dir, None, "after_debug"
                )
                after_verification = _run_ground_truth_checkpoint(
                    {"ground-truth": {"checks": []}}, log_dir, None, "after_verification"
                )

            self.assertTrue(after_debug["passed"])
            self.assertTrue(after_verification["passed"])
            self.assertTrue((log_dir / "ground_truth_after_debug.json").is_file())
            self.assertTrue((log_dir / "ground_truth_after_verification.json").is_file())
            self.assertTrue((log_dir / "ground_truth.json").is_file())
            self.assertTrue(
                json.loads((log_dir / "ground_truth_after_debug.json").read_text())["passed"]
            )

    def test_summary_round_trip_keeps_checkpoint_and_integrity_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            summary = SummaryRecord(
                test_name="case-a",
                technique="allStepsAtOnce",
                status="PASS",
                verified=True,
                ground_truth_passed=True,
                ground_truth_configured=True,
                ground_truth_after_debug_passed=True,
                ground_truth_after_verification_passed=True,
                ground_truth_integrity_match=True,
            )
            path = save_test_summary(summary, Path(temp_dir))
            loaded = load_test_summary(path)

            self.assertTrue(loaded.ground_truth_after_debug_passed)
            self.assertTrue(loaded.ground_truth_after_verification_passed)
            self.assertTrue(loaded.ground_truth_integrity_match)


if __name__ == "__main__":
    unittest.main()
