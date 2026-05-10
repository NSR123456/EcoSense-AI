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

        print(f"[RECOMMENDER]: Generating dynamic insights for anomaly at {anomaly.get('date')} using Ollama.")
        
        # Enhanced prompt for both classification and recommendation
        from src.llm.energy_fine_tuner import generate_fine_tuned_response
        
        # The fine-tuned model was trained on simple phrases, not massive instruction prompts
        # We pass a simple contextual trigger that the model understands
        input_text = f"Energy consumption spike of {anomaly.get('deviation_pct', 0):.1f}% detected in {anomaly['building_id']}. How to reduce energy consumption?"
        
        response = generate_fine_tuned_response("recommender", input_text)
        
        anomaly_type = "True Waste Spike"
        recommendation = "Investigate building for unmapped loads or schedule drifts."
        
        if response and "Type:" in response and "Recommendation:" in response:
            try:
                parts = response.split("Recommendation:")
                anomaly_type = parts[0].replace("Type:", "").strip()
                recommendation = parts[1].strip()
            except Exception as e:
                print(f"Recommender Agent: Error parsing Ollama response: {e}")
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

    def get_stream_snapshot(self):
        """Return current Active_Stream rows and basic stats."""
        active_stream = self.db.read_tab("Active_Stream")
        if not active_stream:
            return None, 0, {}
        stream_count = len(active_stream)
        latest_row = active_stream[-1]

        # Compute per-building stats
        from collections import defaultdict
        building_stats = defaultdict(list)
        for row in active_stream:
            try:
                building_stats[row.get("building_id", "unknown")].append(
                    float(row.get("consumption_kwh", 0))
                )
            except (ValueError, TypeError):
                continue

        stats = {}
        for bid, vals in building_stats.items():
            avg = sum(vals) / len(vals) if vals else 0
            stats[bid] = {"count": len(vals), "avg_kwh": round(avg, 2),
                          "max_kwh": round(max(vals), 2) if vals else 0}

        return latest_row, stream_count, stats

    def analyze_continuous(self):
        """Always return agent messages for the current stream state.

        Unlike ``handle_stream_event`` which returns ``None`` when there is no
        anomaly, this method *always* produces role-specific outputs so the
        Agent Theater is never stuck at 'typing...'.
        """
        latest_row, stream_count, building_stats = self.get_stream_snapshot()
        if latest_row is None:
            return None, None

        # Try regular anomaly detection
        anomaly = self.analyst.check_for_deviations()
        result = None
        if anomaly:
            context = self.planner.cross_reference(anomaly)
            recommendation = self.recommender.get_recommendation(anomaly, context)
            result = {"anomaly": anomaly, "context": context, "recommendation": recommendation}

        return result, {
            "stream_count": stream_count,
            "latest_row": latest_row,
            "building_stats": building_stats,
        }

    def chat_with_user(self, user_message: str, building_context: str = "") -> str:
        """Chat with user using Ollama LLM"""
        prompt = f"""
You are an AI assistant for energy management in buildings.

Building Context: {building_context}

User Question: {user_message}

Provide a helpful, specific response about energy management, building data, or anomalies.
"""
        return generate_with_gemini(prompt, safety_delay=0)
