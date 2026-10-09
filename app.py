from datetime import date as date_cls

import streamlit as st

import matchmaking
import ratings
import storage

st.set_page_config(page_title="羽毛球俱乐部排阵", layout="wide")
st.session_state.setdefault("active_date", date_cls.today())
st.session_state.setdefault("suggestion", None)
st.session_state.setdefault("suggestion_date", None)
st.session_state.setdefault("exclude_quads", set())
st.session_state.setdefault("flash", "")

if st.session_state["flash"]:
    st.success(st.session_state["flash"])
    st.session_state["flash"] = ""

page = st.sidebar.radio(
    "功能", ["成员管理", "今晚出席", "排阵与比分", "积分榜"]
)


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


def team_rows(team, members, ratings_map=None):
    total = 0.0
    for pid in team:
        m = members.get(pid)
        if m is None:
            continue
        r = ratings_map[pid] if ratings_map else m["rating"]
        total += r
        st.write(f"**{m['name']}** — {r:.0f}")
    st.write(f"合计积分：{total:.0f}")


def current_suggestion(date_str):
    if st.session_state["suggestion_date"] != date_str:
        return None
    return st.session_state["suggestion"]


if page == "成员管理":
    st.header("成员管理")
    with st.form("add_member_form", clear_on_submit=True):
        name = st.text_input("姓名")
        rating = st.number_input(
            "初始积分", min_value=0.0, value=float(storage.DEFAULT_RATING), step=10.0
        )
        submitted = st.form_submit_button("新增成员")
    if submitted:
        try:
            m = storage.add_member(name, rating)
            st.success(f"已新增成员「{m['name']}」，初始积分 {m['rating']:.0f}")
        except ValueError as e:
            st.warning(str(e))

    members = storage.load_members()
    if not members:
        st.info("还没有成员，请先在上方录入。")
    else:
        stats = overall_stats(storage.load_matches())
        st.subheader(f"成员列表（共 {len(members)} 人）")
        for m in sorted(members, key=lambda x: -x["rating"]):
            played, wins = stats.get(m["id"], (0, 0))
            cols = st.columns([3, 2, 2, 2, 1])
            cols[0].write(f"**{m['name']}**")
            cols[1].write(f"积分 {m['rating']:.0f}")
            cols[2].write(f"场次 {played}")
            cols[3].write(f"胜 {wins} / 负 {played - wins}")
            if cols[4].button("删除", key=f"del_{m['id']}"):
                storage.delete_member(m["id"])
                st.rerun()

elif page == "今晚出席":
    st.header("今晚出席")
    d = st.date_input("日期", key="active_date")
    date_str = d.isoformat()
    members = storage.load_members()
    if not members:
        st.info("还没有成员，请先到「成员管理」录入。")
    else:
        current = set(storage.get_attendance(date_str))
        played, bench = matchmaking.player_stats(
            current, storage.matches_on(date_str)
        )
        members_by_name = {x["id"]: x for x in members}
        checked = []
        for m in members:
            label = f"{m['name']}（积分 {m['rating']:.0f}）"
            if st.checkbox(
                label,
                value=m["id"] in current,
                key=f"att_{date_str}_{m['id']}",
            ):
                checked.append(m["id"])
        storage.set_attendance(date_str, checked)
        if checked:
            st.write(f"**今晚共 {len(checked)} 人出席**")
            rows = [
                {
                    "姓名": members_by_name[p]["name"],
                    "已上场": played.get(p, 0),
                    "连续休息": bench.get(p, 0),
                }
                for p in checked
            ]
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.write("今晚暂无出席人员。")

elif page == "排阵与比分":
    st.header("排阵与比分")
    d = st.date_input("日期", key="active_date")
    date_str = d.isoformat()
    members = storage.members_by_id()
    attendance = storage.get_attendance(date_str)
    tonight = storage.matches_on(date_str)
    active = storage.active_match(date_str)

    if attendance:
        st.write(f"出席 {len(attendance)} 人 · 今晚共 {len(tonight)} 场")

    if active:
        st.subheader("当前进行中的比赛")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**A 队**")
            team_rows(active["team_a"], members)
        with c2:
            st.markdown("**B 队**")
            team_rows(active["team_b"], members)
        s1 = st.number_input(
            "A 队得分",
            min_value=0,
            max_value=30,
            step=1,
            key=f"score_a_{active['id']}",
        )
        s2 = st.number_input(
            "B 队得分",
            min_value=0,
            max_value=30,
            step=1,
            key=f"score_b_{active['id']}",
        )
        if st.button("提交比分"):
            if s1 == s2:
                st.warning("比分不能相同，必须分出胜负")
            else:
                before = active["ratings_before"] or {
                    p: members[p]["rating"]
                    for p in active["team_a"] + active["team_b"]
                }
                try:
                    after = ratings.apply_result(
                        before, active["team_a"], active["team_b"], s1, s2
                    )
                except ValueError as e:
                    st.warning(str(e))
                else:
                    storage.finish_match(active["id"], s1, s2, before, after)
                    all_members = storage.load_members()
                    for m in all_members:
                        if m["id"] in after:
                            m["rating"] = after[m["id"]]
                    storage.save_members(all_members)
                    delta = {p: round(after[p] - before[p], 1) for p in after}
                    winner = "A 队" if s1 > s2 else "B 队"
                    st.session_state["flash"] = (
                        f"已记录：A {s1} : {s2} B，{winner}胜。积分变化："
                        + "，".join(
                            f"{members[p]['name']} {delta[p]:+.1f}"
                            for p in sorted(delta, key=lambda x: -delta[x])
                        )
                    )
                    st.rerun()
    elif len(attendance) < 4:
        st.warning("出席人数不足 4 人，请先到「今晚出席」勾选成员。")
    else:
        available = attendance

        def run_suggest(exclude):
            return matchmaking.suggest_match(
                members, available, storage.load_matches(), tonight, exclude
            )

        if st.button("生成下一场对阵"):
            st.session_state["exclude_quads"] = set()
            st.session_state["suggestion"] = run_suggest(set())
            st.session_state["suggestion_date"] = date_str
            st.rerun()

        suggestion = current_suggestion(date_str)
        if suggestion is None:
            if not tonight:
                st.info("点击「生成下一场对阵」开始排阵。")
        else:
            st.subheader("建议对阵")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**A 队**")
                team_rows(suggestion["team_a"], members)
            with c2:
                st.markdown("**B 队**")
                team_rows(suggestion["team_b"], members)
            st.write(f"双方积分差：{suggestion['balance']:.0f}")
            stat_rows = [
                {
                    "姓名": members[p]["name"],
                    "今晚已上场": suggestion["stats"][p]["played"],
                    "连续休息": suggestion["stats"][p]["bench"],
                }
                for p in sorted(
                    available,
                    key=lambda x: (
                        suggestion["stats"][x]["played"],
                        -suggestion["stats"][x]["bench"],
                    ),
                )
            ]
            st.dataframe(stat_rows, use_container_width=True, hide_index=True)
            b1, b2 = st.columns(2)
            if b1.button("确认开赛"):
                ids = suggestion["team_a"] + suggestion["team_b"]
                names = {p: members[p]["name"] for p in ids}
                before = {p: members[p]["rating"] for p in ids}
                storage.add_match(
                    date_str,
                    suggestion["team_a"],
                    suggestion["team_b"],
                    names,
                    before,
                )
                st.session_state["suggestion"] = None
                st.session_state["suggestion_date"] = None
                st.session_state["exclude_quads"] = set()
                st.session_state["flash"] = "比赛已开始，结束后请录入比分。"
                st.rerun()
            if b2.button("换一组"):
                exclude = set(st.session_state["exclude_quads"])
                exclude.add(frozenset(suggestion["team_a"] + suggestion["team_b"]))
                st.session_state["exclude_quads"] = exclude
                new = run_suggest(exclude)
                if new:
                    st.session_state["suggestion"] = new
                    st.session_state["suggestion_date"] = date_str
                else:
                    st.warning("没有其他可替换的组合了。")
                st.rerun()

elif page == "积分榜":
    st.header("积分榜")
    members = storage.load_members()
    finished = [m for m in storage.load_matches() if m["score_a"] is not None]
    stats = overall_stats(finished)
    rows = []
    for m in members:
        played, wins = stats.get(m["id"], (0, 0))
        rows.append(
            {
                "姓名": m["name"],
                "积分": round(m["rating"], 1),
                "场次": played,
                "胜": wins,
                "负": played - wins,
                "胜率": f"{wins / played:.0%}" if played else "-",
            }
        )
    rows.sort(key=lambda r: -r["积分"])
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("还没有成员。")

    st.subheader("历史对阵")
    history = list(reversed(storage.load_matches()))
    if not history:
        st.info("暂无比赛记录。")
    for m in history:
        score = (
            f"A {m['score_a']} : {m['score_b']} B"
            if m["score_a"] is not None
            else "未开始"
        )
        names = m.get("names", {})
        a = " / ".join(names.get(p, p) for p in m["team_a"])
        b = " / ".join(names.get(p, p) for p in m["team_b"])
        label = f"{m['date']} 第 {m['seq'] + 1} 场 · {a} vs {b} · {score}"
        with st.expander(label):
            if m["ratings_before"] and m["ratings_after"]:
                deltas = [
                    (
                        m["names"].get(p, p),
                        m["ratings_after"][p] - m["ratings_before"][p],
                    )
                    for p in m["ratings_before"]
                ]
                deltas.sort(key=lambda x: -x[1])
                st.write(
                    "积分变化：" + "，".join(f"{n} {d:+.1f}" for n, d in deltas)
                )
