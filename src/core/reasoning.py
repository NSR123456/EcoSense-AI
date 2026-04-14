import pandas as pd


def derive_insights(metrics: dict) -> dict:
    avg = metrics.get("avg_consumption", 0)
    mx = metrics.get("max_consumption", 0)
    var_ratio = metrics.get("variability_ratio", 0)
    normalized = metrics.get("normalized_kpis", {})
    per_sqft = normalized.get("avg_kwh_per_sqft")
    per_flat = normalized.get("avg_kwh_per_flat")
    per_occ = normalized.get("avg_kwh_per_occupant")

    # Conservative baseline thresholds for demonstration datasets.
    high_norm_sqft = per_sqft is not None and per_sqft > 0.08
    high_norm_flat = per_flat is not None and per_flat > 22
    high_norm_occ = per_occ is not None and per_occ > 8
    normalized_high = high_norm_sqft or high_norm_flat or high_norm_occ

    return {
        "increasing_trend": metrics.get("trend") == "increasing",
        "decreasing_trend": metrics.get("trend") == "decreasing",
        "high_variability": var_ratio > 0.15,
        "peak_spike": (mx / avg) > 1.8 if avg > 0 else False,
        "high_avg_consumption": avg > 250,
        "high_normalized_intensity": normalized_high,
        "has_anomalies": metrics.get("anomaly_count", 0) > 0,
        "high_base_load": metrics.get("min_consumption", 0) > 100,
    }


def compute_recent_pattern(bdf: pd.DataFrame) -> dict:
    if bdf.empty or "consumption_kwh" not in bdf.columns:
        return {
            "recent_avg": 0.0,
            "previous_avg": 0.0,
            "recent_change_pct": 0.0,
            "urgency": "medium",
            "time_window": "this week",
        }

    df = bdf.sort_values("date") if "date" in bdf.columns else bdf.copy()

    if len(df) < 14:
        recent = df["consumption_kwh"].tail(min(7, len(df)))
        prev = df["consumption_kwh"].head(min(7, len(df)))
    else:
        recent = df["consumption_kwh"].tail(7)
        prev = df["consumption_kwh"].tail(14).head(7)

    recent_avg = float(recent.mean()) if len(recent) else 0.0
    previous_avg = float(prev.mean()) if len(prev) else 0.0
    change_pct = ((recent_avg - previous_avg) / previous_avg * 100) if previous_avg > 0 else 0.0

    if change_pct >= 10:
        urgency = "high"
        time_window = "today"
    elif change_pct >= 3:
        urgency = "medium"
        time_window = "this week"
    else:
        urgency = "low"
        time_window = "this month"

    return {
        "recent_avg": round(recent_avg, 2),
        "previous_avg": round(previous_avg, 2),
        "recent_change_pct": round(change_pct, 2),
        "urgency": urgency,
        "time_window": time_window,
    }


def estimate_savings(metrics: dict, insights: dict) -> dict:
    avg = metrics.get("avg_consumption", 0.0)
    percent = 0
    basis = []

    if insights.get("increasing_trend"):
        percent += 8
        basis.append("rising energy trend")
    if insights.get("high_variability"):
        percent += 7
        basis.append("irregular daily usage")
    if insights.get("peak_spike"):
        percent += 5
        basis.append("avoidable peak spike")
    if insights.get("high_avg_consumption"):
        percent += 10
        basis.append("high base consumption")
    if insights.get("high_normalized_intensity"):
        percent += 6
        basis.append("high normalized intensity")

    percent = min(percent, 25)

    return {
        "estimated_percent": round(percent, 1),
        "estimated_daily_kwh": round(avg * percent / 100.0, 2),
        "estimated_monthly_kwh": round(avg * percent / 100.0 * 30, 2),
        "basis": basis,
    }


def derive_action_plan(metrics: dict, insights: dict, recent_pattern: dict) -> list:
    actions = []
    time_window = recent_pattern.get("time_window", "this week")
    urgency = recent_pattern.get("urgency", "medium")

    if insights.get("high_variability"):
        actions.append({
            "title": "Stabilize operating schedule",
            "what": "Check whether cooling, lighting, or heavy equipment is being used inconsistently",
            "when": time_window,
            "impact": "high",
            "urgency": urgency,
        })

    if insights.get("peak_spike"):
        actions.append({
            "title": "Investigate spike day",
            "what": f"Review what was running on peak day {metrics.get('peak_day', 'unknown')} and avoid simultaneous heavy loads",
            "when": "today",
            "impact": "high",
            "urgency": "high",
        })

    if insights.get("high_base_load"):
        actions.append({
            "title": "Reduce after-hours load",
            "what": "Check always-on equipment and switch off unnecessary loads after operating hours",
            "when": "today",
            "impact": "high",
            "urgency": "high",
        })

    if insights.get("high_avg_consumption"):
        actions.append({
            "title": "Plan efficiency upgrade",
            "what": "Identify old cooling, lighting, or motor equipment for phased replacement",
            "when": "this month",
            "impact": "medium",
            "urgency": "medium",
        })

    if insights.get("high_normalized_intensity"):
        actions.append({
            "title": "Benchmark by building size",
            "what": "Review kWh per area/flat/occupant to identify inefficient zones and normalize operating targets",
            "when": "this week",
            "impact": "medium",
            "urgency": "medium",
        })

    if not actions:
        actions.append({
            "title": "Continue monitoring",
            "what": "No major inefficiency detected. Continue monitoring usage and keep non-essential loads off",
            "when": "this month",
            "impact": "low",
            "urgency": "low",
        })

    return actions