import html

import streamlit as st
import plotly.graph_objects as go
import pandas as pd


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