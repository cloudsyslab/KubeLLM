"""Tests for metrics_db.calculate_cost and external model_pricing.json."""

import importlib
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEBUG_DIR = REPO_ROOT / "debug_assistant_latest"

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(DEBUG_DIR))

import debug_assistant_latest.metrics_db as metrics_db


class TestCalculateCost(unittest.TestCase):
    def setUp(self):
        importlib.reload(metrics_db)

    def test_known_model_cost_from_json(self):
        # gpt-4o-mini: 1000 in, 2000 out => 0.0006 + 0.0048
        cost = metrics_db.calculate_cost("gpt-4o-mini", 1000, 2000)
        self.assertEqual(cost, 0.0054)

    def test_unknown_model_warns_and_returns_zero(self):
        buf = StringIO()
        with redirect_stdout(buf):
            cost = metrics_db.calculate_cost("unknown-model-xyz", 100, 100)
        self.assertEqual(cost, 0.0)
        out = buf.getvalue()
        self.assertIn("Unknown model", out)
        self.assertIn("unknown-model-xyz", out)


if __name__ == "__main__":
    unittest.main()
