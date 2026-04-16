import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.services.google_sheets import DatabaseManager
from datetime import datetime

def render_v2_realtime_ui():
    st.markdown("## ⚡ EcoSense v2: Real-time Multi-Agent Audit")
    
    col_header, col_refresh = st.columns([4, 1])
    with col_header:
        st.info("Streaming live energy data from Google Sheets and monitoring with autonomous agents.")
    with col_refresh:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()

    db = DatabaseManager()
    
    # --- 1. DATA STREAM VIEW ---
    st.subheader("📊 Live Energy Stream (Active_Stream)")
    stream_data = db.read_tab("Active_Stream")
    
    if not stream_data:
        st.warning("No data found in Active_Stream. Ensure the simulator is running.")
        return

    df_stream = pd.DataFrame(stream_data)
    df_stream["consumption_kwh"] = pd.to_numeric(df_stream["consumption_kwh"], errors="coerce")
    df_stream["date"] = pd.to_datetime(df_stream["date"])
    
    # Live Chart
    fig = go.Figure()
    # Regular data
    normal_data = df_stream[df_stream["is_faulty"] == "NO"]
    fig.add_trace(go.Scatter(
        x=normal_data["date"], y=normal_data["consumption_kwh"],
        mode='lines+markers', name='Normal Usage',
        line=dict(color='#059669', width=2)
    ))
    # Faulty data
    faulty_data = df_stream[df_stream["is_faulty"] == "YES"]
    if not faulty_data.empty:
        fig.add_trace(go.Scatter(
            x=faulty_data["date"], y=faulty_data["consumption_kwh"],
            mode='markers', name='Synthetic Fault',
            marker=dict(color='#ef4444', size=10, symbol='x')
        ))
    
    fig.update_layout(
        title="Real-time Consumption vs Anomaly Detection",
        xaxis_title="Timeline",
        yaxis_title="kWh",
        template="plotly_white",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- 2. AGENT INSIGHTS (Audit Ledger) ---
    st.divider()
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("📜 Agent Audit Ledger")
        ledger_data = db.read_tab("Audit_Ledger")
        if ledger_data:
            df_ledger = pd.DataFrame(ledger_data)
            st.dataframe(df_ledger.sort_values("timestamp", ascending=False), use_container_width=True)
        else:
            st.info("No audit logs yet. The agents are still monitoring...")

    with c2:
        st.subheader("📅 Campus Schedule")
        schedule_data = db.read_tab("Campus_Schedule")
        if schedule_data:
            df_schedule = pd.DataFrame(schedule_data)
            st.table(df_schedule[["event_name", "date", "start_time"]])
        else:
            st.info("Schedule is empty.")

    # --- 3. SYSTEM CONTROLS ---
    st.divider()
    st.subheader("⚙️ Simulation Controls")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Full System Reset", help="Clears Google Sheet logs and resets the data pointer."):
            # We can't directly trigger the reset in the background process easily here
            # but we can clear the sheets.
            db.clear_tab("Active_Stream")
            db.clear_tab("Audit_Ledger")
            st.success("Sheets cleared! Please restart the script to reset the data pointer.")
    with col2:
        st.caption("To start the simulation, run: `python scripts/ecosense_v2.py` in your terminal.")
