from src.graph.state import EcoSenseState
from src.tools.analytics_tools import get_building_bundle


def action_planner_node(state: EcoSenseState) -> EcoSenseState:
    building_id = state["building_id"]
    bundle = get_building_bundle(building_id)

    actions = bundle["actions"]
    savings = bundle["savings"]
    recent = bundle["recent_pattern"]

    msgs = state.get("messages", [])
    if actions:
        msgs.append({
            "agent": "ActionPlanner",
            "type": "proposal",
            "content": f"Top action: {actions[0]['title']} ({actions[0]['when']})"
        })

    return {
        **state,
        "actions": actions,
        "messages": msgs,
        "plan": {**state.get("plan", {}), "savings": savings, "recent_pattern": recent},
    }