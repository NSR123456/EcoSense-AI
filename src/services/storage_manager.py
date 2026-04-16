import sqlite3
import os
import json

class StorageManager:
    def __init__(self, db_path=None):
        if db_path is None:
            # Use absolute path to avoid context issues between backend/frontend
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.db_path = os.path.join(base_dir, "data", "digital_twin.db")
        else:
            self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS load_states (
                    floor TEXT,
                    load_name TEXT,
                    active INTEGER,
                    kwh REAL,
                    hours INTEGER,
                    PRIMARY KEY (floor, load_name)
                )
            """)
            conn.commit()

    def initialize_defaults(self, default_loads):
        """Seed the database with default loads if empty."""
        with sqlite3.connect(self.db_path) as conn:
            # Check if empty
            count = conn.execute("SELECT COUNT(*) FROM load_states").fetchone()[0]
            if count == 0:
                print("Seeding digital twin database with defaults...")
                for floor, loads in default_loads.items():
                    for name, data in loads.items():
                        conn.execute(
                            "INSERT INTO load_states (floor, load_name, active, kwh, hours) VALUES (?, ?, ?, ?, ?)",
                            (floor, name, 1 if data["active"] else 0, data["kwh"], data["hours"])
                        )
                conn.commit()

    def update_load(self, floor, load_name, active, hours):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE load_states SET active = ?, hours = ? WHERE floor = ? AND load_name = ?",
                (1 if active else 0, hours, floor, load_name)
            )
            affected = cursor.rowcount
            conn.commit()
            return affected > 0

    def get_all_loads(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT floor, load_name, active, kwh, hours FROM load_states")
            rows = cursor.fetchall()
            
            # Reconstruct the nested dictionary format used in the app
            load_dict = {}
            for floor, name, active, kwh, hours in rows:
                if floor not in load_dict:
                    load_dict[floor] = {}
                load_dict[floor][name] = {
                    "active": bool(active),
                    "kwh": kwh,
                    "hours": hours
                }
            return load_dict

    def reset_to_defaults(self, default_loads):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM load_states")
            conn.commit()
        self.initialize_defaults(default_loads)
