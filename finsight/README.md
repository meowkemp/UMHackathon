# FinSight AI — Smart Purchase Advisor

An AI-powered financial decision assistant built for UMHackathon 2026, designed to help users make smarter purchase decisions through simulation, benchmarking, and explainable AI.

## 🎥 Demo Video
```
https://youtu.be/O9APzIVNmJs
```
# Project Overview
FinSight AI enables users to:
💰 Evaluate whether they should BUY, DELAY, or RECONSIDER a purchase
📊 Simulate financial impact over time
🤖 Receive AI-generated explanations using ILMU GLM
📸 Scan receipts and auto-extract prices using OCR

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
# OCR Setup (REQUIRED for Receipt Scanner)

FinSight uses Tesseract OCR for extracting text from receipts.

### Step 1: Install Tesseract
Download from:
```
https://github.com/UB-Mannheim/tesseract/wiki
```

### Step 2: Find Installation Path
Example:
```
C:\Program Files\Tesseract-OCR\tesseract.exe
```

### Step 3: Configure in Code
Open:
```
app.py
```
Go to line 30 and update:
```
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
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

## Team
Fantastic 5 (Team ID: 27)

## Team Members
1. Bibianne Zheyee Joseph
2. Hang Xiu Jun
3. Kishanea A/P Jeyakumar
4. Liew Jia Xin
5. Ng Guan Yik
