from datetime import date as date_cls, datetime, timedelta

import streamlit as st

import i18n
import matchmaking
import ratings
import storage

st.set_page_config(page_title="Badminton", layout="wide")


def T(key, **kw):
    return i18n.t(st.session_state.lang, key, **kw)


st.session_state.setdefault("lang", "zh")
st.session_state.setdefault("active_date", date_cls.today())
st.session_state.setdefault("suggestions", {})
st.session_state.setdefault("sug_club", None)
st.session_state.setdefault("sug_date", None)
st.session_state.setdefault("flash", "")
st.session_state.setdefault("warning", "")


def fmt_time(iso):
    if not iso:
        return "-"
    return datetime.fromisoformat(iso).strftime("%H:%M")


def fmt_duration(m):
    if not m.get("started_at") or not m.get("finished_at"):
        return "-"
    seconds = int(
        (
            datetime.fromisoformat(m["finished_at"])
            - datetime.fromisoformat(m["started_at"])
        ).total_seconds()
    )
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def join_deltas(deltas):
    sep = "，" if st.session_state.lang == "zh" else ", "
    return sep.join(f"{n} {d:+.1f}" for n, d in deltas)


def overall_stats(matches):
    stats = {}
    for m in matches:
        if m["score_a"] is None:
            continue
        winner_team = m["team_a"] if m["winner"] == "A" else m["team_b"]
        for pid in m["team_a"] + m["team_b"]:
            played, wins = stats.get(pid, (0, 0))
            stats[pid] = (played + 1, wins + (1 if pid in winner_team else 0))
    return stats


def team_block(team, name_of, rating_of=None):
    total = 0.0
    any_rating = False
    for pid in team:
        name = name_of(pid)
        r = rating_of(pid) if rating_of is not None else None
        if r is None:
            st.write(f"**{name}**")
        else:
            any_rating = True
            total += r
            st.write(f"**{name}** — {r:.0f}")
    if any_rating:
        st.caption(T("total_rating", r=round(total)))


with st.sidebar:
    lang_pick = st.selectbox(
        "语言 / Language", ["中文", "English"],
        index=0 if st.session_state.lang == "zh" else 1,
    )
    st.session_state.lang = "zh" if lang_pick == "中文" else "en"

clubs = storage.list_clubs()

if not clubs:
    st.title(T("welcome"))
    with st.form("first_club"):
        name = st.text_input(T("club_name"))
        if st.form_submit_button(T("create")):
            try:
                new_club = storage.create_club(name)
                st.session_state.club_id = new_club["id"]
                st.rerun()
            except storage.DuplicateNameError:
                st.warning(T("club_dup"))
            except ValueError:
                st.warning(T("club_name_invalid"))
    st.stop()

if st.session_state.get("club_id") not in [c["id"] for c in clubs]:
    st.session_state.club_id = clubs[0]["id"]

with st.sidebar:
    club_names = [c["name"] for c in clubs]
    current_club_name = next(
        c["name"] for c in clubs if c["id"] == st.session_state.club_id
    )
    picked = st.selectbox(
        T("club"), club_names, index=club_names.index(current_club_name)
    )
    st.session_state.club_id = next(c["id"] for c in clubs if c["name"] == picked)
    with st.expander(T("new_club")):
        new_name = st.text_input(T("club_name"), key="new_club_name")
        if st.button(T("create"), key="create_club_btn"):
            try:
                new_club = storage.create_club(new_name)
                st.session_state.club_id = new_club["id"]
                st.rerun()
            except storage.DuplicateNameError:
                st.session_state.warning = T("club_dup")
                st.rerun()
            except ValueError:
                st.session_state.warning = T("club_name_invalid")
                st.rerun()
    page = st.radio(
        T("nav"),
        [T("p_tonight"), T("p_members"), T("p_standings"), T("p_history")],
    )

club = st.session_state.club_id

if st.session_state["flash"]:
    st.success(st.session_state["flash"])
    st.session_state["flash"] = ""
if st.session_state["warning"]:
    st.warning(st.session_state["warning"])
    st.session_state["warning"] = ""


def submit_score(match, score_a, score_b):
    try:
        score_a = int(str(score_a).strip())
        score_b = int(str(score_b).strip())
    except ValueError:
        st.session_state.warning = T("score_invalid")
        st.rerun()
        return
    members = storage.members_by_id(club)
    if score_a == score_b:
        st.session_state.warning = T("score_tie")
        st.rerun()
        return
    before = match["ratings_before"]
    try:
        after = ratings.apply_result(
            before, match["team_a"], match["team_b"], score_a, score_b
        )
    except ValueError:
        st.session_state.warning = T("score_range")
        st.rerun()
        return
    storage.finish_match(club, match["id"], score_a, score_b, before, after)
    all_members = storage.load_members(club)
    for m in all_members:
        if m["id"] in after:
            m["rating"] = after[m["id"]]
    storage.save_members(club, all_members)
    deltas = sorted(
        (
            (match["names"].get(p, p), round(after[p] - before[p], 1))
            for p in after
        ),
        key=lambda x: -x[1],
    )
    winner = T("team_a") if score_a > score_b else T("team_b")
    st.session_state.flash = T(
        "score_saved", a=score_a, b=score_b, w=winner, changes=join_deltas(deltas)
    )
    st.rerun()


def start_match(court_no, suggestion, date_str, members):
    ids = suggestion["team_a"] + suggestion["team_b"]
    names = {p: members[p]["name"] for p in ids}
    before = {p: members[p]["rating"] for p in ids}
    storage.add_match(
        club, date_str, court_no,
        suggestion["team_a"], suggestion["team_b"], names, before,
    )
    st.session_state.suggestions.pop(court_no, None)
    st.session_state.flash = T("match_started")
    st.rerun()


def render_court(court_no, active, suggestion, members, date_str, others_used, available):
    with st.container(border=True):
        st.markdown(f"**{T('court')} {court_no}**")
        if active is not None:
            st.caption(T("running_at", t=fmt_time(active["started_at"])))
            snap = active.get("names", {})
            before = active.get("ratings_before") or {}
            c1, c2 = st.columns(2)
            with c1:
                st.caption(T("team_a"))
                team_block(
                    active["team_a"],
                    lambda p: snap.get(p) or members.get(p, {}).get("name", p),
                    lambda p: before.get(p),
                )
            with c2:
                st.caption(T("team_b"))
                team_block(
                    active["team_b"],
                    lambda p: snap.get(p) or members.get(p, {}).get("name", p),
                    lambda p: before.get(p),
                )
            sc = st.columns(2)
            score_a = sc[0].text_input("A", key=f"sa_{active['id']}")
            score_b = sc[1].text_input("B", key=f"sb_{active['id']}")
            bb = st.columns(2)
            if bb[0].button(
                T("submit_score"), key=f"sub_{active['id']}",
                type="primary", width="stretch",
            ):
                submit_score(active, score_a, score_b)
            if bb[1].button(
                T("cancel_match"), key=f"cx_{active['id']}",
                width="stretch",
            ):
                storage.cancel_match(club, active["id"])
                st.session_state.flash = T("match_cancelled")
                st.rerun()
        elif suggestion is not None:
            c1, c2 = st.columns(2)
            with c1:
                st.caption(T("team_a"))
                team_block(
                    suggestion["team_a"],
                    lambda p: members[p]["name"],
                    lambda p: members[p]["rating"],
                )
            with c2:
                st.caption(T("team_b"))
                team_block(
                    suggestion["team_b"],
                    lambda p: members[p]["name"],
                    lambda p: members[p]["rating"],
                )
            st.caption(T("balance", n=round(suggestion["balance"])))
            bb = st.columns(2)
            if bb[0].button(
                T("confirm_start"), key=f"start_{court_no}",
                type="primary", width="stretch",
            ):
                start_match(court_no, suggestion, date_str, members)
            if bb[1].button(
                T("regen"), key=f"regen_{court_no}", width="stretch"
            ):
                pool = [p for p in available if p not in others_used]
                exclude = {frozenset(suggestion["team_a"] + suggestion["team_b"])}
                new = matchmaking.suggest_match(
                    members, pool, storage.load_matches(club),
                    storage.matches_on(club, date_str),
                    datetime.now(), exclude,
                )
                if new:
                    st.session_state.suggestions[court_no] = new
                else:
                    st.session_state.warning = T("no_other_pairing")
                st.rerun()
        else:
            st.caption(T("court_free"))


if page == T("p_tonight"):
    c = st.columns([2, 2, 8])
    d = c[0].date_input(T("date"), key="active_date")
    date_str = d.isoformat()
    settings = storage.get_settings(club)
    n_courts = int(
        c[1].number_input(
            T("courts"), min_value=1, max_value=12,
            value=int(settings["courts"]), step=1, key="courts_input",
        )
    )
    if n_courts != settings["courts"]:
        storage.set_settings(club, courts=n_courts)

    members = storage.members_by_id(club)
    if st.session_state.sug_club != club or st.session_state.sug_date != date_str:
        st.session_state.suggestions = {}
        st.session_state.sug_club = club
        st.session_state.sug_date = date_str

    tonight = storage.matches_on(club, date_str)
    active_list = storage.active_matches(club, date_str)
    active_by_court = {m["court"]: m for m in active_list}
    on_court = {p for m in active_list for p in m["team_a"] + m["team_b"]}

    st.subheader(T("attendance"))
    if not members:
        st.info(T("no_members_tonight"))
        checked = []
    else:
        current = set(storage.get_attendance(club, date_str))
        ordered = sorted(members.values(), key=lambda m: m["name"])
        checked = []
        cb_cols = st.columns(3)
        for i, m in enumerate(ordered):
            with cb_cols[i % 3]:
                label = T(
                    "member_chip", n=m["name"], r=f"{m['rating']:.0f}"
                )
                if st.checkbox(
                    label, value=m["id"] in current,
                    key=f"att_{date_str}_{m['id']}",
                ):
                    checked.append(m["id"])
        storage.set_attendance(club, date_str, checked)

    now = datetime.now()
    available = [p for p in checked if p not in on_court]

    suggestions = {
        court: s for court, s in st.session_state.suggestions.items()
        if court <= n_courts
        and set(s["team_a"] + s["team_b"]) <= set(available)
    }
    st.session_state.suggestions = suggestions

    player_court = {
        p: court
        for court, m in active_by_court.items()
        for p in m["team_a"] + m["team_b"]
    }
    for court, s in suggestions.items():
        for p in s["team_a"] + s["team_b"]:
            player_court.setdefault(p, court)

    if checked:
        played, rest = matchmaking.player_stats(checked, tonight, now)
        st.caption(
            T("attendance_summary", n=len(checked), on=len(on_court))
        )
        stat_rows = [
            {
                T("col_name"): members[p]["name"],
                T("col_games"): played.get(p, 0),
                T("col_rest"): round(rest.get(p, 0) / 60, 1),
                T("col_court"): str(player_court[p]) if p in player_court else T("rest"),
            }
            for p in sorted(checked, key=lambda x: -rest.get(x, 0))
        ]
        st.dataframe(stat_rows, width="stretch", hide_index=True)

    need_gen = [
        court for court in range(1, n_courts + 1)
        if court not in active_by_court and court not in suggestions
    ]
    if st.button(
        T("gen_all", n=len(need_gen)), disabled=not need_gen,
        type="primary",
    ):
        if len(available) < 4:
            st.session_state.warning = T("not_enough_players")
            st.rerun()
        else:
            new_sugs = matchmaking.suggest_matches(
                members, available, storage.load_matches(club),
                tonight, now, need_gen,
            )
            suggestions.update(new_sugs)
            st.session_state.suggestions = suggestions
            st.rerun()

    used_by_court = {
        court: set(s["team_a"]) | set(s["team_b"])
        for court, s in suggestions.items()
    }
    max_court = max([n_courts, *active_by_court.keys()])
    court_cols = st.columns(3)
    for i, court_no in enumerate(range(1, max_court + 1)):
        with court_cols[i % 3]:
            others_used = set()
            for cno, ids in used_by_court.items():
                if cno != court_no:
                    others_used |= ids
            render_court(
                court_no,
                active_by_court.get(court_no),
                suggestions.get(court_no),
                members,
                date_str,
                others_used,
                available,
            )

elif page == T("p_members"):
    st.header(T("p_members"))
    with st.form("add_member_form", clear_on_submit=True):
        name = st.text_input(T("name"))
        rating = st.number_input(
            T("initial_rating"), min_value=0.0,
            value=float(storage.DEFAULT_RATING), step=10.0,
        )
        submitted = st.form_submit_button(T("add_member"))
    if submitted:
        try:
            m = storage.add_member(club, name, rating)
            st.session_state.flash = T(
                "member_added", n=m["name"], r=f"{m['rating']:.0f}"
            )
            st.rerun()
        except storage.DuplicateNameError:
            st.session_state.warning = T("name_dup", n=name.strip())
            st.rerun()
        except ValueError:
            st.session_state.warning = T("name_empty")
            st.rerun()

    member_list = storage.load_members(club)
    if not member_list:
        st.info(T("no_members"))
    else:
        stats = overall_stats(storage.load_matches(club))
        st.subheader(T("member_list", n=len(member_list)))
        for m in sorted(member_list, key=lambda x: -x["rating"]):
            played, wins = stats.get(m["id"], (0, 0))
            cols = st.columns([3, 2, 2, 3, 1])
            cols[0].write(f"**{m['name']}**")
            cols[1].write(f"{T('rating')} {m['rating']:.0f}")
            cols[2].write(f"{T('games')} {played}")
            cols[3].write(T("w_l", w=wins, l=played - wins))
            if cols[4].button(
                T("delete"), key=f"del_{m['id']}", width="stretch"
            ):
                storage.delete_member(club, m["id"])
                st.rerun()

elif page == T("p_standings"):
    st.header(T("p_standings"))
    member_list = storage.load_members(club)
    finished = [
        m for m in storage.load_matches(club) if m["score_a"] is not None
    ]
    stats = overall_stats(finished)
    rows = []
    for m in member_list:
        played, wins = stats.get(m["id"], (0, 0))
        rows.append(
            {
                T("col_name"): m["name"],
                T("rating"): round(m["rating"], 1),
                T("games"): played,
                T("wins"): wins,
                T("losses"): played - wins,
                T("win_rate"): f"{wins / played:.0%}" if played else "-",
            }
        )
    rows.sort(key=lambda r: -r[T("rating")])
    if rows:
        st.dataframe(rows, width="stretch", hide_index=True)
    else:
        st.info(T("no_members"))

elif page == T("p_history"):
    st.header(T("p_history"))
    all_matches = storage.load_matches(club)
    if not all_matches:
        st.info(T("h_no_data"))
    else:
        fc1, fc2 = st.columns(2)
        range_pick = fc1.selectbox(
            T("h_range"),
            [T("h_all"), T("h_today"), T("h_7"), T("h_30")],
        )
        name_pool = sorted(
            {n for m in all_matches for n in m.get("names", {}).values()}
        )
        player_pick = fc2.selectbox(
            T("h_player"), [T("h_all_players")] + name_pool
        )
        cutoff = None
        if range_pick == T("h_today"):
            cutoff = date_cls.today().isoformat()
        elif range_pick == T("h_7"):
            cutoff = (date_cls.today() - timedelta(days=7)).isoformat()
        elif range_pick == T("h_30"):
            cutoff = (date_cls.today() - timedelta(days=30)).isoformat()

        rows = []
        for m in sorted(
            all_matches, key=lambda x: (x["date"], x["seq"]), reverse=True
        ):
            if cutoff and m["date"] < cutoff:
                continue
            names = m.get("names", {})
            if player_pick != T("h_all_players") and player_pick not in names.values():
                continue
            team_a = " / ".join(names.get(p, p) for p in m["team_a"])
            team_b = " / ".join(names.get(p, p) for p in m["team_b"])
            score = (
                f"{m['score_a']}:{m['score_b']}"
                if m["score_a"] is not None
                else T("ongoing")
            )
            winner = "-"
            if m["winner"]:
                winner = T("team_a") if m["winner"] == "A" else T("team_b")
            chg = "-"
            if m.get("ratings_before") and m.get("ratings_after"):
                deltas = sorted(
                    (
                        (
                            names.get(p, p),
                            m["ratings_after"][p] - m["ratings_before"][p],
                        )
                        for p in m["ratings_before"]
                    ),
                    key=lambda x: -x[1],
                )
                chg = join_deltas(deltas)
            rows.append(
                {
                    T("h_date"): m["date"],
                    T("h_start"): fmt_time(m.get("started_at")),
                    T("h_end"): fmt_time(m.get("finished_at")),
                    T("h_court"): m.get("court", "-"),
                    T("h_teams_a"): team_a,
                    T("h_teams_b"): team_b,
                    T("h_score"): score,
                    T("h_winner"): winner,
                    T("h_duration"): fmt_duration(m),
                    T("h_rating_chg"): chg,
                }
            )
        st.caption(T("h_count", n=len(rows)))
        if rows:
            st.dataframe(rows, width="stretch", hide_index=True)
        else:
            st.info(T("h_no_data"))
