from src.graph.state import EcoSenseState
from src.tools.analytics_tools import get_building_bundle
from src.tools.retrieval_tools import get_evidence_for_query


def compliance_node(state: EcoSenseState) -> EcoSenseState:
    building_id = state["building_id"]
    bundle = get_building_bundle(building_id)
    metrics = bundle["metrics"]
    insights = bundle["insights"]

    score = 100
    if insights.get("high_avg_consumption"):
        score -= 20
    if insights.get("high_variability"):
        score -= 15
    if insights.get("increasing_trend"):
        score -= 10
    score -= min(metrics.get("anomaly_count", 0) * 2, 20)
    score = max(0, score)

    status = "Excellent" if score >= 80 else ("Acceptable" if score >= 60 else ("Needs Improvement" if score >= 40 else "Critical"))
    evidence = get_evidence_for_query(f"energy benchmark variability anomalies score {score}", top_k=3)
    existing_evidence = state.get("evidence", [])

    merged = []
    seen = set()
    for item in existing_evidence + evidence:
        text = item.get("text")
        key = text if text else str(item)
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)

    compliance = {
        "score": score,
        "status": status,
        "evidence": evidence,
    }

    msgs = state.get("messages", [])
    msgs.append({"agent": "Compliance", "type": "evidence", "content": f"Score={score}, evidence={len(evidence)} items"})

    return {
        **state,
        "compliance": compliance,
        "evidence": merged,
        "messages": msgs,
    }