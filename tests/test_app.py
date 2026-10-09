from datetime import date as date_cls
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import storage

APP_PATH = Path(__file__).parent.parent / "app.py"
TODAY = date_cls.today().isoformat()


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    at = AppTest.from_file(str(APP_PATH), default_timeout=15)
    at.run()
    assert not at.exception
    return at


def seed_club(names=("Alice", "Bob", "Cara", "Dan", "Eve", "Frank")):
    club = storage.create_club("Test Club")["id"]
    ids = [storage.add_member(club, n)["id"] for n in names]
    storage.set_attendance(club, TODAY, ids)
    return club, ids


def click(at, label):
    matches = [b for b in at.button if b.label == label]
    assert matches, f"button {label!r} not found: {[b.label for b in at.button]}"
    matches[0].click()
    at.run()
    assert not at.exception


def navigate(at, page_label):
    at.radio[0].set_value(page_label)
    at.run()
    assert not at.exception


def test_first_run_welcome(app):
    assert app.title[0].value == "创建第一个俱乐部"
    assert not app.exception


def test_all_pages_render_zh(app):
    seed_club()
    app.run()
    assert not app.exception
    for page in ["今晚", "成员", "积分榜", "历史"]:
        navigate(app, page)


def test_all_pages_render_en(app):
    seed_club()
    app.run()
    lang = [s for s in app.selectbox if s.label == "语言 / Language"][0]
    lang.set_value("English")
    app.run()
    assert not app.exception
    for page in ["Tonight", "Members", "Standings", "History"]:
        navigate(app, page)


def test_generate_and_start_match(app):
    seed_club()
    app.run()
    click(app, "为 2 个空闲场地生成对阵")
    click(app, "开赛")
    club = storage.list_clubs()[0]["id"]
    active = storage.active_matches(club, TODAY)
    assert len(active) == 1
    score_inputs = [i for i in app.text_input if i.label in ("A", "B")]
    assert len(score_inputs) == 2


def test_submit_score_updates_rating(app):
    club, ids = seed_club()
    before = {p: 1000.0 for p in ids[:4]}
    storage.add_match(
        club, TODAY, 1, ids[:2], ids[2:4],
        {p: n for p, n in zip(ids[:4], ["Alice", "Bob", "Cara", "Dan"])},
        before,
    )
    app.run()
    assert not app.exception
    inputs = [i for i in app.text_input if i.label in ("A", "B")]
    assert len(inputs) == 2
    inputs[0].set_value("21")
    inputs[1].set_value("15")
    click(app, "提交比分")
    matches = storage.matches_on(club, TODAY)
    assert matches[0]["score_a"] == 21
    assert matches[0]["finished_at"] is not None
    members = {m["id"]: m["ratings"]["open_double"] for m in storage.load_members(club)}
    assert members[ids[0]] > 1000
    assert members[ids[2]] < 1000


def test_add_member_form(app):
    seed_club(names=("Alice",))
    app.run()
    navigate(app, "成员")
    name_input = [t for t in app.text_input if t.label == "姓名"][0]
    name_input.set_value("New Player")
    click(app, "新增成员")
    assert "New Player" in [m["name"] for m in storage.load_members(
        storage.list_clubs()[0]["id"]
    )]


def test_court_count_adjustable(app):
    seed_club()
    app.run()
    courts = [i for i in app.number_input if i.label == "场地数量"][0]
    courts.set_value(4)
    app.run()
    assert not app.exception
    club = storage.list_clubs()[0]["id"]
    assert storage.get_settings(club)["courts"] == 4


def test_shuffle_replaces_suggestion(app):
    seed_club()
    app.run()
    click(app, "为 2 个空闲场地生成对阵")
    before = app.session_state["suggestions"]
    click(app, "换一组")
    after = app.session_state["suggestions"]
    assert set(before) == set(after)
    assert after != before or len(before) == 1


def test_cancel_match(app):
    club, ids = seed_club()
    app.run()
    click(app, "为 2 个空闲场地生成对阵")
    click(app, "开赛")
    assert storage.active_matches(club, TODAY)
    click(app, "作废")
    assert storage.active_matches(club, TODAY) == []


def test_create_and_switch_club(app):
    seed_club()
    app.run()
    name_input = [t for t in app.text_input if t.key == "new_club_name"][0]
    name_input.set_value("Second Club")
    click(app, "创建")
    clubs = storage.list_clubs()
    assert [c["name"] for c in clubs] == ["Test Club", "Second Club"]
    assert app.session_state["club_id"] == clubs[1]["id"]
    club_sel = [s for s in app.selectbox if s.label == "俱乐部"][0]
    club_sel.set_value("Test Club")
    app.run()
    assert not app.exception
    assert app.session_state["club_id"] == clubs[0]["id"]


def history_count(at):
    captions = [c.value for c in at.caption if c.value.startswith("共")]
    return captions[-1] if captions else None


def test_history_custom_date_range(app):
    from datetime import timedelta

    club, ids = seed_club(names=("Alice", "Bob", "Cara", "Dan"))
    names = {p: n for p, n in zip(ids, ["Alice", "Bob", "Cara", "Dan"])}
    ratings = {p: 1000.0 for p in ids}
    old = (date_cls.today() - timedelta(days=40)).isoformat()
    storage.add_match(club, old, 1, ids[:2], ids[2:], names, ratings)
    storage.add_match(club, TODAY, 1, ids[:2], ids[2:], names, ratings)
    app.run()
    navigate(app, "历史")
    assert history_count(app) == "共 2 场"

    range_pick = [s for s in app.selectbox if s.label == "时间范围"][0]
    range_pick.set_value("自定义范围")
    app.run()
    assert not app.exception
    d_from = [d for d in app.date_input if d.key == "h_from"][0]
    d_from.set_value(date_cls.today() - timedelta(days=7))
    app.run()
    assert history_count(app) == "共 1 场"

    d_to = [d for d in app.date_input if d.key == "h_to"][0]
    d_to.set_value(date_cls.today() - timedelta(days=100))
    app.run()
    assert history_count(app) == "共 0 场"
    assert any("不能晚于" in w.value for w in app.warning)


def test_free_court_shows_board_selector(app):
    seed_club()
    app.run()
    board_sels = [s for s in app.selectbox if s.label == "比赛类型"]
    assert len(board_sels) == 2
    assert board_sels[0].options == ["开放单打", "女子单打", "开放双打", "女子双打"]


def test_standings_board_selector(app):
    club, ids = seed_club(names=("Alice", "Bob", "Cara", "Dan"))
    names = {p: n for p, n in zip(ids, ["Alice", "Bob", "Cara", "Dan"])}
    ratings = {p: 1000.0 for p in ids}
    storage.add_match(
        club, TODAY, 1, ids[:2], ids[2:], names, ratings,
        board="open_double",
    )
    storage.finish_match(
        club, storage.matches_on(club, TODAY)[0]["id"],
        21, 15, ratings, {ids[0]: 1016.0, ids[1]: 1016.0, ids[2]: 984.0, ids[3]: 984.0},
    )
    app.run()
    navigate(app, "积分榜")
    board_sel = [s for s in app.selectbox if s.label == "比赛类型"][0]
    assert board_sel.options == ["开放单打", "女子单打", "开放双打", "女子双打"]


def test_history_shows_board_column(app):
    club, ids = seed_club(names=("Alice", "Bob", "Cara", "Dan"))
    names = {p: n for p, n in zip(ids, ["Alice", "Bob", "Cara", "Dan"])}
    ratings = {p: 1000.0 for p in ids}
    storage.add_match(
        club, TODAY, 1, ids[:2], ids[2:], names, ratings, board="womens_double"
    )
    app.run()
    navigate(app, "历史")
    assert len(app.dataframe) == 1
    cols = list(app.dataframe[0].value.columns)
    assert "类型" in cols


def test_add_member_with_gender(app):
    seed_club(names=("Alice",))
    app.run()
    navigate(app, "成员")
    name_input = [t for t in app.text_input if t.label == "姓名"][0]
    name_input.set_value("New Girl")
    gender_sel = [s for s in app.selectbox if s.label == "性别"][0]
    gender_sel.set_value("女")
    click(app, "新增成员")
    members = storage.load_members(storage.list_clubs()[0]["id"])
    m = next(x for x in members if x["name"] == "New Girl")
    assert m["gender"] == "f"


def test_womens_court_flow(app):
    club = storage.create_club("Test Club")["id"]
    ids = [storage.add_member(club, n, gender="f")["id"]
           for n in ("Alice", "Bob", "Cara", "Dan")]
    storage.set_attendance(club, TODAY, ids)
    app.run()
    board_sel = [s for s in app.selectbox if s.label == "比赛类型"][0]
    board_sel.set_value("女子双打")
    app.run()
    click(app, "为 2 个空闲场地生成对阵")
    sugs = app.session_state["suggestions"]
    assert sugs[1]["board"] == "womens_double"
    click(app, "开赛")
    active = storage.active_matches(club, TODAY)
    assert active[0]["board"] == "womens_double"
    inputs = [i for i in app.text_input if i.label in ("A", "B")]
    inputs[0].set_value("21")
    inputs[1].set_value("15")
    click(app, "提交比分")
    members = {m["id"]: m for m in storage.load_members(club)}
    winner_team = active[0]["team_a"]
    loser_team = active[0]["team_b"]
    assert members[winner_team[0]]["ratings"]["womens_double"] > 1000
    assert members[loser_team[0]]["ratings"]["womens_double"] < 1000
    assert members[winner_team[0]]["ratings"]["open_double"] == 1000
