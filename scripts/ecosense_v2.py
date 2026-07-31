import os
import sys
import time
import threading
from dotenv import load_dotenv

# Add project root to sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.services.database import DatabaseManager
from src.services.simulator import EnergySimulator
from src.services.agents import AgentTeam
from src.services.telegram_bot import TelegramBot

load_dotenv()

def _run_stream_event(event_key: str, payload: list, agent_team: AgentTeam, telegram_bot: TelegramBot) -> None:
    result = agent_team.handle_stream_event(payload)
    if not result:
        return

    context = result.get("context", {})
    if context.get("status") != "true_waste":
        return

    anomaly = result.get("anomaly", {})
    recommendation = result.get("recommendation", {}) or {}
    alert_msg = (
        f"EcoSense Waste Alert\n"
        f"Building: {anomaly.get('building_id', 'unknown')}\n"
        f"Date: {anomaly.get('date', 'unknown')}\n"
        f"Consumption: {anomaly.get('consumption_kwh', 'unknown')} kWh\n"
        f"Baseline: {anomaly.get('baseline', 'unknown')} kWh\n"
        f"Deviation: {anomaly.get('deviation_pct', 'unknown')}%\n"
        f"Type: {recommendation.get('type', 'True Waste')}\n"
        f"Recommendation: {recommendation.get('recommendation', 'Investigate and correct the source of wastage.') }"
    )
    telegram_bot.send_alert(alert_msg)


def main():
    # 1. Initialize DatabaseManager
    db = DatabaseManager()

    # 2. Check/Create Sheets Tabs
    print("Initializing Google Sheet Workspace...")
    db.initialize_workspace()

    # 3. Seed Campus_Schedule
    db.seed_campus_schedule()

    # 4. Initialize Components
    csv_path = os.getenv(
        "SIMULATION_CSV_PATH",
        os.path.join(ROOT, "data", "sample", "ecosense_train_hourly.csv"),
    )
    simulator = EnergySimulator(csv_path, db)
    agent_team = AgentTeam(db)
    telegram_bot = TelegramBot(db, simulator, agent_team)

    processed_events = set()

    def on_update(payload):
        event_key = f"{payload[0]}|{payload[1]}|{payload[2]}"
        if event_key in processed_events:
            return
        processed_events.add(event_key)
        _run_stream_event(event_key, payload, agent_team, telegram_bot)

    # 5. Start Simulator in a separate thread
    sim_thread = threading.Thread(target=simulator.start_stream, args=(on_update,), daemon=True)
    sim_thread.start()

    # 6. Start Telegram Bot (Main Thread)
    print("EcoSense AI (v2) Initialized Successfully. Live stream running.")
    telegram_bot.run_bot()

if __name__ == "__main__":
    main()
