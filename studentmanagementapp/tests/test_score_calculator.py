import pytest

from studentapp.services import score_calculator as calc

def _map(**kwargs):

    base = {
        "score_15m_1": None, "score_15m_2": None, "score_15m_3": None,
        "score_15m_4": None, "score_15m_5": None,
        "score_45m_1": None, "score_45m_2": None, "score_45m_3": None,
        "score_final": None,
    }
    base.update(kwargs)
    return base

class TestCalculateAverage:

    def test_all_cells_filled(self):

        m = _map(
            score_15m_1=8.0, score_15m_2=9.0, score_45m_1=7.5, score_final=8.5
        )

        assert calc.calculate_average(m) == pytest.approx(57.5 / 7)

    def test_null_cells_excluded_from_both_parts(self):

        m = _map(score_15m_1=8.0, score_15m_2=9.0)

        assert calc.calculate_average(m) == pytest.approx(8.5)

    def test_partial_entry_does_not_divide_by_total_columns(self):

        m = _map(score_15m_1=6.0, score_15m_2=8.0)
        assert calc.calculate_average(m) == pytest.approx(7.0)

    def test_zero_is_counted(self):

        m = _map(score_15m_1=0.0, score_15m_2=8.0)

        assert calc.calculate_average(m) == pytest.approx(4.0)

    def test_all_zero(self):

        m = _map(score_15m_1=0.0, score_final=0.0)
        assert calc.calculate_average(m) == pytest.approx(0.0)

    def test_all_null_returns_none(self):

        assert calc.calculate_average(_map()) is None

    def test_weights_are_applied(self):

        m = _map(score_15m_1=10.0, score_45m_1=0.0, score_final=0.0)

        assert calc.calculate_average(m) == pytest.approx(10 / 6)

    def test_final_alone(self):

        m = _map(score_final=9.0)
        assert calc.calculate_average(m) == pytest.approx(9.0)

class TestRoundAndPass:

    def test_round_half_up(self):

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
