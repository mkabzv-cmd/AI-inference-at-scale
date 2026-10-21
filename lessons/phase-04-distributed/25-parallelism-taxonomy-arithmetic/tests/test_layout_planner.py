from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from layout_planner import evaluate, pipeline_ranges  # noqa: E402


class LayoutPlannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.models = json.loads(
            (ROOT / "inputs" / "models.json").read_text(encoding="utf-8")
        )

    def test_pp_layer_balance(self) -> None:
        self.assertEqual(
            pipeline_ranges(31, 3),
            [[0, 10], [11, 20], [21, 30]],
        )

    def test_invalid_world_size(self) -> None:
        result = evaluate(
            "divisible-small-shape",
            self.models["divisible-small-shape"],
            gpus=3,
            dp=2,
            tp=1,
            pp=1,
        )
        self.assertFalse(result["valid"])
        self.assertTrue(
            any("DP*TP*PP" in reason for reason in result["reasons"])
        )

    def test_zero_factor_is_structured_instead_of_dividing_by_zero(self) -> None:
        result = evaluate(
            "divisible-small-shape",
            self.models["divisible-small-shape"],
            gpus=3,
            dp=1,
            tp=0,
            pp=3,
        )
        self.assertFalse(result["valid"])
        self.assertIn("tp must be positive", result["reasons"])
        self.assertIsNone(result["layout"]["world_size"])
        self.assertFalse(result["memory"]["fits_estimate"])

    def test_three_way_tp_rejection(self) -> None:
        result = evaluate(
            "power-of-two-7b-shape",
            self.models["power-of-two-7b-shape"],
            gpus=3,
            dp=1,
            tp=3,
            pp=1,
        )
        self.assertFalse(result["valid"])
        self.assertTrue(
            any("hidden_size" in reason for reason in result["reasons"])
        )

    def test_valid_three_way_tp(self) -> None:
        result = evaluate(
            "divisible-small-shape",
            self.models["divisible-small-shape"],
            gpus=3,
            dp=1,
            tp=3,
            pp=1,
        )
        self.assertTrue(result["valid"], result["reasons"])
        self.assertTrue(result["memory"]["fits_estimate"])

    def test_more_pipeline_stages_than_layers_is_structured(self) -> None:
        model = dict(self.models["divisible-small-shape"])
        model["layers"] = 2
        result = evaluate(
            "two-layer-shape",
            model,
            gpus=3,
            dp=1,
            tp=1,
            pp=3,
        )
        self.assertFalse(result["valid"])
        self.assertEqual(
            result["layout"]["pipeline_layer_counts"],
            [1, 1, 0],
        )

    def test_invalid_head_dimension_serializes_as_null(self) -> None:
        model = dict(self.models["divisible-small-shape"])
        model["hidden_size"] = 769
        result = evaluate(
            "invalid-head-shape",
            model,
            gpus=3,
            dp=1,
            tp=1,
            pp=3,
        )
        self.assertFalse(result["valid"])
        self.assertIsNone(result["checks"]["head_dim"])
        json.dumps(result, allow_nan=False)

    def test_kv_replication_uses_conservative_local_head_count(self) -> None:
        model = dict(self.models["divisible-small-shape"])
        model["attention_heads"] = 12
        model["kv_heads"] = 2
        model["allow_kv_head_replication"] = True
        result = evaluate(
            "replicated-kv-shape",
            model,
            gpus=3,
            dp=1,
            tp=3,
            pp=1,
        )
        self.assertTrue(result["valid"], result["reasons"])
        self.assertEqual(
            result["memory"]["screening_local_kv_heads"],
            1,
        )
        self.assertGreater(
            result["memory"]["kv_cache_gib_per_rank"],
            result["memory"]["average_kv_cache_gib_per_rank"],
        )


if __name__ == "__main__":
    unittest.main()
