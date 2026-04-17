"""
Scheduler for periodic energy analysis and insights publication

Runs analysis on fixed schedule and publishes to Telegram + Google Sheets.
"""

import asyncio
import logging
import schedule
import time
from datetime import datetime, time as dt_time
from typing import List, Optional

from src.services.insights_publisher import publisher

logger = logging.getLogger(__name__)

class EnergyAnalysisScheduler:
    """Schedules periodic energy analysis and insights."""

    def __init__(self, buildings: Optional[List[str]] = None):
        self.buildings = buildings or ["Academic Building", "Admin Block", "Library", "Auditorium"]
        self.schedule = schedule.Scheduler()
        self.is_running = False

    def schedule_hourly_analysis(self):
        """Schedule building analysis every hour."""
        self.schedule.every(1).hours.do(self._run_async_task, self._analyze_all_buildings)
        logger.info("Scheduled: Hourly building analysis")

    def schedule_daily_summary(self, run_time: str = "08:00"):
        """
        Schedule daily summary at specific time.

        Args:
            run_time: Time in HH:MM format (24-hour)
        """
        hour, minute = map(int, run_time.split(':'))
        self.schedule.every().day.at(run_time).do(self._run_async_task, self._publish_daily_summary)
        logger.info(f"Scheduled: Daily summary at {run_time}")

    def schedule_building_analysis(self, building_id: str, interval_hours: int = 6):
        """Schedule analysis for specific building."""
        self.schedule.every(interval_hours).hours.do(
            self._run_async_task,
            self._analyze_single_building,
            building_id
        )
        logger.info(f"Scheduled: Building {building_id} analysis every {interval_hours} hours")

    async def _analyze_all_buildings(self):
        """Run analysis for all buildings."""
        logger.info(f"Starting periodic analysis for all buildings - {datetime.now()}")

        for building in self.buildings:
            try:
                result = await publisher.publish_sensor_insights(building, [])
                logger.info(f"Analysis published for {building}: {result}")
            except Exception as e:
                logger.error(f"Failed to analyze {building}: {e}")

        logger.info("Periodic analysis completed")

    async def _analyze_single_building(self, building_id: str):
        """Run analysis for single building."""
        logger.info(f"Analyzing building: {building_id}")

        try:
            result = await publisher.publish_sensor_insights(building_id, [])
            logger.info(f"Published for {building_id}: {result}")
        except Exception as e:
            logger.error(f"Analysis failed for {building_id}: {e}")

    async def _publish_daily_summary(self):
        """Publish daily summary."""
        logger.info("Publishing daily summary")

        try:
            summary = await publisher.publish_daily_summary(self.buildings)
            logger.info(f"Daily summary published: {summary}")
        except Exception as e:
            logger.error(f"Failed to publish daily summary: {e}")

    def _run_async_task(self, coro_func, *args):
        """Helper to run async tasks in sync context."""
        try:
            asyncio.run(coro_func(*args))
        except RuntimeError as e:
            # Handle case where event loop already exists
            loop = None
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.is_running():
                asyncio.ensure_future(coro_func(*args))
            else:
                loop.run_until_complete(coro_func(*args))

    def start(self):
        """Start scheduler loop."""
        self.is_running = True
        logger.info("Energy Analysis Scheduler started")

        try:
            while self.is_running:
                self.schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Scheduler stopped")
            self.is_running = False

    def stop(self):
        """Stop scheduler."""
        self.is_running = False
        logger.info("Scheduler stopping...")

# Default scheduler instance
default_scheduler = EnergyAnalysisScheduler()