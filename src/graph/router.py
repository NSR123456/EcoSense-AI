def should_run_root_cause(state) -> str:
    route = state.get("route", "")
    return "root_cause" if route in ["root_cause", "action_planner"] else "skip_root_cause"


def should_run_action_planner(state) -> str:
    route = state.get("route", "")
    return "action_planner" if route == "action_planner" else "skip_action_planner"


def should_run_compliance(state) -> str:
    route = state.get("route", "")
    return "compliance" if route == "compliance" else "skip_compliance"


def should_run_comparison(state) -> str:
    route = state.get("route", "")
    return "comparison" if route == "comparison" else "skip_comparison"