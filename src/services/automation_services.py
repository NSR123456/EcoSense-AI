import os
import requests
import streamlit as st
from datetime import datetime
from src.services.google_sheets import DatabaseManager
from src.services.telegram_bot import TelegramBot

# Initialize Services
db_manager = DatabaseManager()
telegram_service = TelegramBot()

def log_action_to_sheets(building_id: str, source_doc: str, finding_type: str, savings_kwh: float, action: str):
    """
    Python replacement for n8n logging. Directly writes to Google Sheets 'Audit_Ledger'.
    """
    try:
        log_entry = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            building_id,
            finding_type,
            f"{action} (Source: {source_doc}, Savings: {savings_kwh}kWh)",
            "Manual Log"
        ]
        db_manager.write_rows("Audit_Ledger", [log_entry])
        return {"status": "success", "message": "Action logged to Google Sheets Ledger"}
    except Exception as e:
        return {"status": "error", "message": f"Logging failed: {str(e)}"}

def send_telegram_alert(building_id: str, source_doc: str, finding_type: str, savings_kwh: float, action: str):
    """
    Python replacement for n8n alerting. Directly sends message via Telegram Bot.
    """
    try:
        message = (
            f"🚨 *EcoSense Action Alert*\n\n"
            f"*Building:* {building_id}\n"
            f"*Type:* {finding_type}\n"
            f"*Action:* {action}\n"
            f"*Estimated Savings:* {savings_kwh} kWh\n"
            f"*Source:* {source_doc}"
        )
        telegram_service.send_alert(message)
        return {"status": "success", "message": "Telegram alert sent successfully"}
    except Exception as e:
        return {"status": "error", "message": f"Alerting failed: {str(e)}"}

def update_visualization_alert(building_id: str, actual: float, optimized: float):
    """
    Python replacement for n8n visualization. Sends a summary alert with metrics.
    """
    try:
        savings = actual - optimized
        message = (
            f"📊 *EcoSense Visualization Update*\n\n"
            f"*Building:* {building_id}\n"
            f"*Current Consumption:* {actual:.2f} kWh\n"
            f"*Optimized Target:* {optimized:.2f} kWh\n"
            f"*Potential Savings:* {savings:.2f} kWh"
        )
        telegram_service.send_alert(message)
        return {"status": "success", "message": "Visualization alert sent successfully"}
    except Exception as e:
        return {"status": "error", "message": f"Visualization update failed: {str(e)}"}
