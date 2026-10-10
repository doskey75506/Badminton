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


def _gender_ok(member, board):
    if board.startswith("womens"):
        return member.get("gender") == "f"
    return True


def _pairings(quad):
    a, b, c, d = quad
    return [((a, b), (c, d)), ((a, c), (b, d)), ((a, d), (b, c))]


def _team_rating(members, team, board):
    return sum(members[p]["ratings"][board] for p in team)


def suggest_match(members, available_ids, all_matches, tonight_matches, now, exclude=None, board="open_double"):
    is_single = board.endswith("single")
    need = 2 if is_single else 4
    if len(available_ids) < need:
        return None
    played, rest = player_stats(available_ids, tonight_matches, now)
    partners, opponents = pair_counts(all_matches)
    exclude = exclude or set()
    top = sorted(rest.values(), reverse=True)[:need]
    top_sum = sum(top)
    rest_span = REST_TOLERANCE * need

    best = None
    for group in itertools.combinations(sorted(available_ids), need):
        if frozenset(group) in exclude:
            continue
        group_rest = sum(rest[p] for p in group)
        rest_bucket = int((top_sum - group_rest) // rest_span)
        best_pairing = None
        if is_single:
            pairings = [((group[0],), (group[1],))]
        else:
            pairings = _pairings(group)
        for team_a, team_b in pairings:
            balance = abs(
                _team_rating(members, team_a, board)
                - _team_rating(members, team_b, board)
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
        "board": board,
    }


def suggest_matches(members, available_ids, all_matches, tonight_matches, now, courts_boards):
    normalized = []
    for item in courts_boards:
        if isinstance(item, tuple):
            normalized.append(item)
        else:
            normalized.append((item, "open_double"))
    pool = list(available_ids)
    out = {}
    for court, board in normalized:
        gender_pool = [p for p in pool if _gender_ok(members[p], board)]
        suggestion = suggest_match(
            members, gender_pool, all_matches, tonight_matches, now, board=board
        )
        if suggestion is None:
            continue
        out[court] = suggestion
        used = set(suggestion["team_a"]) | set(suggestion["team_b"])
        pool = [p for p in pool if p not in used]
    return out


def suggest_substitutes(
    members, free_ids, team_a, team_b, outgoing,
    all_matches, tonight_matches, now, board,
):
    outgoing = set(outgoing)
    slots = [("a", i) for i, p in enumerate(team_a) if p in outgoing]
    slots += [("b", i) for i, p in enumerate(team_b) if p in outgoing]
    slot_pids = [p for p in team_a + team_b if p in outgoing]
    free_ids = list(free_ids)
    need = len(slots)
    if need == 0 or len(free_ids) < need:
        return None
    _, rest = player_stats(free_ids, tonight_matches, now)
    partners, opponents = pair_counts(all_matches)
    top = sorted((rest[p] for p in free_ids), reverse=True)[:need]
    top_sum = sum(top)
    rest_span = REST_TOLERANCE * need
    rating = {p: members[p]["ratings"][board] for p in free_ids}
    kept_a = sum(
        members[p]["ratings"][board] for p in team_a if p not in outgoing
    )
    kept_b = sum(
        members[p]["ratings"][board] for p in team_b if p not in outgoing
    )
    best = None
    for combo in itertools.permutations(free_ids, need):
        new_a = list(team_a)
        new_b = list(team_b)
        for k, (side, i) in enumerate(slots):
            (new_a if side == "a" else new_b)[i] = combo[k]
        add_a = [combo[k] for k in range(need) if slots[k][0] == "a"]
        add_b = [combo[k] for k in range(need) if slots[k][0] == "b"]
        rest_bucket = int(
            (top_sum - sum(rest[p] for p in combo)) // rest_span
        )
        balance = abs(
            kept_a + sum(rating[p] for p in add_a)
            - kept_b - sum(rating[p] for p in add_b)
        )
        balance_bucket = math.ceil(balance / BALANCE_TOLERANCE)
        pair_rep = (
            partners[tuple(sorted(new_a))] + partners[tuple(sorted(new_b))]
        )
        opp_rep = 0
        for a in new_a:
            for b in new_b:
                opp_rep += opponents[tuple(sorted((a, b)))]
        key = (rest_bucket, balance_bucket, pair_rep, opp_rep, combo)
        if best is None or key < best[0]:
            best = (key, combo)
    if best is None:
        return None
    return {slot_pids[k]: best[1][k] for k in range(need)}
