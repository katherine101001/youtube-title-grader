"""
YouTube Title Optimizer — Assignment Architecture
  Page 1: End user — idea → best title
  Page 2: Behind the scenes — full AI decision process

Backend: Render /optimize (iterative Gemini + model scoring)
n8n: orchestrates trigger → predict → AI reason → Google Sheets → respond
"""
import streamlit as st
import requests
import json
import os

st.set_page_config(page_title="YouTube Title Optimizer", page_icon="🎬", layout="centered")
st.markdown("""<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
.stButton > button { font-size: 1.1rem !important; padding: 0.8rem 2rem !important; }
</style>""", unsafe_allow_html=True)

N8N_URL = os.environ.get("N8N_WEBHOOK", "https://katherine2304.app.n8n.cloud/webhook/optimize")
RENDER_URL = "https://youtube-title-grader.onrender.com/optimize"

CATS = {1:"Film & Animation",2:"Autos & Vehicles",10:"Music",15:"Pets & Animals",17:"Sports",
        19:"Travel & Events",20:"Gaming",22:"People & Blogs",23:"Comedy",24:"Entertainment",
        25:"News & Politics",26:"Howto & Style",27:"Education",28:"Science & Tech",29:"Nonprofits"}
CAT_ID = {v:k for k,v in CATS.items()}

page = st.sidebar.radio("View", ["🎯 End User", "🔧 How AI Decides"], label_visibility="collapsed")

# ═══════════════════════════════════════════════════════════
# PAGE 1 — End User
# ═══════════════════════════════════════════════════════════
if page == "🎯 End User":
    st.markdown("""
    <div style="text-align:center;padding:3rem 0 2rem 0;">
        <h1 style="font-size:3rem;margin-bottom:0.5rem;">🎬 Title Optimizer</h1>
        <p style="font-size:1.1rem;color:#999;">Tell me your video idea. AI does the rest.</p>
    </div>
    """, unsafe_allow_html=True)

    idea = st.text_area(
        "What's your video about?",
        placeholder="e.g. I want to make a video comparing iPhone 17 and Samsung S25 cameras...",
        height=100,
    )
    col1, col2 = st.columns([2, 1])
    with col1:
        cat_name = st.selectbox("Category", list(CATS.values()), index=list(CATS.values()).index("Entertainment"))
    with col2:
        st.write("")
        go = st.button("🚀 Optimize", type="primary", use_container_width=True, disabled=not idea.strip())

    if go and idea.strip():
        with st.spinner("AI optimizing your title..."):
            try:
                # Call Render API directly for structured data
                resp = requests.post(RENDER_URL, json={"idea": idea.strip(), "category_id": CAT_ID[cat_name]}, timeout=180)
                if resp.ok:
                    d = resp.json()
                    title = d.get("best_title", "?")
                    score = d.get("best_score", 0)
                    idea_text = d.get("idea", idea)
                    category_text = d.get("category", cat_name)

                    st.divider()
                    st.markdown(f"""
                    <div style="background:#1e293b;border-radius:12px;padding:2rem 1.5rem;margin:1rem 0;max-width:100%;overflow:hidden;">
                        <div style="font-size:0.65rem;color:#64748b;text-transform:uppercase;letter-spacing:0.15em;margin-bottom:0.5rem;">Your Idea</div>
                        <div style="font-size:1rem;color:#e2e8f0;word-wrap:break-word;overflow-wrap:break-word;line-height:1.4;">{idea_text}</div>
                        <div style="font-size:0.75rem;color:#64748b;margin-top:0.25rem;margin-bottom:1.5rem;">Category: {category_text}</div>
                        <div style="font-size:0.65rem;color:#64748b;text-transform:uppercase;letter-spacing:0.15em;margin-bottom:0.5rem;">Optimized Title</div>
                        <div style="font-size:1.4rem;font-weight:700;color:#f1f5f9;word-wrap:break-word;overflow-wrap:break-word;line-height:1.3;">&ldquo;{title}&rdquo;</div>
                        <div style="font-size:2.5rem;font-weight:800;color:#22c55e;margin-top:0.75rem;line-height:1;">{score}<span style="font-size:0.9rem;color:#94a3b8;font-weight:400;"> / 100</span></div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Try n8n for AI analysis (best-effort)
                    try:
                        r2 = requests.post(N8N_URL, json={"idea": idea.strip(), "category_id": CAT_ID[cat_name]}, timeout=60)
                        if r2.ok:
                            n8n_d = r2.json()
                            analysis = n8n_d.get("ai_analysis", n8n_d.get("output", ""))
                            if analysis:
                                with st.expander("💡 AI's reasoning"):
                                    st.write(analysis)
                    except:
                        pass  # n8n is optional, skip if unavailable

                    if score >= 75:
                        st.success("Strong title. Worth publishing.")
                    elif score >= 50:
                        st.info("Good. Try more details in your idea for better results.")
                    else:
                        st.warning("Needs work. Describe your idea more specifically.")
                else:
                    st.warning(f"Render API error ({resp.status_code})")
            except requests.Timeout:
                st.warning("Timed out — n8n may be stuck.")
            except requests.RequestException:
                st.warning("Can't reach n8n. Check connection.")

    elif not go:
        st.divider()
        st.markdown("""
        <div style="text-align:center;padding:3rem 0;color:#555;">
            <div style="font-size:4rem;margin-bottom:1rem;">💡</div>
            Describe your video idea. AI generates titles, scores them, and improves until it finds the best one.
        </div>
        """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# PAGE 2 — Behind the Scenes
# ═══════════════════════════════════════════════════════════
else:
    st.markdown("""
    <div style="text-align:center;padding:3rem 0 1.5rem 0;">
        <h1 style="font-size:2.5rem;margin-bottom:0.5rem;">How AI Decides</h1>
        <p style="font-size:1.05rem;color:#999;">Every round, every title, every score. Transparent.</p>
    </div>
    """, unsafe_allow_html=True)

    idea2 = st.text_area("Video idea", placeholder="e.g. a video essay about why Minecraft is still popular...", height=80)
    c1, c2 = st.columns([2, 1])
    with c1:
        cat2 = st.selectbox("Category", list(CATS.values()), key="c2", index=list(CATS.values()).index("Entertainment"))
    with c2:
        st.write("")
        go2 = st.button("Run & Watch", type="primary", use_container_width=True, disabled=not idea2.strip())

    if go2 and idea2.strip():
        with st.spinner("Running optimization..."):
            try:
                # Call Render API directly for structured data (rounds, scores)
                resp = requests.post(RENDER_URL, json={"idea": idea2.strip(), "category_id": CAT_ID[cat2]}, timeout=180)
                if resp.ok:
                    d = resp.json()
                    rounds = d.get("rounds", [])
                    best_title = d.get("best_title", "?")
                    best_score = d.get("best_score", 0)

                    # ── SUMMARY CARD ──
                    if rounds:
                        st.divider()
                        idea_text = d.get("idea", idea2)
                        category_text = d.get("category", cat2)
                        st.markdown(f"""
                        <div style="background:#1e293b;border-radius:12px;padding:2rem 1.5rem;margin:1rem 0;max-width:100%;overflow:hidden;">
                            <div style="font-size:0.65rem;color:#64748b;text-transform:uppercase;letter-spacing:0.15em;margin-bottom:0.5rem;">Video Idea</div>
                            <div style="font-size:1rem;color:#e2e8f0;word-wrap:break-word;overflow-wrap:break-word;line-height:1.4;">{idea_text}</div>
                            <div style="font-size:0.75rem;color:#64748b;margin-top:0.25rem;margin-bottom:1.5rem;">Category: {category_text}</div>
                            <div style="font-size:0.65rem;color:#64748b;text-transform:uppercase;letter-spacing:0.15em;margin-bottom:0.5rem;">Best Title</div>
                            <div style="font-size:1.4rem;font-weight:700;color:#f1f5f9;word-wrap:break-word;overflow-wrap:break-word;line-height:1.3;">&ldquo;{best_title}&rdquo;</div>
                            <div style="font-size:2.5rem;font-weight:800;color:#22c55e;margin-top:0.75rem;line-height:1;">{best_score}<span style="font-size:0.9rem;color:#94a3b8;font-weight:400;"> / 100</span></div>
                        </div>
                        """, unsafe_allow_html=True)

                        for rd in rounds:
                            rn = rd.get("round", "?")
                            desc = rd.get("description", "")
                            candidates = rd.get("candidates", [])

                            st.markdown(f"### Round {rn}")
                            st.caption(desc)

                            for c in candidates:
                                t = c.get("title", "")
                                s = c.get("score", 0)
                                dec = c.get("decision", "")
                                helps = c.get("helps", [])
                                hurts = c.get("hurts", [])

                                if s >= 80:
                                    badge = f":green[{s}/100]"
                                elif s >= 65:
                                    badge = f":orange[{s}/100]"
                                else:
                                    badge = f":red[{s}/100]"

                                with st.expander(f"{badge}  |  {dec}  |  {t}"):
                                    ch1, ch2 = st.columns(2)
                                    with ch1:
                                        st.caption("**Helps** :arrow_up:")
                                        for h in helps:
                                            effect = h['effect']
                                            bar = "█" * max(1, int(abs(effect) * 80))
                                            st.caption(f"`{h['feature']}` {bar} {effect:+.4f}")
                                    with ch2:
                                        st.caption("**Hurts** :arrow_down:")
                                        for h in hurts:
                                            effect = h['effect']
                                            bar = "█" * max(1, int(abs(effect) * 80))
                                            st.caption(f"`{h['feature']}` {bar} {effect:+.4f}")
                            st.divider()

                        # ── AI ANALYSIS from n8n (best-effort) ──
                        try:
                            r2 = requests.post(N8N_URL, json={"idea": idea2.strip(), "category_id": CAT_ID[cat2]}, timeout=60)
                            if r2.ok:
                                n8n_d = r2.json()
                                analysis = n8n_d.get("ai_analysis", n8n_d.get("output", ""))
                                if analysis:
                                    st.markdown("### :robot_face: AI Analysis")
                                    st.info(analysis)
                        except:
                            st.caption("(AI analysis unavailable — n8n may be offline)")

                    elif d:
                        st.json(d)
                else:
                    st.warning(f"Render API error ({resp.status_code})")
            except requests.Timeout:
                st.warning("Timed out.")
            except requests.RequestException:
                st.warning("Can't reach n8n.")

    elif not go2:
        st.divider()
        st.markdown("""
        <div style="text-align:center;padding:2rem 0;color:#555;">
            <div style="font-size:3rem;margin-bottom:1rem;"></div>
            Enter a video idea and click <strong>Run & Watch</strong>. You'll see every round of optimization.
        </div>
        """, unsafe_allow_html=True)

st.divider()
st.caption("Render /optimize → n8n orchestrator → Gemini AI reasoning → Google Sheets logging")
