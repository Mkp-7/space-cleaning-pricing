"""
Simple compound-growth revenue forecast, driven off actual logged job history.
"""

from datetime import datetime
import calendar

import pandas as pd


def monthly_revenue_history(jobs):
    """Aggregate completed/paid job revenue by calendar month."""
    if not jobs:
        return pd.DataFrame(columns=["month", "revenue"])

    df = pd.DataFrame(jobs)
    df = df[df["status"].isin(["Completed", "Paid"])]
    if df.empty:
        return pd.DataFrame(columns=["month", "revenue"])

    df["job_date"] = pd.to_datetime(df["job_date"], errors="coerce")
    df = df.dropna(subset=["job_date"])
    df["month"] = df["job_date"].dt.to_period("M").astype(str)

    grouped = df.groupby("month")["price_charged"].sum().reset_index()
    grouped.columns = ["month", "revenue"]
    return grouped.sort_values("month")


def project_forecast(base_monthly_revenue, monthly_growth_pct, num_months, target_monthly=None):
    """
    Returns a DataFrame with month-by-month projected revenue using
    compound growth: revenue_n = base * (1 + growth)^n
    """
    rows = []
    today = datetime.now()
    revenue = base_monthly_revenue
    for i in range(1, num_months + 1):
        revenue = revenue * (1 + monthly_growth_pct / 100) if i > 1 else base_monthly_revenue * (1 + monthly_growth_pct / 100)
        month_index = today.month - 1 + i
        year = today.year + month_index // 12
        month = month_index % 12 + 1
        label = f"{calendar.month_abbr[month]} {year}"
        rows.append({
            "Month": label,
            "Projected Revenue": round(revenue, 2),
            "Target": target_monthly if target_monthly else None,
        })
    return pd.DataFrame(rows)
