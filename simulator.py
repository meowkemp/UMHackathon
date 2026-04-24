"""
simulator.py
------------
Pure financial math — no AI, no UI.
Takes user inputs and returns scenario projections.
"""

# Assumption: All income and expenses are monthly and remain constant throughout simulation period

def simulate_savings(income: float, expenses: float, savings: float,
                     purchase_cost: float = 0.0, months: int = 12,
                     monthly_emi: float = 0.0) -> dict:
    """
    Simulate savings balance month-by-month.

    purchase_cost is subtracted in month 1 only.
    monthly_emi is deducted every month before adding surplus.

    Returns a dict with:
      - balances:  list of savings values for each month
      - zero_month: month index (1-based) balance first hits zero, or None
    """
    monthly_surplus = income - expenses - monthly_emi # Net monthly cash available after all fixed obligations
    balance = savings
    results = []
    zero_month = None

    for m in range(months):
        if m == 0:
            balance -= purchase_cost # Apply purchase cost only once at start (Month 1)
        balance += monthly_surplus

        # Record first month where balance becomes negative
        # Do not clamp to 0 so we can model debt accumulation realistically
        if balance < 0 and zero_month is None:
            zero_month = m + 1

        # Store monthly balance rounded to 2 decimal places (currency format)
        results.append(round(balance, 2))

    return {"balances": results, "zero_month": zero_month}


def get_scenarios(income: float, expenses: float, savings: float,
                  price: float, months: int = 12,
                  monthly_emi: float = 0.0) -> dict:
    """
    Returns four scenarios:
      - buy_now:      purchase immediately at full price
      - delay:        wait and purchase at 90% of price (sales / patience)
      - skip:         don't buy at all
      - cheaper_alt:  purchase at 70% of price (second hand / budget brand)
    """

    # Enforce validation before running simulations
    warnings = validate_inputs(income, expenses, savings, price, monthly_emi)
    if warnings:
        return {
            "error": True,
            "warnings": warnings
        }     

    return {
        "buy_now": simulate_savings(income, expenses, savings, price, months, monthly_emi),

        # Delay scenario assumes 10% price reduction (discount / waiting strategy)
        "delay":   simulate_savings(income, expenses, savings, price * 0.9, months, monthly_emi),

        # Skip scenario assumes no purchase is made
        "skip":    simulate_savings(income, expenses, savings, 0.0, months, monthly_emi),

        # Cheaper alternative assumes budget-friendly option at 70% cost
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

    warnings = validate_inputs(income, expenses, savings, price, monthly_emi)
    if warnings:
        return {
            "error": True,
            "warnings": warnings
        } # Return errors instead of metrics if inputs are invalid

    # Safety buffer: 30% of savings is kept untouched for emergency fund
    buffer = savings * 0.30

    # Only this portion of savings is considered usable for purchases
    spendable = max(savings - buffer, 0)

    # Immediate financial impact after purchase
    remaining_balance = round(savings - price, 2)

    net_disposable = round(income - expenses - monthly_emi, 2)

    # If savings already cover purchase, no recovery time needed
    if savings >= price:
        recovery_months = 0.0
    else:
        shortfall = max(price - spendable, 0)

        # Recovery time assumes savings shortfall is covered by monthly surplus
        if net_disposable > 0:
            recovery_months = round(shortfall / net_disposable, 1)

        # Cannot recover financially if monthly cash flow is non-positive
        else:
            recovery_months = None 


    # Risk classification is based on cash flow stability, affordability, and recovery duration.
    # It evaluates both immediate balance impact and long-term repayment ability.
    if net_disposable <= 0:
        risk_level = "CRITICAL"
    elif remaining_balance < 0 or recovery_months > 6:
        risk_level = "HIGH"
    elif 3 <= recovery_months <= 6:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    expense_ratio = round((expenses / income) * 100, 1) if income > 0 else None
    can_afford_now = savings >= price

    return {
        "remaining_balance": float(remaining_balance),
        "recovery_months": float(recovery_months) if recovery_months is not None else None,
        "expense_ratio":  float(expense_ratio) if expense_ratio is not None else None,
        "net_disposable":    float(net_disposable),
        "risk_level":        risk_level,
        "can_afford_now":    can_afford_now,
    }

def validate_inputs(income: float, expenses: float, savings: float,
                    price: float, monthly_emi: float = 0.0) -> list[str]:
    
    """
    Returns a list of warning messages for invalid or edge-case inputs.
    Empty list means all inputs are valid.
    """

    warnings = []

    # Income must be positive for meaningful financial simulation
    if income <= 0:
        warnings.append("Income must be greater than zero.")

    # Warning: spending exceeds income → no savings possible
    if expenses > income:
        warnings.append("Monthly expenses exceed income — no surplus available.")
    
    if savings < 0:
        warnings.append("Savings balance is negative.")
    
    if price <= 0:
        warnings.append("Purchase price must be greater than zero.")
    
    if monthly_emi < 0:
        warnings.append("Monthly EMI cannot be negative.")

    surplus = income - expenses

    # EMI exceeds available surplus, indicating potential cash flow instability
    if monthly_emi > surplus and surplus > 0:
        warnings.append("Monthly EMI exceeds your available surplus.")
    elif monthly_emi > 0 and surplus <= 0:
        warnings.append("Monthly EMI cannot be supported — no surplus after expenses.")

    return warnings