"""
simulator.py
------------
Pure financial math — no AI, no UI.
Takes user inputs and returns scenario projections.
"""

def simulate_savings(income: float, expenses: float, savings: float,
                     purchase_cost: float = 0.0, months: int = 12,
                     monthly_emi: float = 0.0) -> list[float]:
    """
    Simulate savings balance month-by-month.
    purchase_cost is subtracted in month 1 only.
    monthly_emi is deducted every month before adding surplus.
    Negative balances model debt accumulation realistically.
    Returns a list of savings values for each month.
    """
    monthly_surplus = income - expenses - monthly_emi
    balance = savings
    results = []

    for m in range(months):
        if m == 0:
            balance -= purchase_cost
        balance += monthly_surplus
        results.append(round(balance, 2))

    return results


def get_scenarios(income: float, expenses: float, savings: float,
                  price: float, months: int = 12,
                  monthly_emi: float = 0.0) -> dict:
    """
    Returns four scenarios as flat lists (compatible with charts + AI engine):
      - buy_now:      purchase immediately at full price
      - delay:        wait and purchase at 90% of price (sales / patience)
      - skip:         don't buy at all
      - cheaper_alt:  purchase at 70% of price (second hand / budget brand)
    """
    return {
        "buy_now":     simulate_savings(income, expenses, savings, price,       months, monthly_emi),
        "delay":       simulate_savings(income, expenses, savings, price * 0.9, months, monthly_emi),
        "skip":        simulate_savings(income, expenses, savings, 0.0,         months, monthly_emi),
        "cheaper_alt": simulate_savings(income, expenses, savings, price * 0.7, months, monthly_emi),
    }


def get_summary_metrics(income: float, expenses: float, savings: float,
                        price: float, monthly_emi: float = 0.0) -> dict:
    """
    Returns key decision metrics:
      - remaining_balance: savings minus purchase price
      - recovery_months:   months to recover (price - spendable savings) from surplus, respecting 30% buffer
      - net_disposable:    income - expenses - monthly_emi
      - risk_level:        LOW / MEDIUM / HIGH / CRITICAL
      - expense_ratio:     expenses / income as percentage
      - can_afford_now:    whether current savings cover the price
    """
    buffer = savings * 0.30
    spendable = max(savings - buffer, 0)
    remaining_balance = round(savings - price, 2)
    net_disposable = round(income - expenses - monthly_emi, 2)

    if savings >= price:
        recovery_months = 0.0
    else:
        shortfall = max(price - spendable, 0)
        if net_disposable > 0:
            recovery_months = round(shortfall / net_disposable, 1)
        else:
            recovery_months = None

    # FIXED priority order
    if net_disposable <= 0:
        risk_level = "CRITICAL"
    elif recovery_months is not None and 3 <= recovery_months <= 6:
        risk_level = "MEDIUM"                          # ← check MEDIUM first
    elif remaining_balance < 0 or (recovery_months is not None and recovery_months > 6):
        risk_level = "HIGH"
    else:
        risk_level = "LOW"

    expense_ratio = round((expenses / income) * 100, 1) if income > 0 else None
    can_afford_now = savings >= price

    return {
        "remaining_balance": float(remaining_balance),
        "recovery_months":  float(recovery_months) if recovery_months is not None else None,
        "expense_ratio":    float(expense_ratio) if expense_ratio is not None else None,
        "net_disposable":   float(net_disposable),
        "risk_level":       risk_level,
        "can_afford_now":   can_afford_now,
    }