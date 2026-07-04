"""
YouTube Title Optimizer — two views:
  Page 1: End user — enter idea, get best title
  Page 2: Behind the scenes — see AI's decision-making process
"""
import streamlit as st
import requests
import os

st.set_page_config(page_title="YouTube Title Optimizer", page_icon="🎬", layout="centered")
st.markdown("""<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
.stButton > button { font-size: 1.1rem !important; padding: 0.8rem 2rem !important; }
</style>""", unsafe_allow_html=True)

API_BASE = os.environ.get("API_URL", "https://youtube-title-grader.onrender.com")
N8N_URL  = os.environ.get("N8N_WEBHOOK", "https://katherine2304.app.n8n.cloud/webhook/optimize")

CATS = {1:"Film & Animation",2:"Autos & Vehicles",10:"Music",15:"Pets & Animals",17:"Sports",
        19:"Travel & Events",20:"Gaming",22:"People & Blogs",23:"Comedy",24:"Entertainment",
        25:"News & Politics",26:"Howto & Style",27:"Education",28:"Science & Tech",29:"Nonprofits"}
CAT_ID = {v:k for k,v in CATS.items()}

# ── Page selector ──
page = st.sidebar.radio("View", ["🎯 End User", "🔧 How AI Decides"], label_visibility="collapsed")

# ══════════════════════════════════════════════════════════════════════
# PAGE 1 — End user
# ══════════════════════════════════════════════════════════════════════
if page == "🎯 End User":
    st.markdown("""
    <div style="text-align:center;padding:3rem 0 2rem 0;">
        <h1 style="font-size:3rem;margin-bottom:0.5rem;">🎬 Title Optimizer</h1>
        <p style="font-size:1.1rem;color:#999;">Tell me your video idea. AI turns it into a high-scoring title.</p>
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
        optimize = st.button("🚀 Optimize", type="primary", use_container_width=True, disabled=not idea.strip())

    if optimize and idea.strip():
        with st.spinner("AI generating and optimizing..."):
            try:
                resp = requests.post(N8N_URL, json={"idea": idea.strip(), "category_id": CAT_ID[cat_name]}, timeout=300)
                if resp.ok:
                    data = resp.json()
                    best = data.get("best") or {}
                    best_title = best.get("title", data.get("best_title", "?"))
                    best_score = best.get("score", data.get("best_score", 0))

                    st.divider()
                    st.markdown(f"""
                    <div style="text-align:center;padding:1rem 0;">
                        <div style="font-size:0.85rem;color:#888;margin-bottom:0.5rem;">🏆 YOUR OPTIMIZED TITLE</div>
                        <div style="font-size:1.8rem;font-weight:800;line-height:1.3;">"{best_title}"</div>
                        <div style="font-size:2.5rem;font-weight:800;color:#22c55e;margin-top:0.5rem;">{best_score}<span style="font-size:1rem;color:#888;">/100</span></div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Publish tip
                    if best_score >= 75:
                        st.success("Strong title — worth publishing as-is.")
                    elif best_score >= 50:
                        st.info("Good, but could be better. Try again with more detail in your idea.")
                    else:
                        st.warning("Needs work. Try describing your video idea more specifically.")
                else:
                    st.warning(f"n8n error ({resp.status_code}). Is the workflow activated?")
            except requests.Timeout:
                st.warning("Timed out — n8n may be stuck. Check the workflow.")
            except requests.RequestException:
                st.warning("Can't reach n8n. Is the workflow activated?")

    elif not optimize:
        st.divider()
        st.markdown("""
        <div style="text-align:center;padding:3rem 0;color:#555;">
            <div style="font-size:4rem;margin-bottom:1rem;">💡</div>
            Describe your video idea above. AI will generate titles, score each, and keep improving.
        </div>
        """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# PAGE 2 — Behind the scenes
# ══════════════════════════════════════════════════════════════════════
else:
    st.markdown("""
    <div style="text-align:center;padding:3rem 0 1.5rem 0;">
        <h1 style="font-size:2.5rem;margin-bottom:0.5rem;">🔧 How AI Decides</h1>
        <p style="font-size:1.05rem;color:#999;">See what happens behind the scenes — every round, every score.</p>
    </div>
    """, unsafe_allow_html=True)

    idea2 = st.text_area(
        "Video idea",
        placeholder="e.g. a video essay about why Minecraft is still popular after 15 years...",
        height=80,
    )
    col1b, col2b = st.columns([2, 1])
    with col1b:
        cat_name2 = st.selectbox("Category", list(CATS.values()), key="cat2",
                                 index=list(CATS.values()).index("Entertainment"))
    with col2b:
        st.write("")
        run = st.button("🔬 Run & Watch", type="primary", use_container_width=True, disabled=not idea2.strip())

    if run and idea2.strip():
        with st.spinner("Running optimization... this may take 30-60 seconds."):
            try:
                resp = requests.post(N8N_URL, json={"idea": idea2.strip(), "category_id": CAT_ID[cat_name2]}, timeout=300)
                if resp.ok:
                    data = resp.json()
                    rounds = data.get("all_rounds") or data.get("allRounds") or []
                    best = data.get("best") or {}
                    best_title = best.get("title", data.get("best_title", "?"))
                    best_score = best.get("score", data.get("best_score", 0))

                    if rounds:
                        st.divider()
                        st.markdown(f"### 🏆 Winner: \"{best_title}\" — {best_score}/100")
                        st.divider()

                        for i, r in enumerate(rounds):
                            parts = r.split(" → ")
                            title_part = parts[0] if len(parts) > 0 else r
                            score_part = parts[1] if len(parts) > 1 else "?"

                            col_a, col_b = st.columns([4, 1])
                            with col_a:
                                st.markdown(f"**Round {i+1}**: {title_part}")
                            with col_b:
                                try:
                                    s = int(score_part)
                                    c = "#22c55e" if s >= 75 else ("#f59e0b" if s >= 50 else "#ef4444")
                                    st.markdown(f"<span style='font-size:1.3rem;font-weight:800;color:{c};'>{s}</span>", unsafe_allow_html=True)
                                except ValueError:
                                    st.caption(score_part)
                        st.divider()

                        # Summary
                        scores_only = []
                        for r in rounds:
                            parts = r.split(" → ")
                            try:
                                scores_only.append(int(parts[1]) if len(parts) > 1 else 0)
                            except ValueError:
                                pass
                        if len(scores_only) >= 2:
                            first_score = scores_only[0]
                            last_score = scores_only[-1]
                            improvement = last_score - first_score
                            st.markdown(f"""
                            <div style="background:#1a1a1a;border:1px solid #333;border-radius:10px;padding:1rem;text-align:center;">
                                Started at <strong>{first_score}</strong> → ended at <strong>{last_score}</strong>
                                &nbsp;·&nbsp;
                                <span style="color:{'#22c55e' if improvement > 0 else '#ef4444'};">
                                    {'+' if improvement > 0 else ''}{improvement} points
                                </span>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.json(data)
                else:
                    st.warning(f"n8n error ({resp.status_code})")
            except requests.Timeout:
                st.warning("Timed out. n8n may be stuck.")
            except requests.RequestException:
                st.warning("Can't reach n8n.")

    elif not run:
        st.divider()
        st.markdown("""
        <div style="text-align:center;padding:2rem 0;color:#555;">
            <div style="font-size:3rem;margin-bottom:1rem;">🔍</div>
            Enter a video idea and click <strong>Run & Watch</strong>.<br>
            You'll see every round of AI optimization — what titles were generated, how they scored, and which one won.
        </div>
        """, unsafe_allow_html=True)

# ── Footer ──
st.divider()
st.caption("Powered by Gemini · Model scored on 47k YouTube trending videos · Right 89% on top picks")
