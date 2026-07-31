"""
Forecasting & Predictive Maintenance UI Panel

Visualizes:
  1. Prophet-based equipment failure forecasts (predictive_model.py)
  2. Isolation Forest anomaly timelines (detect_anomalies_with_ml in analytics.py)
  3. Per-sensor maintenance schedule with priority tiers

Used by the dashboard front-end when a user runs analysis on a building.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _priority_color(priority: str) -> str:
    return {
        "critical": "#dc2626",
        "high":     "#ea580c",
        "medium":   "#d97706",
        "low":      "#16a34a",
    }.get(str(priority).lower(), "#475569")


def _priority_badge(priority: str) -> str:
    color = _priority_color(priority)
    p = str(priority).upper()
    return (
        f'<span style="background:{color};color:white;padding:2px 8px;'
        f'border-radius:10px;font-size:11px;font-weight:600;">{p}</span>'
    )


def _build_synthetic_sensor_history(
    stream_df: pd.DataFrame,
    selected_building: str,
) -> dict[str, pd.DataFrame]:
    """Create plausible per-sensor time-series from the Active_Stream.

    We don't require a real multi-sensor table to be present. Instead we
    derive three virtual equipment sensors from the building's consumption
    profile so the forecasting UI has content to render immediately after
    the CSV Live Demo starts. This mirrors how the orchestrator groups
    readings by ``sensor_type`` in ``AnalystAgent``.
    """

    if stream_df is None or stream_df.empty:
        return {}

    df = stream_df.copy()
    if "consumption_kwh" not in df.columns or "date" not in df.columns:
        return {}

    if selected_building and selected_building != "All":
        df = df[df.get("building_id", pd.Series(dtype=str)).astype(str) == str(selected_building)]
        if df.empty:
            return {}

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date")
    df["consumption_kwh"] = pd.to_numeric(df["consumption_kwh"], errors="coerce").ffill().fillna(0.0)

    base = df["consumption_kwh"].astype(float)
    t = df["date"]

    synthetic = {
        "energy_meter": pd.DataFrame({"timestamp": t, "value": base.values}),
        "hvac_temp":    pd.DataFrame({"timestamp": t, "value": (20.0 + 0.03 * base.values + (base.values - base.mean()) * 0.25).clip(15, 42)}),
        "vibration":    pd.DataFrame({"timestamp": t, "value": (0.15 + 0.0015 * base.values + (base.values.rank(pct=True) - 0.5) * 0.4).clip(0.01, 3.0)}),
    }
    return synthetic


# ---------------------------------------------------------------------------
# Anomaly timeline (analytics.py -> detect_anomalies_with_ml)
# ---------------------------------------------------------------------------

def render_anomaly_timeline(sensor_histories: dict[str, pd.DataFrame]) -> None:
    from src.core.analytics import detect_anomalies_with_ml

    st.markdown("#### 🕵️ Anomaly Timeline (Isolation Forest + Z-score guard)")
    st.caption(
        "Runs ``detect_anomalies_with_ml`` from ``analytics.py`` per sensor. "
        "Green = normal, Red = flagged anomaly, shaded region = 3σ safety band."
    )

    if not sensor_histories:
        st.info("No stream history yet. Start the Live Demo to populate the anomaly timeline.")
        return

    sensor_names = list(sensor_histories.keys())
    fig = make_subplots(
        rows=len(sensor_names),
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        subplot_titles=[s.replace("_", " ").title() for s in sensor_names],
    )

    for row_idx, sname in enumerate(sensor_names, start=1):
        sdf = sensor_histories[sname].copy().sort_values("timestamp")
        values = sdf["value"].astype(float).tolist()
        ts = sdf["timestamp"].tolist()

        try:
            labels = detect_anomalies_with_ml(values, contamination=0.04, window_size=min(12, max(3, len(values) // 4)))
        except Exception:
            labels = [0] * len(values)

        normal_x, normal_y, anom_x, anom_y = [], [], [], []
        for t, v, lbl in zip(ts, values, labels):
            if int(lbl) == 1:
                anom_x.append(t)
                anom_y.append(v)
            else:
                normal_x.append(t)
                normal_y.append(v)

        # Safety band
        y_mean = pd.Series(values).mean()
        y_std = max(pd.Series(values).std(), 1e-6)
        upper = [y_mean + 3 * y_std] * len(ts)
        lower = [max(0.0, y_mean - 3 * y_std)] * len(ts)

        fig.add_trace(
            go.Scatter(
                x=list(ts) + list(reversed(ts)),
                y=upper + list(reversed(lower)),
                fill="toself",
                fillcolor="rgba(59,130,246,0.08)",
                line=dict(width=0),
                showlegend=False,
                hoverinfo="skip",
                name="3σ band",
            ),
            row=row_idx, col=1,
        )
        fig.add_trace(
            go.Scatter(x=normal_x, y=normal_y, mode="lines+markers",
                       marker=dict(size=4, color="#10b981"),
                       line=dict(color="#059669", width=1.2),
                       name="Normal", showlegend=(row_idx == 1)),
            row=row_idx, col=1,
        )
        if anom_x:
            fig.add_trace(
                go.Scatter(x=anom_x, y=anom_y, mode="markers",
                           marker=dict(size=9, color="#ef4444", symbol="x",
                                       line=dict(width=1, color="#7f1d1d")),
                           name="Anomaly", showlegend=(row_idx == 1)),
                row=row_idx, col=1,
            )
        fig.update_yaxes(title_text="Value", row=row_idx, col=1)

    fig.update_layout(
        height=140 + 160 * len(sensor_names),
        template="plotly_white",
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(title_text="Timestamp", row=len(sensor_names), col=1)
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Prophet forecasting + maintenance schedule (predictive_model.py)
# ---------------------------------------------------------------------------

def _train_and_predict(sensor_key: str, sdf: pd.DataFrame, days_ahead: int = 7) -> dict[str, Any]:
    """Wrap PredictiveMaintenanceModel.train_model + predict_failure."""
    from src.models.predictive_model import PredictiveMaintenanceModel

    if "predictive_models" not in st.session_state:
        st.session_state.predictive_models = {}

    model = st.session_state.predictive_models.get(sensor_key)
    if model is None:
        model = PredictiveMaintenanceModel()
        st.session_state.predictive_models[sensor_key] = model

    readings = [
        {"timestamp": pd.Timestamp(t).to_pydatetime() if not isinstance(t, datetime) else t,
         "value": float(v)}
        for t, v in zip(sdf["timestamp"].tolist(), sdf["value"].tolist())
    ]

    status = model.train_model(sensor_key, readings)
    prediction = model.predict_failure(sensor_key, days_ahead=days_ahead)
    schedule = model.get_maintenance_schedule(sensor_key)

    # Extract forecast series for plotting
    forecast_df = prediction.get("forecast")
    failure_threshold = prediction.get("threshold")

    history_df = sdf.copy()
    history_df["timestamp"] = pd.to_datetime(history_df["timestamp"])

    chart_df = None
    if forecast_df is not None and not forecast_df.empty:
        fdf = forecast_df.copy()
        if "ds" in fdf.columns and "yhat" in fdf.columns:
            chart_df = pd.DataFrame({
                "timestamp": pd.to_datetime(fdf["ds"]),
                "yhat":      fdf["yhat"].astype(float),
                "yhat_upper": fdf.get("yhat_upper", fdf["yhat"]).astype(float),
                "yhat_lower": fdf.get("yhat_lower", fdf["yhat"]).astype(float),
            })

    return {
        "training_status": status,
        "prediction":      prediction,
        "schedule":        schedule,
        "chart_df":        chart_df,
        "history_df":      history_df,
        "threshold":       failure_threshold,
    }


def render_forecast_panel(
    sensor_histories: dict[str, pd.DataFrame],
    days_ahead: int = 7,
) -> dict[str, Any]:
    st.markdown("#### 🔮 Prophet Failure Forecast & Maintenance Schedule")
    st.caption(
        "Calls ``PredictiveMaintenanceModel.train_model`` then ``predict_failure`` from ``predictive_model.py``. "
        "Each sensor is forecasted independently with daily/weekly/yearly seasonality enabled."
    )

    if not sensor_histories:
        st.info("No stream data yet. Start the Live Demo to enable failure forecasting.")
        return {}

    sensor_keys = list(sensor_histories.keys())
    tabs = st.tabs([s.replace("_", " ").title() for s in sensor_keys])

    all_schedules: list[dict[str, Any]] = []
    per_sensor_results: dict[str, Any] = {}

    for tab, sname in zip(tabs, sensor_keys):
        with tab:
            sdf = sensor_histories[sname]
            if len(sdf) < 10:
                st.warning(f"Not enough history for {sname} ({len(sdf)} points). Prophet needs ≥ 50 for best results; using statistical fallback.")
            result = _train_and_predict(sname, sdf, days_ahead=days_ahead)
            per_sensor_results[sname] = result

            pred = result["prediction"]
            schedule = result["schedule"]
            chart_df = result["chart_df"]
            history_df = result["history_df"]
            threshold = result["threshold"]

            # ---- KPIs ----
            k1, k2, k3 = st.columns(3)
            with k1:
                d2f = pred.get("days_to_failure")
                if d2f is None:
                    st.metric("Days to Failure", "No failure", delta="within forecast")
                else:
                    st.metric(
                        "Days to Failure",
                        f"{int(round(float(d2f)))} d",
                        delta=f"Confidence {int(float(pred.get('confidence_score', 0)) * 100)}%",
                        delta_color="inverse",
                    )
            with k2:
                fail_ts = pred.get("predicted_failure_time")
                if fail_ts:
                    if isinstance(fail_ts, str):
                        try:
                            fail_ts = pd.Timestamp(fail_ts).to_pydatetime()
                        except Exception:
                            pass
                    display = fail_ts.strftime("%Y-%m-%d %H:%M") if hasattr(fail_ts, "strftime") else str(fail_ts)
                else:
                    display = "Not predicted"
                st.metric("Predicted Failure At", display)
            with k3:
                label = schedule.get("priority", "low")
                st.markdown(
                    f"<div style='padding-top:14px'>Priority: {_priority_badge(label)} &nbsp; "
                    f"<b>{schedule.get('action', 'routine_check').replace('_', ' ').title()}</b></div>",
                    unsafe_allow_html=True,
                )

            # ---- Forecast chart ----
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(x=history_df["timestamp"], y=history_df["value"],
                           mode="lines+markers", name="History",
                           line=dict(color="#334155", width=1.5),
                           marker=dict(size=4)),
            )
            if chart_df is not None:
                fig.add_trace(
                    go.Scatter(
                        x=list(chart_df["timestamp"]) + list(reversed(chart_df["timestamp"])),
                        y=list(chart_df["yhat_upper"]) + list(reversed(chart_df["yhat_lower"])),
                        fill="toself",
                        fillcolor="rgba(34,197,94,0.12)",
                        line=dict(width=0),
                        showlegend=False,
                        name="Uncertainty",
                    )
                )
                fig.add_trace(
                    go.Scatter(x=chart_df["timestamp"], y=chart_df["yhat"],
                               mode="lines", name="Prophet forecast",
                               line=dict(color="#16a34a", width=2, dash="dot")),
                )
            if threshold is not None:
                fig.add_hline(y=float(threshold), line_dash="dash",
                              line_color="#dc2626", annotation_text="Failure threshold",
                              line_width=1.2)
            fig.update_layout(
                height=360,
                template="plotly_white",
                margin=dict(l=10, r=10, t=30, b=10),
                xaxis_title="Timestamp",
                yaxis_title=sname.replace("_", " ").title(),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig, use_container_width=True)

            # Training status note
            status = result["training_status"] or {}
            msg = status.get("message", "")
            mode = status.get("mode", "")
            if msg:
                st.caption(f"Training note — {mode}: {msg}")

            schedule_row = {
                "sensor":     sname,
                "priority":   schedule.get("priority", "low"),
                "action":     schedule.get("action", "routine_check"),
                "scheduled":  schedule.get("scheduled_date"),
                "reason":     pred.get("failure_reason") or schedule.get("action", ""),
                "confidence": int(float(pred.get("confidence_score", 0)) * 100),
            }
            all_schedules.append(schedule_row)

    # ---------- Combined maintenance schedule ----------
    st.markdown("---")
    st.markdown("#### 🛠️ Combined Maintenance Schedule")
    if not all_schedules:
        st.info("No maintenance items to display.")
        return per_sensor_results

    sched_df = pd.DataFrame(all_schedules)
    priority_map = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sched_df["_priority_rank"] = sched_df["priority"].apply(
        lambda p: priority_map.get(str(p).lower(), 9)
    )
    sched_df = sched_df.sort_values(
        by=["_priority_rank", "scheduled", "sensor"],
        ascending=[True, True, True],
    ).drop(columns=["_priority_rank"])

    sched_df["priority"] = sched_df["priority"].apply(_priority_badge)
    sched_df["action"] = sched_df["action"].astype(str).str.replace("_", " ").str.title()

    formatted = sched_df.rename(columns={
        "sensor": "Sensor",
        "priority": "Priority",
        "action": "Action",
        "scheduled": "Scheduled On",
        "reason": "Reason",
        "confidence": "Confidence %",
    })
    st.write(formatted.to_html(escape=False, index=False), unsafe_allow_html=True)

    # Critical alert banner
    critical_rows = [r for r in all_schedules if str(r["priority"]).lower() == "critical"]
    if critical_rows:
        sensors = ", ".join([r["sensor"].replace("_", " ").title() for r in critical_rows])
        st.error(
            f"🚨 **CRITICAL MAINTENANCE ALERT**: Equipment requiring *immediate* action — {sensors}. "
            "See the schedule above for failure timestamps. Log a work order today and notify on-call via Telegram."
        )
    elif any(str(r["priority"]).lower() == "high" for r in all_schedules):
        urgent_sensors = ", ".join([r["sensor"].replace("_", " ").title() for r in all_schedules if str(r["priority"]).lower() == "high"])
        st.warning(f"⚠️ **High-Priority Maintenance**: {urgent_sensors}. Schedule before the predicted failure window.")

    return per_sensor_results


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------

def render_forecasting_suite(
    stream_data: list[dict] | None,
    selected_building: str | None = None,
    days_ahead: int = 7,
) -> dict[str, Any]:
    """Render the full forecasting + anomaly panel.

    Parameters
    ----------
    stream_data : list[dict]
        Rows from the Active_Stream sheet (building_id, date, consumption_kwh).
    selected_building : str
        The building focus from the sidebar ("All" = no filter).
    days_ahead : int
        How many days into the future Prophet should predict.

    Returns
    -------
    dict
        ``{sensor: {training_status, prediction, schedule, chart_df, history_df, threshold}}``
    """

    st.subheader("📈 Predictive Forecasting & Equipment Health")
    st.markdown(
        "Brings the backend forecasting stack (**Prophet failure predictions**, "
        "**Isolation Forest anomaly detection**, **priority-tiered maintenance schedule**) "
        "directly into the operations room. Both engines use the exact source modules used by "
        "``AnalystAgent`` in ``agents/orchestrator.py``."
    )

    stream_df = pd.DataFrame(stream_data or [])
    histories = _build_synthetic_sensor_history(stream_df, selected_building or "All")
    render_anomaly_timeline(histories)
    st.markdown("---")
    results = render_forecast_panel(histories, days_ahead=days_ahead)
    return results
