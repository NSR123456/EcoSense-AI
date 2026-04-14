from src.graph.state import EcoSenseState
from src.core.confidence import compute_confidence


def synthesizer_node(state: EcoSenseState) -> EcoSenseState:
    issues = state.get("issues", [])
    causes = state.get("causes", [])
    actions = state.get("actions", [])
    compliance = state.get("compliance", {})
    evidence = state.get("evidence", [])
    retrieval_meta = state.get("retrieval_meta", {})
    critiques = state.get("critiques", [])
    metrics = state.get("metrics", {})
    insights = state.get("insights", {})
    normalized = metrics.get("normalized_kpis", {})
    bctx = metrics.get("building_context", {})
    recent = state.get("plan", {}).get("recent_pattern", {})

    statistical_evidence = [
        {
            "text": (
                f"Consumption stats: avg={metrics.get('avg_consumption', 0):.1f} kWh, "
                f"min={metrics.get('min_consumption', 0):.1f} kWh, "
                f"max={metrics.get('max_consumption', 0):.1f} kWh"
            ),
            "source": "statistical",
        },
        {
            "text": (
                f"Pattern stats: variability ratio={metrics.get('variability_ratio', 0):.2f}, "
                f"anomalies={metrics.get('anomaly_count', 0)}, trend={metrics.get('trend', 'stable')}"
            ),
            "source": "statistical",
        },
    ]
    if causes:
        statistical_evidence.append(
            {"text": f"Top cause signal: {causes[0].get('impact', 'N/A')}", "source": "statistical"}
        )

    merged_evidence = []
    seen = set()
    for item in (evidence or []) + statistical_evidence:
        text = item.get("text", "")
        key = text if text else str(item)
        if key in seen:
            continue
        seen.add(key)
        merged_evidence.append(item)

    stat_count = sum(1 for e in merged_evidence if str(e.get("source", "")).lower() == "statistical")
    retrieval_meta = {
        **retrieval_meta,
        "statistical_count": stat_count,
        "total_evidence": len(merged_evidence),
    }

    confidence = compute_confidence(issues=issues, evidence=merged_evidence, critiques=critiques)

    top_issue = issues[0]["name"] if issues else "No issue"
    top_cause = causes[0]["impact"] if causes else "No major cause identified"
    top_action = actions[0]["title"] if actions else "Continue monitoring"

    score = compliance.get("score")
    status = compliance.get("status")
    top_issue_conf = issues[0].get("confidence") if issues else None
    top_issue_conf_txt = f"{int(round(top_issue_conf * 100))}%" if isinstance(top_issue_conf, (int, float)) else "N/A"
    anomaly_count = metrics.get("anomaly_count", 0)
    variability_ratio = metrics.get("variability_ratio", 0.0)
    risk_level = issues[0]["severity"] if issues else "low"

    technical_lines = [
        "Decision rationale for selected building:",
        (
            f"- Building context: type={bctx.get('building_type', 'unknown')}, "
            f"area={bctx.get('area_sqft', 'N/A')}, flats={bctx.get('num_flats', 'N/A')}, "
            f"occupancy={bctx.get('occupancy', 'N/A')}"
        ),
        (
            f"- Consumption pattern: avg={metrics.get('avg_consumption', 0):.1f} kWh, "
            f"min={metrics.get('min_consumption', 0):.1f} kWh, "
            f"max={metrics.get('max_consumption', 0):.1f} kWh, "
            f"variability ratio={metrics.get('variability_ratio', 0):.2f}, "
            f"anomalies={metrics.get('anomaly_count', 0)}, trend={metrics.get('trend', 'stable')}"
        ),
    ]

    if recent:
        technical_lines.append(
            (
                f"- Recent movement: recent avg={recent.get('recent_avg', 0)} kWh vs previous avg={recent.get('previous_avg', 0)} kWh "
                f"({recent.get('recent_change_pct', 0)}% change), urgency={recent.get('urgency', 'medium')}"
            )
        )

    if normalized.get("normalization_available"):
        technical_lines.append(
            (
                f"- Normalized intensity: kWh/sqft={normalized.get('avg_kwh_per_sqft')}, "
                f"kWh/flat={normalized.get('avg_kwh_per_flat')}, "
                f"kWh/occupant={normalized.get('avg_kwh_per_occupant')}"
            )
        )

    technical_lines.extend(
        [
            f"- Statistical cause signal: {top_cause}",
            f"- Decision priority: {top_action}",
            f"- Confidence: {confidence['score']}/100 ({confidence['label']})",
        ]
    )

    if score is not None:
        technical_lines.append(f"- Compliance score: {score} ({status})")

    technical = "\n".join(technical_lines)

    simple = f"Main issue is {top_issue.lower()}. Best next step is {top_action.lower()}."
    if normalized.get("normalization_available"):
        simple += " Decision also considers building size and occupancy."

    final_response = {
        "risk_card": {
            "title": "Energy Ops Risk (This Building)",
            "value": (
                f"{str(risk_level).title()} "
                f"(anomalies={anomaly_count}, variability={variability_ratio:.2f})"
            ),
        },
        "issue_card": {
            "title": "Top Issue",
            "value": f"{top_issue} (confidence={top_issue_conf_txt})",
        },
        "cause_card": {
            "title": "Likely Cause",
            "value": top_cause,
        },
        "action_card": {
            "title": "Best Next Action",
            "value": top_action,
        },
        "normalized_risk_card": {
            "title": "Normalized Risk",
            "value": "high" if insights.get("high_normalized_intensity") else "normal",
        },
        "confidence_card": confidence,
        "technical": technical,
        "simple": simple,
        "issues": issues,
        "causes": causes,
        "actions": actions,
        "compliance": compliance,
        "evidence": merged_evidence,
        "retrieval_meta": retrieval_meta,
        "critiques": critiques,
        "messages": state.get("messages", []),
        "metrics": metrics,
        "insights": insights,
    }

    msgs = state.get("messages", [])
    msgs.append({"agent": "Synthesizer", "type": "decision", "content": f"Finalized response with confidence={confidence['score']}"})

    return {
        **state,
        "confidence": confidence,
        "technical": technical,
        "simple": simple,
        "final_response": final_response,
        "messages": msgs,
    }