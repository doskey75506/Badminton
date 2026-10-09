import json
import uuid
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
MEMBERS_FILE = DATA_DIR / "members.json"
MATCHES_FILE = DATA_DIR / "matches.json"
ATTENDANCE_FILE = DATA_DIR / "attendance.json"

DEFAULT_RATING = 1000


class DuplicateNameError(ValueError):
    pass


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


def load_members():
    return _load(MEMBERS_FILE, [])


def save_members(members):
    _save(MEMBERS_FILE, members)


def add_member(name, rating=None):
    name = name.strip()
    if not name:
        raise ValueError("成员姓名不能为空")
    members = load_members()
    if any(m["name"] == name for m in members):
        raise DuplicateNameError(f"成员「{name}」已存在")
    member = {
        "id": uuid.uuid4().hex[:10],
        "name": name,
        "rating": float(rating if rating is not None else DEFAULT_RATING),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    members.append(member)
    save_members(members)
    return member


def delete_member(member_id):
    members = [m for m in load_members() if m["id"] != member_id]
    save_members(members)
    attendance = load_attendance()
    for date, ids in attendance.items():
        attendance[date] = [i for i in ids if i != member_id]
    save_attendance(attendance)


def members_by_id():
    return {m["id"]: m for m in load_members()}


def load_matches():
    return _load(MATCHES_FILE, [])


def save_matches(matches):
    _save(MATCHES_FILE, matches)


def add_match(date, team_a, team_b, names, ratings_before):
    matches = load_matches()
    today = [m for m in matches if m["date"] == date]
    seq = max((m["seq"] for m in today), default=-1) + 1
    match = {
        "id": uuid.uuid4().hex[:10],
        "date": date,
        "seq": seq,
        "team_a": list(team_a),
        "team_b": list(team_b),
        "names": names,
        "ratings_before": dict(ratings_before),
        "ratings_after": None,
        "score_a": None,
        "score_b": None,
        "winner": None,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "finished_at": None,
    }
    matches.append(match)
    save_matches(matches)
    return match


def finish_match(match_id, score_a, score_b, ratings_before, ratings_after):
    matches = load_matches()
    for m in matches:
        if m["id"] == match_id:
            m["score_a"] = score_a
            m["score_b"] = score_b
            m["winner"] = "A" if score_a > score_b else "B"
            m["ratings_before"] = ratings_before
            m["ratings_after"] = ratings_after
            m["finished_at"] = datetime.now().isoformat(timespec="seconds")
            break
    save_matches(matches)


def active_match(date):
    for m in reversed(load_matches()):
        if m["date"] == date and m["score_a"] is None:
            return m
    return None


def matches_on(date):
    return [m for m in load_matches() if m["date"] == date]


def load_attendance():
    return _load(ATTENDANCE_FILE, {})


def save_attendance(attendance):
    _save(ATTENDANCE_FILE, attendance)


def get_attendance(date):
    return load_attendance().get(date, [])


def set_attendance(date, member_ids):
    attendance = load_attendance()
    attendance[date] = list(member_ids)
    save_attendance(attendance)
