import os
import time
import random
import pandas as pd
from datetime import datetime
from src.services.google_sheets import DatabaseManager
from dotenv import load_dotenv

load_dotenv()

class TimeTravelSimulator:
    def __init__(self, csv_path, db_manager: DatabaseManager):
        self.csv_path = csv_path
        self.db = db_manager
        self.df = pd.read_csv(csv_path)
        self.pointer = 0
        self.simulation_speed = int(os.getenv("SIMULATION_SPEED", 5))
        self.is_running = False

    def reset_system(self):
        """Clear sheets and reset the CSV pointer."""
        print("Resetting system: Clearing sheets and resetting pointer.")
        self.db.clear_tab("Active_Stream")
        self.db.clear_tab("Audit_Ledger")
        self.pointer = 0

    def start_streaming(self):
        """Release one hour of data every N seconds to the Active_Stream sheet."""
        print(f"Starting simulation streamer (Speed: {self.simulation_speed}s per hour).")
        self.is_running = True
        
        while self.is_running and self.pointer < len(self.df):
            row = self.df.iloc[self.pointer].to_dict()
            
            # Inject synthetic faults
            is_faulty = False
            consumption = float(row["consumption_kwh"])
            if random.random() < 0.15: # 15% chance of a fault
                print(f"Injecting synthetic fault for {row['building_id']} at {row['date']}")
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
            time.sleep(self.simulation_speed)

    def stop_streaming(self):
        self.is_running = False
        print("Simulation streamer stopped.")
