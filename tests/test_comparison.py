import unittest
from datetime import datetime
from decimal import Decimal

from talk_with_data.comparison import (
    canonicalize_rows,
    canonicalize_value,
    count_decimals,
    get_column_decimals,
    has_order_by,
    is_number,
    results_match,
)

UNORDERED = "SELECT state, count(*) FROM customers GROUP BY state"
ORDERED = "SELECT state, count(*) FROM customers GROUP BY state ORDER BY 2 DESC"


class TestComparison(unittest.TestCase):
    def test_results_match(self) -> None:
        gold = [("SP", 10), ("RJ", 5)]

        self.assertTrue(results_match([("SP", 10), ("RJ", 5)], gold, UNORDERED))
        self.assertTrue(results_match([("RJ", 5), ("SP", 10)], gold, UNORDERED))
        self.assertFalse(results_match([("RJ", 5), ("SP", 10)], gold, ORDERED))
        self.assertTrue(results_match([("SP", 10), ("RJ", 5)], gold, ORDERED))
        self.assertFalse(results_match([("SP", 10), ("RJ", 6)], gold, UNORDERED))
        self.assertFalse(results_match([("SP", 10)], gold, UNORDERED))
        self.assertFalse(results_match([("SP", 10), ("SP", 10)], gold, UNORDERED))
        self.assertFalse(results_match([("SP", 10, 1), ("RJ", 5, 1)], gold, UNORDERED))
        self.assertFalse(results_match([(10,), (5,)], gold, UNORDERED))

    def test_results_match_numbers(self) -> None:
        self.assertTrue(results_match([(12.557,)], [(12.6,)], UNORDERED))
        self.assertTrue(results_match([(12.6,)], [(12.6,)], UNORDERED))
        self.assertFalse(results_match([(45.7567,)], [(45.1,)], UNORDERED))
        self.assertTrue(results_match([(0.5912,)], [(0.59,)], UNORDERED))
        self.assertFalse(results_match([(0.64,)], [(0.59,)], UNORDERED))
        self.assertTrue(results_match([(13.0,)], [(13,)], UNORDERED))
        self.assertFalse(results_match([(7.4,)], [(7,)], UNORDERED))
        self.assertTrue(results_match([(Decimal("2.50"),)], [(2.5,)], UNORDERED))

    def test_results_match_other_values(self) -> None:
        moment = datetime(2017, 11, 24, 10, 0)

        self.assertTrue(results_match([(moment, None)], [(moment, None)], UNORDERED))
        self.assertFalse(results_match([("sao paulo",)], [("São Paulo",)], UNORDERED))
        self.assertTrue(results_match([], [], UNORDERED))
        self.assertFalse(results_match([], [(1,)], UNORDERED))
        self.assertFalse(results_match([(1,)], [], UNORDERED))

    def test_has_order_by(self) -> None:
        self.assertTrue(has_order_by("SELECT 1 ORDER BY 1"))
        self.assertTrue(has_order_by("select 1 order\n  by x desc"))
        self.assertFalse(has_order_by("SELECT 1"))
        self.assertFalse(has_order_by("SELECT reorder by_date FROM t"))

    def test_get_column_decimals(self) -> None:
        rows = [("a", 1, 12.6, 0.59), ("b", 2, 13.0, 0.5)]

        self.assertEqual(get_column_decimals(rows), [0, 0, 1, 2])
        self.assertEqual(get_column_decimals([(None,), (3.25,)]), [2])
        self.assertEqual(get_column_decimals([]), [])

    def test_canonicalize_rows(self) -> None:
        self.assertEqual(
            canonicalize_rows([("a", 12.557, 3, None)], [0, 1, 0, 0]),
            [("a", 12.6, 3.0, None)],
        )
        self.assertEqual(canonicalize_rows([], []), [])

        with self.assertRaises(ValueError):
            canonicalize_rows([(1, 2)], [0])

    def test_canonicalize_value(self) -> None:
        self.assertEqual(canonicalize_value(12.557, 1), 12.6)
        self.assertEqual(canonicalize_value(7.4, 0), 7.4)
        self.assertEqual(canonicalize_value(7, 0), 7.0)
        self.assertEqual(canonicalize_value(Decimal("2.55"), 1), 2.5)
        self.assertEqual(canonicalize_value("text", 2), "text")
        self.assertIsNone(canonicalize_value(None, 2))
        self.assertIs(canonicalize_value(True, 2), True)

    def test_count_decimals(self) -> None:
        self.assertEqual(count_decimals(12.6), 1)
        self.assertEqual(count_decimals(0.59), 2)
        self.assertEqual(count_decimals(13.0), 1)
        self.assertEqual(count_decimals(13), 0)
        self.assertEqual(count_decimals(0.00001), 5)
        self.assertEqual(count_decimals(Decimal("2.50")), 1)

    def test_is_number(self) -> None:
        for number in (1, 1.5, Decimal("2.5")):
            self.assertTrue(is_number(number))

        for other in (True, "1", None, datetime(2017, 1, 1)):
            self.assertFalse(is_number(other))


if __name__ == "__main__":
    unittest.main()
