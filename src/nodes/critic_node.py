from src.graph.state import EcoSenseState


def critic_node(state: EcoSenseState) -> EcoSenseState:
    critiques = []

    actions = state.get("actions", [])
    evidence = state.get("evidence", [])
    issues = state.get("issues", [])
    compliance = state.get("compliance", {})

    if actions and not issues:
        critiques.append({"type": "support_gap", "message": "Actions proposed without detected issues."})

    if compliance and compliance.get("score", 100) < 60 and len(evidence) == 0:
        critiques.append({"type": "evidence_gap", "message": "Low score but no benchmark evidence retrieved."})

    msgs = state.get("messages", [])
    msgs.append({"agent": "Critic", "type": "critique", "content": f"Critiques: {len(critiques)}"})

    return {
        **state,
        "critiques": critiques,
        "messages": msgs,
    }