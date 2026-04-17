"""
Main runner for Energy Management AI Platform with Scheduler

Integrates:
- Multi-agent analysis (orchestrator)
- Insights publishing (Telegram + Google Sheets)
- Periodic scheduler
"""

import os
import sys
import signal
import logging
from pathlib import Path
from dotenv import load_dotenv

# Setup path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

from src.services.scheduler import default_scheduler

scheduler_instance = None

def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    global scheduler_instance
    logger.info(f"Received signal {sig}, shutting down gracefully...")
    if scheduler_instance:
        scheduler_instance.stop()
    sys.exit(0)

def main():
    """Main entry point."""
    global scheduler_instance

    logger.info("="*60)
    logger.info("EcoSense Energy Management AI Platform")
    logger.info("Energy Analyzer + Scheduler + Telegram/Sheets Integration")
    logger.info("="*60)

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Initialize scheduler
    scheduler_instance = default_scheduler

    # Configure schedules
    logger.info("Configuring analysis schedules...")
    scheduler_instance.schedule_hourly_analysis()  # Every hour
    scheduler_instance.schedule_daily_summary("08:00")  # 8 AM daily

    # Optional: Schedule individual building analysis
    for building in ["Academic Building", "Admin Block"]:
        scheduler_instance.schedule_building_analysis(building, interval_hours=3)

    logger.info("✓ All schedules configured")
    logger.info("\nStarting scheduler...")
    logger.info("Press Ctrl+C to stop\n")

    try:
        scheduler_instance.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()