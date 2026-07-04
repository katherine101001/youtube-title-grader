# 🎬 YouTube Title Optimizer — Agentic AI Pipeline

**Pre-upload viral title prediction + AI reasoning + automated actions.**  
Built as part of SWE402 Data Mining coursework (XMUM).

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red)](https://streamlit.io/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-teal)](https://fastapi.tiangolo.com/)
[![XGBoost](https://img.shields.io/badge/XGBoost-1.7+-green)](https://xgboost.readthedocs.io/)
[![n8n](https://img.shields.io/badge/n8n-2.27-red)](https://n8n.io/)
[![Gemini](https://img.shields.io/badge/Gemini-2.0+-orange)](https://ai.google.dev/)

---

## What It Does

A content creator types a video idea → the system generates 10 title candidates across 2 optimization rounds, scores each with an XGBoost model trained on real YouTube trending data, explains *why* each title works via SHAP feature attribution, and an AI agent autonomously reasons over the results to give actionable advice.

| Page | User | Shows |
|------|------|-------|
| 🎯 End User | Creator | Best title, score /100, AI analysis |
| 🔧 How AI Decides | Developer / Analyst | Full 2-round breakdown with helps/hurts per candidate |

---

## Architecture (5-Layer Agentic AI)

```
🔔 TRIGGER        Streamlit → n8n Webhook
     ↓
📥 INGESTION      n8n HTTP Request → Render API
     ↓
🧠 PREDICTION     FastAPI /optimize: Gemini generates titles → XGBoost scores → SHAP explains
     ↓
🤖 AI AGENT       n8n LangChain Agent (Gemini): reasons over results, writes analysis
     ↓
📤 ACTION         → Respond to Webhook (JSON to Streamlit)
                  → Google Sheets (audit log)
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Streamlit (2-page UI) |
| **ML Backend** | FastAPI + XGBoost + scikit-learn |
| **Text Generation** | Google Gemini (via LangChain) |
| **Orchestration** | n8n (5-node agentic workflow) |
| **Explainability** | SHAP feature contributions (helps/hurts) |
| **Deployment** | Render (API) + Streamlit Cloud (UI) + n8n Cloud |
| **Training Data** | GB YouTube Trending (47K unique videos, 17 features) |

---

## Files

| File | Purpose |
|------|---------|
| `app.py` | FastAPI backend — `/optimize` endpoint, model inference, Gemini integration |
| `streamlit_app.py` | Streamlit frontend — 2-page UI (end-user + developer transparency view) |
| `n8n_workflow.json` | n8n 5-layer agentic AI workflow (trigger → predict → reason → act) |
| `youtube_model.joblib` | Trained XGBoost pipeline (TF-IDF + scaler + OHE + model, v1.0) |
| `Project/SWE2304438_Project.ipynb` | Colab notebook — full EDA, feature engineering, training, evaluation |
| `Dockerfile` | Container config for Render deployment |
| `render.yaml` | Render blueprints config |
| `requirements.txt` | Streamlit dependencies |
| `requirements_api.txt` | FastAPI dependencies |

---

## Quick Links

- **Live App (Streamlit):** [youtube-title-grader.streamlit.app](https://youtube-title-grader.streamlit.app/)
- **API Docs:** `https://youtube-title-grader.onrender.com/docs`
- **n8n Webhook:** `https://katherine2304.app.n8n.cloud/webhook/optimize`

---

## Model Performance

| Metric | Value |
|--------|-------|
| Macro F1 | 0.7043 |
| Baseline (stratified) | 0.339 |
| HIGH-tier precision (τ=0.70) | High precision, low coverage (speaks only when sure) |
| Features | 5,000 TF-IDF + 17 structural + 15 category OHE |

---

## How to Run Locally

```bash
# Backend
pip install -r requirements_api.txt
uvicorn app:app --port 8000

# Frontend (separate terminal)
pip install -r requirements.txt
streamlit run streamlit_app.py
```

---

*Built for SWE402 Data Mining — Agentic AI Workflow Assignment*
