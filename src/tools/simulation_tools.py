from copy import deepcopy


def simulate_energy_actions(metrics: dict, insights: dict, scenario: dict) -> dict:
    """
    Deterministic what-if simulator.
    scenario example:
    {
        "reduce_peak_pct": 10,
        "reduce_base_load_pct": 8,
        "reduce_variability_pct": 12,
        "efficiency_upgrade_pct": 15
    }
    """

    simulated = deepcopy(metrics)

    avg_val = metrics.get("avg_consumption", 0.0)
    max_val = metrics.get("max_consumption", 0.0)
    min_val = metrics.get("min_consumption", 0.0)
    std_val = metrics.get("std_dev", 0.0)
    anomaly_count = metrics.get("anomaly_count", 0)

    reduce_peak_pct = scenario.get("reduce_peak_pct", 0) / 100.0
    reduce_base_load_pct = scenario.get("reduce_base_load_pct", 0) / 100.0
    reduce_variability_pct = scenario.get("reduce_variability_pct", 0) / 100.0
    efficiency_upgrade_pct = scenario.get("efficiency_upgrade_pct", 0) / 100.0

    # apply effects
    new_max = max_val * (1 - reduce_peak_pct)
    new_min = min_val * (1 - reduce_base_load_pct)
    new_std = std_val * (1 - reduce_variability_pct)

    overall_reduction = (
        0.35 * reduce_peak_pct +
        0.30 * reduce_base_load_pct +
        0.20 * reduce_variability_pct +
        0.40 * efficiency_upgrade_pct
    )
    # Increase cap to allow for more dramatic simulation feedback
    overall_reduction = min(overall_reduction, 0.85)

    new_avg = avg_val * (1 - overall_reduction)
    new_anomalies = max(0, int(round(anomaly_count * (1 - reduce_peak_pct - reduce_variability_pct * 0.5))))

    simulated["avg_consumption"] = round(new_avg, 2)
    simulated["max_consumption"] = round(new_max, 2)
    simulated["min_consumption"] = round(new_min, 2)
    simulated["std_dev"] = round(new_std, 2)
    simulated["variability_ratio"] = round((new_std / new_avg), 3) if new_avg > 0 else 0.0
    simulated["anomaly_count"] = new_anomalies

    savings_daily = round(avg_val - new_avg, 2)
    savings_monthly = round(savings_daily * 30, 2)
    savings_pct = round(((avg_val - new_avg) / avg_val) * 100, 2) if avg_val > 0 else 0.0

    score_delta = 0
    score_delta += int(reduce_peak_pct * 20)
    score_delta += int(reduce_base_load_pct * 20)
    score_delta += int(reduce_variability_pct * 15)
    score_delta += int(efficiency_upgrade_pct * 25)

    return {
        "original_metrics": metrics,
        "simulated_metrics": simulated,
        "scenario": scenario,
        "estimated_savings_daily_kwh": savings_daily,
        "estimated_savings_monthly_kwh": savings_monthly,
        "estimated_savings_pct": savings_pct,
        "estimated_score_improvement": min(score_delta, 25),
    }