import streamlit as st
import plotly.graph_objects as go
from src.tools.simulation_tools import simulate_energy_actions


def render_simulator_panel(metrics: dict, insights: dict):
    st.subheader("What-If Simulator")

    c1, c2 = st.columns(2)

    with c1:
        reduce_peak_pct = st.slider("Reduce peak load (%)", 0, 30, 10, 1)
        reduce_base_load_pct = st.slider("Reduce base load (%)", 0, 30, 8, 1)

    with c2:
        reduce_variability_pct = st.slider("Reduce variability (%)", 0, 30, 10, 1)
        efficiency_upgrade_pct = st.slider("Efficiency upgrade impact (%)", 0, 30, 12, 1)

    scenario = {
        "reduce_peak_pct": reduce_peak_pct,
        "reduce_base_load_pct": reduce_base_load_pct,
        "reduce_variability_pct": reduce_variability_pct,
        "efficiency_upgrade_pct": efficiency_upgrade_pct,
    }

    sim = simulate_energy_actions(metrics, insights, scenario)

    st.markdown("### Projected Outcome")
    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("Savings %", f"{sim['estimated_savings_pct']}%")
    with k2:
        st.metric("Daily Savings", f"{sim['estimated_savings_daily_kwh']} kWh")
    with k3:
        st.metric("Monthly Savings", f"{sim['estimated_savings_monthly_kwh']} kWh")

    k4, k5 = st.columns(2)
    with k4:
        st.metric("Projected Score Gain", f"+{sim['estimated_score_improvement']}")
    with k5:
        st.metric(
            "Anomalies",
            f"{sim['simulated_metrics']['anomaly_count']}",
            delta=f"{sim['simulated_metrics']['anomaly_count'] - sim['original_metrics']['anomaly_count']}"
        )

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Current",
        x=["Avg Consumption", "Max Consumption", "Min Consumption", "Std Dev"],
        y=[
            sim["original_metrics"]["avg_consumption"],
            sim["original_metrics"]["max_consumption"],
            sim["original_metrics"]["min_consumption"],
            sim["original_metrics"]["std_dev"],
        ],
        marker_color="#0984E3"
    ))
    fig.add_trace(go.Bar(
        name="Simulated",
        x=["Avg Consumption", "Max Consumption", "Min Consumption", "Std Dev"],
        y=[
            sim["simulated_metrics"]["avg_consumption"],
            sim["simulated_metrics"]["max_consumption"],
            sim["simulated_metrics"]["min_consumption"],
            sim["simulated_metrics"]["std_dev"],
        ],
        marker_color="#00B894"
    ))
    fig.update_layout(
        barmode="group",
        height=350,
        template="plotly_white",
        title="Current vs Simulated Metrics",
        margin=dict(t=50, b=40),
    )
    st.plotly_chart(fig, width="stretch", key="simulator_chart")

    return sim