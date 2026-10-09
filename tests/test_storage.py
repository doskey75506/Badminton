import pytest

import storage


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def club(data_dir):
    return storage.create_club("Test Club")["id"]


def test_create_club_and_duplicate(data_dir):
    club = storage.create_club("Alpha")
    assert storage.list_clubs() == [club]
    with pytest.raises(storage.DuplicateNameError):
        storage.create_club("Alpha")
    with pytest.raises(ValueError):
        storage.create_club("   ")


def test_member_lifecycle(club):
    m = storage.add_member(club, "张三")
    assert m["ratings"]["open_double"] == storage.DEFAULT_RATING
    assert m["gender"] is None
    with pytest.raises(storage.DuplicateNameError):
        storage.add_member(club, "张三")
    with pytest.raises(ValueError):
        storage.add_member(club, "  ")
    storage.set_attendance(club, "2026-10-09", [m["id"]])
    storage.delete_member(club, m["id"])
    assert storage.load_members(club) == []
    assert storage.get_attendance(club, "2026-10-09") == []


def test_settings_roundtrip(club):
    assert storage.get_settings(club)["courts"] == storage.DEFAULT_COURTS
    storage.set_settings(club, courts=5)
    assert storage.get_settings(club)["courts"] == 5


def test_attendance_roundtrip(club):
    storage.set_attendance(club, "2026-10-09", ["a", "b"])
    assert storage.get_attendance(club, "2026-10-09") == ["a", "b"]
    assert storage.get_attendance(club, "2026-10-10") == []


def test_match_lifecycle(club):
    m = storage.add_match(
        club, "2026-10-09", 1, ["a", "b"], ["c", "d"],
        {"a": "A", "b": "B", "c": "C", "d": "D"},
        {"a": 1000.0, "b": 1000.0, "c": 1000.0, "d": 1000.0},
    )
    assert m["started_at"] is not None
    assert m["finished_at"] is None
    active = storage.active_matches(club, "2026-10-09")
    assert [x["id"] for x in active] == [m["id"]]

    storage.finish_match(club, m["id"], 21, 15, m["ratings_before"], {"a": 1010.0})
    finished = storage.matches_on(club, "2026-10-09")
    assert finished[0]["finished_at"] is not None
    assert finished[0]["winner"] == "A"
    assert storage.active_matches(club, "2026-10-09") == []

    with pytest.raises(ValueError):
        storage.cancel_match(club, m["id"])


def test_cancel_unfinished_match(club):
    m = storage.add_match(
        club, "2026-10-09", 2, ["a", "b"], ["c", "d"], {},
        {"a": 1000.0, "b": 1000.0, "c": 1000.0, "d": 1000.0},
    )
    storage.cancel_match(club, m["id"])
    assert storage.load_matches(club) == []


def test_multi_club_isolation(data_dir):
    c1 = storage.create_club("One")["id"]
    c2 = storage.create_club("Two")["id"]
    storage.add_member(c1, "Alice")
    storage.add_member(c2, "Bob")
    assert [m["name"] for m in storage.load_members(c1)] == ["Alice"]
    assert [m["name"] for m in storage.load_members(c2)] == ["Bob"]
    storage.set_settings(c1, courts=6)
    assert storage.get_settings(c2)["courts"] == storage.DEFAULT_COURTS


def test_member_gender_and_boards(club):
    m = storage.add_member(club, "Alice", rating=1200, gender="f")
    assert m["gender"] == "f"
    for b in storage.BOARDS:
        assert m["ratings"][b] == 1200.0
    loaded = storage.load_members(club)[0]
    assert loaded["gender"] == "f"
    assert loaded["ratings"]["womens_double"] == 1200.0


def test_member_migration_old_format(data_dir):
    import json

    club = storage.create_club("Old")["id"]
    club_dir = data_dir / "clubs" / club
    club_dir.mkdir(parents=True, exist_ok=True)
    (club_dir / "members.json").write_text(
        json.dumps([
            {"id": "x", "name": "Legacy", "rating": 1100.0,
             "created_at": "2026-01-01T00:00:00"},
        ]),
        encoding="utf-8",
    )
    members = storage.load_members(club)
    assert members[0]["ratings"]["open_single"] == 1100.0
    assert members[0]["ratings"]["womens_double"] == 1100.0
    assert members[0]["gender"] is None
    assert "rating" not in members[0]


def test_match_migration_old_csv(data_dir):
    import pandas as pd

    club = storage.create_club("Old")["id"]
    club_dir = data_dir / "clubs" / club
    club_dir.mkdir(parents=True, exist_ok=True)
    old_cols = [
        "id", "date", "seq", "court", "team_a", "team_b",
        "names", "ratings_before", "ratings_after",
        "score_a", "score_b", "winner", "started_at", "finished_at",
    ]
    row = {
        "id": "m1", "date": "2026-10-01", "seq": "0", "court": "1",
        "team_a": "a|b", "team_b": "c|d",
        "names": '{"a":"A","b":"B","c":"C","d":"D"}',
        "ratings_before": '{"a":1000,"b":1000,"c":1000,"d":1000}',
        "ratings_after": '{"a":1010,"b":1010,"c":990,"d":990}',
        "score_a": "21", "score_b": "15", "winner": "A",
        "started_at": "2026-10-01T20:00:00",
        "finished_at": "2026-10-01T20:20:00",
    }
    pd.DataFrame([row], columns=old_cols).to_csv(
        club_dir / "matches.csv", index=False
    )
    matches = storage.load_matches(club)
    assert matches[0]["board"] == "open_double"
    assert matches[0]["team_a"] == ["a", "b"]


def test_match_board_roundtrip(club):
    m = storage.add_match(
        club, "2026-10-09", 1, ["a"], ["b"], {"a": "A", "b": "B"},
        {"a": 1000.0, "b": 1000.0}, board="open_single",
    )
    assert m["board"] == "open_single"
    loaded = storage.matches_on(club, "2026-10-09")[0]
    assert loaded["board"] == "open_single"
    assert loaded["team_a"] == ["a"]
    assert loaded["team_b"] == ["b"]
