import re
from collections import Counter
from collections.abc import Sequence
from decimal import Decimal
from typing import TypeGuard

Number = int | float | Decimal
Rows = Sequence[Sequence[object]]
ORDER_BY = re.compile(r"\border\s+by\b", re.IGNORECASE)


def results_match(predicted: Rows, gold: Rows, gold_sql: str) -> bool:
    if {len(row) for row in predicted} != {len(row) for row in gold}:
        return False

    decimals = get_column_decimals(gold)
    predicted_rows = canonicalize_rows(predicted, decimals)
    gold_rows = canonicalize_rows(gold, decimals)

    if has_order_by(gold_sql):
        return predicted_rows == gold_rows

    return Counter(predicted_rows) == Counter(gold_rows)


def has_order_by(sql: str) -> bool:
    return ORDER_BY.search(sql) is not None


def get_column_decimals(rows: Rows) -> list[int]:
    return [
        max((count_decimals(value) for value in column if is_number(value)), default=0)
        for column in zip(*rows, strict=True)
    ]


def canonicalize_rows(rows: Rows, decimals: Sequence[int]) -> list[tuple[object, ...]]:
    return [
        tuple(
            canonicalize_value(value, places)
            for value, places in zip(row, decimals, strict=True)
        )
        for row in rows
    ]


def canonicalize_value(value: object, places: int) -> object:
    if not is_number(value):
        return value

    return round(float(value), places) if places else float(value)


def count_decimals(number: Number) -> int:
    if isinstance(number, int):
        return 0

    return len(format(Decimal(repr(float(number))), "f").partition(".")[2])


def is_number(value: object) -> TypeGuard[Number]:
    return isinstance(value, int | float | Decimal) and not isinstance(value, bool)
