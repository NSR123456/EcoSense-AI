import os
import sys
import types
import unittest
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.services.simulator import EnergySimulator
from src.services.telegram_bot import TelegramBot


class FakeDatabase:
    def __init__(self):
        self.rows = []
        self.audit = []

    def write_rows(self, tab_name, rows):
        if tab_name == "Active_Stream":
            self.rows.extend(rows)
        elif tab_name == "Audit_Ledger":
            self.audit.extend(rows)

    def read_tab(self, tab_name):
        if tab_name == "Active_Stream":
            return [
                {
                    "building_id": row[0],
                    "date": row[1],
                    "consumption_kwh": row[2],
                    "is_faulty": row[3],
                }
                for row in self.rows
            ]
        if tab_name == "Audit_Ledger":
            return list(self.audit)
        return []

    def clear_tab(self, tab_name):
        if tab_name == "Active_Stream":
            self.rows = []
        elif tab_name == "Audit_Ledger":
            self.audit = []


class FakeTelegramBot(TelegramBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sent_messages = []

    def is_configured(self):
        return True

    def send_alert(self, message):
        self.sent_messages.append(message)
        return True


class TestLiveDemoIntegration(unittest.TestCase):
    def test_simulator_writes_rows_and_telegram_alerts(self):
        db = FakeDatabase()
        telegram_bot = FakeTelegramBot(db_manager=db)
        simulator = EnergySimulator(db_manager=db, focus_building="141")
        simulator.simulation_speed = 0
        simulator.fault_probability = 0.0

        def on_update(payload):
            telegram_bot.send_alert(f"stream:{payload[0]}:{payload[2]}")
            simulator.stop_stream()

        simulator.start_stream(on_update=on_update)

        self.assertGreater(len(db.rows), 0)
        self.assertEqual(db.rows[0][0], "141")
        self.assertIn("stream:141", telegram_bot.sent_messages[0])


if __name__ == "__main__":
    unittest.main()
