import itertools
import math
from collections import Counter

BALANCE_TOLERANCE = 100


def player_stats(available_ids, tonight_matches):
    order = sorted(tonight_matches, key=lambda m: m["seq"])
    played = {pid: 0 for pid in available_ids}
    bench = {pid: 0 for pid in available_ids}
    for m in order:
        for pid in m["team_a"] + m["team_b"]:
            if pid in played:
                played[pid] += 1
    for pid in available_ids:
        streak = 0
        for m in reversed(order):
            if pid in m["team_a"] + m["team_b"]:
                break
            streak += 1
        bench[pid] = streak
    return played, bench


def pair_counts(all_matches):
    partners = Counter()
    opponents = Counter()
    for m in all_matches:
        for team in (m["team_a"], m["team_b"]):
            for pair in itertools.combinations(sorted(team), 2):
                partners[pair] += 1
        for a in m["team_a"]:
            for b in m["team_b"]:
                opponents[tuple(sorted((a, b)))] += 1
    return partners, opponents


def _pairings(quad):
    a, b, c, d = quad
    return [((a, b), (c, d)), ((a, c), (b, d)), ((a, d), (b, c))]


def _team_rating(members, team):
    return sum(members[p]["rating"] for p in team)


def suggest_match(members, available_ids, all_matches, tonight_matches, exclude=None):
    if len(available_ids) < 4:
        return None
    played, bench = player_stats(available_ids, tonight_matches)
    partners, opponents = pair_counts(all_matches)
    exclude = exclude or set()

    best = None
    for quad in itertools.combinations(sorted(available_ids), 4):
        if frozenset(quad) in exclude:
            continue
        played_sum = sum(played[p] for p in quad)
        bench_sum = sum(bench[p] for p in quad)
        best_pairing = None
        for team_a, team_b in _pairings(quad):
            balance = abs(
                _team_rating(members, team_a) - _team_rating(members, team_b)
            )
            bucket = math.ceil(balance / BALANCE_TOLERANCE)
            pair_rep = (
                partners[tuple(sorted(team_a))] + partners[tuple(sorted(team_b))]
            )
            opp_rep = 0
            for a in team_a:
                for b in team_b:
                    opp_rep += opponents[tuple(sorted((a, b)))]
            key = (bucket, pair_rep, opp_rep, team_a)
            if best_pairing is None or key < best_pairing[0]:
                best_pairing = (key, team_a, team_b, balance)
        bucket, pair_rep, opp_rep, _ = best_pairing[0]
        full_key = (played_sum, -bench_sum, bucket, pair_rep, opp_rep, quad)
        if best is None or full_key < best[0]:
            best = (full_key, best_pairing, quad)

    if best is None:
        return None
    _, (_, team_a, team_b, balance), _ = best
    stats = {
        p: {"played": played[p], "bench": bench[p]} for p in available_ids
    }
    return {
        "team_a": list(team_a),
        "team_b": list(team_b),
        "balance": balance,
        "stats": stats,
    }
