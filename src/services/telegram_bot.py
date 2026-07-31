import os
import requests
from telegram import Update
from telegram.error import Conflict
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()

class TelegramBot:
    def __init__(self, db_manager=None, simulator=None, agent_team=None, **kwargs):
        self.token = os.getenv("TELEGRAM_TOKEN")
        self.chat_id = os.getenv("MY_CHAT_ID")
        self.db = db_manager
        self.simulator = simulator
        self.agent_team = agent_team
        self._extra_kwargs = kwargs
        self.application = None
        self.running = False

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        status_msg = "EcoSense AI (v2) Status: ONLINE\n"
        if self.simulator and self.simulator.is_running:
            status_msg += "Simulation: RUNNING\n"
        else:
            status_msg += "Simulation: IDLE\n"

        # Add selected building information
        if self.simulator and hasattr(self.simulator, 'focus_building'):
            focus_building = self.simulator.focus_building or "All"
            status_msg += f"Focus Building: {focus_building}\n"

        if self.db:
            active = self.db.read_tab("Active_Stream")
            audit = self.db.read_tab("Audit_Ledger")
            status_msg += f"Active stream rows: {len(active)}\n"
            status_msg += f"Audit ledger entries: {len(audit)}\n"
            if active:
                latest = active[-1]
                status_msg += f"Latest point: {latest.get('building_id')} @ {latest.get('date')}\n"

        await update.message.reply_text(status_msg)

    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /reset command."""
        if self.simulator and self.db:
            # Clear sheets
            self.simulator.reset_system()
            # Try to restart simulation if we have an agent team
            if self.agent_team:
                # Start simulation in background thread
                import threading
                def telegram_sim_thread():
                    def telegram_on_update(payload):
                        # Run agent analysis and send insights via Telegram
                        result = self.agent_team.handle_stream_event(payload)
                        if result and "error" not in result:
                            anomaly = result.get("anomaly", {})
                            building_id = anomaly.get('building_id', 'unknown')
                            date = anomaly.get('date', 'unknown')
                            deviation = anomaly.get('deviation_pct', 0)
                            
                            insight_msg = f"🚨 ANOMALY DETECTED\nBuilding: {building_id}\nDate: {date}\nDeviation: {deviation:.1f}%\n"
                            
                            if result.get("recommendation"):
                                rec = result["recommendation"].get("recommendation", "Investigate")
                                insight_msg += f"Recommendation: {rec}"
                            
                            self.send_alert(insight_msg)
                    
                    self.simulator.start_stream(on_update=telegram_on_update)
                
                thread = threading.Thread(target=telegram_sim_thread, daemon=True)
                thread.start()
                await update.message.reply_text("System Reset: Sheets cleared, pointer reset, and simulation restarted!")
            else:
                await update.message.reply_text("System Reset: Sheets cleared and pointer reset. Use /start_sim to begin simulation.")
        else:
            await update.message.reply_text("Reset failed: Simulator or database not initialized.")

    async def start_sim(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start_sim command."""
        if self.simulator and self.agent_team:
            # Start simulation in background thread
            import threading
            def telegram_sim_thread():
                def telegram_on_update(payload):
                    # Run agent analysis and send insights via Telegram
                    result = self.agent_team.handle_stream_event(payload)
                    if result and "error" not in result:
                        anomaly = result.get("anomaly", {})
                        building_id = anomaly.get('building_id', 'unknown')
                        date = anomaly.get('date', 'unknown')
                        deviation = anomaly.get('deviation_pct', 0)
                        
                        insight_msg = f"🚨 ANOMALY DETECTED\nBuilding: {building_id}\nDate: {date}\nDeviation: {deviation:.1f}%\n"
                        
                        if result.get("recommendation"):
                            rec = result["recommendation"].get("recommendation", "Investigate")
                            insight_msg += f"Recommendation: {rec}"
                        
                        self.send_alert(insight_msg)
                
                self.simulator.start_stream(on_update=telegram_on_update)
            
            thread = threading.Thread(target=telegram_sim_thread, daemon=True)
            thread.start()
            await update.message.reply_text("Simulation started! Will send alerts for anomalies detected.")
        else:
            await update.message.reply_text("Start failed: Simulator or agent team not initialized.")

    async def stop_sim(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop_sim command."""
        if self.simulator:
            self.simulator.is_running = False
            await update.message.reply_text("Simulation stopped.")
        else:
            await update.message.reply_text("Stop failed: Simulator not initialized.")

    async def insights(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /insights command."""
        if self.db:
            active = self.db.read_tab("Active_Stream")
            audit = self.db.read_tab("Audit_Ledger")
            
            insight_msg = f"**SYSTEM INSIGHTS**\n"
            
            # Add selected building information
            if self.simulator and hasattr(self.simulator, 'focus_building'):
                focus_building = self.simulator.focus_building or "All"
                insight_msg += f"Focus Building: {focus_building}\n"
            
            insight_msg += f"Active Stream: {len(active)} data points\n"
            insight_msg += f"Audit Ledger: {len(audit)} actions logged\n"
            
            if active:
                latest = active[-1]
                insight_msg += f"\n**Latest Reading:**\n"
                insight_msg += f"Building: {latest.get('building_id', 'Unknown')}\n"
                insight_msg += f"Date: {latest.get('date', 'Unknown')}\n"
                insight_msg += f"Consumption: {latest.get('consumption_kwh', 'Unknown')} kWh\n"
                insight_msg += f"Status: {'**FAULTY**' if latest.get('is_faulty') == 'YES' else 'Normal'}"
            
            if audit:
                insight_msg += f"\n**Recent Actions:**\n"
                recent_actions = audit[-3:]  # Last 3 actions
                for action in recent_actions:
                    insight_msg += f"â¢ {action.get('finding_type', 'Unknown')} â {action.get('action_description', 'Unknown')}\n"
            
            await update.message.reply_text(insight_msg)
        else:
            await update.message.reply_text("Insights failed: Database not initialized.")

    async def building(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /building command - check specific building data."""
        if not self.db:
            await update.message.reply_text("Building check failed: Database not initialized.")
            return
        
        # Get building name from command argument or use focus building
        building_name = None
        if context.args:
            building_name = " ".join(context.args).strip()
        elif self.simulator and hasattr(self.simulator, 'focus_building'):
            building_name = self.simulator.focus_building
        
        if not building_name or building_name.lower() == "all":
            await update.message.reply_text("Please specify a building name: /building <building_name>\nExample: /building FBS Building")
            return
        
        # Get available buildings from database
        try:
            active = self.db.read_tab("Active_Stream")
            available_buildings = list(set(row.get('building_id') for row in active if row.get('building_id')))
        except Exception as e:
            await update.message.reply_text(f"Database error: {str(e)}")
            return
        
        # Case-insensitive building matching
        matching_building = None
        for available in available_buildings:
            if available.lower() == building_name.lower():
                matching_building = available
                break
        
        if not matching_building:
            building_msg = f"**BUILDING REPORT: {building_name}**\n"
            building_msg += f"Status: Building not found\n\n"
            building_msg += f"**Available Buildings:**\n"
            for building in sorted(available_buildings):
                building_msg += f"â¢ {building}\n"
            building_msg += f"\n**Note:** Use exact building name or start simulation with this building selected to generate data."
            await update.message.reply_text(building_msg)
            return
        
        # Use the correct case building name
        building_name = matching_building
        
        # Filter data for the specific building
        building_active = [row for row in active if row.get('building_id') == building_name]
        try:
            audit = self.db.read_tab("Audit_Ledger")
            building_audit = [row for row in audit if row.get('building_id') == building_name]
        except Exception:
            building_audit = []
        
        building_msg = f"**BUILDING REPORT: {building_name}**\n"
        building_msg += f"Data Points: {len(building_active)}\n"
        building_msg += f"Audit Actions: {len(building_audit)}\n"
        
        if building_active:
            # Get statistics
            consumptions = [float(row.get('consumption_kwh', 0)) for row in building_active if row.get('consumption_kwh')]
            if consumptions:
                avg_consumption = sum(consumptions) / len(consumptions)
                max_consumption = max(consumptions)
                min_consumption = min(consumptions)
                building_msg += f"Avg Consumption: {avg_consumption:.2f} kWh\n"
                building_msg += f"Max Consumption: {max_consumption:.2f} kWh\n"
                building_msg += f"Min Consumption: {min_consumption:.2f} kWh\n"
            
            # Latest reading
            latest = building_active[-1]
            building_msg += f"\n**Latest Reading:**\n"
            building_msg += f"Date: {latest.get('date', 'Unknown')}\n"
            building_msg += f"Consumption: {latest.get('consumption_kwh', 'Unknown')} kWh\n"
            building_msg += f"Status: {'**FAULTY**' if latest.get('is_faulty') == 'YES' else 'Normal'}"
            
            # Count faulty readings
            faulty_count = sum(1 for row in building_active if row.get('is_faulty') == 'YES')
            if faulty_count > 0:
                building_msg += f"\n**Alerts:** {faulty_count} anomaly readings detected"
        else:
            building_msg += "No stream data available for this building."
            building_msg += f"\n\n**Tip:** Start simulation with '{building_name}' selected to generate data."
        
        if building_audit:
            building_msg += f"\n\n**Recent Actions for {building_name}:**\n"
            recent_actions = building_audit[-3:]  # Last 3 actions
            for action in recent_actions:
                action_type = action.get('finding_type', 'Unknown')
                action_desc = action.get('action_description', 'Unknown')
                building_msg += f"â¢ {action_type} â {action_desc}\n"
        
        await update.message.reply_text(building_msg)

    def is_configured(self) -> bool:
        return bool(self.token and self.chat_id)

    def send_alert(self, message):
        """Send proactive alerts for True Anomalies."""
        if not message or "None" in message:
            print("Telegram: Skipping alert for empty or None message.")
            return False

        if not self.is_configured():
            print("Telegram: Token or Chat ID not found. Skipping alert.")
            return False

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                print("Telegram: Alert sent successfully.")
                return True
            else:
                print(f"Telegram: Failed to send alert. Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            print(f"Telegram: Error sending alert: {e}")
            return False

    def stop_bot(self):
        """Stop the bot instance."""
        if self.application and self.running:
            print("Telegram: Stopping bot instance...")
            self.running = False
            self.application.stop()
            self.application = None
            print("Telegram: Bot stopped.")

    def run_bot(self):
        """Run the bot (polling)."""
        if not self.token:
            print("Telegram: No token found. Bot will not run.")
            return

        if self.running and self.application is not None:
            print("Telegram: Bot already running. Skipping duplicate start.")
            return

        try:
            self.application = ApplicationBuilder().token(self.token).build()
            
            status_handler = CommandHandler('status', self.status)
            reset_handler = CommandHandler('reset', self.reset)
            start_sim_handler = CommandHandler('start_sim', self.start_sim)
            stop_sim_handler = CommandHandler('stop_sim', self.stop_sim)
            insights_handler = CommandHandler('insights', self.insights)
            building_handler = CommandHandler('building', self.building)
            
            self.application.add_handler(status_handler)
            self.application.add_handler(reset_handler)
            self.application.add_handler(start_sim_handler)
            self.application.add_handler(stop_sim_handler)
            self.application.add_handler(insights_handler)
            self.application.add_handler(building_handler)
            
            self.running = True
            print("Telegram: Bot starting...")
            self.application.run_polling()
        except Conflict as e:
            print(f"Telegram: Bot polling conflict detected. Another bot instance is using this token: {e}")
            self.running = False
            self.application = None
        except Exception as e:
            print(f"Telegram: Bot error: {e}")
            self.running = False
            self.application = None
