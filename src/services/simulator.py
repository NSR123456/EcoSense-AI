import os
import time
import pandas as pd
from datetime import datetime
from src.services.database import DatabaseManager
from dotenv import load_dotenv

load_dotenv()

class EnergySimulator:
    def __init__(self, csv_path=None, db_manager: DatabaseManager = None, focus_building=None):
        self.csv_path = csv_path or os.getenv("SIMULATION_CSV_PATH", "data/sample/building_energy_multi.csv")
        self.db = db_manager
        self.focus_building = focus_building
        self.df = pd.read_csv(self.csv_path)
        # Filter data if focus_building is specified and not "All"
        if self.focus_building and self.focus_building != "All":
            self.df = self.df[self.df['building_id'] == self.focus_building].copy()
        self.pointer = 0
        self.simulation_speed = int(os.getenv("SIMULATION_SPEED", 2))
        self.is_running = False

    def reset_system(self):
        """Clear sheets and reset the CSV pointer."""
        print("Resetting system: Clearing sheets and resetting pointer.")
        if self.db:
            self.db.clear_tab("Active_Stream")
            self.db.clear_tab("Audit_Ledger")
        self.pointer = 0

    def start_stream(self, on_update=None):
        """Release one hour of data every N seconds to the Active_Stream sheet."""
        print(f"Starting simulation streamer (Speed: {self.simulation_speed}s per hour).")
        self.is_running = True

        while self.is_running and self.pointer < len(self.df):
            row = self.df.iloc[self.pointer].to_dict()

            # Inject synthetic faults every 5th simulated hour
            is_faulty = False
            consumption = float(row["consumption_kwh"])
            if (self.pointer + 1) % 5 == 0:
                print(f"Injecting synthetic fault for {row['building_id']} at {row['date']} (cycle {self.pointer + 1})")
                consumption *= 1.5
                is_faulty = True

            payload = [
                row["building_id"],
                row["date"],
                round(consumption, 2),
                "YES" if is_faulty else "NO"
            ]

            try:
                print(f"Streaming data point: {payload}")
                self.db.write_rows("Active_Stream", [payload])
            except Exception as e:
                print(f"Simulator error during write: {e}. Retrying in 5s.")
                time.sleep(5)
                continue

            self.pointer += 1
            if on_update:
                try:
                    on_update(payload)
                except Exception as callback_error:
                    print(f"Error in on_update callback: {callback_error}")
            time.sleep(self.simulation_speed)

    def stop_stream(self):
        self.is_running = False
        print("Simulation streamer stopped.")

    # Deprecated alias for backwards compatibility
    def start_streaming(self):
        return self.start_stream()

    def stop_streaming(self):
        return self.stop_stream()
