from src.ingestion.data_loader import load_dataset
from src.core.analytics import compute_building_metrics
from src.core.reasoning import derive_insights, compute_recent_pattern, estimate_savings, derive_action_plan


def get_building_bundle(building_id: str) -> dict:
    df = load_dataset()
    bdf = df[df["building_id"] == building_id].copy()

    metrics = compute_building_metrics(bdf)
    insights = derive_insights(metrics)
    recent_pattern = compute_recent_pattern(bdf)
    savings = estimate_savings(metrics, insights)
    actions = derive_action_plan(metrics, insights, recent_pattern)

    return {
        "df": bdf,
        "metrics": metrics,
        "insights": insights,
        "recent_pattern": recent_pattern,
        "savings": savings,
        "actions": actions,
    }