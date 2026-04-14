from src.graph.state import EcoSenseState
from src.tools.analytics_tools import get_building_bundle


def detect_issues_node(state: EcoSenseState) -> EcoSenseState:
    building_id = state["building_id"]
    bundle = get_building_bundle(building_id)

    metrics = bundle["metrics"]
    insights = bundle["insights"]

    issues = []
    if insights.get("has_anomalies"):
        issues.append({"name": "High anomaly frequency", "severity": "high", "confidence": 0.88})
    if insights.get("high_variability"):
        issues.append({"name": "Unstable usage pattern", "severity": "medium", "confidence": 0.81})
    if insights.get("increasing_trend"):
        issues.append({"name": "Rising consumption trend", "severity": "medium", "confidence": 0.76})
    if insights.get("high_base_load"):
        issues.append({"name": "High base load", "severity": "high", "confidence": 0.84})
    if insights.get("high_normalized_intensity"):
        issues.append({"name": "High normalized energy intensity", "severity": "medium", "confidence": 0.79})

    if not issues:
        issues.append({"name": "No major issue detected", "severity": "low", "confidence": 0.70})

    msgs = state.get("messages", [])
    msgs.append({
        "agent": "DetectIssues",
        "type": "finding",
        "content": f"Detected {len(issues)} issue(s); anomalies={metrics.get('anomaly_count', 0)}, trend={metrics.get('trend')}"
    })

    return {
        **state,
        "metrics": metrics,
        "insights": insights,
        "issues": issues,
        "messages": msgs,
    }