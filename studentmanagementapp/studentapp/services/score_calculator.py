from decimal import Decimal, ROUND_HALF_UP

from studentapp.models.score import (
    SCORE_COLUMNS_15M,
    SCORE_COLUMNS_45M,
    SCORE_COLUMN_FINAL,
    WEIGHT_15M,
    WEIGHT_45M,
    WEIGHT_FINAL,
)

SCORE_PRECISION = 2

def _to_float(value):

    if value is None:
        return None
    return float(value)

def calculate_average(score_map: dict) -> float | None:

    numerator = 0.0
    denominator = 0.0

    for col in SCORE_COLUMNS_15M:
        v = _to_float(score_map.get(col))
        if v is not None:
            numerator += v * WEIGHT_15M
            denominator += WEIGHT_15M

    for col in SCORE_COLUMNS_45M:
        v = _to_float(score_map.get(col))
        if v is not None:
            numerator += v * WEIGHT_45M
            denominator += WEIGHT_45M

    v = _to_float(score_map.get(SCORE_COLUMN_FINAL))
    if v is not None:
        numerator += v * WEIGHT_FINAL
        denominator += WEIGHT_FINAL

    if denominator == 0:
        return None

    return numerator / denominator

def round_score(value: float | None) -> Decimal | None:

    if value is None:
        return None
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def is_passed(average: float | None, passing_score: float) -> bool | None:

    if average is None:
        return None
    return average >= passing_score

def calculate(score_map: dict, passing_score: float) -> tuple[Decimal | None, bool | None]:

    average = calculate_average(score_map)
    rounded = round_score(average)
    return rounded, is_passed(average, passing_score)
