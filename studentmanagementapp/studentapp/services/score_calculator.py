"""SERVICE score_calculator — Tính điểm trung bình môn (<<include>> của SD11/SD14).

Công thức DUY NHẤT (áp dụng ở mọi nơi: lưu nháp, tính lại sau phúc khảo,
báo cáo, xuất file)::

    ĐTB = (Σ điểm 15' có giá trị × 1
         + Σ điểm 1 tiết có giá trị × 2
         + Σ điểm thi có giá trị × 3)
         / (số ô 15' có giá trị
         + số ô 1 tiết có giá trị × 2
         + số ô thi có giá trị × 3)

Nguyên tắc:
* Ô ``NULL`` (chưa nhập) bị loại khỏi **cả tử số và mẫu số** → không ảnh hưởng ĐTB.
* Ô ``0.00`` (vắng / thi 0 điểm) là ô **có giá trị** → vẫn tính → HS vắng bị trừ
  điểm đúng thực tế.
* Mẫu số **KHÔNG** dùng "số cột theo quy chế" — nếu dùng, khi Giáo viên mới chấm
  dở (VD 2/5 cột) ĐTB sẽ nhảy giữa các lần lưu.
"""
from decimal import Decimal, ROUND_HALF_UP

from studentapp.models.score import (
    SCORE_COLUMNS_15M,
    SCORE_COLUMNS_45M,
    SCORE_COLUMN_FINAL,
    WEIGHT_15M,
    WEIGHT_45M,
    WEIGHT_FINAL,
)

#: Số chữ số thập phân của ĐTB trong DB (DECIMAL(4,2)).
SCORE_PRECISION = 2


def _to_float(value):
    """Chuyển giá trị ô điểm (Decimal/None) về float; ``None`` nghĩa là chưa nhập."""
    if value is None:
        return None
    return float(value)


def calculate_average(score_map: dict) -> float | None:
    """Tính ĐTB từ dict {tên cột: giá trị}.

    Trả về ``None`` khi không có ô nào có giá trị (học sinh chưa có điểm).
    """
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
    """Làm tròn ĐTB về 2 chữ số thập phân (quy tắc HALF_UP, khớp DECIMAL(4,2))."""
    if value is None:
        return None
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def is_passed(average: float | None, passing_score: float) -> bool | None:
    """Trạng thái Đạt: ĐTB >= ngưỡng quy định. ``None`` khi chưa có ĐTB."""
    if average is None:
        return None
    return average >= passing_score


def calculate(score_map: dict, passing_score: float) -> tuple[Decimal | None, bool | None]:
    """Tính cả ĐTB và trạng thái Đạt — hàm dùng chung cho mọi luồng ghi điểm.

    :return: ``(average_score, is_passed)``
    """
    average = calculate_average(score_map)
    rounded = round_score(average)
    return rounded, is_passed(average, passing_score)


def count_filled(score_map: dict) -> int:
    """Đếm số ô đã nhập (không tính ô NULL)."""
    from studentapp.models.score import ALL_SCORE_COLUMNS

    return sum(1 for col in ALL_SCORE_COLUMNS if score_map.get(col) is not None)
