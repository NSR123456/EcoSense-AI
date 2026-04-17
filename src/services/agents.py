import os
import time
from datetime import datetime
from src.services.database import DatabaseManager
from src.llm.client import generate_with_gemini

class AnalystAgent:
    """Finds 20% deviations in Active_Stream."""
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def check_for_deviations(self):
        print("Analyst Agent: Checking for deviations in Active_Stream Excel sheet.")
        data = self.db.read_tab("Active_Stream")
        if not data or len(data) == 0:
            print("Analyst Agent: Excel sheet Active_Stream is empty - cannot analyze.")
            return None
        print(f"Analyst Agent: Found {len(data)} rows in Excel sheet, proceeding with analysis.")

        # Assuming the latest row is the most recent event
        latest_row = data[-1]

        try:
            consumption = float(latest_row.get("consumption_kwh", 0))
        except (ValueError, TypeError):
            print(f"Analyst Agent: Skipping invalid data row: {latest_row}")
            return None

        is_faulty = latest_row.get("is_faulty") == "YES"
        building_id = latest_row.get("building_id")

        # Build a historical baseline from prior rows for the same building
        same_building = [r for r in data[:-1] if r.get("building_id") == building_id]
        baseline = 0.0
        if len(same_building) >= 3:
            values = []
            for row in same_building[-12:]:
                try:
                    values.append(float(row.get("consumption_kwh", 0)))
                except (ValueError, TypeError):
                    continue
            if values:
                baseline = sum(values) / len(values)

        deviation = None
        if baseline > 0:
            deviation = round((consumption - baseline) / baseline * 100, 1)

        if is_faulty or (baseline > 0 and deviation >= 10):  # Reduced threshold for demo
            print(f"[ANALYST]: Anomaly detected at {latest_row.get('date')} for {building_id}. baseline={baseline:.2f}, actual={consumption:.2f}, delta={deviation}%")
            latest_row["baseline"] = round(baseline, 2)
            latest_row["deviation_pct"] = deviation
            latest_row["anomaly_reason"] = "synthetic_fault" if is_faulty else "baseline_deviation"
            return latest_row

        print(f"[ANALYST]: No anomaly for {building_id} at {latest_row.get('date')}. baseline={baseline:.2f}, actual={consumption:.2f}")
        return None

class PlannerAgent:
    """Cross-references Active_Stream spikes against Campus_Schedule."""
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def cross_reference(self, anomaly):
        if not anomaly:
            return None

        print("[PLANNER]: Cross-referencing anomaly with Campus_Schedule.")
        schedule = self.db.read_tab("Campus_Schedule")
        anomaly_date = str(anomaly.get("date", "")).split(" ")[0]

        events = [e for e in schedule if str(e.get("date", "")).strip() == anomaly_date]

        if events:
            print(f"[PLANNER]: Scheduled event found on {anomaly_date}: {events[0].get('event_name')}. Likely expected.")
            return {"status": "expected", "event": events[0]}
        print(f"[PLANNER]: No schedule event found on {anomaly_date}. Waste identified.")
        return {"status": "true_waste"}

class RecommenderAgent:
    """Provides NLP advice for 'True Waste' events."""
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def get_recommendation(self, anomaly, context):
        if not anomaly or context.get("status") != "true_waste":
            print("[RECOMMENDER]: No waste event to generate recommendation for.")
            return None

        print(f"[RECOMMENDER]: Generating dynamic insights for anomaly at {anomaly.get('date')} using Gemini.")
        
        # Enhanced prompt for both classification and recommendation
        prompt = f"""
        System: You are an Energy Audit Specialist for a campus.
        Context: A building energy spike was detected on {anomaly['date']} at building '{anomaly['building_id']}'.
        Current Consumption: {anomaly['consumption_kwh']} kWh.
        No scheduled event was found on the campus calendar for this time.
        
        Task: 
        1. Classify the anomaly type (e.g., HVAC Drift, Lighting Waste, Equipment Left On, Phantom Load). 
        2. Provide a short, actionable energy-saving recommendation.
        
        Response Format (Strictly follow this):
        Type: [2-3 words classification]
        Recommendation: [Short, specific NLP advice, max 15 words]
        """
        
        response = generate_with_gemini(prompt, safety_delay=4)
        
        anomaly_type = "True Waste Spike"
        recommendation = "Investigate building for unmapped loads or schedule drifts."
        
        if response and "Type:" in response and "Recommendation:" in response:
            try:
                parts = response.split("Recommendation:")
                anomaly_type = parts[0].replace("Type:", "").strip()
                recommendation = parts[1].strip()
            except Exception as e:
                print(f"Recommender Agent: Error parsing Gemini response: {e}")
        elif response:
            # Fallback if parsing fails but there is a response
            recommendation = response
        
        print(f"Recommender Agent: Insight generated - Type: {anomaly_type}, Rec: {recommendation}")
        
        # Log to Audit Ledger
        log_entry = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            anomaly.get("building_id"),
            anomaly_type,
            recommendation,
            "Logged"
        ]
        self.db.write_rows("Audit_Ledger", [log_entry])
        
        return {"type": anomaly_type, "recommendation": recommendation}


class AgentTeam:
    """Orchestrates the analyst, planner, and recommender agents."""
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.analyst = AnalystAgent(db_manager)
        self.planner = PlannerAgent(db_manager)
        self.recommender = RecommenderAgent(db_manager)

    def handle_stream_event(self, event_row):
        print("AgentTeam: Received new stream event, checking Excel data...")

        # RULE: If Excel sheet is empty → STOP immediately, no analysis
        active_stream = self.db.read_tab("Active_Stream")
        if not active_stream or len(active_stream) == 0:
            print("AgentTeam: Excel sheet is empty - no data available for analysis")
            return {
                "error": "No data available for analysis",
                "message": "Excel sheet Active_Stream tab contains no rows"
            }

        print(f"AgentTeam: Excel sheet has {len(active_stream)} rows, proceeding with analysis")

        anomaly = self.analyst.check_for_deviations()
        if not anomaly:
            print("AgentTeam: No anomaly detected in current Excel data.")
            return None

        context = self.planner.cross_reference(anomaly)
        recommendation = self.recommender.get_recommendation(anomaly, context)

        return {
            "anomaly": anomaly,
            "context": context,
            "recommendation": recommendation
        }
