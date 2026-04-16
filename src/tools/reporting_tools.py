import os
import pandas as pd
from datetime import datetime
from src.report.pdf_generator import generate_pdf_report

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "outputs", "automation")
EMAIL_LOG_PATH = os.path.join(LOG_DIR, "email_logs.csv")

def build_pdf(result: dict) -> str:
    return generate_pdf_report(result)

def send_report_email(result: dict, report_path: str, user: str) -> bool:
    """
    Simulates sending an email and logs the event to the database (CSV).
    """
    os.makedirs(LOG_DIR, exist_ok=True)
    
    resp = result.get("final_response", {})
    building_id = result.get("building_id", "N/A")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_entry = {
        "timestamp": timestamp,
        "user": user,
        "building_id": building_id,
        "risk": resp.get("risk_card", {}).get("value", "N/A"),
        "report_path": report_path,
        "status": "Sent (Simulated)"
    }
    
    df = pd.DataFrame([log_entry])
    
    if os.path.exists(EMAIL_LOG_PATH):
        df.to_csv(EMAIL_LOG_PATH, mode='a', header=False, index=False)
    else:
        df.to_csv(EMAIL_LOG_PATH, index=False)
        
    return True