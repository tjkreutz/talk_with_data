import unittest
from random import Random
from statistics import StatisticsError

from talk_with_data.metrics import (
    Attempt,
    Outcome,
    _bootstrap_interval,
    _compute_accuracy,
    _compute_accuracy_std,
    _compute_outcome_rates,
    _compute_run_accuracies,
    _compute_template_accuracies,
    _count_consistency,
    summarize,
)


def _attempt(question: str, template: str, run: int, outcome: Outcome) -> Attempt:
    return Attempt(
        question_id=question,
        template=template,
        run=run,
        question="?",
        sql="SELECT 1",
        outcome=outcome,
        result=[],
        gold=[],
    )


class TestMetrics(unittest.TestCase):
    def setUp(self) -> None:
        self.attempts = [
            _attempt("q1", "a", 1, "correct"),
            _attempt("q1", "a", 2, "correct"),
            _attempt("q2", "a", 1, "correct"),
            _attempt("q2", "a", 2, "wrong"),
            _attempt("q3", "b", 1, "error"),
            _attempt("q3", "b", 2, "empty"),
        ]

    def test_summarize(self) -> None:
        summary = summarize(self.attempts)

        self.assertEqual(summary["questions"], 3)
        self.assertEqual(summary["runs"], 2)
        self.assertEqual(summary["accuracy"], 0.5)
        self.assertEqual(summary["accuracy_std"], 0.236)
        self.assertEqual(summary["template_accuracy"], {"a": 0.75, "b": 0.0})
        self.assertEqual(
            summary["outcomes"],
            {"correct": 0.5, "wrong": 0.167, "empty": 0.167, "error": 0.167},
        )
        self.assertEqual(
            summary["consistency"],
            {"always_correct": 1, "sometimes_correct": 1, "never_correct": 1},
        )
        self.assertEqual(len(summary["accuracy_ci95"]), 2)  # type: ignore[arg-type]
        self.assertEqual(summary, summarize(self.attempts))

    def test_compute_accuracy(self) -> None:
        self.assertEqual(_compute_accuracy(self.attempts), 0.5)
        self.assertEqual(_compute_accuracy(self.attempts[:2]), 1.0)
        self.assertEqual(_compute_accuracy(self.attempts[4:]), 0.0)

    def test_compute_accuracy_std(self) -> None:
        self.assertAlmostEqual(_compute_accuracy_std(self.attempts), 0.2357, places=4)

        with self.assertRaises(StatisticsError):
            _compute_accuracy_std(self.attempts[:1])

    def test_compute_run_accuracies(self) -> None:
        run_accuracies = _compute_run_accuracies(self.attempts)

        self.assertAlmostEqual(run_accuracies[0], 2 / 3)
        self.assertAlmostEqual(run_accuracies[1], 1 / 3)
        self.assertEqual(len(run_accuracies), 2)

    def test_compute_outcome_rates(self) -> None:
        self.assertEqual(
            _compute_outcome_rates(self.attempts[:4]),
            {"correct": 0.75, "wrong": 0.25, "empty": 0.0, "error": 0.0},
        )

    def test_compute_template_accuracies(self) -> None:
        self.assertEqual(
            _compute_template_accuracies(self.attempts), {"a": 0.75, "b": 0.0}
        )

    def test_count_consistency(self) -> None:
        self.assertEqual(
            _count_consistency(self.attempts),
            {"always_correct": 1, "sometimes_correct": 1, "never_correct": 1},
        )
        self.assertEqual(
            _count_consistency(self.attempts[:2]),
            {"always_correct": 1, "sometimes_correct": 0, "never_correct": 0},
        )

    def test_bootstrap_interval(self) -> None:
        self.assertEqual(_bootstrap_interval([0.5] * 5, Random(1)), (0.5, 0.5))

        values = [0.0, 0.2, 0.6, 0.8, 1.0, 1.0]
        lower, upper = _bootstrap_interval(values, Random(1))

        self.assertLess(lower, upper)
        self.assertGreaterEqual(lower, min(values))
        self.assertLessEqual(upper, max(values))
        self.assertEqual((lower, upper), _bootstrap_interval(values, Random(1)))


if __name__ == "__main__":
    unittest.main()
