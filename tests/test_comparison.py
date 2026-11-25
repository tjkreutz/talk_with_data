import unittest
from datetime import datetime
from decimal import Decimal

from talk_with_data.comparison import (
    _canonicalize_rows,
    _canonicalize_value,
    _count_decimals,
    _get_column_decimals,
    _is_number,
    results_match,
)


class TestComparison(unittest.TestCase):
    def test_results_match(self) -> None:
        gold = [("SP", 10), ("RJ", 5)]

        self.assertTrue(results_match([("SP", 10), ("RJ", 5)], gold))
        self.assertFalse(results_match([("RJ", 5), ("SP", 10)], gold))
        self.assertFalse(results_match([("SP", 10), ("RJ", 6)], gold))
        self.assertFalse(results_match([("SP", 10)], gold))
        self.assertFalse(results_match([("SP", 10), ("SP", 10)], gold))
        self.assertFalse(results_match([("SP", 10, 1), ("RJ", 5, 1)], gold))
        self.assertFalse(results_match([(10,), (5,)], gold))

    def test_results_match_numbers(self) -> None:
        self.assertTrue(results_match([(12.557,)], [(12.6,)]))
        self.assertTrue(results_match([(12.6,)], [(12.6,)]))
        self.assertFalse(results_match([(45.7567,)], [(45.1,)]))
        self.assertTrue(results_match([(0.5912,)], [(0.59,)]))
        self.assertFalse(results_match([(0.64,)], [(0.59,)]))
        self.assertTrue(results_match([(13.0,)], [(13,)]))
        self.assertFalse(results_match([(7.4,)], [(7,)]))
        self.assertTrue(results_match([(Decimal("2.50"),)], [(2.5,)]))

    def test_results_match_other_values(self) -> None:
        moment = datetime(2017, 11, 24, 10, 0)

        self.assertTrue(results_match([(moment, None)], [(moment, None)]))
        self.assertFalse(results_match([("sao paulo",)], [("São Paulo",)]))
        self.assertTrue(results_match([], []))
        self.assertFalse(results_match([], [(1,)]))
        self.assertFalse(results_match([(1,)], []))

    def test_get_column_decimals(self) -> None:
        rows = [("a", 1, 12.6, 0.59), ("b", 2, 13.0, 0.5)]

        self.assertEqual(_get_column_decimals(rows), [0, 0, 1, 2])
        self.assertEqual(_get_column_decimals([(None,), (3.25,)]), [2])
        self.assertEqual(_get_column_decimals([]), [])

    def test_canonicalize_rows(self) -> None:
        self.assertEqual(
            _canonicalize_rows([("a", 12.557, 3, None)], [0, 1, 0, 0]),
            [("a", 12.6, 3.0, None)],
        )
        self.assertEqual(_canonicalize_rows([], []), [])

        with self.assertRaises(ValueError):
            _canonicalize_rows([(1, 2)], [0])

    def test_canonicalize_value(self) -> None:
        self.assertEqual(_canonicalize_value(12.557, 1), 12.6)
        self.assertEqual(_canonicalize_value(7.4, 0), 7.4)
        self.assertEqual(_canonicalize_value(7, 0), 7.0)
        self.assertEqual(_canonicalize_value(Decimal("2.55"), 1), 2.5)
        self.assertEqual(_canonicalize_value("text", 2), "text")
        self.assertIsNone(_canonicalize_value(None, 2))
        self.assertIs(_canonicalize_value(True, 2), True)

    def test_count_decimals(self) -> None:
        self.assertEqual(_count_decimals(12.6), 1)
        self.assertEqual(_count_decimals(0.59), 2)
        self.assertEqual(_count_decimals(13.0), 1)
        self.assertEqual(_count_decimals(13), 0)
        self.assertEqual(_count_decimals(0.00001), 5)
        self.assertEqual(_count_decimals(Decimal("2.50")), 1)

    def test_is_number(self) -> None:
        for number in (1, 1.5, Decimal("2.5")):
            self.assertTrue(_is_number(number))

        for other in (True, "1", None, datetime(2017, 1, 1)):
            self.assertFalse(_is_number(other))


if __name__ == "__main__":
    unittest.main()
