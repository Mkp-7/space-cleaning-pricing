"""
Rule-based pricing suggestion engine.

Three named strategies, matching how a small cleaning company actually
thinks about positioning:
  - Budget:  undercut the market to win price-sensitive jobs
  - Market:  match what competitors typically charge
  - Premium: charge above market, betting on quality/reputation

Comparisons only make sense within the same pricing unit (you can't compare
a "per hour" rate to a "flat rate" job), so stats are computed per-unit.
"""

import statistics

STRATEGIES = {
    "budget": {"label": "🟢 Budget (undercut market)", "pct": -10},
    "market": {"label": "🟡 Market (match average)", "pct": 0},
    "premium": {"label": "🔵 Premium (above market)", "pct": 12},
}


def compute_competitor_stats(service_id, competitor_prices):
    """Only compares competitor rates that share the service's pricing unit."""
    rates = [
        cp["rate"] for cp in competitor_prices
        if cp["service_id"] == service_id and cp["rate"] is not None
    ]
    if not rates:
        return None
    return {
        "min": min(rates),
        "max": max(rates),
        "avg": round(statistics.mean(rates), 2),
        "median": round(statistics.median(rates), 2),
        "count": len(rates),
    }


def suggested_price(stats, strategy_key, custom_pct=None):
    if stats is None:
        return None
    pct = custom_pct if custom_pct is not None else STRATEGIES[strategy_key]["pct"]
    return round(stats["avg"] * (1 + pct / 100), 2)


def evaluate_service(our_rate, stats, suggested):
    """
    Returns (status, emoji, message) for the per-service traffic light.
    🟢 aligned / good position   🟡 worth reviewing   🔴 outlier / no data
    """
    if stats is None:
        return "no-data", "⚪", "No competitor data logged yet for this service/unit."

    if our_rate is None:
        return "missing", "⚪", "You haven't set a rate for this service."

    if our_rate > stats["max"]:
        return "high-outlier", "🔴", f"Priced above every tracked competitor (max ${stats['max']:.2f})."

    if our_rate < stats["min"]:
        return "low-outlier", "🔴", f"Priced below every tracked competitor (min ${stats['min']:.2f}) - check margin."

    if suggested is not None:
        diff_pct = abs(our_rate - suggested) / suggested * 100 if suggested else 0
        if diff_pct <= 5:
            return "aligned", "🟢", "Matches your selected strategy well."
        else:
            direction = "above" if our_rate > suggested else "below"
            return "review", "🟡", f"${abs(our_rate - suggested):.2f} {direction} the suggested target."

    return "ok", "🟢", "Within competitor range."
