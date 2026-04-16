import os
import sys
import time
import threading
from dotenv import load_dotenv

# Add project root to sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.services.google_sheets import DatabaseManager
from src.services.simulator import TimeTravelSimulator
from src.services.agents import AnalystAgent, PlannerAgent, RecommenderAgent
from src.services.telegram_bot import TelegramBot

load_dotenv()

def run_agent_loop(db, analyst, planner, recommender, telegram_bot):
    """Periodically check for anomalies and process them."""
    print("Agent Theatre: Monitoring Active_Stream for anomalies...")
    processed_dates = set()
    
    while True:
        try:
            anomaly = analyst.check_for_deviations()
            if anomaly and anomaly['date'] not in processed_dates:
                processed_dates.add(anomaly['date'])
                
                context = planner.cross_reference(anomaly)
                if context and context['status'] == "true_waste":
                    insight = recommender.get_recommendation(anomaly, context)
                    
                    if insight:
                        anomaly_type = insight.get("type", "True Waste")
                        recommendation = insight.get("recommendation", "N/A")
                        
                        # Notify via Telegram with dynamic insights
                        alert_msg = (
                            f"*Building:* {anomaly['building_id']}\n"
                            f"*Date:* {anomaly['date']}\n"
                            f"*Consumption:* {anomaly['consumption_kwh']} kWh\n"
                            f"*Anomaly Type:* {anomaly_type}\n"
                            f"*Recommendation:* {recommendation}"
                        )
                        telegram_bot.send_alert(alert_msg)
            
        except Exception as e:
            print(f"Agent Loop Error: {e}")
        
        time.sleep(10) # Check every 10 seconds

def main():
    # 1. Initialize DatabaseManager
    db = DatabaseManager()
    
    # 2. Check/Create Sheets Tabs
    print("Initializing Google Sheet Workspace...")
    db.initialize_workspace()
    
    # 3. Seed Campus_Schedule
    db.seed_campus_schedule()
    
    # 4. Initialize Components
    csv_path = os.path.join(ROOT, "data", "sample", "building_energy.csv")
    simulator = TimeTravelSimulator(csv_path, db)
    
    analyst = AnalystAgent(db)
    planner = PlannerAgent(db)
    recommender = RecommenderAgent(db)
    
    telegram_bot = TelegramBot(db, simulator)
    
    # 5. Start Simulator in a separate thread
    sim_thread = threading.Thread(target=simulator.start_streaming, daemon=True)
    sim_thread.start()
    
    # 6. Start Agent Loop in a separate thread
    agent_thread = threading.Thread(target=run_agent_loop, args=(db, analyst, planner, recommender, telegram_bot), daemon=True)
    agent_thread.start()
    
    # 7. Start Telegram Bot (Main Thread)
    print("EcoSense AI (v2) Initialized Successfully.")
    telegram_bot.run_bot()

if __name__ == "__main__":
    main()
