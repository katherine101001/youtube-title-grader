"""
YouTube Pre-Upload Engagement Advisor — FastAPI (the deployed product)
Deploy: Render / Railway / Koyeb (free tier, HTTPS)

Serves `youtube_model.joblib` (pipeline version `yt-deep-1.0`), the YouTube
deep-dive model from SWE2304438_Project.ipynb. It predicts a *draft's*
engagement tier (low / med / high) BEFORE upload, from content the creator
controls — title + tags, structural copywriting features, planned publish
timing, and the video category. ZERO post-publication metrics are used as
inputs (no views/likes/comments): it judges "what you are about to post".

The model is confidence-gated: it only "fires" a high-confidence PROMOTE
signal when P(high) >= tau (0.70). At that threshold the HIGH-tier precision
is high while coverage is deliberately low — the system speaks only when sure.

Design notes (all validated in the notebook):
- Tuned XGBoost (multi:softprob, 3 tiers). Features = TF-IDF(title+tags) +
  17 structural features (10 generic copywriting + 7 YouTube-specific:
  hour/dow/weekend/tag_count/no_comments/no_ratings/desc_len) + categoryId one-hot.
- Tier edges and all transformers were fit on TRAIN rows only (no leakage).
- `helps` / `hurts` are exact signed XGBoost `pred_contribs` for the predicted
  class (SHAP-free): the content features that pushed the tier UP vs DOWN.
"""
from typing import Optional, List, Dict
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import joblib, numpy as np, xgboost as xgb, os, re, requests
import pandas as pd
from scipy.sparse import hstack

MODEL_PATH = os.environ.get("MODEL_PATH", "youtube_model.joblib")
A = joblib.load(MODEL_PATH)
model      = A["model"]
tfidf      = A["tfidf"]
scaler     = A["scaler"]
ohe        = A["ohe"]
NUM_COLS   = A["numeric_cols"] if "numeric_cols" in A else A["num_cols"]  
CLASSES    = A["classes"]                 # ['low', 'med', 'high']
FEATNAMES  = A["feature_names"]           
TIER_EDGES = A.get("tier_edges", [])      # train-only quantile edges (reference)
TAU        = float(A.get("tau", 0.70))    # confidence gate on P(high)
VERSION    = A.get("version", "yt-deep-1.0")

YT_CAT = {1: "Film & Animation", 2: "Autos & Vehicles", 10: "Music", 15: "Pets & Animals",
          17: "Sports", 19: "Travel & Events", 20: "Gaming", 22: "People & Blogs", 23: "Comedy",
          24: "Entertainment", 25: "News & Politics", 26: "Howto & Style", 27: "Education",
          28: "Science & Tech", 29: "Nonprofits"}

app = FastAPI(title="YouTube Pre-Upload Engagement Advisor", version=VERSION)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Draft(BaseModel):
    title: str = Field(..., description="Planned video title")
    tags: str = Field("", description="YouTube-style pipe-separated tags, e.g. 'football|highlights|arsenal'")
    category_id: int = Field(24, description="YouTube categoryId (e.g. 10=Music, 20=Gaming, 24=Entertainment, 27=Education)")
    description: str = Field("", description="Planned video description")
    published_at: Optional[str] = Field(None, description="Planned publish time, ISO 8601 UTC. If omitted, 'now' is used.")
    comments_disabled: bool = Field(False, description="Will comments be disabled?")
    ratings_disabled: bool = Field(False, description="Will likes/ratings be disabled?")


class Result(BaseModel):
    prediction: str                  # low / med / high
    probabilities: Dict[str, float]
    p_high: float                   
    gate_fires: bool                 # True iff p_high >= tau 
    decision: str                    # PROMOTE / PROMISING / REVISE / REWORK
    recommended_action: str          
    helps: List[Dict]                # content features pushing the tier UP
    hurts: List[Dict]                # content features pushing the tier DOWN
    category: str
    tau: float
    model_version: str


def numeric_features(draft: Draft, text: str) -> List[float]:
    """Reproduce the notebook's 17 structural features in the exact NUM_COLS order."""
    t = text or ""
    # --- 10 generic copywriting features (GEN) ---
    gen = [
        len(t),                                          # len
        len(t.split()),                                  # words
        len(re.findall(r"[A-Z]", t)) / (len(t) + 1),     # caps ratio
        int(bool(re.search(r"\d", t))),                  # has_num
        int("?" in t),                                   # has_q
        int("!" in t),                                   # has_excl
        len(re.findall(r"[\U0001F000-\U0001FFFF]", t)),  # emoji count
        t.count("#"),                                    # hashtags
        t.count("@"),                                    # mentions
        int("http" in t),                                # has_url
    ]
    # --- publish timing (UTC) ---
    pub = pd.to_datetime(draft.published_at, utc=True, errors="coerce") if draft.published_at \
        else pd.Timestamp.now(tz="UTC")
    if pd.isna(pub):
        pub = pd.Timestamp.now(tz="UTC")
    hour = int(pub.hour)
    dow = int(pub.dayofweek)
    weekend = int(dow >= 5)
    # --- tag_count: count '|' in RAW tags +1, but 0 for empty/placeholder ---
    raw_tags = (draft.tags or "").strip()
    tag_count = 0 if raw_tags in ("", "[None]", "nan") else raw_tags.count("|") + 1
    # --- 7 YouTube-specific features (YT) ---
    yt = [
        hour, dow, weekend, tag_count,
        int(draft.comments_disabled),
        int(draft.ratings_disabled),
        len(draft.description or ""),                    # desc_len
    ]
    return gen + yt


def build_text(draft: Draft) -> str:
    """text = title + ' ' + tags_clean  (tags_clean = '|'->' ', drop [None])."""
    tags_clean = (draft.tags or "").replace("[None]", "").replace("|", " ")
    return f"{draft.title} {tags_clean}".strip()


def build_X(draft: Draft, text: str):
    """Stack [TF-IDF(text), scaled structural, categoryId one-hot] in training order."""
    return hstack([
        tfidf.transform([text]),
        scaler.transform([numeric_features(draft, text)]),
        ohe.transform(pd.DataFrame({"categoryId": [str(draft.category_id)]})),
    ]).tocsr()


def pretty_feature(name: str, active: bool) -> str:
    """Make a feature name human-readable for the advice payload.

    For one-hot categories, `active` distinguishes "this video IS category X"
    (value != 0) from the counterfactual "this video is NOT category X"
    (value == 0) — a 'not-' contribution is still meaningful in TreeSHAP.
    """
    if name.startswith("cat_"):
        try:
            label = "category:" + YT_CAT.get(int(name[4:]), name[4:])
        except ValueError:
            label = name
        return label if active else "not-" + label
    return name


def top_drivers(X, pred_num: int, k: int = 6):
    """Exact signed XGBoost contributions for the predicted class (helps vs hurts)."""
    raw = model.get_booster().predict(xgb.DMatrix(X), pred_contribs=True)
    if raw.ndim == 2:                                    # (n, n_class*(n_feat+1))
        raw = raw.reshape(raw.shape[0], len(CLASSES), -1)
    contribs = raw[0][pred_num][:-1]                     # drop the bias term
    order = np.argsort(contribs)[::-1]
    helps, hurts = [], []
    for idx in order:
        name = pretty_feature(FEATNAMES[idx], X[0, idx] != 0) if idx < len(FEATNAMES) else f"f{idx}"
        val = float(contribs[idx])
        if val > 1e-4 and len(helps) < k:
            helps.append({"feature": name, "effect": round(val, 4)})
        elif val < -1e-4 and len(hurts) < k:
            hurts.append({"feature": name, "effect": round(val, 4)})
    return helps, hurts[::-1]


def decide(pred_label: str, p_high: float):
    """Confidence-gated decision the AI agent reasons over."""
    if p_high >= TAU:
        return "PROMOTE", "High-confidence top-tier draft — worth promotion / ad spend as-is."
    if pred_label == "high":
        return "PROMISING", "Predicted high but below the confidence gate — tighten the hooks, then re-check."
    if pred_label == "med":
        return "REVISE", "Mid-tier draft — revise the title/tags using the drivers below before publishing."
    return "REWORK", "Weak draft — rework the title, tags and format using the drivers below."


@app.get("/health")
def health():
    return {"status": "ok", "model_version": VERSION}


@app.get("/categories")
def categories():
    """Return the YouTube categoryId→name mapping so frontends can build dropdowns."""
    return {"categories": [{"id": k, "name": v} for k, v in sorted(YT_CAT.items())]}


@app.get("/model_info")
def model_info():
    return {
        "version": VERSION,
        "classes": CLASSES,
        "tau": TAU,
        "tier_edges": TIER_EDGES,
        "n_structural_features": len(NUM_COLS),
        "structural_features": NUM_COLS,
        "note": "YouTube pre-upload model. Content + timing + category only; no post-publication metrics.",
    }


@app.post("/predict", response_model=Result)
def predict(draft: Draft):
    try:
        text = build_text(draft)
        X = build_X(draft, text)
        pred_num = int(model.predict(X)[0])
        proba = model.predict_proba(X)[0]
        p_high = float(proba[CLASSES.index("high")])
        pred_label = CLASSES[pred_num]
        helps, hurts = top_drivers(X, pred_num)
        decision, action = decide(pred_label, p_high)
        return Result(
            prediction=pred_label,
            probabilities={CLASSES[i]: round(float(p), 4) for i, p in enumerate(proba)},
            p_high=round(p_high, 4),
            gate_fires=p_high >= TAU,
            decision=decision,
            recommended_action=action,
            helps=helps,
            hurts=hurts,
            category=YT_CAT.get(draft.category_id, str(draft.category_id)),
            tau=TAU,
            model_version=VERSION,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Suggest endpoint models
# ---------------------------------------------------------------------------
NUM_COLS_SET = set(NUM_COLS)  # for fast lookup: is a feature structural?
# Build high-signal keyword bank from TF-IDF vocabulary (sorted by Gini importance)
_tfidf_importance: List[Dict] = []
for _i, _name in enumerate(FEATNAMES):
    if _name in NUM_COLS_SET or _name.startswith("cat_"):
        continue
    _gini = float(model.feature_importances_[_i])
    if _gini >= 0.0005:
        _tfidf_importance.append({"word": _name, "gini": round(_gini, 4)})
_tfidf_importance.sort(key=lambda x: -x["gini"])
HIGH_SIGNAL_WORDS = [w["word"] for w in _tfidf_importance[:200]]  # top 200 words


class SuggestRequest(BaseModel):
    title: str = Field(..., description="Current draft title")
    tags: str = Field("", description="Current tags")
    category_id: int = Field(24, description="YouTube categoryId")
    description: str = Field("", description="Current description")
    published_at: Optional[str] = Field(None, description="Planned publish time")
    comments_disabled: bool = Field(False)
    ratings_disabled: bool = Field(False)
    num_candidates: int = Field(3, description="How many alternatives to generate", ge=1, le=5)


class SuggestCandidate(BaseModel):
    title: str
    score: int  # 0-100 composite score
    probabilities: Dict[str, float]
    decision: str
    improvement: int  # score gain vs original (+/-)


class SuggestResponse(BaseModel):
    original_title: str
    original_score: int
    original_decision: str
    high_signal_keywords: List[str]  # words that could boost the score
    alternatives: List[SuggestCandidate]
    generator: str  # "llm"


# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")


def _generate_with_llm(original_title: str, category_name: str, current_score: int,
                       decision: str, keywords: List[str], helps: List[Dict],
                       num: int) -> Optional[List[str]]:
    """Call Gemini to generate better title alternatives. Returns None if unavailable."""
    if not GEMINI_KEY or len(GEMINI_KEY) < 10:
        return None

    helps_str = ", ".join(h["feature"] for h in helps[:5]) if helps else "(none)"
    kw_str = ", ".join(keywords[:30])

    system_prompt = (
        "You are a YouTube title optimization expert. Your job: generate alternative video titles "
        "that would score HIGHER on an ML model trained on real YouTube trending data. "
        "The model is heavily text-driven — word choice is everything. "
        "Structural features (word count, tags, emoji) barely matter. "
        "Focus purely on compelling WORD CHOICE and phrasing.\n\n"
        "Rules:\n"
        "- Return ONLY a JSON array of strings, no other text.\n"
        "- Each title must be different from the original and from each other.\n"
        "- Keep titles realistic — they should sound like real YouTube videos.\n"
        "- Use high-signal keywords naturally. Don't keyword-stuff.\n"
        "- Length: 40-100 characters is the sweet spot."
    )

    user_message = (
        f"Original title: \"{original_title}\"\n"
        f"Category: {category_name}\n"
        f"Current score: {current_score}/100 ({decision})\n"
        f"Words that help engagement in this category: {kw_str}\n"
        f"What the model liked: {helps_str}\n\n"
        f"Generate {num} alternative titles that would score higher than {current_score}."
    )

    # Gemini API: combine system prompt + user message into a single prompt
    full_prompt = f"{system_prompt}\n\n---\n\n{user_message}"

    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
            params={"key": GEMINI_KEY},
            headers={"content-type": "application/json"},
            json={
                "contents": [{"parts": [{"text": full_prompt}]}],
                "generationConfig": {
                    "temperature": 0.9,
                    "maxOutputTokens": 500,
                },
            },
            timeout=30,
        )
        if resp.ok:
            data = resp.json()
            # Gemini response: candidates[0].content.parts[0].text
            text = ""
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    text = parts[0].get("text", "")

            if text:
                # Extract JSON array from response
                try:
                    titles = json.loads(text)
                    if isinstance(titles, list):
                        return [t for t in titles if isinstance(t, str)][:num]
                except json.JSONDecodeError:
                    match = re.search(r"\[.*?\]", text, re.DOTALL)
                    if match:
                        try:
                            titles = json.loads(match.group())
                            if isinstance(titles, list):
                                return [t for t in titles if isinstance(t, str)][:num]
                        except json.JSONDecodeError:
                            pass
    except requests.RequestException:
        pass
    return None


def _score_title(title: str, base_draft: dict) -> dict:
    """Score a single title through the model. Returns score info dict."""
    draft = Draft(
        title=title,
        tags=base_draft.get("tags", ""),
        category_id=base_draft.get("category_id", 24),
        description=base_draft.get("description", ""),
        published_at=base_draft.get("published_at"),
        comments_disabled=base_draft.get("comments_disabled", False),
        ratings_disabled=base_draft.get("ratings_disabled", False),
    )
    text = build_text(draft)
    X = build_X(draft, text)
    proba = model.predict_proba(X)[0]
    p_high = float(proba[CLASSES.index("high")])
    score = round(proba[CLASSES.index("low")] * 0 + proba[CLASSES.index("med")] * 50 + proba[CLASSES.index("high")] * 100)
    pred_label = CLASSES[int(model.predict(X)[0])]
    decision, _ = decide(pred_label, p_high)
    return {
        "title": title,
        "score": score,
        "probabilities": {CLASSES[i]: round(float(p), 4) for i, p in enumerate(proba)},
        "decision": decision,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/keywords")
def get_keywords():
    """Top TF-IDF words ranked by Gini importance — the model's 'viral vocabulary'."""
    return {
        "keywords": _tfidf_importance[:100],
        "total_in_vocabulary": len(_tfidf_importance),
        "note": "These are the words with the strongest predictive signal for engagement.",
    }


@app.post("/suggest", response_model=SuggestResponse)
def suggest(req: SuggestRequest):
    category_name = YT_CAT.get(req.category_id, str(req.category_id))

    # 1. Score the original title
    base_draft = req.model_dump()
    original = _score_title(req.title, base_draft)
    original_score = original["score"]
    original_decision = original["decision"]

    # 2. Get relevant keywords (use the global high-signal list)
    keywords = HIGH_SIGNAL_WORDS[:50]

    # 3. Get helps from the original prediction for context
    draft = Draft(
        title=req.title, tags=req.tags, category_id=req.category_id,
        description=req.description, published_at=req.published_at,
        comments_disabled=req.comments_disabled, ratings_disabled=req.ratings_disabled,
    )
    text = build_text(draft)
    X = build_X(draft, text)
    pred_num = int(model.predict(X)[0])
    helps, _ = top_drivers(X, pred_num, k=10)

    # 4. Generate alternatives via Gemini
    generator = "llm"
    candidates = _generate_with_llm(
        req.title, category_name, original_score, original_decision,
        keywords, helps, req.num_candidates,
    )
    if not candidates:
        candidates = []  # LLM unavailable, return empty

    # 5. Score each candidate
    alternatives = []
    for title in candidates:
        scored = _score_title(title, base_draft)
        alternatives.append(SuggestCandidate(
            title=scored["title"],
            score=scored["score"],
            probabilities=scored["probabilities"],
            decision=scored["decision"],
            improvement=scored["score"] - original_score,
        ))

    # Sort by score descending
    alternatives.sort(key=lambda x: -x.score)

    return SuggestResponse(
        original_title=req.title,
        original_score=original_score,
        original_decision=original_decision,
        high_signal_keywords=keywords[:20],
        alternatives=alternatives,
        generator=generator,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
