import os
import random
import time
from pathlib import Path
import pandas as pd
from datetime import datetime
from src.services.database import DatabaseManager
from src.ingestion.data_loader import load_dataset, _normalize_energy_frame
from dotenv import load_dotenv

load_dotenv()

class EnergySimulator:
    def __init__(self, csv_path=None, db_manager=None, focus_building=None):
        raw_path = csv_path or os.getenv("SIMULATION_CSV_PATH", "data/sample/ecosense_train_hourly.csv")
        self.csv_path = Path(raw_path)
        if not self.csv_path.is_absolute():
            self.csv_path = Path(__file__).resolve().parents[2] / self.csv_path
        self.db = db_manager
        self.focus_building = str(focus_building).strip() if focus_building not in (None, "", "All") else focus_building
        self.df = self._load_data()
        self.df = self._normalize_frame(self.df)
        # Filter data if focus_building is specified and not "All"
        if self.focus_building and self.focus_building != "All":
            self.df = self.df[self.df['building_id'] == self.focus_building].copy()
        self.pointer = 0
        self.simulation_speed = int(os.getenv("SIMULATION_SPEED", 2))
        self.fault_probability = float(os.getenv("FAULT_PROBABILITY", 0.15))
        self.is_running = False

    def _load_data(self) -> pd.DataFrame:
        # Prefer normalized dataset loading for the simulator.
        if self.csv_path and Path(self.csv_path).exists():
            try:
                df = pd.read_csv(self.csv_path)
                normalized = _normalize_energy_frame(df)
                if not normalized.empty:
                    return normalized
            except Exception as exc:
                print(f"Simulator failed to normalize {self.csv_path}: {exc}")

        df = load_dataset()
        if df.empty:
            print("Simulator could not load any energy data for streaming.")
        return df

    def _normalize_frame(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame(columns=["building_id", "date", "consumption_kwh"])

        normalized = df.copy()
        if "building_id" in normalized.columns:
            normalized["building_id"] = normalized["building_id"].astype(str).str.strip()
        if "date" not in normalized.columns and "timestamp" in normalized.columns:
            normalized = normalized.rename(columns={"timestamp": "date"})
        if "consumption_kwh" not in normalized.columns and "meter_reading" in normalized.columns:
            normalized = normalized.rename(columns={"meter_reading": "consumption_kwh"})
        return normalized

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

            # Inject synthetic faults probabilistically rather than rigidly every Nth point.
            is_faulty = False
            consumption = float(row["consumption_kwh"])
            if self.fault_probability > 0 and random.random() < self.fault_probability:
                print(f"Injecting synthetic fault for {row['building_id']} at {row['date']} (prob={self.fault_probability})")
                consumption *= 1.5
                is_faulty = True

            payload = [
                row["building_id"],
                # Ensure date/timestamp is JSON-serializable (ISO string)
                (row["date"].to_pydatetime().isoformat() if hasattr(row.get("date"), "to_pydatetime") else
                 (row.get("date").isoformat() if hasattr(row.get("date"), "isoformat") else str(row.get("date")))),
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
