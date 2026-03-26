
import streamlit as st
import random
import plotly.graph_objects as go

# ========================= Page Config =========================
st.set_page_config(page_title="E-Sport Tournament", page_icon="🏆", layout="wide")

# ========================= Session State Init =========================
for key, default in {
    "teams": [],
    "tournament_log": [],
    "bracket_matches": [],
    "current_match_index": 0,
    "tournament_phase": None,
    "upper_winner": None,
    "lower_teams": [],
    "lower_winner": None,
    "champion": None,
    "tournament_type": None,
    "phase_history": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

teams = st.session_state.teams


def build_matches(teams):
    matches = []
    for i in range(0, len(teams), 2):
        left = teams[i]
        right = teams[i+1] if i+1 < len(teams) else "BYE"
        matches.append({
            "left": left,
            "right": right,
            "winner": None,
            "loser": None
        })
    return matches
# ========================= Helper Functions =========================
def sequential_search(name):
    for i, t in enumerate(teams):
        if t["name"].lower() == name.lower():
            return i
    return -1

def merge_sort(arr):
    if len(arr) > 1:
        mid = len(arr) // 2
        L, R = arr[:mid], arr[mid:]
        merge_sort(L); merge_sort(R)
        i = j = k = 0
        while i < len(L) and j < len(R):
            if L[i]["win"] - L[i]["loss"] >= R[j]["win"] - R[j]["loss"]:
                arr[k] = L[i]; i += 1
            else:
                arr[k] = R[j]; j += 1
            k += 1
        while i < len(L): arr[k] = L[i]; i += 1; k += 1
        while j < len(R): arr[k] = R[j]; j += 1; k += 1

def build_bracket_matches(team_list):
    matches, nodes = [], list(team_list)
    for i in range(0, len(nodes) - 1, 2):
        matches.append({"left": nodes[i], "right": nodes[i+1], "winner": None})
    if len(nodes) % 2 == 1:
        matches.append({"left": nodes[-1], "right": "BYE", "winner": nodes[-1]})
    return matches

def record_win_loss(winner, loser):
    w = sequential_search(winner)
    l = sequential_search(loser)
    if w != -1: teams[w]["win"] += 1
    if l != -1: teams[l]["loss"] += 1

def reset_tournament():
    for k in ["bracket_matches", "tournament_log", "phase_history"]:
        st.session_state[k] = []
    st.session_state["current_match_index"] = 0
    for k in ["tournament_phase", "upper_winner", "lower_winner", "champion", "tournament_type"]:
        st.session_state[k] = None
    st.session_state["lower_teams"] = []

def save_round_to_history(phase, matches):
    history = st.session_state.phase_history
    if history and history[-1][0] == phase:
        history[-1][1].append([dict(m) for m in matches])
    else:
        history.append((phase, [[dict(m) for m in matches]]))

# ========================= Bracket Tree Visualizer =========================
def draw_bracket():
    history = st.session_state.phase_history
    cur_phase = st.session_state.tournament_phase
    cur_matches = st.session_state.bracket_matches

    # Collect all rounds
    all_rounds = []
    phase_label_map = {
        "upper": "Upper",
        "lower": "Lower",
        "grand_final": "Grand Final"
    }
    phase_color_map = {
        "upper":       "#3b82f6",
        "lower":       "#ef4444",
        "grand_final": "#f59e0b"
    }

    for phase_name, rounds in history:
        for r_idx, round_matches in enumerate(rounds):
            all_rounds.append((phase_name, r_idx + 1, round_matches))

    # Add current in-progress round if not yet saved
    if cur_phase and cur_matches:
        already = False
        if history and history[-1][0] == cur_phase:
            last_saved = history[-1][1][-1] if history[-1][1] else []
            if last_saved and last_saved[0].get("left") == cur_matches[0].get("left"):
                already = True
        if not already:
            r_num = (len(history[-1][1]) + 1) if (history and history[-1][0] == cur_phase) else 1
            all_rounds.append((cur_phase, r_num, cur_matches))

    if not all_rounds:
        st.info("ยังไม่มีข้อมูล Bracket")
        return

    num_cols = len(all_rounds)
    col_w = 3.5
    row_h = 1.2
    max_matches = max(len(r[2]) for r in all_rounds)
    canvas_h = max_matches * row_h * 2 + 1.5

    edge_x, edge_y = [], []
    shapes = []
    annotations = []
    hover_x, hover_y, hover_text = [], [], []

    def team_y(match_idx, total_matches, side):
        # side: 0=top, 1=bottom
        slot_h = canvas_h / (total_matches + 0.5)
        center = (match_idx + 0.5) * slot_h
        offset = 0.35
        return center + offset if side == 0 else center - offset

    # Build match positions for edge routing
    match_positions = {}  # (col_idx, match_idx) -> (x, y_top, y_bot, match)

    for col_idx, (phase_name, r_num, matches) in enumerate(all_rounds):
        x = col_idx * col_w
        total = len(matches)
        for m_idx, match in enumerate(matches):
            yt = team_y(m_idx, total, 0)
            yb = team_y(m_idx, total, 1)
            match_positions[(col_idx, m_idx)] = (x, yt, yb, match)

    # Draw
    for col_idx, (phase_name, r_num, matches) in enumerate(all_rounds):
        x = col_idx * col_w
        total = len(matches)
        p_color = phase_color_map.get(phase_name, "#94a3b8")
        col_label = f"{phase_label_map.get(phase_name, phase_name)} R{r_num}"

        # Column header
        annotations.append(dict(
            x=x, y=canvas_h + 0.2,
            text=f"<b>{col_label}</b>",
            showarrow=False,
            font=dict(size=12, color=p_color),
            xanchor="center", yanchor="bottom"
        ))

        for m_idx, match in enumerate(matches):
            x_pos, yt, yb, _ = match_positions[(col_idx, m_idx)]
            left = match["left"]
            right = match["right"]
            winner = match["winner"]
            box_w = 1.4

            for side, team, y in [(0, left, yt), (1, right, yb)]:
                is_winner = (team == winner and winner is not None)
                is_bye = (team == "BYE")
                fill = "#f59e0b" if is_winner else ("#1e293b" if not is_bye else "#0f172a")
                border = "#f59e0b" if is_winner else (p_color if not is_bye else "#334155")
                txt_color = "#0f172a" if is_winner else ("#94a3b8" if is_bye else "white")
                label = ("🏆 " + team) if is_winner else team

                # Box
                shapes.append(dict(
                    type="rect",
                    x0=x - box_w/2, x1=x + box_w/2,
                    y0=y - 0.22, y1=y + 0.22,
                    fillcolor=fill,
                    line=dict(color=border, width=2 if is_winner else 1),
                    layer="above"
                ))

                # Label
                annotations.append(dict(
                    x=x, y=y,
                    text=f"<b>{label}</b>" if is_winner else label,
                    showarrow=False,
                    font=dict(size=10, color=txt_color),
                    xanchor="center", yanchor="middle"
                ))

                # Hover point
                hover_x.append(x); hover_y.append(y)
                status = "🏆 Winner" if is_winner else ("BYE" if is_bye else "—")
                hover_text.append(f"{team}<br>{status}")

            # Vertical connector between two slots
            edge_x += [x, x, None]
            edge_y += [yt - 0.22, yb + 0.22, None]

            # Horizontal connector to next round
            if col_idx + 1 < len(all_rounds) and winner and winner != "BYE":
                next_matches = all_rounds[col_idx + 1][2]
                for nm_idx, nm in enumerate(next_matches):
                    if nm["left"] == winner or nm["right"] == winner:
                        nx, nyt, nyb, _ = match_positions[(col_idx + 1, nm_idx)]
                        ny = nyt if nm["left"] == winner else nyb
                        y_w = yt if winner == left else yb
                        mid_x = (x + nx) / 2
                        edge_x += [x + box_w/2, mid_x, mid_x, nx - box_w/2, None]
                        edge_y += [y_w, y_w, ny, ny, None]
                        break

    fig = go.Figure()

    # Edges
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y, mode="lines",
        line=dict(color="#475569", width=1.5),
        hoverinfo="none", showlegend=False
    ))

    # Invisible hover points
    fig.add_trace(go.Scatter(
        x=hover_x, y=hover_y, mode="markers",
        marker=dict(size=8, color="rgba(0,0,0,0)"),
        text=hover_text, hoverinfo="text",
        showlegend=False
    ))

    fig.update_layout(
        shapes=shapes,
        annotations=annotations,
        paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a",
        xaxis=dict(
            showgrid=False, zeroline=False, showticklabels=False,
            range=[-2, (num_cols - 1) * col_w + 2]
        ),
        yaxis=dict(
            showgrid=False, zeroline=False, showticklabels=False,
            range=[-0.5, canvas_h + 0.8]
        ),
        margin=dict(l=10, r=10, t=20, b=10),
        height=max(350, int(canvas_h * 80) + 100),
        dragmode="pan",
        hoverlabel=dict(bgcolor="#1e293b", font_size=12, font_color="white")
    )

    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})

# ========================= Custom CSS =========================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@600;700&family=Inter:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.main-title {
    text-align:center; font-family:'Rajdhani',sans-serif;
    font-size:2.8rem; font-weight:700; letter-spacing:4px;
    background:linear-gradient(90deg,#f97316,#facc15,#f97316);
    background-size:200%; -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;
    animation:shine 3s linear infinite;
}
@keyframes shine{0%{background-position:0%}100%{background-position:200%}}
.sub-title{text-align:center;color:#64748b;letter-spacing:3px;font-size:0.8rem;margin-bottom:2rem;}
.match-card{background:#1e293b;border-radius:12px;padding:1.2rem;border:1px solid #334155;}
.team-badge{background:#0f172a;border-radius:8px;padding:0.5rem 1rem;font-weight:bold;}
.champion-banner{
    background:linear-gradient(135deg,#92400e,#f59e0b,#92400e);
    border-radius:16px;padding:2rem;text-align:center;
    font-family:'Rajdhani',sans-serif;font-size:2.2rem;font-weight:700;
    color:white;letter-spacing:2px;box-shadow:0 0 40px rgba(245,158,11,0.4);
}
.phase-badge{background:#7c3aed;color:white;border-radius:20px;padding:0.3rem 1rem;font-size:0.85rem;font-weight:600;}
.log-entry{background:#0f172a;border-left:3px solid #f97316;padding:0.4rem 0.8rem;margin-bottom:0.3rem;border-radius:4px;font-size:0.9rem;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">⚡ E-SPORT TOURNAMENT ⚡</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">MANAGE · BRACKET · CHAMPION</div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["👥 Teams", "📊 Rankings", "🎮 Tournament", "🌲 Bracket Tree", "📜 Log"])

# ========================= TAB 1 =========================
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("➕ Add Team")
        new_name = st.text_input("Team Name", key="add_name")
        if st.button("Add Team", use_container_width=True, type="primary"):
            if not new_name.strip():
                st.warning("กรุณากรอกชื่อทีม")
            elif sequential_search(new_name.strip()) != -1:
                st.error(f"ทีม **{new_name}** มีอยู่แล้ว!")
            else:
                teams.append({"name": new_name.strip(), "win": 0, "loss": 0})
                st.success(f"✅ เพิ่มทีม **{new_name}**"); st.rerun()
        st.divider()
        st.subheader("✏️ Update Team")
        if teams:
            upd_sel = st.selectbox("เลือกทีม", [t["name"] for t in teams], key="upd_sel")
            upd_name = st.text_input("ชื่อใหม่", key="upd_name")
            if st.button("Update", use_container_width=True):
                if upd_name.strip():
                    idx = sequential_search(upd_sel)
                    if idx != -1:
                        teams[idx]["name"] = upd_name.strip()
                        st.success(f"เปลี่ยนเป็น **{upd_name}**"); st.rerun()
        else:
            st.info("ยังไม่มีทีม")
    with col2:
        st.subheader("🗑️ Delete Team")
        if teams:
            del_sel = st.selectbox("เลือกทีมที่จะลบ", [t["name"] for t in teams], key="del_sel")
            if st.button("Delete Team", use_container_width=True):
                idx = sequential_search(del_sel)
                if idx != -1:
                    teams.pop(idx); st.success(f"ลบ **{del_sel}**"); st.rerun()
        else:
            st.info("ไม่มีทีมให้ลบ")
        st.divider()
        st.subheader("🔍 Search Team")
        search_name = st.text_input("ค้นหา", key="search_inp")
        if st.button("Search", use_container_width=True):
            idx = sequential_search(search_name.strip())
            if idx == -1: st.error("ไม่พบทีม")
            else:
                t = teams[idx]; st.success(f"พบ: **{t['name']}** | W:{t['win']} L:{t['loss']}")
        st.divider()
        st.subheader("⚠️ Data Management")
        ca, cb = st.columns(2)
        with ca:
            if st.button("🧹 Reset Scores", use_container_width=True):
                for t in teams: t["win"] = 0; t["loss"] = 0
                st.success("รีเซ็ตคะแนน"); st.rerun()
        with cb:
            if st.button("💣 Remove All", use_container_width=True):
                teams.clear(); st.success("ลบทั้งหมด"); st.rerun()

# ========================= TAB 2 =========================
with tab2:
    st.subheader("📊 Team Rankings")
    if not teams:
        st.info("ยังไม่มีทีม")
    else:
        st_teams = list(teams); merge_sort(st_teams)
        cols = st.columns([1,3,2,2,2])
        for c, l in zip(cols,["Rank","Team","Wins","Losses","Score"]): c.markdown(f"**{l}**")
        st.divider()
        for rank, t in enumerate(st_teams, 1):
            cols = st.columns([1,3,2,2,2])
            medal = ["🥇","🥈","🥉"][rank-1] if rank<=3 else f"#{rank}"
            cols[0].write(medal); cols[1].write(f"**{t['name']}**")
            cols[2].write(f"✅ {t['win']}"); cols[3].write(f"❌ {t['loss']}")
            sc = t['win']-t['loss']
            cols[4].markdown(f"<span style='color:{'#22c55e' if sc>=0 else '#ef4444'};font-weight:bold'>{sc:+d}</span>", unsafe_allow_html=True)

# ========================= TAB 3 =========================
with tab3:
    st.subheader("🎮 Tournament")

    if st.session_state.champion:
        st.markdown(f'<div class="champion-banner">🏆 CHAMPION : {st.session_state.champion} 🏆</div>', unsafe_allow_html=True)
        if st.button("🔄 Reset Tournament", use_container_width=True):
            reset_tournament(); st.rerun()

    elif st.session_state.tournament_phase is None:
        if len(teams) < 2:
            st.warning("⚠️ เพิ่มทีมอย่างน้อย 2 ทีมก่อนเริ่ม")
        else:
            st.markdown(f"**ทีมที่พร้อม:** {len(teams)} ทีม")
            t_type = st.radio("รูปแบบการแข่งขัน", ["Single Elimination", "Double Elimination"], horizontal=True)
            if t_type == "Double Elimination" and len(teams) < 3:
                st.warning("Double Elimination ต้องการอย่างน้อย 3 ทีม")
            else:
                if st.button("🚀 Start Tournament!", use_container_width=True, type="primary"):
                    reset_tournament()
                    team_names = [t["name"] for t in teams]
                    random.shuffle(team_names)
                    st.session_state.tournament_type = t_type
                    st.session_state.upper_matches = build_matches(team_names)
                    st.session_state.lower_matches = []
                    st.session_state.lower_queue = []

                    st.session_state.current_match_index = 0
                    st.session_state.tournament_phase = "upper"
                    st.session_state.tournament_log = [f"🎮 **{t_type}** เริ่มแล้ว! ({len(teams)} ทีม)"]
                    st.rerun()
    else:
        phase = st.session_state.tournament_phase
        matches = st.session_state.bracket_matches
        idx = st.session_state.current_match_index
        phase_labels = {"upper":"🔵 Upper Bracket","lower":"🔴 Lower Bracket","grand_final":"⭐ Grand Final"}
        st.markdown(f'<span class="phase-badge">{phase_labels.get(phase,phase)}</span>', unsafe_allow_html=True)
        st.write("")

        # Auto BYE
        while idx < len(matches) and matches[idx]["right"] == "BYE":
            winner = matches[idx]["left"]
            matches[idx]["winner"] = winner
            w = sequential_search(winner)
            if w != -1: teams[w]["win"] += 1
            st.session_state.tournament_log.append(f"⏭️ **{winner}** ผ่าน (BYE)")
            idx += 1
        st.session_state.current_match_index = idx
        all_done = idx >= len(matches)

        if not all_done:
            match = matches[idx]
            left, right = match["left"], match["right"]
            st.markdown(f"### Match {idx+1} / {len(matches)}")
            cl, cv, cr = st.columns([2,1,2])
            with cl: st.markdown(f'<div class="team-badge">🔵 {left}</div>', unsafe_allow_html=True)
            with cv: st.markdown("<div style='text-align:center;font-size:1.8rem'>⚔️</div>", unsafe_allow_html=True)
            with cr: st.markdown(f'<div class="team-badge">🔴 {right}</div>', unsafe_allow_html=True)
            
            st.write("")
            cw1, cw2 = st.columns(2)

            with cw1:
                if st.button(
                    f"🏆 {left} ชนะ",
                    key=f"left_win_{idx}",   # 👈 เพิ่มตรงนี้
                    use_container_width=True,
                    type="primary"
                ):
                    record_win_loss(left, right)
                    matches[idx]["winner"] = left
                    st.session_state.tournament_log.append(f"⚔️ **{left}** ชนะ **{right}**")
                    st.session_state.current_match_index += 1
                    st.rerun()
            with cw2:
                if st.button(
                    f"🏆 {right} ชนะ",
                    key=f"right_win_{idx}", 
                    use_container_width=True,
                    type="primary"
                ):
                    record_win_loss(right, left)
                    matches[idx]["winner"] = right
                    st.session_state.tournament_log.append(f"⚔️ **{right}** ชนะ **{left}**")
                    st.session_state.current_match_index += 1
                    st.rerun()

            st.progress(idx / len(matches))
            st.caption(f"Match {idx+1} / {len(matches)}")
            
        else:
            winners = [m["winner"] for m in matches if m["winner"]]
            save_round_to_history(phase, matches)

            if phase == "upper":
                winners = []
                losers = []

                for m in matches:
                    if m["winner"]:
                        winners.append(m["winner"])
                        losers.append(m["loser"])

                if len(winners) == 1:
                    # ได้แชมป์ Upper
                    st.session_state.upper_winner = winners[0]

                    # เอาคนแพ้ทั้งหมดไป Lower
                    st.session_state.lower_matches = build_matches(losers)
                    st.session_state.tournament_phase = "lower"
                    st.session_state.current_match_index = 0
                    st.session_state.tournament_log.append("🔴 **Lower Bracket เริ่ม!**")
                    st.rerun()
                else:
                    # เล่น Upper ต่อ
                    st.session_state.upper_matches = build_matches(winners)

                    # เก็บคนแพ้สะสม
                    st.session_state.lower_queue.extend(losers)

                    st.session_state.current_match_index = 0
                    st.rerun()
            elif phase == "lower":
                winners = [m["winner"] for m in matches if m["winner"]]

                if len(winners) == 1:
                    # ได้ผู้ชนะ Lower
                    st.session_state.lower_winner = winners[0]

                    # ไป Grand Final
                    gf = [st.session_state.upper_winner, winners[0]]
                    st.session_state.bracket_matches = build_matches(gf)

                    st.session_state.current_match_index = 0
                    st.session_state.tournament_phase = "grand_final"
                    st.session_state.tournament_log.append("⭐ **Grand Final เริ่ม!**")
                    st.rerun()
                else:
                    # เล่น Lower ต่อ
                    st.session_state.lower_matches = build_matches(winners)
                    st.session_state.current_match_index = 0
                    st.rerun()
            elif phase == "grand_final":
                if winners:
                    st.session_state.champion = winners[0]; st.rerun()

        st.write("")
        if st.button("❌ ยกเลิก Tournament", use_container_width=True):
            reset_tournament(); st.rerun()

# ========================= TAB 4: Bracket Tree =========================
with tab4:
    st.subheader("🌲 Bracket Tree")
    if not st.session_state.phase_history and not st.session_state.tournament_phase:
        st.info("เริ่ม Tournament ก่อนเพื่อดู Bracket Tree ที่นี่")
        st.markdown("""
        **Bracket Tree จะแสดง:**
        - 📦 กล่องแต่ละทีมในแต่ละ Match
        - 🔗 เส้นเชื่อมระหว่างผู้ชนะในแต่ละรอบ
        - 🏆 ไฮไลท์ทีมที่ชนะด้วยสีทอง
        - 🔵 Upper / 🔴 Lower / ⭐ Grand Final แยกสี
        """)
    else:
        draw_bracket()
        st.write("")
        lc, mc, rc = st.columns(3)
        lc.markdown("<span style='color:#f59e0b'>█</span> **ทีมที่ชนะ**", unsafe_allow_html=True)
        mc.markdown("<span style='color:#475569'>█</span> **ทีมที่แข่ง**", unsafe_allow_html=True)
        rc.markdown("<span style='color:#1e293b'>█</span> **BYE**", unsafe_allow_html=True)

# ========================= TAB 5 =========================
with tab5:
    st.subheader("📜 Match Log")
    if not st.session_state.tournament_log:
        st.info("ยังไม่มีประวัติ")
    else:
        for entry in reversed(st.session_state.tournament_log):
            st.markdown(f'<div class="log-entry">{entry}</div>', unsafe_allow_html=True)