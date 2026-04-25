"""
app.py
------
FinSight AI — Streamlit frontend.
Run with:  streamlit run app.py
"""

import base64
import sys
import os
import re

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

try:
    import pytesseract
    import cv2
    import numpy as np
    from PIL import Image
    import html
    _OCR_AVAILABLE = True
except ImportError:
    _OCR_AVAILABLE = False
    
# Set path (Windows) — update to match your machine, or remove if Tesseract is on PATH
# pytesseract.pytesseract.tesseract_cmd = r"C:\Users\YourName\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"

# Make sure core/ is importable
sys.path.insert(0, os.path.dirname(__file__))
from core.advisor      import make_decision
from core.ai_explainer import get_ai_explanation, get_followup_answer, scan_receipt_image
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

div[data-testid="stMarkdownContainer"] h1,
div[data-testid="stMarkdownContainer"] h2,
div[data-testid="stMarkdownContainer"] h3 {
    font-weight: 900;
}

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

.BUY {
    background: #dcfce7;
    color: #14532d;
}

.DELAY {
    background: #fffbeb;
    color: #78350f;
    border: 1px solid #fde68a;
    border-radius: 18px;
}

.RECONSIDER {
    background: #fee2e2;
    color: #7f1d1d;
}

/* ===== BUTTON ===== */
.stButton > button,
.stButton > button[kind="primary"] {
    border-radius: 12px !important;
    padding: 12px 18px;
    font-weight: 600;
    background: linear-gradient(135deg, #60a5fa, #3b82f6) !important;
    color: #111827 !important;
    border: none;
    transition: all 0.2s ease;
}

.stButton > button:hover,
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #93c5fd, #60a5fa) !important;
    box-shadow: 0 6px 16px rgba(59,130,246,0.3);
    color: #111827 !important;
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

/* ===== TAB FIX ===== */
div[data-testid="stTabs"] button {
    border-radius: 12px 12px 0 0;
    padding: 10px 16px;
    color: #6B7280;
    font-size: 20px;
    font-weight: 500;
}

/* ACTIVE TAB */
div[data-testid="stTabs"] button[aria-selected="true"] {
    background: white;
    color: #111827 !important;
    font-size: 20px;
    font-weight: 600;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

/* ===== CUSTOM ALERT CARDS ===== */

.alert-warning {
    background: linear-gradient(135deg, #fff7ed, #fde68a);
    color: #7c2d12;
    border: 1px solid #facc15;
    border-radius: 14px;
    padding: 14px 16px;
    margin-top: 10px;
    font-weight: 500;
}

.alert-success {
    background: linear-gradient(135deg, #ecfdf5, #bbf7d0);
    color: #14532d;
    border: 1px solid #22c55e;
    border-radius: 14px;
    padding: 14px 16px;
    margin-top: 10px;
    font-weight: 500;
}

/* ===== MAROON INFO SYSTEM ===== */

.info-block {
    border-radius: 14px;
    padding: 14px 18px;
    margin: 10px 0;
    font-weight: 500;
    transition: 0.2s;
}

.info-block:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 16px rgba(0,0,0,0.05);
}

.info-maroon {
    background: #fff1f2;
    color: #881337;
    border: 1px solid #fda4af;
    border-radius: 14px;
    padding: 14px 18px;
}

.info-maroon-success {
    background: linear-gradient(135deg, #f0fdf4, #dcfce7);
    color: #14532d;
    border: 1px solid #86efac;
}

.info-maroon-warning {
    background: #fef3c7;
    color: #7c2d12;
    border: 1px solid #facc15;
    border-radius: 14px;
    padding: 14px 18px;
    margin: 10px 0;
    font-weight: 500;
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

/* ===== BREAK EVEN ===== */
.break-even-box {
    background: #fffbeb;
    color: #78350f;
    border: 1px solid #fde68a;
    border-radius: 14px;
    padding: 14px 18px;
    font-weight: 600;
    margin-top: 10px;
}

/* ===== DEFICIT ===== */
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
div[data-testid="stNumberInput"] {
    background: white;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    padding: 6px 10px;
}

div[data-testid="stNumberInput"] input {
    border: none !important;
    background: transparent !important;
    font-size: 16px;
    font-weight: 500;
    color: #111827;
}

div[data-testid="stNumberInput"] > div {
    border: none !important;
}

div[data-testid="stNumberInput"] button {
    display: none;
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

# ── Shared benchmarks (computed once, available to all tabs) ──────────────────
benchmarks = get_peer_benchmarks(income, employment_map[persona])

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

    # ── Session state initialisation ──────────────────────────────────────────
    if "analysis" not in st.session_state:
        st.session_state.analysis = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "chat_context" not in st.session_state:
        st.session_state.chat_context = {}

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

        # ── Score + risk ──────────────────────────────────────────────────────
        score = calculate_score(income, expenses, savings, price, urgency)
        risk  = classify_risk(score, metrics.get("months_to_save"))
        score_label, score_emoji = get_score_label(score)

        # ── Scenarios for richer AI context ───────────────────────────────────
        scenarios = get_scenarios(income, expenses, savings, price, months=12)

        # ── AI explanation ────────────────────────────────────────────────────
        with st.spinner("Getting personalised advice..."):
            ai_raw = get_ai_explanation(
                income, expenses, savings, price,
                item, decision, reason, benchmarks, persona,
                score=score, risk=risk, scenarios=scenarios,
                category=category, urgency=urgency,
            )

        # ── Persist to session state so results survive rerenders ─────────────
        st.session_state.analysis = {
            "decision": decision, "reason": reason, "metrics": metrics,
            "score": score, "risk": risk, "ai": validate_ai_output(ai_raw),
        }
        st.session_state.chat_history = []
        st.session_state.chat_context = {
            "income": income, "expenses": expenses, "savings": savings,
            "price": price, "item": item, "decision": decision,
        }

    # ── Display results (persists after button click) ─────────────────────────
    if st.session_state.analysis:
        a        = st.session_state.analysis
        decision = a["decision"]
        metrics  = a["metrics"]
        score    = a["score"]
        risk     = a["risk"]
        ai       = a["ai"]
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
                    {a["reason"]}
                    </div>
                    """, unsafe_allow_html=True)

        # ── AI explanation ────────────────────────────────────────────────────
        st.subheader("🧠 AI Advisor")

        if ai["summary"]:
            st.markdown(f"**{ai['summary']}**")
        if ai.get("tradeoff"):
            st.warning(f"⚖️ **Trade-off:** {ai['tradeoff']}")
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
        if ai.get("confidence"):
            conf_color = {"HIGH": "🟢", "MEDIUM": "🟡", "LOW": "🔴"}.get(ai["confidence"], "⚪")
            st.caption(f"AI confidence: {conf_color} {ai['confidence']}")

        # ── Follow-up chat ────────────────────────────────────────────────────
        st.divider()
        st.markdown("**💬 Ask a follow-up question**")

        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(f"**You:** {msg['content']}")
            else:
                st.markdown(f"**FinSight:** {msg['content']}")

        followup    = st.text_input("e.g. What if I wait 3 months? What's a cheaper option?", key="followup_input")
        ask_clicked = st.button("Ask", key="followup_btn")

        if ask_clicked:
            q = followup.strip() if followup else ""
            if q:
                with st.spinner("Thinking..."):
                    answer = get_followup_answer(
                        q,
                        st.session_state.chat_history,
                        st.session_state.chat_context,
                    )
                if "unavailable" in answer.lower() or "api key" in answer.lower():
                    st.error(f"⚠️ {answer} — The ILMU server may be busy. Wait a moment and try again.")
                elif answer.startswith("__"):
                    st.error("⚠️ AI unavailable — try again in a moment.")
                else:
                    st.session_state.chat_history.append({"role": "user",      "content": q})
                    st.session_state.chat_history.append({"role": "assistant", "content": answer})
                    st.rerun()
            else:
                st.warning("Type a question first!")

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
        "Month":    months_labels * 4,
        "Savings":  scenarios["buy_now"] + scenarios["delay"] + scenarios["cheaper_alt"] + scenarios["skip"],
        "Scenario": ["Buy Now"] * 12 + ["Delay (10% off)"] * 12 + ["Cheaper Alt (30% off)"] * 12 + ["Skip entirely"] * 12,
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
        "Cheaper Alt (30% off)": "#8b5cf6",
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
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Buy Now",                  f"RM {scenarios['buy_now'][-1]:,.0f}",     delta=f"RM {scenarios['buy_now'][-1] - savings:,.0f}")
    c2.metric("Delay (10% off)",          f"RM {scenarios['delay'][-1]:,.0f}",       delta=f"RM {scenarios['delay'][-1] - savings:,.0f}")
    c3.metric("Cheaper Alt (30% off)",    f"RM {scenarios['cheaper_alt'][-1]:,.0f}", delta=f"RM {scenarios['cheaper_alt'][-1] - savings:,.0f}")
    c4.metric("Skip entirely",            f"RM {scenarios['skip'][-1]:,.0f}",        delta=f"RM {scenarios['skip'][-1] - savings:,.0f}")

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

            import html
            try:
                import pytesseract, cv2, numpy as np
                from PIL import Image
                _OCR_AVAILABLE = True
            except ImportError:
                _OCR_AVAILABLE = False

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
            # TRY AI FIRST
            # ─────────────────────────────
            api_key = os.environ.get("ILMU_API_KEY", "")
            items = []

            if api_key:
                try:
                    with st.spinner("🤖 Scanning with AI..."):
                        scan = scan_receipt_image(uploaded.getvalue(), uploaded.type)

                    if scan.get("error") == "VISION_NOT_SUPPORTED":
                        st.warning("⚠️ AI vision not supported — using OCR instead.")
                    elif scan.get("error") and scan["price"] == 0:
                        st.warning(f"⚠️ AI scan failed ({scan['error']}) — using OCR instead.")
                    elif scan["price"] > 0:
                        items = [{"item": scan["item"], "price": scan["price"]}]

                except Exception as e:
                    st.warning("⚠️ AI failed — switching to OCR")
                    st.caption(str(e)[:120])

            # ─────────────────────────────
            # OCR FALLBACK
            # ─────────────────────────────
            if not items:
                if _OCR_AVAILABLE:
                    with st.spinner("🔍 Running OCR..."):
                        items, text = ocr_extract_items(uploaded)

                        safe_text = html.escape(text)

                        st.markdown(f"""
                        <div class="card">
                        <b>🧾 Extracted Text</b><br><br>
                        {safe_text}
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.error("❌ No items detected. Tesseract OCR is not installed — only AI scanning is available.")

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
                score = calculate_score(income, expenses, savings, total_price)
                risk  = classify_risk(score, result["metrics"].get("months_to_save"))

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
                
                # ── AI Advisor (full engine, same as Tab 1) ──────────────────
                st.subheader("🧠 AI Advisor")
                with st.spinner("Getting personalised advice..."):
                    scen_re    = get_scenarios(income, expenses, savings, total_price, months=12)
                    ai_receipt = get_ai_explanation(
                        income, expenses, savings, total_price,
                        items[0]["item"] if len(items) == 1 else f"{len(items)}-item receipt",
                        decision, reason, benchmarks, persona,
                        score=score, risk=risk, scenarios=scen_re,
                        category="Other", urgency=5,
                    )
                ai = validate_ai_output(ai_receipt)

                if ai["summary"]:
                    st.markdown(f"**{ai['summary']}**")
                if ai.get("tradeoff"):
                    st.warning(f"⚖️ **Trade-off:** {ai['tradeoff']}")
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
                if ai.get("confidence"):
                    conf_color = {"HIGH": "🟢", "MEDIUM": "🟡", "LOW": "🔴"}.get(ai["confidence"], "⚪")
                    st.caption(f"AI confidence: {conf_color} {ai['confidence']}")

            else:
                st.error("❌ No items detected. Try a clearer image.")
