from collections.abc import Sequence
from decimal import Decimal
from typing import TypeGuard

Number = int | float | Decimal
Rows = Sequence[Sequence[object]]


def results_match(predicted: Rows, gold: Rows) -> bool:
    if {len(row) for row in predicted} != {len(row) for row in gold}:
        return False

    decimals = _get_column_decimals(gold)

    return _canonicalize_rows(predicted, decimals) == _canonicalize_rows(gold, decimals)


def _get_column_decimals(rows: Rows) -> list[int]:
    return [
        max(
            (_count_decimals(value) for value in column if _is_number(value)), default=0
        )
        for column in zip(*rows, strict=True)
    ]


def _canonicalize_rows(rows: Rows, decimals: Sequence[int]) -> list[tuple[object, ...]]:
    return [
        tuple(
            _canonicalize_value(value, places)
            for value, places in zip(row, decimals, strict=True)
        )
        for row in rows
    ]


def _canonicalize_value(value: object, places: int) -> object:
    if not _is_number(value):
        return value

    return round(float(value), places) if places else float(value)


def _count_decimals(number: Number) -> int:
    if isinstance(number, int):
        return 0

    return len(format(Decimal(repr(float(number))), "f").partition(".")[2])


def _is_number(value: object) -> TypeGuard[Number]:
    return isinstance(value, int | float | Decimal) and not isinstance(value, bool)
