"""
app.py
------
FinSight AI — Streamlit frontend.
Run with:  streamlit run app.py
"""

import base64
import sys
import os

import pytesseract
import cv2
import numpy as np
from PIL import Image
import re

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Set path (Windows)
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\Angel\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"

def generate_local_insights(income, expenses, savings, price, score, risk):
    surplus = income - expenses
    remaining = savings - price

    summary = ""
    explanation = ""
    alternatives = ""
    action = ""

    # Summary
    if surplus > 0 and remaining > 1000:
        summary = "You are financially stable for this purchase."
    elif remaining < 500:
        summary = "This purchase may reduce your financial safety."
    else:
        summary = "This purchase is manageable but requires caution."

    # Explanation
    explanation = f"After buying, you will have RM {remaining:,.2f} left. Your monthly surplus is RM {surplus:,.2f}."

    # Alternatives
    if price > surplus:
        alternatives = "Consider delaying or finding a cheaper alternative."
    else:
        alternatives = "You could proceed, but compare prices before buying."

    # Action
    if risk == "HIGH":
        action = "Avoid this purchase for now."
    elif risk == "MEDIUM":
        action = "Wait 1–2 months before buying."
    else:
        action = "Safe to proceed."

    return {
        "summary": summary,
        "explanation": explanation,
        "alternatives": alternatives,
        "action": action
    }

# Make sure core/ is importable
sys.path.insert(0, os.path.dirname(__file__))
from core.advisor      import make_decision
from core.ai_explainer import get_ai_explanation, scan_receipt_image
from core.benchmarks   import get_peer_benchmarks, get_expense_percentile, get_savings_percentile
from core.simulator    import get_scenarios
from core.scoring      import calculate_score, classify_risk, validate_inputs, validate_ai_output, get_score_label

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FinSight AI",
    layout="wide",
    page_icon="💡"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;800&display=swap');

/* ===== GLOBAL ===== */
html, body, [class*="css"] {
    font-family: Open Sans
}

/* ===== GLOBAL FONT ===== */
html, body, [class*="css"] {
    font-family: 'Poppins', sans-serif;
    font-weight: 400;
}


/* ===== BACKGROUND ===== */
.stApp {
    background: linear-gradient(
        135deg,
        #dbeafe 0%,
        #c7d2fe 25%,
        #a5b4fc 60%,
        #eef2ff 100%
    );
}

/* Subtle texture */
.stApp::before {
    content: "";
    position: fixed;
    inset: 0;
    background-image: radial-gradient(rgba(99,102,241,0.05) 1px, transparent 1px);
    background-size: 24px 24px;
    pointer-events: none;
}

/* ===== HEADERS ===== */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Poppins', sans-serif;
    font-weight: 900;
    letter-spacing: -0.02em;
}

/* Streamlit titles */
div[data-testid="stMarkdownContainer"] h1,
div[data-testid="stMarkdownContainer"] h2,
div[data-testid="stMarkdownContainer"] h3 {
    font-weight: 900;
}

/* Paragraphs, labels, inputs */
p, label, span, input {
    font-weight: 600;
}

/* ===== CARD ===== */
.card {
    background: white;
    border: 1px solid #E2E8F0;
    border-radius: 16px;
    padding: 20px;
    margin: 12px 0;
    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
}

/* ===== DECISION ===== */
.decision-card {
    font-size: 2rem;
    font-weight: 700;
    text-align: center;
    padding: 26px;
    border-radius: 18px;
    margin: 20px 0;
}

/* STATES */
.BUY {
    background: #dcfce7;
    color: #14532d;
}

/* ===== DELAY (CLEAN WARNING STYLE) ===== */
.DELAY {
    background: #fffbeb;              /* soft solid */
    color: #78350f;
    border: 1px solid #fde68a;
    border-radius: 18px;
}

.RECONSIDER {
    background: #fee2e2;
    color: #7f1d1d;
}

/* ===== BUTTON ===== */
.stButton > button {
    border-radius: 12px;
    padding: 12px 18px;
    font-weight: 600;

    background: linear-gradient(135deg, #60a5fa, #3b82f6);
    color: white;
    border: none;

    transition: all 0.2s ease;
}

.stButton > button:hover {
    background: linear-gradient(135deg, #93c5fd, #60a5fa);
    box-shadow: 0 6px 16px rgba(59,130,246,0.3);
}

/* ===== SIDEBAR ===== */
section[data-testid="stSidebar"] {
    background: linear-gradient(
        180deg,
        #fff1f2 0%,
        #ffe4e6 50%,
        #fecdd3 100%
    );
    border-right: 1px solid #fda4af;
    
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #881337;
    }
    
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] label {
}
}

/* ===== TAB FIX (IMPORTANT) ===== */
div[data-testid="stTabs"] button {
    border-radius: 12px 12px 0 0;
    padding: 10px 16px;
    color: #6B7280;
}

/* ACTIVE TAB (WORKING SELECTOR) */
div[data-testid="stTabs"] button[aria-selected="true"] {
    background: white;
    color: #111827;
    font-weight: 600;

    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

/* ===== CUSTOM ALERT CARDS ===== */

/* WARNING */
.alert-warning {
    background: linear-gradient(135deg, #fff7ed, #fde68a);
    color: #7c2d12;
    border: 1px solid #facc15;
    border-radius: 14px;
    padding: 14px 16px;
    margin-top: 10px;
    font-weight: 500;
}

/* SUCCESS */
.alert-success {
    background: linear-gradient(135deg, #ecfdf5, #bbf7d0);
    color: #14532d;
    border: 1px solid #22c55e;
    border-radius: 14px;
    padding: 14px 16px;
    margin-top: 10px;
    font-weight: 500;
}

/* ===== BUTTON TEXT FIX ===== */
.stButton > button {
    color: #111827 !important;   /* force black text */
}

/* ===== MAROON INFO SYSTEM ===== */

.info-block {
    border-radius: 14px;
    padding: 14px 18px;
    margin: 10px 0;
    font-weight: 500;
    transition: 0.2s;
}

/* MAIN MAROON (default info) */
.info-maroon {
    background: #fff1f2;
    color: #881337;
    border: 1px solid #fda4af;
    border-radius: 14px;
    padding: 14px 18px;
}

/* SUCCESS (maroon-green tone) */
.info-maroon-success {
    background: linear-gradient(135deg, #f0fdf4, #dcfce7);
    color: #14532d;
    border: 1px solid #86efac;
}

/* WARNING (maroon-yellow tone) */
.info-maroon-warning {
    background: #fef3c7;        /* soft yellow */
    color: #7c2d12;             /* maroon text */
    border: 1px solid #facc15;
    border-radius: 14px;
    padding: 14px 18px;
    margin: 10px 0;
    font-weight: 500;
}

/* hover effect */
.info-block:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 16px rgba(0,0,0,0.05);
}

/* ===== SURPLUS (GREEN) ===== */
.surplus-box {
    background: #f0fdf4;
    color: #166534;
    border: 1px solid #bbf7d0;
    border-radius: 14px;
    padding: 14px 18px;
    font-weight: 600;
    margin-top: 10px;
}

/* ===== BREAK EVEN (MAROON-YELLOW) ===== */
.break-even-box {
    background: #fffbeb;
    color: #78350f;
    border: 1px solid #fde68a;
    border-radius: 14px;
    padding: 14px 18px;
    font-weight: 600;
    margin-top: 10px;
}

/* ===== DEFICIT (MAROON-RED) ===== */
.deficit-box {
    background: #fef2f2;
    color: #7f1d1d;
    border: 1px solid #fecaca;
    border-radius: 14px;
    padding: 14px 18px;
    font-weight: 600;
    margin-top: 10px;
}

/* ===== CLEAN NUMBER INPUT ===== */

/* whole container */
div[data-testid="stNumberInput"] {
    background: white;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    padding: 6px 10px;
}

/* input field */
div[data-testid="stNumberInput"] input {
    border: none !important;
    background: transparent !important;
    font-size: 16px;
    font-weight: 500;
    color: #111827;
}

/* remove ugly inner borders */
div[data-testid="stNumberInput"] > div {
    border: none !important;
}

/* hide +/- buttons (important) */
div[data-testid="stNumberInput"] button {
    display: none;
}

/* ===== TAB TEXT SIZE ===== */
div[data-testid="stTabs"] button {
    font-size: 20px; 
    font-weight: 500;
    color: #6B7280;
}

/* ===== ACTIVE TAB (CLICKED) ===== */
div[data-testid="stTabs"] button[aria-selected="true"] {
    color: #111827 !important; 
    font-size: 20px;      
    font-weight: 600;

    background: white;
    border-radius: 12px 12px 0 0;

    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

</style>
""", unsafe_allow_html=True)
    
# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — user profile
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("💡 FinSight AI")
    st.caption("Smart Purchase Advisor")
    st.divider()

    st.header("👤 Your Profile")

    persona = st.selectbox(
        "Who are you?",
        ["Student", "Young Professional", "SME Owner", "Gig Worker"]
    )

    employment_map = {
        "Student":            "Student",
        "Young Professional": "Employed",
        "SME Owner":          "Self-employed",
        "Gig Worker":         "Self-employed",
    }

    income   = st.number_input("Monthly Income (RM)",   min_value=0.0, value=3000.0, step=100.0)
    expenses = st.number_input("Monthly Expenses (RM)", min_value=0.0, value=1800.0, step=100.0)
    savings  = st.number_input("Current Savings (RM)",  min_value=0.0, value=5000.0, step=500.0)

    surplus = income - expenses
    st.divider()

    if surplus > 0:
        st.markdown(f"""
        <div class="surplus-box">
        💚 Surplus: RM {surplus:,.0f}/month
        </div>
    """, unsafe_allow_html=True)
    
    elif surplus == 0:
        st.markdown(f"""
                    <div class="break-even-box">
                    ⚠️ Breaking even every month
                    </div>
                    """, unsafe_allow_html=True)
        
    else:
        st.markdown(f"""
                    <div class="deficit-box">
                    🔴 Deficit: RM {abs(surplus):,.0f}/mo
                    </div>
                    """, unsafe_allow_html=True)

st.caption("All values in Malaysian Ringgit (RM)")

# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🧠 Decision Engine",
    "📈 Scenario Simulator",
    "📊 Peer Benchmarks",
    "📸 Smart Scanner",
])

# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — PURCHASE ADVISOR
# ═════════════════════════════════════════════════════════════════════════════
with tab1:
    st.header("🛒 Should You Buy It?")

    col1, col2 = st.columns(2)
    with col1:
        item     = st.text_input("What do you want to buy?", "iPhone 15")
        price    = st.number_input("Price (RM)", min_value=1.0, value=4500.0, step=50.0)
    with col2:
        category = st.selectbox("Category", ["Electronics", "Transport", "Fashion", "Food", "Essential", "Other"])
        urgency  = st.slider("How urgent is this? (1 = Not important , 10 = Important)", 1, 10, 5)

    if st.button("🔍 Analyze Purchase", use_container_width=True, type="primary"):

        # ── Validate inputs first ─────────────────────────────────────────────
        errors = validate_inputs(income, expenses, savings, price)
        if errors:
            for e in errors:
                st.error(e)
            st.stop()

        # ── Decision engine ───────────────────────────────────────────────────
        result   = make_decision(income, expenses, savings, price, urgency)
        decision = result["decision"]
        reason   = result["reason"]
        metrics  = result["metrics"]

        # ── Score + risk (Person 5) ───────────────────────────────────────────
        score = calculate_score(income, expenses, savings, price, urgency)
        risk  = classify_risk(score, metrics.get("months_to_save"))
        score_label, score_emoji = get_score_label(score)

        # ── Metrics row ───────────────────────────────────────────────────────
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Monthly Surplus",   f"RM {metrics['surplus']:,.0f}")
        m2.metric("Spendable Savings", f"RM {metrics['spendable']:,.0f}")
        m3.metric("Emergency Buffer",  f"RM {metrics['buffer']:,.0f}")
        if metrics["months_to_save"] is not None:
            m4.metric("Months to Save", f"{metrics['months_to_save']} mo")
        else:
            m4.metric("Savings After", f"RM {metrics['savings_after']:,.0f}")
        m5.metric(f"Health Score {score_emoji}", f"{score}/100 — {score_label}", delta=f"Risk: {risk}")

        st.progress(score / 100)

        # ── Decision card ─────────────────────────────────────────────────────
        emoji = {"BUY": "✅", "DELAY": "⏳", "RECONSIDER": "⚠️"}[decision]
        st.markdown(
            f'<div class="decision-card {decision}">{emoji} {decision}</div>',
            unsafe_allow_html=True
        )
        st.markdown(f"""
                    <div class="card">
                    {reason}
                    </div>
                    """, unsafe_allow_html=True)

        # ── AI explanation (Person 3) ─────────────────────────────────────────
        st.subheader("🧠 AI Advisor")
        with st.spinner("Getting personalised advice..."):
            benchmarks = get_peer_benchmarks(income, employment_map[persona])
            ai_raw = get_ai_explanation(
                income, expenses, savings, price,
                item, decision, reason, benchmarks, persona,
                score=score, risk=risk
            )
            ai = validate_ai_output(ai_raw)

        if ai["summary"]:
            st.markdown(f"**{ai['summary']}**")
        if ai["explanation"]:
            st.write(ai["explanation"])
        if ai["alternatives"]:
           st.markdown(f"""
                       <div class="info-block info-maroon">
                       💡 <b>Smarter alternatives:</b> {ai['alternatives']}
                       </div>
                       """, unsafe_allow_html=True)
        if ai["action"]:
            st.markdown(f"""
                        <div class="info-block info-maroon-success">
                        ✅ <b>Do this today:</b> {ai['action']}
                        </div>
                        """, unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — SCENARIO SIMULATOR
# ═════════════════════════════════════════════════════════════════════════════
with tab2:
    st.header("📈 Savings Scenario Simulator")
    st.caption("Compare how your savings grow under each choice over the next 12 months.")

    sim_price = st.number_input(
        "Purchase price to simulate (RM)",
        min_value=1.0,
        value=float(st.session_state.get("sim_price", 4500.0)),
        step=50.0,
        key="sim_price"
    )

    scenarios = get_scenarios(income, expenses, savings, sim_price, months=12)

    months_labels = [f"Month {i+1}" for i in range(12)]
    df_plot = pd.DataFrame({
        "Month":    months_labels * 3,
        "Savings":  scenarios["buy_now"] + scenarios["delay"] + scenarios["skip"],
        "Scenario": ["Buy Now"] * 12 + ["Delay (10% off)"] * 12 + ["Skip entirely"] * 12,
    })

    fig = px.line(
    df_plot,
    x="Month",
    y="Savings",
    color="Scenario",
    title="Projected Savings Over 12 Months",
    color_discrete_map={
        "Buy Now": "#ef4444",
        "Delay (10% off)": "#f59e0b",
        "Skip entirely": "#22c55e",
    }
    )
    
    fig.update_layout(
    plot_bgcolor='white',
    paper_bgcolor='white',
    yaxis_tickprefix="RM ",
    legend_title_text=""
    )
    
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor='rgba(0,0,0,0.1)')
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Summary table
    st.subheader("12-Month Outcome Summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("Buy Now",         f"RM {scenarios['buy_now'][-1]:,.0f}",  delta=f"RM {scenarios['buy_now'][-1] - savings:,.0f}")
    c2.metric("Delay (10% off)", f"RM {scenarios['delay'][-1]:,.0f}",   delta=f"RM {scenarios['delay'][-1] - savings:,.0f}")
    c3.metric("Skip entirely",   f"RM {scenarios['skip'][-1]:,.0f}",    delta=f"RM {scenarios['skip'][-1] - savings:,.0f}")

    diff = scenarios["skip"][-1] - scenarios["buy_now"][-1]
    st.markdown(f"""
                <div class="info-maroon">
                💡 Buying now costs you <b>RM {diff:,.0f}</b> compared to not buying over 12 months.
                </div>
                """, unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — PEER BENCHMARKS
# ═════════════════════════════════════════════════════════════════════════════
with tab3:
    st.header("📊 How Do You Compare?")
    st.caption("Benchmarked against real users with similar income from our dataset.")

    benchmarks = get_peer_benchmarks(income, employment_map[persona])

    if not benchmarks:
        st.warning("Not enough peer data for your income level. Try adjusting your income.")
    else:
        exp_pct  = get_expense_percentile(income, expenses)
        save_pct = get_savings_percentile(income, savings)

        st.subheader(f"Your peer group: {benchmarks['peer_count']} people with similar income")

        # Expense percentile
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**💸 Expense Ratio**")
            user_exp_ratio  = round(expenses / income * 100, 1) if income > 0 else 0
            peer_exp_ratio  = round(benchmarks["avg_expenses"] / benchmarks["avg_income"] * 100, 1)
            st.metric("Yours",      f"{user_exp_ratio}% of income")
            st.metric("Peer avg",   f"{peer_exp_ratio}% of income")
            if user_exp_ratio < peer_exp_ratio:
                st.markdown(f"""
                            <div class="alert-success">
                            ✅ You spend less than {exp_pct:.0f}% of your peers.
                            </div>
                            """, unsafe_allow_html=True)
            else:
               st.markdown(f"""
                           <div class="info-block info-maroon-warning">
                           ⚠️ You spend more than {exp_pct:.0f}% of your peers.
                           </div>
                           """, unsafe_allow_html=True)

        with col2:
            st.markdown("**💰 Savings**")
            st.metric("Your savings",  f"RM {savings:,.0f}")
            st.metric("Peer avg",      f"RM {benchmarks['avg_savings']:,.0f}")
            if save_pct >= 50:
                st.markdown(f"""
                            <div class="alert-success">
                            ✅ You save more than {save_pct:.0f}% of your peers.
                            </div>
                            """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                            <div class="info-block info-maroon-warning">
                            ⚠️ You save less than {save_pct:.0f}% of your peers.
                            </div>
                            """, unsafe_allow_html=True)

        st.divider()

        # Radar / bar comparison
        categories = ["Income", "Expenses", "Savings"]
        user_vals  = [income, expenses, savings]
        peer_vals  = [benchmarks["avg_income"], benchmarks["avg_expenses"], benchmarks["avg_savings"]]

        fig2 = go.Figure(data=[
            go.Bar(name="You",       x=categories, y=user_vals, marker_color="#6366f1"),
            go.Bar(name="Peer Avg",  x=categories, y=peer_vals, marker_color="#94a3b8"),
        ])
        fig2.update_layout(
            barmode="group",
            title="You vs Peer Average (RM)",
            yaxis_tickprefix="RM ",
        )
        st.plotly_chart(fig2, use_container_width=True)

        # Extra stats
        st.subheader("More Peer Stats")
        s1, s2, s3 = st.columns(3)
        s1.metric("Avg Credit Score",     f"{benchmarks['avg_credit_score']:.0f}")
        s2.metric("Avg Debt-to-Income",   f"{benchmarks['avg_debt_ratio']:.2f}")
        s3.metric("% with Active Loan",   f"{benchmarks['pct_has_loan']:.0f}%")

# ═══════════════════════
# TAB 4 — SMART SCANNER 
# ═══════════════════════
with tab4:
    st.header("📸 Smart Receipt Scanner")
    st.caption("AI + OCR hybrid scanner with multi-item detection and financial analysis.")

    uploaded = st.file_uploader(
        "Upload image", 
        type=["jpg", "jpeg", "png", "webp"], 
        key="receipt_upload"
    )

    if uploaded:
        st.image(uploaded, width=400)

        if st.button("🔍 Scan & Analyze", use_container_width=True, type="primary"):

            import json, urllib.request, html
            import pytesseract, cv2, numpy as np
            from PIL import Image
            import re

            # ─────────────────────────────
            # OCR FUNCTION (FINAL ROBUST)
            # ─────────────────────────────
            def ocr_extract_items(uploaded):
                image = Image.open(uploaded)
                img_np = np.array(image)

                # Preprocessing (better OCR accuracy)
                gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
                gray = cv2.medianBlur(gray, 3)

                thresh = cv2.adaptiveThreshold(
                    gray, 255,
                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY,
                    11, 2
                )

                config = "--oem 3 --psm 6"
                text = pytesseract.image_to_string(thresh, config=config)

                lines = [l.strip() for l in text.split("\n") if l.strip()]
                items = []

                for line in lines:

                    # 🔥 SUPER ROBUST PRICE MATCH
                    match = re.search(r"(?:RM\s*)?(\d+[\.,:\-]\d{2})", line)

                    if match:
                        price_str = match.group(1)

                        # normalize OCR mistakes
                        price_str = price_str.replace(":", ".")\
                                             .replace(",", ".")\
                                             .replace("-", ".")\
                                             .replace("'", "")

                        try:
                            price = float(price_str)
                        except:
                            continue

                        # remove price from text
                        name = re.sub(r"(?:RM\s*)?\d+[\.,:\-]\d{2}", "", line).strip()

                        if name == "":
                            name = "Unknown item"

                        # filter noise
                        if 1 < price < 10000:
                            items.append({
                                "item": name,
                                "price": price
                            })

                return items, text

            # ─────────────────────────────
            # LOCAL INSIGHTS
            # ─────────────────────────────
            def generate_local_insights(total_price, income, expenses, savings):
                surplus = income - expenses
                remaining = savings - total_price

                if remaining > 2000:
                    summary = "You are financially comfortable for this purchase."
                elif remaining < 500:
                    summary = "This purchase may reduce your financial safety."
                else:
                    summary = "This purchase is manageable but requires caution."

                explanation = f"Total spending: RM {total_price:.2f}. Remaining savings: RM {remaining:.2f}."

                if total_price > surplus:
                    alternatives = "Consider splitting purchases or delaying non-essential items."
                else:
                    alternatives = "You can proceed, but compare prices for better deals."

                action = "Proceed wisely." if remaining > 1000 else "Delay recommended."

                return {
                    "summary": summary,
                    "explanation": explanation,
                    "alternatives": alternatives,
                    "action": action
                }

            # ─────────────────────────────
            # TRY AI FIRST
            # ─────────────────────────────
            api_key = os.environ.get("ILMU_API_KEY", "")
            items = []

            if api_key:
                try:
                    with st.spinner("🤖 Scanning with AI..."):

                        img_bytes = uploaded.getvalue()
                        img_b64 = base64.b64encode(img_bytes).decode()

                        body = json.dumps({
                            "model": "ilmu-glm-5.1",
                            "messages": [{
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image",
                                        "source": {
                                            "type": "base64",
                                            "media_type": uploaded.type,
                                            "data": img_b64,
                                        }
                                    },
                                    {
                                        "type": "text",
                                        "text": (
                                            "Extract ALL items and prices. "
                                            "Return STRICT JSON array only like: "
                                            "[{\"item\":\"...\",\"price\":123.45}]"
                                        )
                                    }
                                ]
                            }]
                        }).encode()

                        req = urllib.request.Request(
                            "https://api.ilmu.ai/anthropic/v1/messages",
                            data=body,
                            headers={
                                "Content-Type": "application/json",
                                "x-api-key": api_key,
                                "anthropic-version": "2023-06-01",
                            }
                        )

                        with urllib.request.urlopen(req, timeout=60) as resp:
                            data = json.loads(resp.read().decode())
                            raw = data["content"][0]["text"]

                        clean = raw.replace("```json", "").replace("```", "").strip()
                        parsed = json.loads(clean)

                        if isinstance(parsed, list):
                            items = parsed

                except Exception as e:
                    st.warning("⚠️ AI failed — switching to OCR")
                    st.caption(str(e)[:120])

            # ─────────────────────────────
            # OCR FALLBACK
            # ─────────────────────────────
            if not items:
                with st.spinner("🔍 Running OCR..."):
                    items, text = ocr_extract_items(uploaded)

                    # FIX HTML BREAK
                    safe_text = html.escape(text)

                    st.markdown(f"""
                    <div class="card">
                    <b>🧾 Extracted Text</b><br><br>
                    {safe_text}
                    </div>
                    """, unsafe_allow_html=True)

            # ─────────────────────────────
            # DISPLAY RESULTS
            # ─────────────────────────────
            if items:
                
                # ── Calculate total ─────────────────────
                total_price = sum(i["price"] for i in items)
                st.success(f"🛒 {len(items)} items detected — Total: RM {total_price:.2f}")
                
                # ── Table ───────────────────────────────
                df_items = pd.DataFrame(items)
                st.dataframe(df_items, use_container_width=True)
                
                # ── Decision Engine ─────────────────────
                result = make_decision(income, expenses, savings, total_price, urgency=5)
                decision = result["decision"]
                reason = result["reason"]
                
                emoji = {
                    "BUY": "✅",
                    "DELAY": "⏳",
                    "RECONSIDER": "⚠️"
                    }[decision]
                
                # ── Decision Card ───────────────────────
                st.markdown(
                    f'<div class="decision-card {decision}">{emoji}<br>{decision}</div>',
                    unsafe_allow_html=True
                    )
                
                # ── Decision Summary ────────────────────
                st.markdown(f"""
                            <div class="card">
                            <b>Decision Summary</b><br><br>
                            {reason}
                            </div>
                            """, unsafe_allow_html=True)
                
                # ── Smart Insights ──────────────────────
                st.subheader("🧠 Smart Insights")
                
                ai = generate_local_insights(total_price, income, expenses, savings)
                
                st.markdown(f"""
                            <div class="card">
                            <p><b>{ai['summary']}</b></p>
                            <p>{ai['explanation']}</p>
                            <div style="background:#f1f5f9;padding:10px;border-radius:8px;margin-top:10px;">
                            💡 {ai['alternatives']}
                            </div>
                            
                            <div style="background:#dcfce7;padding:10px;border-radius:8px;margin-top:10px;">
                            ✅ {ai['action']}
                            </div>
                            
                            </div>
                            """, unsafe_allow_html=True)
            else:
                st.error("❌ No items detected. Try a clearer image.")