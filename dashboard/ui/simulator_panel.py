import time
import pandas as pd
from dashboard.building_store import load_energy_dataset

class EnergySimulator:
    def __init__(self, db_manager):
        self.db = db_manager
        self.is_running = False

    def start_stream(self, on_update_callback):
        self.is_running = True
        df = load_energy_dataset()
        
        # Stream data row by row
        for _, row in df.iterrows():
            if not self.is_running: break
            
            payload = row.to_dict()
            # 1. Sync to Google Sheets
            self.db.write_rows("Active_Stream", [list(payload.values())])
            
            # 2. Run Agents & Telegram via callback
            on_update_callback(payload)
            
            time.sleep(5) # Simulation speed

    def stop_stream(self):
        self.is_running = False


def render_simulator_panel(status: str | None = None):
    import streamlit as st

    st.subheader("Simulation Panel")
    st.write("This panel is a placeholder for simulator controls and status.")
    if status:
        st.info(f"Simulation status: {status}")
    else:
        st.info("Simulation status is not available.")

    st.caption("Use the main dashboard controls to start, stop, and reset the live simulation.")