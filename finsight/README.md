# FinSight AI — Smart Purchase Advisor

An AI-powered financial decision tool built for the UMHackathon.

## Project Structure

```
finsight/
├── app.py                  ← Streamlit frontend (run this)
├── requirements.txt
├── data/
│   └── cleaned_finance_data.csv   ← Peer benchmark dataset
└── core/
    ├── __init__.py
    ├── advisor.py          ← Decision logic (buy/delay/reconsider)
    ├── simulator.py        ← Savings projection math
    ├── benchmarks.py       ← Dataset peer comparisons
    └── ai_explainer.py     ← ILMU GLM API call
```

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set your API key
**Windows (PowerShell):**
```powershell
$env:ILMU_API_KEY = "your-api-key-here"
```

**Mac/Linux:**
```bash
export ILMU_API_KEY="your-api-key-here"
```

### 3. Run the app
```bash
streamlit run app.py
```

The app opens automatically at http://localhost:8501

## Features

| Tab | What it does |
|-----|-------------|
| 🛒 Purchase Advisor | Enter any item + price → get BUY / DELAY / RECONSIDER with AI explanation |
| 📈 Scenario Simulator | See how savings grow under 3 choices over 12 months |
| 📊 Peer Benchmarks | Compare your finances against real peer-group data |
| 📸 Receipt Scanner | Upload a photo → auto-extract price → instant analysis |
