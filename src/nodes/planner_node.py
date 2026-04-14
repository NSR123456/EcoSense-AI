from src.graph.state import EcoSenseState


def planner_node(state: EcoSenseState) -> EcoSenseState:
    query = state.get("query", "").lower()

    if any(k in query for k in ["compare", "vs", "versus"]):
        route = "comparison"
        required = ["retrieval", "detect_issues", "comparison", "critic", "synthesizer"]
    elif any(k in query for k in ["benchmark", "score", "compliance", "standard"]):
        route = "compliance"
        required = ["retrieval", "detect_issues", "compliance", "critic", "synthesizer"]
    elif any(k in query for k in ["what should i do", "action", "fix", "recommend"]):
        route = "action_planner"
        required = ["retrieval", "detect_issues", "root_cause", "action_planner", "critic", "synthesizer"]
    elif any(k in query for k in ["why", "cause", "inefficient", "high usage"]):
        route = "root_cause"
        required = ["retrieval", "detect_issues", "root_cause", "critic", "synthesizer"]
    else:
        route = "detect_issues"
        required = ["retrieval", "detect_issues", "critic", "synthesizer"]

    msgs = state.get("messages", [])
    msgs.append({"agent": "Planner", "type": "plan", "content": f"Selected route: {route}; nodes: {required}"})

    return {
        **state,
        "route": route,
        "plan": {"required_nodes": required},
        "messages": msgs,
    }