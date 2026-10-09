import pytest

import ratings


def test_winner_gains_and_deltas_sum_to_zero():
    before = {"A": 1000.0, "B": 1000.0, "C": 1000.0, "D": 1000.0}
    after = ratings.apply_result(
        before, ["A", "B"], ["C", "D"], 21, 15
    )
    for p in ["A", "B"]:
        assert after[p] > before[p]
    for p in ["C", "D"]:
        assert after[p] < before[p]
    total_before = sum(before.values())
    total_after = sum(after.values())
    assert round(total_after - total_before, 6) == 0


def test_expected_score_symmetry():
    assert ratings.expected_score(1000, 1200) == pytest.approx(
        1 - ratings.expected_score(1200, 1000)
    )


def test_tie_rejected():
    before = {"A": 1000.0, "B": 1000.0}
    with pytest.raises(ValueError):
        ratings.apply_result(before, ["A"], ["B"], 21, 21)


def test_score_out_of_range_rejected():
    before = {"A": 1000.0, "B": 1000.0}
    with pytest.raises(ValueError):
        ratings.apply_result(before, ["A"], ["B"], 31, 20)


def test_bigger_margin_bigger_change():
    before = {"A": 1000.0, "B": 1000.0}
    close = ratings.apply_result(before, ["A"], ["B"], 21, 20)
    blowout = ratings.apply_result(before, ["A"], ["B"], 21, 5)
    assert blowout["A"] - before["A"] > close["A"] - before["A"]


def test_upset_win_awards_more():
    before = {"A": 900.0, "B": 1100.0}
    after = ratings.apply_result(before, ["A"], ["B"], 21, 18)
    assert after["A"] - before["A"] > 0
