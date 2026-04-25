"""
benchmarks.py
-------------
Loads the cleaned dataset and computes peer-group comparisons.
Uses median for savings (robust against outliers in synthetic data).
"""

import os
import pandas as pd

_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "cleaned_finance_data.csv")
_df: pd.DataFrame | None = None


def _load() -> pd.DataFrame:
    global _df
    if _df is None:
        _df = pd.read_csv(_DATA_PATH)
    return _df


def _get_peers(income: float, employment_status: str = "Employed") -> pd.DataFrame:
    df = _load()
    low  = income * 0.70
    high = income * 1.30

    peers = df[
        (df["monthly_income_rm"] >= low) &
        (df["monthly_income_rm"] <= high) &
        (df["employment_status"].str.lower() == employment_status.lower())
    ]

    if len(peers) < 10:
        peers = df[
            (df["monthly_income_rm"] >= low) &
            (df["monthly_income_rm"] <= high)
        ]

    return peers


def get_peer_benchmarks(income: float, employment_status: str = "Employed") -> dict:
    peers = _get_peers(income, employment_status)

    if peers.empty:
        return {}

    # Use MEDIAN for savings — synthetic dataset has extreme outliers
    return {
        "peer_count":        len(peers),
        "avg_income":        round(peers["monthly_income_rm"].median(), 2),
        "avg_expenses":      round(peers["monthly_expenses_rm"].median(), 2),
        "avg_savings":       round(peers["savings_rm"].median(), 2),
        "avg_savings_ratio": round(peers["savings_to_income_ratio"].median(), 2),
        "avg_debt_ratio":    round(peers["debt_to_income_ratio"].median(), 2),
        "avg_credit_score":  round(peers["credit_score"].median(), 1),
        "pct_has_loan":      round((peers["has_loan"] == "Yes").mean() * 100, 1),
    }


def get_expense_percentile(income: float, expenses: float) -> float:
    """
    What % of peers spend LESS than you (higher = you spend more than most).
    """
    peers = _get_peers(income)
    if peers.empty:
        return 50.0

    user_ratio  = expenses / income
    peer_ratios = peers["monthly_expenses_rm"] / peers["monthly_income_rm"]
    percentile  = (peer_ratios < user_ratio).mean() * 100
    return round(percentile, 1)


def get_savings_percentile(income: float, savings: float) -> float:
    """
    What % of peers have LESS savings than you (higher = you save more than most).
    Caps outliers at 99th percentile to avoid synthetic data distortion.
    """
    peers = _get_peers(income)
    if peers.empty:
        return 50.0

    p99 = peers["savings_rm"].quantile(0.99)
    peer_savings = peers["savings_rm"].clip(upper=p99)
    percentile = (peer_savings < savings).mean() * 100
    return round(percentile, 1)