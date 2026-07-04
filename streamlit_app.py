"""
YouTube Title Optimizer — Assignment Architecture
  Page 1: End user — idea → best title
  Page 2: Behind the scenes — full AI decision process

Backend: Render /optimize (iterative Gemini + model scoring)
n8n: orchestrates trigger → predict → AI reason → Google Sheets → respond
"""
import streamlit as st
import requests
import os

st.set_page_config(page_title="YouTube Title Optimizer", page_icon="🎬", layout="centered")
st.markdown("""<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
.stButton > button { font-size: 1.1rem !important; padding: 0.8rem 2rem !important; }
</style>""", unsafe_allow_html=True)

N8N_URL = os.environ.get("N8N_WEBHOOK", "https://katherine2304.app.n8n.cloud/webhook/optimize")

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
                resp = requests.post(N8N_URL, json={"idea": idea.strip(), "category_id": CAT_ID[cat_name]}, timeout=300)
                if resp.ok:
                    d = resp.json()
                    title = d.get("best_title", "?")
                    score = d.get("best_score", 0)
                    analysis = d.get("ai_analysis", "")

                    st.divider()
                    st.markdown(f"""
                    <div style="text-align:center;padding:1rem 0;">
                        <div style="font-size:0.85rem;color:#888;margin-bottom:0.5rem;">YOUR OPTIMIZED TITLE</div>
                        <div style="font-size:1.8rem;font-weight:800;line-height:1.3;">"{title}"</div>
                        <div style="font-size:2.5rem;font-weight:800;color:#22c55e;margin-top:0.5rem;">{score}<span style="font-size:1rem;color:#888;">/100</span></div>
                    </div>
                    """, unsafe_allow_html=True)

                    if analysis:
                        with st.expander("💡 AI's reasoning"):
                            st.write(analysis)

                    if score >= 75:
                        st.success("Strong title. Worth publishing.")
                    elif score >= 50:
                        st.info("Good. Try more details in your idea for better results.")
                    else:
                        st.warning("Needs work. Describe your idea more specifically.")
                else:
                    st.warning(f"Error ({resp.status_code}). Is n8n activated?")
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
                resp = requests.post(N8N_URL, json={"idea": idea2.strip(), "category_id": CAT_ID[cat2]}, timeout=300)
                if resp.ok:
                    d = resp.json()
                    rounds = d.get("rounds", [])
                    best_title = d.get("best_title", "?")
                    best_score = d.get("best_score", 0)
                    analysis = d.get("ai_analysis", "")

                    if rounds:
                        st.divider()
                        st.markdown(f"### Winner: \"{best_title}\" — {best_score}/100")

                        for rd in rounds:
                            rn = rd.get("round", "?")
                            desc = rd.get("description", "")
                            st.markdown(f"#### Round {rn}: {desc}")
                            candidates = rd.get("candidates", [])
                            for c in candidates:
                                t = c.get("title", "")
                                s = c.get("score", 0)
                                color = "#22c55e" if s >= 75 else ("#f59e0b" if s >= 50 else "#ef4444")
                                helps = c.get("helps", [])
                                hurts = c.get("hurts", [])

                                with st.expander(f"{t} — {s}/100"):
                                    col_h1, col_h2 = st.columns(2)
                                    with col_h1:
                                        st.caption("Helps:")
                                        for h in helps[:3]:
                                            st.caption(f"  + {h['feature']}: {h['effect']:.4f}")
                                    with col_h2:
                                        st.caption("Hurts:")
                                        for h in hurts[:3]:
                                            st.caption(f"  - {h['feature']}: {h['effect']:.4f}")
                            st.divider()

                        if analysis:
                            st.info(f"**AI says:** {analysis}")
                    else:
                        st.json(d)
                else:
                    st.warning(f"Error ({resp.status_code})")
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
