# YouTube Title Grader

Pre-upload YouTube title screening tool. Paste a title, get an XGBoost engagement score, see which words help or hurt, and get AI-generated alternatives scored by the model.

## How it works

- **Model**: XGBoost classifier trained on 47,591 GB YouTube trending videos
- **Input**: Title, category, optional tags/description/publish time
- **Output**: Engagement score (0-100), helps/hurts breakdown, AI-generated alternatives
- **AI**: Gemini 3.1 Flash Lite generates alternative titles, model scores them

## Architecture

```
Streamlit (frontend) → FastAPI (backend) → XGBoost model
                             ↓
                        Gemini API (title suggestions)
```

## Quick start

```bash
# Backend
pip install -r requirements_api.txt
uvicorn app:app --port 8000

# Frontend (separate terminal)
pip install -r requirements_streamlit.txt
streamlit run streamlit_app.py
```

For AI-powered title suggestions, set `GEMINI_API_KEY` environment variable.

## Deploy

Configured for Render. Push to GitHub, connect Render to the repo.

## Files

| File | Purpose |
|------|---------|
| `app.py` | FastAPI backend |
| `streamlit_app.py` | Streamlit frontend |
| `youtube_model.joblib` | Trained XGBoost model |
| `Project/SWE2304438_Project.ipynb` | Model training notebook |
| `Dockerfile` / `render.yaml` | Deployment config |
