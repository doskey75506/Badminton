from datetime import datetime, timedelta

import pytest

import matchmaking

NOW = datetime(2026, 10, 9, 21, 0, 0)


def make_members(ratings):
    return {
        pid: {"id": pid, "name": pid, "rating": float(r)}
        for pid, r in ratings.items()
    }


EQUAL = make_members({n: 1000 for n in ["A", "B", "C", "D", "E", "F"]})


def match(seq, team_a, team_b, started=None, finished=None, score=(21, 15)):
    return {
        "date": "2026-10-09",
        "seq": seq,
        "team_a": team_a,
        "team_b": team_b,
        "score_a": score[0],
        "score_b": score[1],
        "winner": "A" if score[0] > score[1] else "B",
        "started_at": started.isoformat() if started else None,
        "finished_at": finished.isoformat() if finished else None,
    }


def test_requires_four_players():
    assert (
        matchmaking.suggest_match(EQUAL, ["A", "B", "C"], [], [], NOW) is None
    )


def test_picks_longest_rested_players():
    tonight = [
        match(
            0, ["A", "B"], ["C", "D"],
            started=NOW - timedelta(minutes=10),
            finished=NOW - timedelta(minutes=1),
        )
    ]
    result = matchmaking.suggest_match(EQUAL, list("ABCDEF"), [], tonight, NOW)
    quad = set(result["team_a"] + result["team_b"])
    assert {"E", "F"} <= quad
    assert result["stats"]["E"]["rest"] == pytest.approx(600)
    assert result["stats"]["A"]["rest"] == pytest.approx(60)


def test_player_stats_counts_and_rest():
    tonight = [
        match(
            0, ["A", "B"], ["C", "D"],
            started=NOW - timedelta(minutes=30),
            finished=NOW - timedelta(minutes=20),
        ),
        match(
            1, ["A", "B"], ["E", "F"],
            started=NOW - timedelta(minutes=10),
            finished=NOW - timedelta(minutes=2),
        ),
    ]
    played, rest = matchmaking.player_stats(list("ABCDEF"), tonight, NOW)
    assert played["A"] == 2
    assert played["C"] == 1
    assert played["E"] == 1
    assert rest["A"] == pytest.approx(120)
    assert rest["C"] == pytest.approx(1200)
    assert rest["E"] == pytest.approx(120)


def test_fresh_night_prefers_balance():
    members = make_members({"A": 800, "B": 820, "C": 1200, "D": 1180})
    result = matchmaking.suggest_match(members, list("ABCD"), [], [], NOW)
    teams = [set(result["team_a"]), set(result["team_b"])]
    for team in teams:
        ratings = sorted(members[p]["rating"] for p in team)
        assert ratings[0] < 1000 < ratings[1]
    assert result["balance"] <= 20


def test_avoids_repeated_partner():
    history = [
        match(
            0, ["A", "B"], ["C", "D"],
            started=NOW - timedelta(days=1),
            finished=NOW - timedelta(days=1) + timedelta(minutes=20),
        )
    ]
    result = matchmaking.suggest_match(
        EQUAL, list("ABCDEF"), history, [], NOW
    )
    partners, _ = matchmaking.pair_counts(history)
    for team in (result["team_a"], result["team_b"]):
        assert partners[tuple(sorted(team))] == 0


def test_excluded_quads_are_skipped():
    first = matchmaking.suggest_match(EQUAL, list("ABCDEF"), [], [], NOW)
    excluded = {frozenset(first["team_a"] + first["team_b"])}
    second = matchmaking.suggest_match(
        EQUAL, list("ABCDEF"), [], [], NOW, exclude=excluded
    )
    assert second is not None
    assert frozenset(second["team_a"] + second["team_b"]) not in excluded


def test_multi_court_suggestions_are_disjoint():
    eight = make_members({n: 1000 for n in list("ABCDEFGH")})
    out = matchmaking.suggest_matches(eight, list("ABCDEFGH"), [], [], NOW, [1, 2])
    assert set(out) == {1, 2}
    quad1 = set(out[1]["team_a"] + out[1]["team_b"])
    quad2 = set(out[2]["team_a"] + out[2]["team_b"])
    assert quad1.isdisjoint(quad2)
    assert len(quad1) == 4 and len(quad2) == 4


def test_multi_court_stops_when_pool_exhausted():
    six = make_members({n: 1000 for n in list("ABCDEF")})
    out = matchmaking.suggest_matches(six, list("ABCDEF"), [], [], NOW, [1, 2])
    assert set(out) == {1}
