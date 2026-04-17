"""
Energy Management AI Platform Runner

Runs the multi-agent analysis for buildings.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.agents.orchestrator import orchestrator
from src.services.telegram_bot import TelegramBot
from src.services.google_sheets import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_building_analysis(building_id: str):
    """Run complete analysis for a building."""
    logger.info(f"Starting analysis for building: {building_id}")

    try:
        # Initialize telegram bot for alerts
        telegram = TelegramBot()
        orchestrator.telegram = telegram

        # Run analysis
        report = await orchestrator.process_building(building_id)

        if 'error' in report:
            logger.error(f"Analysis failed: {report['error']}")
            return

        # Print summary
        print(f"\n=== Analysis Report for {building_id} ===")
        print(f"Data Points: {report['data_summary']['data_points']}")
        print(f"Issues Found: {report['analysis']['issues_found']}")
        print(f"Recommendations: {report['recommendations']['recommendations_count']}")
        print(f"Compliance: {'✓' if report['compliance']['compliant'] else '✗'}")
        print(f"Alerts Sent: {report['alerts_generated']}")

        if report['recommendations']['recommendations']:
            print("\nTop Recommendations:")
            for i, rec in enumerate(report['recommendations']['recommendations'][:3], 1):
                print(f"{i}. [{rec['priority']}] {rec['action']}: {rec['description']}")

        if report['compliance']['violations']:
            print("\nCompliance Violations:")
            for violation in report['compliance']['violations']:
                print(f"- {violation['regulation']}: {violation['description']}")

    except Exception as e:
        logger.error(f"Analysis failed: {e}")

async def run_all_buildings():
    """Run analysis for all buildings."""
    buildings = ["Academic Building", "Admin Block", "Library", "Auditorium"]

    for building in buildings:
        await run_building_analysis(building)
        print("\n" + "="*50 + "\n")

async def main():
    if len(sys.argv) > 1:
        building_id = sys.argv[1]
        await run_building_analysis(building_id)
    else:
        await run_all_buildings()

if __name__ == "__main__":
    asyncio.run(main())