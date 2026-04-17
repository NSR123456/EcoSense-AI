"""Root launcher for EcoSense AI autonomous energy audit framework."""

import threading
from src.services.simulator import EnergySimulator
from src.services.agents import AgentTeam
from src.services.google_sheets import DatabaseManager
from src.services.telegram_bot import TelegramBot


def main() -> None:
    """Start the EcoSense AI system."""
    print("Starting EcoSense AI autonomous energy audit framework...")

    database = DatabaseManager()
    database.initialize_workspace()
    database.seed_campus_schedule()

    simulator = EnergySimulator(db_manager=database)
    agents = AgentTeam(db_manager=database)
    telegram_bot = TelegramBot(db_manager=database, simulator=simulator, agent_team=agents)

    # Run the simulator in its own thread so Telegram polling can start concurrently.
    sim_thread = threading.Thread(target=simulator.start_stream, args=(agents.handle_stream_event,), daemon=True)
    sim_thread.start()

    print("EcoSense AI is running. Use Telegram commands to query status.")
    telegram_bot.run_bot()


if __name__ == "__main__":
    main()
