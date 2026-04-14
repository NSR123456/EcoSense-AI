from langgraph.graph import StateGraph, END

from src.graph.state import EcoSenseState
from src.graph.router import (
    should_run_root_cause,
    should_run_action_planner,
    should_run_compliance,
    should_run_comparison,
)
from src.nodes.planner_node import planner_node
from src.nodes.multimodal_node import multimodal_node
from src.nodes.retrieval_node import retrieval_node
from src.nodes.detect_issues_node import detect_issues_node
from src.nodes.root_cause_node import root_cause_node
from src.nodes.action_planner_node import action_planner_node
from src.nodes.compliance_node import compliance_node
from src.nodes.comparison_node import comparison_node
from src.nodes.critic_node import critic_node
from src.nodes.synthesizer_node import synthesizer_node


def build_workflow():
    graph = StateGraph(EcoSenseState)

    graph.add_node("planner", planner_node)
    graph.add_node("multimodal", multimodal_node)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("detect_issues", detect_issues_node)
    graph.add_node("root_cause", root_cause_node)
    graph.add_node("action_planner", action_planner_node)
    graph.add_node("compliance", compliance_node)
    graph.add_node("comparison", comparison_node)
    graph.add_node("critic", critic_node)
    graph.add_node("synthesizer", synthesizer_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "multimodal")
    graph.add_edge("multimodal", "retrieval")
    graph.add_edge("retrieval", "detect_issues")

    graph.add_conditional_edges(
        "detect_issues",
        should_run_comparison,
        {
            "comparison": "comparison",
            "skip_comparison": "root_cause_gate",
        },
    )

    graph.add_node("root_cause_gate", lambda state: state)
    graph.add_conditional_edges(
        "root_cause_gate",
        should_run_root_cause,
        {
            "root_cause": "root_cause",
            "skip_root_cause": "action_planner_gate",
        },
    )

    graph.add_node("action_planner_gate", lambda state: state)
    graph.add_conditional_edges(
        "action_planner_gate",
        should_run_action_planner,
        {
            "action_planner": "action_planner",
            "skip_action_planner": "compliance_gate",
        },
    )

    graph.add_node("compliance_gate", lambda state: state)
    graph.add_conditional_edges(
        "compliance_gate",
        should_run_compliance,
        {
            "compliance": "compliance",
            "skip_compliance": "critic",
        },
    )

    graph.add_edge("root_cause", "action_planner_gate")
    graph.add_edge("action_planner", "compliance_gate")
    graph.add_edge("compliance", "critic")
    graph.add_edge("comparison", "critic")
    graph.add_edge("critic", "synthesizer")
    graph.add_edge("synthesizer", END)

    return graph.compile()


def run_workflow(
    query: str,
    building_id: str,
    compare_building_id: str = None,
    multimodal_inputs: list | None = None,
    operator_note: str = "",
):
    app = build_workflow()
    init_state = {
        "query": query,
        "building_id": building_id,
        "compare_building_id": compare_building_id,
        "multimodal_inputs": multimodal_inputs or [],
        "operator_note": operator_note or "",
        "messages": [],
    }
    return app.invoke(init_state)