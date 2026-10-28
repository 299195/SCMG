from __future__ import annotations

import unittest

from scmg.evaluation import summarize


class EvaluationTests(unittest.TestCase):
    def test_denominators_remain_explicit(self) -> None:
        summary = summarize(
            [
                {"category": "a", "write_positive": True, "reuse_positive": True},
                {"category": "a", "write_positive": False, "reuse_positive": False},
                {"category": "a", "error": "timeout"},
            ]
        )
        self.assertEqual(summary["attempted"], 3)
        self.assertEqual(summary["valid"], 2)
        self.assertEqual(summary["errors"], 1)
        self.assertEqual(summary["write_rate"], 0.5)
        self.assertEqual(summary["conditional_reuse_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
