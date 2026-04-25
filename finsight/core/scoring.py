"""
scoring.py  — Person 5: Backend Support + Validation + Scoring
--------------------------------------------------------------
Owns:
  - Financial health score (0–100)
  - Risk classification
  - Input validation
  - Output validation

All functions are pure (no side effects, no API calls).
app.py imports these and passes results to the UI.
"""


# ── Score weights (tunable) ───────────────────────────────────────────────────
_W_SURPLUS    = 30   # monthly surplus relative to income
_W_SAVINGS    = 25   # savings buffer depth
_W_RECOVERY   = 25   # how quickly user recovers after purchase
_W_URGENCY    = 10   # urgency bonus
_W_DEBT       = 10   # penalty for existing debt context


def calculate_score(
    income:      float,
    expenses:    float,
    savings:     float,
    price:       float,
    urgency:     int   = 5,
    has_loan:    bool  = False,
) -> int:
    """
    Returns a financial health score 0–100 for this purchase decision.

    Higher = healthier / safer to buy.

    Breakdown:
      - Surplus ratio     (30 pts): how much of income is left after expenses
      - Savings depth     (25 pts): how many months of expenses savings covers
      - Recovery time     (25 pts): months needed to recover purchase cost
      - Urgency bonus     (10 pts): urgency 1–10 scaled to 0–10 pts
      - Loan penalty      (10 pts): deducted if user already has a loan
    """
    if income <= 0:
        return 0

    surplus = income - expenses

    # ── Surplus ratio score (0–30) ────────────────────────────────────────────
    surplus_ratio = surplus / income  # ideally >= 0.20
    surplus_score = min(30, max(0, int(surplus_ratio * 100)))  # 30% surplus = 30 pts

    # ── Savings depth score (0–25) ────────────────────────────────────────────
    # How many months of expenses can savings cover?
    savings_months = savings / expenses if expenses > 0 else 0
    # 6+ months = full score, 0 months = 0
    savings_score = min(25, int(savings_months / 6 * 25))

    # ── Recovery time score (0–25) ────────────────────────────────────────────
    # How many months of surplus to recover the purchase cost?
    if surplus <= 0:
        recovery_score = 0
    else:
        recovery_months = price / surplus
        # 0 months = 25 pts, 12+ months = 0 pts
        recovery_score = max(0, int(25 - (recovery_months / 12 * 25)))

    # ── Urgency bonus (0–10) ──────────────────────────────────────────────────
    urgency_score = int((urgency / 10) * 10)

    # ── Loan penalty (0 or -10) ───────────────────────────────────────────────
    loan_penalty = 10 if has_loan else 0

    total = surplus_score + savings_score + recovery_score + urgency_score - loan_penalty
    return max(0, min(100, total))


def classify_risk(score: int, months_to_recover: float | None) -> str:
    """
    Returns "LOW", "MEDIUM", or "HIGH" risk based on score and recovery time.
    months_to_recover=None means the purchase is affordable now (BUY path).
    """
    if months_to_recover is None:
        # Already affordable — risk depends solely on the health score
        if score >= 65:
            return "LOW"
        elif score >= 40:
            return "MEDIUM"
        else:
            return "HIGH"

    if score >= 65 and months_to_recover <= 3:
        return "LOW"
    elif score >= 40 or months_to_recover <= 6:
        return "MEDIUM"
    else:
        return "HIGH"


def validate_inputs(
    income:   float,
    expenses: float,
    savings:  float,
    price:    float,
) -> list[str]:
    """
    Validates user inputs. Returns a list of error strings.
    Empty list = all inputs are valid.
    """
    errors = []

    if income <= 0:
        errors.append("Monthly income must be greater than 0.")
    if expenses < 0:
        errors.append("Monthly expenses cannot be negative.")
    if savings < 0:
        errors.append("Savings cannot be negative.")
    if price <= 0:
        errors.append("Purchase price must be greater than 0.")
    if expenses > income * 2:
        errors.append("Expenses are more than double your income — please check your values.")
    if price > savings * 10:
        errors.append(
            f"Purchase price (RM{price:,.0f}) is extremely high relative to "
            f"savings (RM{savings:,.0f}). Double-check the amount."
        )

    return errors


def validate_ai_output(ai_result: dict) -> dict:
    """
    Validates and sanitises the structured AI output from ai_explainer.py.
    Ensures all expected keys exist.  Only uses fallbacks for fields that
    are genuinely missing — empty strings from the AI are kept as-is so the
    UI simply hides that section rather than showing generic filler text.
    """
    defaults = {
        "summary":      "",
        "tradeoff":     "",
        "explanation":  "",
        "alternatives": "",
        "action":       "",
        "confidence":   "MEDIUM",
    }

    cleaned = {}
    for key, default in defaults.items():
        val = ai_result.get(key, default)
        # Don't overwrite real error messages (summary starting with ⚠️)
        if key == "summary" and isinstance(val, str) and val.startswith("⚠️"):
            cleaned[key] = val
        elif isinstance(val, str):
            cleaned[key] = val.strip()
        else:
            cleaned[key] = str(val).strip()

    # Preserve raw for debugging
    if "raw" in ai_result:
        cleaned["raw"] = ai_result["raw"]

    return cleaned


def get_score_label(score: int) -> tuple[str, str]:
    """
    Returns (label, emoji) for a given score.
    Example: (75, "Good") → ("Good", "💚")
    """
    if score >= 80:
        return "Excellent", "💚"
    elif score >= 60:
        return "Good", "🟢"
    elif score >= 40:
        return "Fair", "🟡"
    elif score >= 20:
        return "Risky", "🟠"
    else:
        return "Critical", "🔴"
