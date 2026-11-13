"""Test score_calculator — công thức ĐTB (logic cốt lõi của Yêu cầu 3)."""
import pytest

from studentapp.services import score_calculator as calc


def _map(**kwargs):
    """Tạo score_map đầy đủ 9 cột, mặc định đều NULL (chưa nhập)."""
    base = {
        "score_15m_1": None, "score_15m_2": None, "score_15m_3": None,
        "score_15m_4": None, "score_15m_5": None,
        "score_45m_1": None, "score_45m_2": None, "score_45m_3": None,
        "score_final": None,
    }
    base.update(kwargs)
    return base


class TestCalculateAverage:
    """Tính ĐTB — chỉ tính ô CÓ GIÁ TRỊ."""

    def test_all_cells_filled(self):
        """Đủ 9 cột: (8+9)×1 + 7.5×2 + 8.5×3 = 52 / 11 = 4.727..."""
        m = _map(
            score_15m_1=8.0, score_15m_2=9.0, score_45m_1=7.5, score_final=8.5
        )
        # tử số = 17*1 + 7.5*2 + 8.5*3 = 17 + 15 + 25.5 = 57.5
        # mẫu số = 2*1 + 1*2 + 1*3 = 7
        assert calc.calculate_average(m) == pytest.approx(57.5 / 7)

    def test_null_cells_excluded_from_both_parts(self):
        """Ô NULL bị loại khỏi CẢ tử số lẫn mẫu số → ĐTB không đổi so với chỉ tính ô có giá trị."""
        m = _map(score_15m_1=8.0, score_15m_2=9.0)
        # tử số = 17, mẫu số = 2 → 8.5 (KHÔNG phải 17/5)
        assert calc.calculate_average(m) == pytest.approx(8.5)

    def test_partial_entry_does_not_divide_by_total_columns(self):
        """GV mới chấm 2/5 cột 15' → mẫu số = 2, KHÔNG phải 5 (chống ĐTB nhảy)."""
        m = _map(score_15m_1=6.0, score_15m_2=8.0)
        assert calc.calculate_average(m) == pytest.approx(7.0)

    def test_zero_is_counted(self):
        """Ô 0.00 là ô CÓ GIÁ TRỊ → vẫn tính (HS vắng bị trừ điểm đúng thực tế)."""
        m = _map(score_15m_1=0.0, score_15m_2=8.0)
        # tử số = 0 + 8 = 8, mẫu số = 2 → 4.0
        assert calc.calculate_average(m) == pytest.approx(4.0)

    def test_all_zero(self):
        """Toàn bộ 0 → ĐTB = 0, không phải None."""
        m = _map(score_15m_1=0.0, score_final=0.0)
        assert calc.calculate_average(m) == pytest.approx(0.0)

    def test_all_null_returns_none(self):
        """Chưa nhập ô nào → ĐTB = None (HS chưa có điểm)."""
        assert calc.calculate_average(_map()) is None

    def test_weights_are_applied(self):
        """Trọng số: 15'×1, 1 tiết×2, thi×3."""
        m = _map(score_15m_1=10.0, score_45m_1=0.0, score_final=0.0)
        # tử số = 10*1 + 0*2 + 0*3 = 10 ; mẫu số = 1 + 2 + 3 = 6
        assert calc.calculate_average(m) == pytest.approx(10 / 6)

    def test_final_alone(self):
        """Chỉ có điểm thi → ĐTB = điểm thi (mẫu số = 3, tử số = điểm × 3)."""
        m = _map(score_final=9.0)
        assert calc.calculate_average(m) == pytest.approx(9.0)


class TestRoundAndPass:
    """Làm tròn & trạng thái Đạt."""

    def test_round_half_up(self):
        """Làm tròn HALF_UP về 2 chữ số (khớp DECIMAL(4,2))."""
        assert float(calc.round_score(8.125)) == 8.13
        assert float(calc.round_score(8.124)) == 8.12

    def test_round_none(self):
        assert calc.round_score(None) is None

    def test_is_passed_threshold(self):
        assert calc.is_passed(5.0, 5.0) is True
        assert calc.is_passed(4.99, 5.0) is False

    def test_is_passed_none(self):
        assert calc.is_passed(None, 5.0) is None

    def test_calculate_returns_tuple(self):
        avg, passed = calc.calculate(_map(score_15m_1=8.0), 5.0)
        assert float(avg) == 8.0
        assert passed is True


class TestCountFilled:
    """Đếm ô đã nhập."""

    def test_counts_only_filled(self):
        m = _map(score_15m_1=8.0, score_final=0.0)
        assert calc.count_filled(m) == 2

    def test_empty_map(self):
        assert calc.count_filled(_map()) == 0
