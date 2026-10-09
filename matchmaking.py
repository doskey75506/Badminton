import itertools
import math
from collections import Counter
from datetime import datetime

BALANCE_TOLERANCE = 100
REST_TOLERANCE = 60


def _parse(ts):
    return datetime.fromisoformat(ts) if ts else None


def rest_seconds(available_ids, tonight_matches, now):
    first_start = None
    last_finish = {}
    for m in sorted(tonight_matches, key=lambda x: x["seq"]):
        started = _parse(m.get("started_at"))
        if started and (first_start is None or started < first_start):
            first_start = started
        finished = _parse(m.get("finished_at"))
        if finished:
            for pid in m["team_a"] + m["team_b"]:
                if last_finish.get(pid) is None or finished > last_finish[pid]:
                    last_finish[pid] = finished
    rest = {}
    for pid in available_ids:
        if pid in last_finish:
            t0 = last_finish[pid]
        elif first_start:
            t0 = first_start
        else:
            t0 = now
        rest[pid] = max(0.0, (now - t0).total_seconds())
    return rest


def player_stats(available_ids, tonight_matches, now):
    played = {pid: 0 for pid in available_ids}
    for m in tonight_matches:
        for pid in m["team_a"] + m["team_b"]:
            if pid in played:
                played[pid] += 1
    rest = rest_seconds(available_ids, tonight_matches, now)
    return played, rest


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


def suggest_match(members, available_ids, all_matches, tonight_matches, now, exclude=None):
    if len(available_ids) < 4:
        return None
    played, rest = player_stats(available_ids, tonight_matches, now)
    partners, opponents = pair_counts(all_matches)
    exclude = exclude or set()
    top4 = sorted(rest.values(), reverse=True)[:4]
    top4_sum = sum(top4)
    rest_span = REST_TOLERANCE * 4

    best = None
    for quad in itertools.combinations(sorted(available_ids), 4):
        if frozenset(quad) in exclude:
            continue
        quad_rest = sum(rest[p] for p in quad)
        rest_bucket = int((top4_sum - quad_rest) // rest_span)
        best_pairing = None
        for team_a, team_b in _pairings(quad):
            balance = abs(
                _team_rating(members, team_a) - _team_rating(members, team_b)
            )
            balance_bucket = math.ceil(balance / BALANCE_TOLERANCE)
            pair_rep = (
                partners[tuple(sorted(team_a))] + partners[tuple(sorted(team_b))]
            )
            opp_rep = 0
            for a in team_a:
                for b in team_b:
                    opp_rep += opponents[tuple(sorted((a, b)))]
            key = (balance_bucket, pair_rep, opp_rep, team_a, team_b)
            if best_pairing is None or key < best_pairing[0]:
                best_pairing = (key, team_a, team_b, balance)
        _, team_a, team_b, balance = best_pairing
        full_key = (rest_bucket,) + best_pairing[0]
        if best is None or full_key < best[0]:
            best = (full_key, team_a, team_b, balance)

    if best is None:
        return None
    _, team_a, team_b, balance = best
    stats = {p: {"played": played[p], "rest": rest[p]} for p in available_ids}
    return {
        "team_a": list(team_a),
        "team_b": list(team_b),
        "balance": balance,
        "stats": stats,
    }


def suggest_matches(members, available_ids, all_matches, tonight_matches, now, courts):
    pool = list(available_ids)
    out = {}
    for court in courts:
        suggestion = suggest_match(
            members, pool, all_matches, tonight_matches, now
        )
        if suggestion is None:
            break
        out[court] = suggestion
        used = set(suggestion["team_a"]) | set(suggestion["team_b"])
        pool = [p for p in pool if p not in used]
    return out
