import math

K_FACTOR = 32


def expected_score(rating_a, rating_b):
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))


def margin_multiplier(score_a, score_b, rating_a, rating_b):
    point_diff = abs(score_a - score_b)
    elo_diff = abs(rating_a - rating_b)
    mult = math.log(point_diff + 1) * (2.2 / (elo_diff * 0.001 + 2.2))
    return max(1.0, min(2.0, mult))


def apply_result(ratings_before, team_a, team_b, score_a, score_b):
    if score_a == score_b:
        raise ValueError("比分不能相同，必须分出胜负")
    if min(score_a, score_b) < 0 or max(score_a, score_b) > 30:
        raise ValueError("比分需在 0-30 之间")
    if not team_a or not team_b:
        raise ValueError("双方队伍不能为空")

    rating_a = sum(ratings_before[p] for p in team_a)
    rating_b = sum(ratings_before[p] for p in team_b)
    exp_a = expected_score(rating_a, rating_b)
    actual_a = 1.0 if score_a > score_b else 0.0
    mult = margin_multiplier(score_a, score_b, rating_a, rating_b)

    delta_a = K_FACTOR * (actual_a - exp_a) * mult
    ratings_after = {}
    for p in team_a:
        ratings_after[p] = round(ratings_before[p] + delta_a, 1)
    for p in team_b:
        ratings_after[p] = round(ratings_before[p] - delta_a, 1)
    for p in ratings_after:
        ratings_after[p] = max(0.0, ratings_after[p])
    return ratings_after
