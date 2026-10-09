import pytest

import matchmaking


def make_members(ratings):
    return {
        pid: {"id": pid, "name": pid, "rating": float(r)}
        for pid, r in ratings.items()
    }


EQUAL = make_members(
    {n: 1000 for n in ["A", "B", "C", "D", "E", "F"]}
)


def match(date, seq, team_a, team_b, score=None):
    return {
        "date": date,
        "seq": seq,
        "team_a": team_a,
        "team_b": team_b,
        "score_a": score[0] if score else None,
        "score_b": score[1] if score else None,
        "winner": ("A" if score[0] > score[1] else "B") if score else None,
    }


def test_requires_four_players():
    assert matchmaking.suggest_match(EQUAL, ["A", "B", "C"], [], []) is None


def test_rotation_prefers_rested_players():
    tonight = [match("2026-10-09", 0, ["A", "B"], ["C", "D"], (21, 15))]
    result = matchmaking.suggest_match(EQUAL, list("ABCDEF"), [], tonight)
    assert set(result["team_a"] + result["team_b"]) >= {"E", "F"}
    assert result["stats"]["E"]["bench"] == 1
    assert result["stats"]["A"]["played"] == 1


def test_player_stats_bench_streak():
    tonight = [
        match("2026-10-09", 0, ["A", "B"], ["C", "D"], (21, 15)),
        match("2026-10-09", 1, ["E", "F"], ["A", "B"], (21, 15)),
    ]
    played, bench = matchmaking.player_stats(list("ABCDEF"), tonight)
    assert played["A"] == 2
    assert played["C"] == 1
    assert bench["C"] == 1
    assert bench["A"] == 0
    assert bench["F"] == 0


def test_balance_splits_strong_and_weak():
    members = make_members({"A": 800, "B": 820, "C": 1200, "D": 1180})
    result = matchmaking.suggest_match(members, list("ABCD"), [], [])
    teams = [set(result["team_a"]), set(result["team_b"])]
    for team in teams:
        ratings = sorted(members[p]["rating"] for p in team)
        assert ratings[0] < 1000 < ratings[1]
    assert result["balance"] <= 20


def test_avoids_repeated_partner():
    history = [match("2026-10-08", 0, ["A", "B"], ["C", "D"], (21, 15))]
    result = matchmaking.suggest_match(EQUAL, list("ABCDEF"), history, [])
    partners, _ = matchmaking.pair_counts(history)
    for team in (result["team_a"], result["team_b"]):
        pair = tuple(sorted(team))
        assert partners[pair] == 0


def test_excluded_quads_are_skipped():
    first = matchmaking.suggest_match(EQUAL, list("ABCDEF"), [], [])
    excluded = {frozenset(first["team_a"] + first["team_b"])}
    second = matchmaking.suggest_match(
        EQUAL, list("ABCDEF"), [], [], exclude=excluded
    )
    assert second is not None
    assert frozenset(second["team_a"] + second["team_b"]) not in excluded
