from src.graph.state import EcoSenseState
from src.tools.analytics_tools import get_building_bundle


def root_cause_node(state: EcoSenseState) -> EcoSenseState:
    building_id = state["building_id"]
    bundle = get_building_bundle(building_id)
    metrics = bundle["metrics"]
    insights = bundle["insights"]

    causes = []
    if insights.get("high_variability"):
        variability_ratio = metrics.get("variability_ratio", 0)
        anomaly_count = metrics.get("anomaly_count", 0)
        causes.append({
            "factor": "irregular_schedule",
            "evidence": f"variability ratio={metrics.get('variability_ratio', 0):.2f}",
            "impact": (
                f"high day-to-day variability (ratio={variability_ratio:.2f}, "
                f"anomalies={anomaly_count}) indicates inconsistent operating schedule"
            ),
            "confidence": 0.82,
        })
    if insights.get("high_base_load"):
        min_load = metrics.get("min_consumption", 0)
        avg_load = metrics.get("avg_consumption", 0)
        base_share = (min_load / avg_load) if avg_load else 0
        causes.append({
            "factor": "always_on_load",
            "evidence": f"minimum consumption={metrics.get('min_consumption', 0):.2f} kWh",
            "impact": (
                f"elevated base load (min={min_load:.1f} kWh, "
                f"base/avg={base_share:.2f}) suggests always-on equipment"
            ),
            "confidence": 0.85,
        })
    if insights.get("peak_spike"):
        max_load = metrics.get("max_consumption", 0)
        avg_load = metrics.get("avg_consumption", 0)
        spike_ratio = (max_load / avg_load) if avg_load else 0
        causes.append({
            "factor": "peak_event",
            "evidence": f"peak day={metrics.get('peak_day', 'unknown')}",
            "impact": (
                f"peak-load spike (max/avg={spike_ratio:.2f}, "
                f"peak day={metrics.get('peak_day', 'unknown')}) may be driving cost"
            ),
            "confidence": 0.78,
        })

    if not causes:
        causes.append({
            "factor": "normal_pattern",
            "evidence": "no strong abnormal signal detected",
            "impact": "no major inefficiency identified",
            "confidence": 0.68,
        })

    msgs = state.get("messages", [])
    msgs.append({"agent": "RootCause", "type": "finding", "content": f"Top cause: {causes[0]['factor']}"})

    return {
        **state,
        "causes": causes,
        "messages": msgs,
    }