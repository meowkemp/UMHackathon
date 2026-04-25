"""
advisor.py
----------
Decision logic: takes financial inputs, returns a recommendation.
No AI involved — pure rule-based reasoning grounded in the dataset.
"""

EMERGENCY_BUFFER_RATIO = 0.30   # keep 30% of savings untouched as emergency fund
 
 
def make_decision(income: float, expenses: float, savings: float,
                  price: float, urgency: int = 5) -> dict:
    """
    Returns a dict with:
      - decision:  "BUY" | "DELAY" | "RECONSIDER"
      - reason:    short human-readable explanation
      - metrics:   dict of computed numbers for display
    """
 
    # ── Core calculations ─────────────────────────────────────────────────────
    surplus           = income - expenses
    buffer            = savings * EMERGENCY_BUFFER_RATIO
    spendable_savings = savings - buffer
 
    # Max affordable: spendable savings + 3 months of surplus (short-term reachable)
    max_affordable = round(max(spendable_savings + surplus * 3, 0), 2)
 
    metrics = {
        "surplus":        round(surplus, 2),
        "buffer":         round(buffer, 2),
        "spendable":      round(spendable_savings, 2),
        "savings_after":  round(savings - price, 2),
        "months_to_save": 0,             # default — overwritten below if needed
        "max_affordable": max_affordable,
    }
 
    # ── Cannot afford AT ALL ──────────────────────────────────────────────────
    if surplus <= 0:
        metrics["months_to_save"] = None  # no surplus = no path to saving
        return {
            "decision": "RECONSIDER",
            "reason": (
                f"Your monthly expenses exceed your income by RM{-surplus:,.2f}. "
                "Buying anything new would worsen your financial position. "
                "Focus on reducing expenses or increasing income first."
            ),
            "metrics": metrics,
        }
 
    # ── Can afford from spendable savings right now ───────────────────────────
    if spendable_savings >= price:
        metrics["months_to_save"] = 0    # already affordable, no wait needed
        return {
            "decision": "BUY",
            "reason": (
                f"You can comfortably afford this. After buying, you'll still have "
                f"RM{savings - price:,.2f} in savings, keeping your "
                f"RM{buffer:,.2f} emergency buffer intact."
            ),
            "metrics": metrics,
        }
 
    # ── Needs saving up ───────────────────────────────────────────────────────
    shortfall     = price - spendable_savings
    months_needed = shortfall / surplus
    metrics["months_to_save"] = round(months_needed, 1)
 
    if months_needed <= 3:
        decision = "DELAY"
        reason = (
            f"You're RM{shortfall:,.2f} short right now, but with your "
            f"RM{surplus:,.2f}/month surplus you can save enough in just "
            f"{months_needed:.1f} months. A short wait protects your buffer."
        )
    elif months_needed <= 12:
        if urgency >= 8:
            decision = "DELAY"
            reason = (
                f"Given the urgency, consider delaying {months_needed:.0f} months "
                f"or look for a cheaper alternative — something around "
                f"RM{max_affordable:,.2f} is within your reach right now."
            )
        else:
            decision = "DELAY"
            reason = (
                f"It would take ~{months_needed:.0f} months of saving. "
                "Unless this is urgent, consider waiting or finding a budget "
                f"alternative around RM{max_affordable:,.2f}."
            )
    else:
        decision = "RECONSIDER"
        reason = (
            f"Saving enough would take over {months_needed:.0f} months. "
            "This purchase may not be realistic at your current income level. "
            f"Consider a cheaper alternative — you can comfortably afford "
            f"something around RM{max_affordable:,.2f}."
        )
 
    return {"decision": decision, "reason": reason, "metrics": metrics}
 