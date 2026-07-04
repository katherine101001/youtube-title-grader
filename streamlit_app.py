"""
YouTube Title Optimizer — enter an idea, AI does the rest.
"""
import streamlit as st
import requests
import os

st.set_page_config(page_title="YouTube Title Optimizer", page_icon="🎬", layout="centered")
st.markdown("""<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
.stButton > button { font-size: 1.1rem !important; padding: 0.8rem 2rem !important; }
</style>""", unsafe_allow_html=True)

API_BASE = os.environ.get("API_URL", "https://youtube-title-grader.onrender.com")
N8N_URL = os.environ.get("N8N_WEBHOOK", "https://katherine2304.app.n8n.cloud/webhook/optimize")

CATS = {1:"Film & Animation",2:"Autos & Vehicles",10:"Music",15:"Pets & Animals",17:"Sports",
        19:"Travel & Events",20:"Gaming",22:"People & Blogs",23:"Comedy",24:"Entertainment",
        25:"News & Politics",26:"Howto & Style",27:"Education",28:"Science & Tech",29:"Nonprofits"}
CAT_ID = {v:k for k,v in CATS.items()}

# ── Header ──
st.markdown("""
<div style="text-align:center;padding:3rem 0 2rem 0;">
    <h1 style="font-size:3rem;margin-bottom:0.5rem;">🎬 Title Optimizer</h1>
    <p style="font-size:1.1rem;color:#999;">Tell me your video idea. AI turns it into a high-scoring title.</p>
</div>
""", unsafe_allow_html=True)

# ── Input ──
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
    optimize = st.button("🚀 Optimize My Title", type="primary", use_container_width=True, disabled=not idea.strip())

# ── Results ──
if optimize and idea.strip():
    with st.spinner("AI is generating and optimizing titles..."):
        try:
            resp = requests.post(N8N_URL, json={
                "idea": idea.strip(),
                "category_id": CAT_ID[cat_name],
            }, timeout=300)

            if resp.ok:
                data = resp.json()

                # Best result
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

                # Round history
                rounds = data.get("all_rounds") or data.get("allRounds") or []
                if rounds:
                    with st.expander("📈 See how AI got there"):
                        for r in rounds:
                            st.caption(r)

            else:
                st.warning(f"n8n error ({resp.status_code}). Is the workflow activated?")
        except requests.Timeout:
            st.warning("Timed out. The AI optimization is taking too long — n8n may be stuck.")
        except requests.RequestException:
            st.warning("Can't reach n8n. Check your connection and make sure the workflow is activated.")

elif not optimize:
    st.divider()
    st.markdown("""
    <div style="text-align:center;padding:3rem 0;color:#555;">
        <div style="font-size:4rem;margin-bottom:1rem;">💡</div>
        <div style="font-size:1.1rem;">
            Describe your video idea above. Be as specific as you want.
        </div>
        <div style="font-size:0.85rem;color:#666;margin-top:0.5rem;">
            AI will generate titles, score each one, and keep improving until it finds the best.
        </div>
    </div>
    """, unsafe_allow_html=True)

st.divider()
st.caption("Powered by Gemini · Model trained on 47k YouTube trending videos · Right 89% of the time on top picks")
