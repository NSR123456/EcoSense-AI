import os
from datetime import datetime
from src.services.google_sheets import DatabaseManager
from src.llm.client import generate_with_gemini

class AnalystAgent:
    """Finds 20% deviations in Active_Stream."""
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def check_for_deviations(self):
        print("Analyst Agent: Checking for deviations in Active_Stream.")
        data = self.db.read_tab("Active_Stream")
        if not data or len(data) == 0:
            return None

        # Assuming the last row is the latest
        latest_row = data[-1]
        
        # Ensure we have actual data, not just headers or empty values
        try:
            consumption_str = latest_row.get("consumption_kwh")
            if consumption_str is None or str(consumption_str).strip() == "" or str(consumption_str).lower() == "consumption_kwh":
                return None
            
            consumption = float(consumption_str)
        except (ValueError, TypeError):
            print(f"Analyst Agent: Skipping invalid data row: {latest_row}")
            return None

        is_faulty = latest_row.get("is_faulty") == "YES"

        # Deviation logic: 20% deviation or synthetic fault
        # For simplicity, we compare to an average or just check if it's marked as faulty
        if is_faulty or consumption > 250: # 250 is a dummy threshold for 20% deviation
            print(f"Analyst Agent: Potential anomaly detected at {latest_row['date']}")
            return latest_row
        return None

class PlannerAgent:
    """Cross-references Active_Stream spikes against Campus_Schedule."""
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def cross_reference(self, anomaly):
        if not anomaly:
            return None
        
        print("Planner Agent: Cross-referencing anomaly with Campus_Schedule.")
        schedule = self.db.read_tab("Campus_Schedule")
        anomaly_date = anomaly.get("date").split(" ")[0] # Get YYYY-MM-DD
        
        events = [e for e in schedule if e.get("date") == anomaly_date]
        
        if events:
            print(f"Planner Agent: Scheduled event found on {anomaly_date}: {events[0]['event_name']}. Likely justified.")
            return {"status": "justified", "event": events[0]}
        else:
            print(f"Planner Agent: No scheduled event found on {anomaly_date}. True Waste confirmed.")
            return {"status": "true_waste"}

class RecommenderAgent:
    """Provides NLP advice for 'True Waste' events."""
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def get_recommendation(self, anomaly, context):
        if not anomaly or context.get("status") == "justified":
            return None
        
        print(f"Recommender Agent: Generating dynamic insights for anomaly at {anomaly['date']} using Gemini.")
        
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
        
        response = generate_with_gemini(prompt)
        
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
