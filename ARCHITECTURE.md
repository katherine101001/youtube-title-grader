# Architecture Diagram — YouTube Title Optimizer (Agentic AI)

## Mermaid (render at mermaid.live or in VS Code)

```mermaid
flowchart TB
    subgraph TRIGGER["🔔 TRIGGER LAYER"]
        UI["Streamlit Frontend\n(User enters video idea + category)"]
    end

    subgraph INGESTION["📥 DATA INGESTION LAYER"]
        WH["n8n Webhook\nPOST /optimize\n{idea, category_id}"]
    end

    subgraph PREDICTION["🧠 PREDICTION LAYER"]
        HTTP["n8n HTTP Request\nforwards to Render API"]
        ML["Render FastAPI /optimize\n┌─────────────────────────┐\n│ Round 1: Gemini → 5 titles │\n│ XGBoost scores each (0-100)│\n│ SHAP → helps/hurts features│\n│ Round 2: Gemini improves   │\n│ XGBoost re-scores           │\n│ Output: best_title, score,  │\n│   rounds[candidates,helps,  │\n│   hurts, decisions]         │\n└─────────────────────────┘"]
    end

    subgraph AGENT["🤖 AI AGENT LAYER"]
        AI["n8n LangChain Agent (Gemini)\n┌─────────────────────────┐\n│ Reads: best_title, score,  │\n│   rounds, helps/hurts      │\n│ Reasons:                    │\n│ 1. Why winner scored best  │\n│ 2. Patterns across rounds  │\n│ 3. Actionable creator tip  │\n│ Output: natural-language   │\n│   analysis (ai_analysis)   │\n└─────────────────────────┘"]
    end

    subgraph ACTION["📤 ACTION / OUTPUT LAYER"]
        RES["Respond to Webhook\nJSON {idea, best_title,\n  best_score, rounds,\n  ai_analysis}"]
        SHEET["Google Sheets\nAppend row: timestamp,\n  idea, best_title, score,\n  rounds, ai_analysis"]
        FRONT["Streamlit UI\nPage 1: End-user view\n  (title + score)\nPage 2: Developer view\n  (rounds + helps/hurts\n   + AI analysis)"]
    end

    UI -->|"POST JSON"| WH
    WH -->|"forward"| HTTP
    HTTP -->|"POST /optimize"| ML
    ML -->|"{rounds, scores, helps/hurts}"| AI
    AI -->|"analysis text"| RES
    AI -->|"log data"| SHEET
    RES -->|"JSON response"| FRONT
```

## Data Flow Summary

```
USER (Streamlit)
  │  idea: "how to cook steak", category_id: 24
  ▼
🔔 TRIGGER LAYER
  │  n8n Webhook POST /optimize
  ▼
📥 DATA INGESTION LAYER
  │  Validate & forward {idea, category_id}
  ▼
🧠 PREDICTION LAYER
  │  Render /optimize
  │  ├─ Round 1: Gemini → 5 titles → XGBoost scores each
  │  │   └─ SHAP feature contributions → helps[] / hurts[]
  │  └─ Round 2: Gemini improves top 2 → XGBoost re-scores
  │  Output: best_title, best_score (0-100), rounds[]
  ▼
🤖 AI AGENT LAYER
  │  n8n LangChain Agent (Gemini)
  │  Reads: rounds, scores, helps/hurts
  │  Reasons: why winner won, patterns, tips
  │  Output: ai_analysis (natural language)
  ▼
📤 ACTION / OUTPUT LAYER
  ├─ Respond to Webhook → JSON → Streamlit (2-page UI)
  └─ Google Sheets → append row (audit log)
```

## Layer Breakdown

| Layer | Component | Technology | Role |
|-------|-----------|------------|------|
| 🔔 Trigger | Streamlit + n8n Webhook | Python, n8n | User submits idea → workflow starts |
| 📥 Ingestion | n8n HTTP Request | n8n | Validates & forwards to prediction API |
| 🧠 Prediction | Render FastAPI /optimize | FastAPI, XGBoost, Gemini | 2-round iterative title generation + ML scoring + SHAP explainability |
| 🤖 AI Agent | n8n LangChain Agent | LangChain, Gemini | Autonomous reasoning over prediction results |
| 📤 Action/Output | Respond to Webhook + Google Sheets | n8n | Structured JSON response + persistent audit log |
