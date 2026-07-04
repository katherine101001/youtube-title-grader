"""
YouTube Title Grader
Pre-upload screening: enter a title, get a score, see what helps/hurts, try alternatives.
"""

import streamlit as st
import requests
import re
from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple

st.set_page_config(page_title="YouTube Title Grader", page_icon="🎬", layout="wide",
                   initial_sidebar_state="collapsed")

API_BASE: str = st.secrets.get("API_URL", "http://localhost:8000")

YT_CATEGORIES: Dict[int, str] = {
    1: "Film & Animation", 2: "Autos & Vehicles", 10: "Music",
    15: "Pets & Animals", 17: "Sports", 19: "Travel & Events",
    20: "Gaming", 22: "People & Blogs", 23: "Comedy",
    24: "Entertainment", 25: "News & Politics", 26: "Howto & Style",
    27: "Education", 28: "Science & Tech", 29: "Nonprofits",
}
CAT_ID_BY_NAME = {v: k for k, v in YT_CATEGORIES.items()}

STRUCT_NAMES = {
    "no_comments", "no_ratings", "hour", "dow", "weekend",
    "tag_count", "desc_len", "words", "len", "caps ratio",
    "has_num", "has_q", "has_excl", "emoji count", "hashtags",
    "mentions", "has_url",
}
STRUCT_LABELS = {
    "no_comments": "comments off", "no_ratings": "ratings off",
    "tag_count": "tags", "desc_len": "description",
    "words": "word count", "len": "title length",
    "caps ratio": "CAPS usage", "has_num": "has a number",
    "has_q": "has a question", "has_excl": "has exclamation",
    "emoji count": "emoji", "hashtags": "hashtags", "mentions": "@mentions",
    "has_url": "URL in title", "hour": "publish hour",
    "dow": "day of week", "weekend": "weekend",
}

# ---------------------------------------------------------------------------
# Hide chrome
# ---------------------------------------------------------------------------
st.markdown("""<style>
#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
.stButton > button { font-size: 1.05rem !important; padding: 0.6rem 1.5rem !important; }
</style>""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def call_predict(payload: dict) -> Optional[dict]:
    try:
        r = requests.post(f"{API_BASE}/predict", json=payload, timeout=60)
        return r.json() if r.ok else None
    except requests.RequestException:
        return None

def call_suggest(payload: dict, num: int = 3) -> Optional[dict]:
    try:
        r = requests.post(f"{API_BASE}/suggest", json={**payload, "num_candidates": num}, timeout=120)
        return r.json() if r.ok else None
    except requests.RequestException:
        return None

def calc_score(probs: Dict[str, float]) -> int:
    return round(probs.get("low", 0) * 0 + probs.get("med", 0) * 50 + probs.get("high", 0) * 100)

def score_color(score: int) -> str:
    if score >= 75: return "#22c55e"
    elif score >= 50: return "#f59e0b"
    return "#ef4444"

def score_label(score: int) -> str:
    if score >= 75: return "Great"
    elif score >= 50: return "Good"
    return "Needs Work"

def label_feature(name: str) -> str:
    if name.startswith("category:"): return f"category: {name[9:]}"
    if name.startswith("not-category:"): return f"not {name[13:]}"
    return STRUCT_LABELS.get(name, name)

# ---------------------------------------------------------------------------
# Gauge
# ---------------------------------------------------------------------------
def render_gauge(score: int, color: str, label: str):
    score = max(0, min(100, score))
    angle = int(score * 1.8)
    st.markdown(f"""
    <div style="text-align:center;margin:0.5rem 0;">
        <svg width="180" height="105" viewBox="0 0 200 120" style="display:block;margin:0 auto;">
            <path d="M 30 110 A 70 70 0 0 1 170 110" fill="none" stroke="#333" stroke-width="12" stroke-linecap="round"/>
            <path d="M 30 110 A 70 70 0 0 1 170 110" fill="none" stroke="{color}" stroke-width="12" stroke-linecap="round" stroke-dasharray="{angle} 180"/>
            <line x1="100" y1="105" x2="100" y2="75" stroke="{color}" stroke-width="2" transform="rotate({angle - 90}, 100, 105)"/>
            <circle cx="100" cy="105" r="4" fill="{color}"/>
        </svg>
        <div style="font-size:2.5rem;font-weight:800;color:{color};line-height:1;">{score}</div>
        <div style="font-size:0.8rem;color:#888;">out of 100</div>
        <div style="font-size:1.1rem;font-weight:700;color:{color};margin-top:0.25rem;">{label}</div>
    </div>""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Insights
# ---------------------------------------------------------------------------
def build_insights(result: dict) -> Tuple[List[str], List[str]]:
    good: List[str] = []
    bad: List[str] = []
    helps = result.get("helps", [])
    hurts = result.get("hurts", [])
    p_high = result["p_high"]
    decision = result["decision"]
    probs = result["probabilities"]

    # Keywords that help
    strong_kw = [(it["feature"], it["effect"]) for it in helps
                 if it["feature"] not in STRUCT_NAMES
                 and not it["feature"].startswith("category:")
                 and not it["feature"].startswith("not-category:")
                 and abs(it["effect"]) >= 0.01][:4]
    if strong_kw:
        kw_list = ", ".join(f"**'{w}'**" for w, v in strong_kw)
        good.append(f"These words are boosting your score: {kw_list}.")

    # Structural signals
    struct_helps = [(label_feature(it["feature"]), it["effect"]) for it in helps
                    if it["feature"] in STRUCT_NAMES and abs(it["effect"]) >= 0.001]
    struct_hurts = [(label_feature(it["feature"]), it["effect"]) for it in hurts
                    if it["feature"] in STRUCT_NAMES and abs(it["effect"]) >= 0.001]
    if struct_helps:
        top = struct_helps[0]
        good.append(f"**{top[0]}** is working in your favor.")
    if struct_hurts:
        top = struct_hurts[0]
        bad.append(f"**{top[0]}** is dragging your score down.")

    # Category fit
    helped_cats = [it["feature"].replace("category:", "") for it in helps
                   if it["feature"].startswith("category:")]
    if helped_cats:
        good.append(f"**{helped_cats[0]}** is a good category for this title.")

    # Decision
    if decision == "PROMOTE":
        good.append("Strong pick — the model is right 89% of the time when it gives this rating.")
    elif decision == "PROMISING":
        good.append("Almost a top score — a small wording change could push it higher.")

    if probs["med"] > 0.25 and probs["high"] < 0.5:
        bad.append("Scores in this middle range are harder to judge. Small changes can tip the balance either way.")

    return good, bad

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown("""
<div style="text-align:center;padding:2rem 0 1rem 0;">
    <h1 style="font-size:2.5rem;margin-bottom:0.25rem;">🎬 YouTube Title Grader</h1>
    <p style="font-size:1.05rem;color:#999;">
        Enter a title. Get an instant score. Improve it before you publish.
    </p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# ZONE 1 — Input
# ---------------------------------------------------------------------------
title = st.text_input(
    "Your video title",
    placeholder="e.g. I Built a Gaming PC That Runs on Tears",
    key="title_input",
)

col_cat, col_btn = st.columns([3, 1])
with col_cat:
    category_name = st.selectbox(
        "Category",
        options=list(YT_CATEGORIES.values()),
        index=list(YT_CATEGORIES.values()).index("Entertainment"),
    )
    category_id = CAT_ID_BY_NAME[category_name]
with col_btn:
    st.write("")
    grade_clicked = st.button("🔮 Grade", type="primary", use_container_width=True,
                              disabled=not title.strip())

# Advanced
with st.expander("⚙️ More options (optional)"):
    a1, a2 = st.columns(2)
    with a1:
        tags = st.text_input("Tags (separate with | )", placeholder="e.g. tech | pc build | gaming")
    with a2:
        description = st.text_area("Description", placeholder="Your planned description...", height=90)
    t1, t2 = st.columns(2)
    with t1:
        publish_date = st.date_input("Publish date", value=datetime.now().date())
    with t2:
        publish_time = st.time_input("Publish time", value=datetime.now().time())
    published_at = datetime.combine(publish_date, publish_time).replace(tzinfo=timezone.utc).isoformat()
    st.info("💡 Make sure **comments and likes are turned on** — the model sees these as strong positives.")

tags_val = tags.strip() if 'tags' in dir() and tags else ""
desc_val = description.strip() if 'description' in dir() and description else ""
pub_at = published_at if 'published_at' in dir() else datetime.now(timezone.utc).isoformat()

# ---------------------------------------------------------------------------
# ZONE 2 — Results
# ---------------------------------------------------------------------------
if grade_clicked and title.strip():
    with st.spinner("Scoring your title..."):
        result = call_predict({
            "title": title.strip(),
            "tags": tags_val,
            "category_id": category_id,
            "description": desc_val,
            "published_at": pub_at,
            "comments_disabled": False,
            "ratings_disabled": False,
        })

    if result is None:
        st.error("Can't reach the backend. Make sure it's running.")
        st.stop()

    score = calc_score(result["probabilities"])
    color = score_color(score)
    label = score_label(score)
    probs = result["probabilities"]
    good, bad = build_insights(result)

    # Remember for Zone 3
    st.session_state["last_payload"] = {
        "title": title.strip(), "tags": tags_val, "category_id": category_id,
        "description": desc_val, "published_at": pub_at,
        "comments_disabled": False, "ratings_disabled": False,
    }

    st.divider()

    # Score + probs
    left, right = st.columns([1, 1.5])

    with left:
        render_gauge(score, color, label)
        st.caption("How likely your title gets high engagement")

        st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
        for tier, emoji, pct, tcolor in [
            ("high", "🔥", probs["high"], "#22c55e"),
            ("med", "👍", probs["med"], "#f59e0b"),
            ("low", "👎", probs["low"], "#ef4444"),
        ]:
            st.markdown(
                f"""<div style="display:flex;align-items:center;gap:0.5rem;margin:0.25rem 0;">
                    <span style="width:24px;">{emoji}</span>
                    <span style="width:36px;font-size:0.8rem;color:#aaa;">{tier}</span>
                    <div style="flex:1;background:#222;border-radius:4px;height:10px;">
                        <div style="width:{pct*100:.0f}%;background:{tcolor};height:10px;border-radius:4px;"></div>
                    </div>
                    <span style="width:40px;text-align:right;font-weight:700;font-size:0.85rem;color:{tcolor};">{pct:.0%}</span>
                </div>""", unsafe_allow_html=True,
            )

    with right:
        decision = result["decision"]
        d_icons = {"PROMOTE": "🚀", "PROMISING": "✨", "REVISE": "🔧", "REWORK": "🔄"}
        d_exps = {
            "PROMOTE": "Strong pick. The model is right 89% of the time when it gives this rating.",
            "PROMISING": "Almost there. A small change to your wording could push this higher.",
            "REVISE": "Decent, but could be better. Try different words or phrasing.",
            "REWORK": "Needs a rewrite. Try a completely different approach.",
        }
        st.markdown(f"""
        <div style="background:#1a1a1a;border:1px solid #333;border-radius:12px;padding:1rem 1.25rem;margin-bottom:1rem;">
            <div style="font-size:1.4rem;font-weight:800;color:{color};margin-bottom:0.5rem;">
                {d_icons.get(decision, '')} {decision}
            </div>
            <div style="color:#aaa;font-size:0.9rem;line-height:1.5;">
                {d_exps.get(decision, '')}
            </div>
        </div>
        """, unsafe_allow_html=True)

        for obs in good:
            st.markdown(f"""<div style="
                background:#22c55e08;border-left:2px solid #22c55e50;
                padding:6px 10px;margin:4px 0;border-radius:0 6px 6px 0;
                font-size:0.88rem;line-height:1.4;
            ">{obs}</div>""", unsafe_allow_html=True)

        for warn in bad:
            st.markdown(f"""<div style="
                background:#ef444408;border-left:2px solid #ef444450;
                padding:6px 10px;margin:4px 0;border-radius:0 6px 6px 0;
                font-size:0.88rem;line-height:1.4;
            ">{warn}</div>""", unsafe_allow_html=True)

    # Helps / Hurts
    st.divider()
    st.markdown("### 🔍 What helped or hurt your score")
    st.caption("Based on the model's analysis of your title.")

    h1, h2 = st.columns(2)
    with h1:
        st.markdown("#### ✅ What helped")
        helps = result.get("helps", [])
        shown = 0
        for item in helps[:6]:
            name = label_feature(item["feature"])
            effect = item["effect"]
            if abs(effect) < 0.0005: continue
            shown += 1
            st.markdown(f"""<div style="
                display:flex;justify-content:space-between;
                background:#22c55e08;border-left:2px solid #22c55e60;
                padding:6px 10px;margin:3px 0;border-radius:0 6px 6px 0;font-size:0.85rem;
            "><span>{name}</span><span style="color:#22c55e;font-weight:700;">+{effect:.4f}</span></div>""", unsafe_allow_html=True)
        if shown == 0: st.caption("(nothing stood out)")

    with h2:
        st.markdown("#### ⚠️ What hurt")
        hurts = result.get("hurts", [])
        shown = 0
        for item in hurts[:6]:
            name = label_feature(item["feature"])
            effect = item["effect"]
            if abs(effect) < 0.0005: continue
            shown += 1
            st.markdown(f"""<div style="
                display:flex;justify-content:space-between;
                background:#ef444408;border-left:2px solid #ef444460;
                padding:6px 10px;margin:3px 0;border-radius:0 6px 6px 0;font-size:0.85rem;
            "><span>{name}</span><span style="color:#ef4444;font-weight:700;">{effect:.4f}</span></div>""", unsafe_allow_html=True)
        if shown == 0: st.caption("(nothing stood out)")

    # Zone 3 — Optimize
    st.divider()
    st.markdown("### 💡 Try different wording")
    st.caption("We'll suggest a few alternatives and show how each one scores.")

    if st.button("✨ Suggest alternatives", type="secondary"):
        payload = st.session_state.get("last_payload", {})
        if not payload:
            st.warning("Grade a title first.")
        else:
            with st.spinner("Generating and scoring alternatives..."):
                suggest_data = call_suggest(payload, num=3)

            if suggest_data is None:
                st.warning("Suggest service not available. Is the backend running /suggest?")
            else:
                alts = suggest_data.get("alternatives", [])
                orig_score = suggest_data.get("original_score", score)

                # Your title
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;align-items:center;
                    background:#1a1a1a;border:1px solid #444;border-radius:10px;
                    padding:0.75rem 1rem;margin:0.5rem 0;">
                    <span style="font-size:0.85rem;color:#888;">Your title</span>
                    <span style="flex:1;margin-left:1rem;font-weight:600;">{suggest_data['original_title']}</span>
                    <span style="font-size:1.3rem;font-weight:800;color:#aaa;">{orig_score}</span>
                </div>
                """, unsafe_allow_html=True)

                for i, alt in enumerate(alts):
                    imp = alt["improvement"]
                    imp_str = f"+{imp}" if imp > 0 else str(imp)
                    imp_color = "#22c55e" if imp > 0 else ("#888" if imp == 0 else "#ef4444")
                    medal = ["🥇", "🥈", "🥉"][i] if i < 3 else ""
                    st.markdown(f"""
                    <div style="display:flex;justify-content:space-between;align-items:center;
                        background:#1a1a1a;border:1px solid #333;border-radius:10px;
                        padding:0.75rem 1rem;margin:0.5rem 0;">
                        <span style="width:32px;">{medal}</span>
                        <span style="flex:1;font-weight:600;">{alt['title']}</span>
                        <span style="font-size:1.3rem;font-weight:800;color:{color};">{alt['score']}</span>
                        <span style="font-size:0.85rem;color:{imp_color};margin-left:0.75rem;width:45px;text-align:right;">({imp_str})</span>
                    </div>
                    """, unsafe_allow_html=True)

else:
    st.divider()
    st.markdown("""
    <div style="text-align:center;padding:4rem 0;color:#555;">
        <div style="font-size:5rem;margin-bottom:1rem;">🎬</div>
        <div style="font-size:1.1rem;">
            Enter your title above and click <strong>Grade</strong>.
        </div>
        <div style="font-size:0.85rem;color:#666;margin-top:0.5rem;">
            You'll get a score, see what's working, and try alternatives.
        </div>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.divider()
st.caption(
    "Trained on 47,591 real YouTube trending videos. "
    "Uses only pre-publish info — no views, likes, or comments. "
    "Right 89% of the time when it gives a top rating."
)
