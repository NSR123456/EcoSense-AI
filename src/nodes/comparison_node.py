from src.graph.state import EcoSenseState
from src.ingestion.data_loader import load_dataset
from src.core.analytics import compute_building_metrics


def comparison_node(state: EcoSenseState) -> EcoSenseState:
    building_id = state["building_id"]
    other = state.get("compare_building_id")

    df = load_dataset()
    a = df[df["building_id"] == building_id]
    b = df[df["building_id"] == other] if other else df.iloc[0:0]

    ma = compute_building_metrics(a)
    mb = compute_building_metrics(b) if not b.empty else {}

    comparison = {
        "building_a": {"id": building_id, "metrics": ma},
        "building_b": {"id": other, "metrics": mb},
        "winner": other if mb and mb.get("avg_consumption", 999999) < ma.get("avg_consumption", 999999) else building_id,
    }

    msgs = state.get("messages", [])
    msgs.append({"agent": "Comparison", "type": "finding", "content": f"Compared {building_id} vs {other}"})

    return {
        **state,
        "comparison": comparison,
        "messages": msgs,
    }