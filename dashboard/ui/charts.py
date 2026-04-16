import html
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np


def render_consumption_chart(df: pd.DataFrame, building_id: str, key: str = "consumption_chart"):
    if df.empty:
        st.info("No building data.")
        return

    bdf = df.copy()
    if "date" in bdf.columns:
        bdf["date"] = pd.to_datetime(bdf["date"])
        bdf = bdf.sort_values("date")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=bdf["date"],
        y=bdf["consumption_kwh"],
        mode="lines+markers",
        name="Daily Consumption",
        line=dict(color="#0ea5e9", width=2.4),
        marker=dict(size=5, color="#ffffff", line=dict(width=1, color="#0ea5e9")),
    ))

    if len(bdf) >= 7:
        rolling = bdf["consumption_kwh"].rolling(7).mean()
        fig.add_trace(go.Scatter(
            x=bdf["date"],
            y=rolling,
            mode="lines",
            name="7-day Rolling Avg",
            line=dict(color="#f97316", width=3),
        ))

    fig.update_layout(
        title=None,
        template="plotly_white",
        height=350,
        margin=dict(t=28, b=40, l=52, r=24),
        xaxis_title="Date",
        yaxis_title="kWh",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#f0fdf4",
        font=dict(family="DM Sans, system-ui, sans-serif", color="#0f172a"),
    )
    st.markdown(
        f'<div class="ecosense-chart-title-bar">Consumption trend — {html.escape(str(building_id))}</div>',
        unsafe_allow_html=True,
    )
    st.plotly_chart(fig, width="stretch", key=key)


def render_issue_bar(issues: list, key: str = "issue_bar"):
    if not issues:
        st.info("No issues.")
        return

    severity_map = {"low": 1, "medium": 2, "high": 3}
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[i["name"] for i in issues],
        y=[severity_map.get(i["severity"], 1) for i in issues],
        text=[f"{int(i['confidence']*100)}%" for i in issues],
        marker_color=[
            "#10b981" if i["severity"] == "low" else "#fbbf24" if i["severity"] == "medium" else "#ef4444"
            for i in issues
        ],
    ))
    fig.update_layout(
        title=dict(text="Detected issues — severity", font=dict(size=16, color="#0f172a")),
        template="plotly_white",
        height=320,
        margin=dict(t=50, b=40),
        yaxis=dict(tickvals=[1, 2, 3], ticktext=["Low", "Medium", "High"]),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#f0fdf4",
        font=dict(family="DM Sans, system-ui, sans-serif", color="#334155"),
    )
    st.plotly_chart(fig, width="stretch", key=key)


def render_simulator_metrics_comparison(sim_result: dict, key: str = "sim_metrics"):
    """
    Display before/after energy metrics in a comparison table format.
    """
    if not sim_result or "original_metrics" not in sim_result:
        return

    original = sim_result.get("original_metrics", {})
    simulated = sim_result.get("simulated_metrics", {})

    # Create comparison dataframe
    metrics_data = {
        "Metric": [
            "Avg Consumption",
            "Max Consumption",
            "Min Consumption",
            "Std Deviation",
            "Anomaly Count",
            "Variability Ratio"
        ],
        "Current (kWh)": [
            f"{original.get('avg_consumption', 0):.2f}",
            f"{original.get('max_consumption', 0):.2f}",
            f"{original.get('min_consumption', 0):.2f}",
            f"{original.get('std_dev', 0):.2f}",
            f"{original.get('anomaly_count', 0)}",
            f"{original.get('variability_ratio', 0):.3f}"
        ],
        "Optimized (kWh)": [
            f"{simulated.get('avg_consumption', 0):.2f}",
            f"{simulated.get('max_consumption', 0):.2f}",
            f"{simulated.get('min_consumption', 0):.2f}",
            f"{simulated.get('std_dev', 0):.2f}",
            f"{simulated.get('anomaly_count', 0)}",
            f"{simulated.get('variability_ratio', 0):.3f}"
        ],
        "Change (%)": [
            f"{-sim_result.get('estimated_savings_pct', 0):.1f}%",
            f"{((simulated.get('max_consumption', 0) - original.get('max_consumption', 0)) / max(original.get('max_consumption', 1), 1) * 100):.1f}%",
            f"{((simulated.get('min_consumption', 0) - original.get('min_consumption', 0)) / max(original.get('min_consumption', 1), 1) * 100):.1f}%",
            f"{((simulated.get('std_dev', 0) - original.get('std_dev', 0)) / max(original.get('std_dev', 1), 1) * 100):.1f}%",
            f"{int((simulated.get('anomaly_count', 0) - original.get('anomaly_count', 0)) / max(original.get('anomaly_count', 1), 1) * 100)}%",
            f"{((simulated.get('variability_ratio', 0) - original.get('variability_ratio', 0)) / max(original.get('variability_ratio', 1), 1) * 100):.1f}%"
        ]
    }

    df = pd.DataFrame(metrics_data)
    st.markdown("### 📊 Energy Metrics Comparison")
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_simulator_savings_chart(sim_result: dict, key: str = "sim_savings"):
    """
    Display savings projections and impact.
    """
    if not sim_result:
        return

    daily_savings = sim_result.get("estimated_savings_daily_kwh", 0)
    monthly_savings = sim_result.get("estimated_savings_monthly_kwh", 0)
    savings_pct = sim_result.get("estimated_savings_pct", 0)
    score_improvement = sim_result.get("estimated_score_improvement", 0)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Daily Savings",
            f"{daily_savings:.1f} kWh",
            delta=f"{savings_pct:.1f}%",
            delta_color="normal"
        )

    with col2:
        st.metric(
            "Monthly Savings",
            f"{monthly_savings:.1f} kWh",
            delta=f"${monthly_savings * 0.12:.2f}",
            delta_color="normal"
        )

    with col3:
        cost_savings = daily_savings * 0.12
        st.metric(
            "Daily Cost Reduction",
            f"${cost_savings:.2f}",
            delta="⚡ Energy",
            delta_color="normal"
        )

    with col4:
        st.metric(
            "Score Improvement",
            f"+{score_improvement}",
            delta="Sustainability",
            delta_color="normal"
        )


def render_consumption_before_after(sim_result: dict, historical_data: dict = None, key: str = "consumption_before_after"):
    """
    Display before/after consumption distribution comparison with line charts.
    """
    if not sim_result:
        return

    original = sim_result.get("original_metrics", {})
    simulated = sim_result.get("simulated_metrics", {})

    # Create synthetic consumption profiles for visualization
    avg_orig = original.get("avg_consumption", 100)
    max_orig = original.get("max_consumption", 150)
    min_orig = original.get("min_consumption", 50)

    avg_sim = simulated.get("avg_consumption", 100)
    max_sim = simulated.get("max_consumption", 150)
    min_sim = simulated.get("min_consumption", 50)

    # Create a 24-hour profile
    hours = list(range(24))
    
    # Current consumption profile (sine wave with peak and baseline)
    current_profile = [
        min_orig + (max_orig - min_orig) * 0.5 * (1 + np.sin((h - 6) * np.pi / 12))
        for h in hours
    ]

    # Optimized consumption profile
    optimized_profile = [
        min_sim + (max_sim - min_sim) * 0.5 * (1 + np.sin((h - 6) * np.pi / 12))
        for h in hours
    ]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=hours,
        y=current_profile,
        mode="lines+markers",
        name="Current Configuration",
        line=dict(color="#ef4444", width=3),
        fill="tozeroy"
    ))

    fig.add_trace(go.Scatter(
        x=hours,
        y=optimized_profile,
        mode="lines+markers",
        name="Optimized Configuration",
        line=dict(color="#10b981", width=3),
        fill="tozeroy"
    ))

    # Add average lines
    fig.add_hline(y=avg_orig, line_dash="dash", line_color="#fbbf24", 
                  annotation_text=f"Current Avg: {avg_orig:.1f} kWh",
                  annotation_position="right")
    fig.add_hline(y=avg_sim, line_dash="dash", line_color="#06b6d4",
                  annotation_text=f"Optimized Avg: {avg_sim:.1f} kWh",
                  annotation_position="right")

    fig.update_layout(
        title="📈 Energy Consumption Profile: 24-Hour Projection",
        xaxis_title="Hour of Day",
        yaxis_title="Power Consumption (kWh)",
        height=400,
        template="plotly_dark",
        hovermode="x unified",
        plot_bgcolor="#1e293b",
        paper_bgcolor="#0f172a",
        font=dict(family="DM Sans, system-ui, sans-serif", color="#e2e8f0"),
        margin=dict(t=80, b=60, l=60, r=60)
    )

    st.plotly_chart(fig, use_container_width=True, key=key)


def render_scenario_impact_bars(sim_result: dict, key: str = "scenario_impact"):
    """
    Display the impact breakdown of different optimization strategies.
    """
    if not sim_result or "scenario" not in sim_result:
        return

    scenario = sim_result.get("scenario", {})

    impact_data = {
        "Strategy": [
            "Peak Reduction",
            "Base Load Reduction",
            "Variability Reduction",
            "Efficiency Upgrade"
        ],
        "Impact Level (%)": [
            scenario.get("reduce_peak_pct", 0),
            scenario.get("reduce_base_load_pct", 0),
            scenario.get("reduce_variability_pct", 0),
            scenario.get("efficiency_upgrade_pct", 0)
        ],
        "Weight": ["35%", "30%", "20%", "40%"]
    }

    df_impact = pd.DataFrame(impact_data)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_impact["Strategy"],
        y=df_impact["Impact Level (%)"],
        marker=dict(
            color=["#3b82f6", "#8b5cf6", "#ec4899", "#f59e0b"],
            line=dict(color="white", width=2)
        ),
        text=[f"{v:.1f}%" for v in df_impact["Impact Level (%)"]],
        textposition="auto"
    ))

    fig.update_layout(
        title="🎯 Optimization Strategy Impact Breakdown",
        xaxis_title="Strategy Type",
        yaxis_title="Impact Level (%)",
        height=350,
        template="plotly_dark",
        plot_bgcolor="#1e293b",
        paper_bgcolor="#0f172a",
        font=dict(family="DM Sans, system-ui, sans-serif", color="#e2e8f0"),
        margin=dict(t=60, b=60, l=60, r=60),
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True, key=key)