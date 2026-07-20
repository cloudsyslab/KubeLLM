import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analyze import clustered_ci, figures, metric_summary, parse, rate_table, wilson


ROOT = Path(__file__).resolve().parents[1]


class ParserTests(unittest.TestCase):
    def test_parse_real_export(self):
        records, issues = parse(ROOT / "data")
        self.assertEqual(len(records), 135)
        self.assertEqual(records.success.sum(), 131)
        self.assertFalse((issues.severity == "error").any())

    def test_detects_missing_artifact(self):
        records, issues = parse(ROOT / "tests" / "fixtures" / "incomplete_data")
        self.assertEqual(len(records), 1)
        self.assertIn("missing_required_artifact", set(issues.code))

    def test_parse_follows_directory_symlink(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source" / "configuration" / "iter-001" / "case-a"
            source.mkdir(parents=True)
            (source.parent / "run_config.json").write_text(json.dumps({"test_names": ["case-a"]}))
            (source.parent / "aggregate.json").write_text(json.dumps({"total_tests": 1, "ground_truth_passed": 1, "passed": 1}))
            (source / "summary.json").write_text(json.dumps({"test_name": "case-a", "status": "PASS", "verified": True, "ground_truth_passed": True, "duration_s": 1, "metrics": {}}))
            (source / "ground_truth.json").write_text(json.dumps({"test_name": "case-a", "passed": True}))
            (source / "config_effective.json").write_text(json.dumps({"test-name": "case-a"}))
            (source / "verification_report.meta.json").write_text(json.dumps({}))
            (source / "verification_report.txt").write_text("report")
            data = root / "data"
            data.mkdir()
            (data / "linked-configuration").symlink_to(source.parents[1], target_is_directory=True)

            records, issues = parse(data)

            self.assertEqual(len(records), 1)
            self.assertEqual(records.iloc[0].configuration, "linked-configuration")
            self.assertFalse((issues.severity == "error").any())

    def test_wilson_bounds(self):
        lo, hi = wilson(5, 5)
        self.assertLess(lo, 1)
        self.assertEqual(hi, 1.0)

    def test_clustered_bootstrap_keeps_case_repetitions(self):
        records, _ = parse(ROOT / "data")
        lo, hi = clustered_ci(records, "ground_truth_passed", seed=7, reps=300)
        self.assertLessEqual(lo, hi)
        table = rate_table(records, ["test_case"], "verification_correct", "wilson", seed=7)
        self.assertTrue((table.n_known == 5).all())

    def test_metric_summary_keeps_configurations_separate(self):
        records = pd.DataFrame({
            "configuration": ["configuration-a", "configuration-a", "configuration-b"],
            "duration_s": [2.0, 3.0, 7.0],
            "api_duration_s": [1.0, 1.0, 2.0],
            "debug_duration_s": [1.0, 2.0, 4.0],
            "verification_duration_s": [0.0, 0.0, 1.0],
            "total_tokens": [10, 20, 30],
            "total_cost": [0.1, 0.2, 0.3],
            "api_total_tokens": [1, 2, 3],
            "debug_total_tokens": [4, 5, 6],
            "verification_total_tokens": [5, 13, 21],
            "api_cost": [0.01, 0.02, 0.03],
            "debug_cost": [0.04, 0.05, 0.06],
            "verification_cost": [0.05, 0.13, 0.21],
        })
        summary = metric_summary(records, ["configuration"])

        self.assertEqual(set(summary.configuration), set(records.configuration))
        for configuration, group in records.groupby("configuration"):
            total = summary.loc[
                (summary.configuration == configuration) & (summary.metric == "duration_s"), "total"
            ].iloc[0]
            self.assertEqual(total, group.duration_s.sum())
        self.assertEqual(
            len(summary.loc[summary.metric == "duration_s"]), records.configuration.nunique()
        )

    def test_figures_writes_ground_truth_success_plot_for_each_configuration(self):
        records = pd.DataFrame({
            "configuration": ["configuration-a", "configuration-a", "configuration-b", "configuration-b"],
            "test_case": ["case-a", "case-b", "case-a", "case-b"],
            "ground_truth_passed": [True, False, False, True],
            "duration_s": [1.0, 2.0, 3.0, 4.0],
            "api_total_tokens": [1, 1, 1, 1],
            "debug_total_tokens": [2, 2, 2, 2],
            "verification_total_tokens": [3, 3, 3, 3],
        })
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir)
            images = figures(records, output)

            success_figures = sorted(name for name in images if name.startswith("success_by_test_case_"))
            self.assertEqual(success_figures, [
                "success_by_test_case_01_configuration-a.png",
                "success_by_test_case_02_configuration-b.png",
            ])
            self.assertTrue(all((output / name).is_file() for name in success_figures))


if __name__ == "__main__": unittest.main()
