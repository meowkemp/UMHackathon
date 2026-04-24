import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import anthropic
import base64
import os

# -------------------------------
# PAGE CONFIG
# -------------------------------
st.set_page_config(page_title="FinSight AI", layout="wide", page_icon="💡")

st.markdown("""
<style>
.big-decision {
    font-size: 2.5rem;
    font-weight: 700;
    text-align: center;
    padding: 20px;
    border-radius: 16px;
    margin: 16px 0;
}
.buy { background: #dcfce7; color: #166534; }
.delay { background: #fef9c3; color: #854d0e; }
.avoid { background: #fee2e2; color: #991b1b; }
</style>
""", unsafe_allow_html=True)

st.title("💡 FinSight AI — Smart Purchase Advisor")

# -------------------------------
# API CLIENT (FIXED)
# -------------------------------
client = anthropic.Anthropic(
    api_key=os.getenv("sk-b61445fa03273944d940b508cdca96db013cc258a7ebc4e1")
)

# -------------------------------
# SESSION STATE
# -------------------------------
if "price" not in st.session_state:
    st.session_state.price = 5000.0
if "item" not in st.session_state:
    st.session_state.item = "iPhone 15"

# -------------------------------
# SIDEBAR
# -------------------------------
st.sidebar.header("👤 Profile")

persona = st.sidebar.selectbox(
    "User Type", ["Student", "Young Professional", "SME Owner"]
)

income = st.sidebar.number_input("Monthly Income (RM)", value=3000.0)
expenses = st.sidebar.number_input("Monthly Expenses (RM)", value=2000.0)
savings = st.sidebar.number_input("Savings (RM)", value=1000.0)

risk_multiplier = {
    "Student": 1.2,
    "SME Owner": 0.8,
    "Young Professional": 1.0
}[persona]

disposable_income = income - expenses

st.sidebar.metric("Disposable Income", f"RM {disposable_income:.0f}")

# -------------------------------
# TABS
# -------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "🛒 Analysis",
    "🔄 Scenarios",
    "📊 Dashboard",
    "📸 Scan"
])

# =========================================================
# 🛒 ANALYSIS
# =========================================================
with tab1:
    st.header("🛒 Purchase Analysis")

    col1, col2 = st.columns(2)

    with col1:
        item = st.text_input("Item", st.session_state.item)
        price = st.number_input("Price (RM)", value=st.session_state.price)

    with col2:
        category = st.selectbox("Category", ["Electronics", "Lifestyle", "Essential"])
        urgency = st.slider("Urgency", 1, 10, 5)

    st.session_state.item = item
    st.session_state.price = price

    if st.button("Analyze"):

        if disposable_income <= 0:
            st.error("⚠️ No disposable income.")
            st.stop()

        months = price / disposable_income
        adjusted_months = months * risk_multiplier
        remaining = savings - price

        # Risk
        if adjusted_months > 6:
            risk = "HIGH"
        elif adjusted_months > 3:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        # Decision
        if remaining < 0:
            decision = "AVOID"
        elif risk == "HIGH" and urgency < 7:
            decision = "DELAY"
        else:
            decision = "BUY"

        decision_class = {
            "BUY": "buy",
            "DELAY": "delay",
            "AVOID": "avoid"
        }[decision]

        score = int(max(0, min(100, 100 - adjusted_months * 10 + urgency * 2)))

        # Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Disposable", f"RM {disposable_income:.0f}")
        m2.metric("Recovery", f"{months:.1f} mo")
        m3.metric("Risk", risk)
        m4.metric("Score", f"{score}/100")

        st.progress(score / 100)

        st.markdown(
            f'<div class="big-decision {decision_class}">{decision}</div>',
            unsafe_allow_html=True
        )

        # AI CALL (FIXED)
        st.subheader("🧠 AI Advice")

        prompt = f"""
User: {persona}, Income RM{income}, Expenses RM{expenses}, Savings RM{savings}
Purchase: {item} RM{price}, urgency {urgency}/10
Risk: {risk}, Recovery: {months:.1f} months

Explain:
1. Should buy or not
2. Why
3. Alternatives
Keep short.
"""

        try:
            response = client.messages.create(
                model="claude-3-5-sonnet-latest",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )

            st.info(response.content[0].text)

        except Exception as e:
            st.error(f"AI Error: {e}")

# =========================================================
# 🔄 SCENARIOS
# =========================================================
with tab2:
    st.header("🔄 Scenario Comparison")

    if disposable_income > 0:

        price = st.session_state.price

        buy = price / disposable_income
        delay = (price * 0.9) / disposable_income
        cheap = (price * 0.7) / disposable_income

        df = pd.DataFrame({
            "Scenario": ["Buy", "Delay", "Cheaper"],
            "Months": [buy, delay, cheap]
        })

        st.bar_chart(df.set_index("Scenario"))

    else:
        st.warning("Set valid income/expenses.")

# =========================================================
# 📊 DASHBOARD
# =========================================================
with tab3:
    st.header("📊 Financial Dashboard")

    remaining = max(disposable_income, 0)

    pie = px.pie(
        values=[expenses, remaining],
        names=["Expenses", "Remaining"]
    )
    st.plotly_chart(pie)

    proj = [savings + remaining * i for i in range(6)]
    st.line_chart(proj)

# =========================================================
# 📸 IMAGE SCAN
# =========================================================
with tab4:
    st.header("📸 Receipt Scanner")

    file = st.file_uploader("Upload Image", type=["jpg", "png", "jpeg"])

    if file:
        st.image(file)

        if st.button("Analyze Image"):

            img_bytes = file.getvalue()
            img_b64 = base64.b64encode(img_bytes).decode()

            try:
                response = client.messages.create(
                    model="claude-3-5-sonnet-latest",
                    max_tokens=300,
                    messages=[{
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": file.type,
                                    "data": img_b64
                                }
                            },
                            {
                                "type": "text",
                                "text": "What item and price is this?"
                            }
                        ]
                    }]
                )

                st.success(response.content[0].text)

            except Exception as e:
                st.error(f"Vision Error: {e}")