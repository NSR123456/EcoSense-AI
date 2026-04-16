import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()

class TelegramBot:
    def __init__(self, db_manager=None, simulator=None):
        self.token = os.getenv("TELEGRAM_TOKEN")
        self.chat_id = os.getenv("MY_CHAT_ID")
        self.db = db_manager
        self.simulator = simulator

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        status_msg = "EcoSense AI (v2) Status: ONLINE\n"
        if self.simulator and self.simulator.is_running:
            status_msg += "Simulation: RUNNING\n"
        else:
            status_msg += "Simulation: IDLE\n"
        
        await update.message.reply_text(status_msg)

    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /reset command."""
        if self.simulator:
            self.simulator.reset_system()
            await update.message.reply_text("System Reset: Sheets cleared and pointer reset.")
        else:
            await update.message.reply_text("Reset failed: Simulator not initialized.")

    def send_alert(self, message):
        """Send proactive alerts for True Anomalies."""
        if not message or "None" in message:
            print("Telegram: Skipping alert for empty or None message.")
            return

        if not self.token or not self.chat_id:
            print("Telegram: Token or Chat ID not found. Skipping alert.")
            return

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": f"🚨 *EcoSense AI Alert*\n\n{message}",
            "parse_mode": "Markdown"
        }
        
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                print("Telegram: Alert sent successfully.")
            else:
                print(f"Telegram: Failed to send alert. Status: {response.status_code}")
        except Exception as e:
            print(f"Telegram: Error sending alert: {e}")

    def run_bot(self):
        """Run the bot (polling)."""
        if not self.token:
            print("Telegram: No token found. Bot will not run.")
            return

        application = ApplicationBuilder().token(self.token).build()
        
        status_handler = CommandHandler('status', self.status)
        reset_handler = CommandHandler('reset', self.reset)
        
        application.add_handler(status_handler)
        application.add_handler(reset_handler)
        
        print("Telegram: Bot starting...")
        application.run_polling()
