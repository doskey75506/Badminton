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
    assert m["rating"] == storage.DEFAULT_RATING
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
