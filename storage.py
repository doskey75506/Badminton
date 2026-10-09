import json
import uuid
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DEFAULT_RATING = 1000
DEFAULT_COURTS = 2


class DuplicateNameError(ValueError):
    pass


def _clubs_file():
    return DATA_DIR / "clubs.json"


def _club_dir(club_id):
    return DATA_DIR / "clubs" / club_id


def _file(club_id, name):
    return _club_dir(club_id) / f"{name}.json"


def _load(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    tmp.replace(path)


def list_clubs():
    return _load(_clubs_file(), [])


def create_club(name):
    name = name.strip()
    if not name:
        raise ValueError("club name cannot be empty")
    clubs = list_clubs()
    if any(c["name"] == name for c in clubs):
        raise DuplicateNameError(f"club 「{name}」 already exists")
    club = {
        "id": uuid.uuid4().hex[:10],
        "name": name,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    clubs.append(club)
    _save(_clubs_file(), clubs)
    return club


def get_settings(club_id):
    settings = {"courts": DEFAULT_COURTS}
    settings.update(_load(_file(club_id, "settings"), {}))
    return settings


def set_settings(club_id, **kwargs):
    settings = get_settings(club_id)
    settings.update(kwargs)
    _save(_file(club_id, "settings"), settings)
    return settings


def load_members(club_id):
    return _load(_file(club_id, "members"), [])


def save_members(club_id, members):
    _save(_file(club_id, "members"), members)


def add_member(club_id, name, rating=None):
    name = name.strip()
    if not name:
        raise ValueError("member name cannot be empty")
    members = load_members(club_id)
    if any(m["name"] == name for m in members):
        raise DuplicateNameError(f"member 「{name}」 already exists")
    member = {
        "id": uuid.uuid4().hex[:10],
        "name": name,
        "rating": float(rating if rating is not None else DEFAULT_RATING),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    members.append(member)
    save_members(club_id, members)
    return member


def delete_member(club_id, member_id):
    members = [m for m in load_members(club_id) if m["id"] != member_id]
    save_members(club_id, members)
    attendance = load_attendance(club_id)
    for date, ids in attendance.items():
        attendance[date] = [i for i in ids if i != member_id]
    save_attendance(club_id, attendance)


def members_by_id(club_id):
    return {m["id"]: m for m in load_members(club_id)}


def load_matches(club_id):
    return _load(_file(club_id, "matches"), [])


def save_matches(club_id, matches):
    _save(_file(club_id, "matches"), matches)


def add_match(club_id, date, court, team_a, team_b, names, ratings_before):
    matches = load_matches(club_id)
    same_day = [m for m in matches if m["date"] == date]
    seq = max((m["seq"] for m in same_day), default=-1) + 1
    match = {
        "id": uuid.uuid4().hex[:10],
        "date": date,
        "seq": seq,
        "court": court,
        "team_a": list(team_a),
        "team_b": list(team_b),
        "names": names,
        "ratings_before": dict(ratings_before),
        "ratings_after": None,
        "score_a": None,
        "score_b": None,
        "winner": None,
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "finished_at": None,
    }
    matches.append(match)
    save_matches(club_id, matches)
    return match


def finish_match(club_id, match_id, score_a, score_b, ratings_before, ratings_after):
    matches = load_matches(club_id)
    for m in matches:
        if m["id"] == match_id:
            m["score_a"] = score_a
            m["score_b"] = score_b
            m["winner"] = "A" if score_a > score_b else "B"
            m["ratings_before"] = ratings_before
            m["ratings_after"] = ratings_after
            m["finished_at"] = datetime.now().isoformat(timespec="seconds")
            break
    save_matches(club_id, matches)


def cancel_match(club_id, match_id):
    matches = load_matches(club_id)
    target = next((m for m in matches if m["id"] == match_id), None)
    if target is None:
        raise ValueError("match not found")
    if target["score_a"] is not None:
        raise ValueError("cannot cancel a finished match")
    save_matches(club_id, [m for m in matches if m["id"] != match_id])


def active_matches(club_id, date):
    return [
        m
        for m in load_matches(club_id)
        if m["date"] == date and m["score_a"] is None
    ]


def matches_on(club_id, date):
    return [m for m in load_matches(club_id) if m["date"] == date]


def load_attendance(club_id):
    return _load(_file(club_id, "attendance"), {})


def save_attendance(club_id, attendance):
    _save(_file(club_id, "attendance"), attendance)


def get_attendance(club_id, date):
    return load_attendance(club_id).get(date, [])


def set_attendance(club_id, date, member_ids):
    attendance = load_attendance(club_id)
    attendance[date] = list(member_ids)
    save_attendance(club_id, attendance)
