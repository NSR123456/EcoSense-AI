"""
Integration layer between Data Pipeline and Telegram/Google Sheets

Sends sensor data insights to configured Telegram and Google Sheets.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from src.services.telegram_bot import TelegramBot
from src.services.google_sheets import DatabaseManager
from src.agents.orchestrator import orchestrator

logger = logging.getLogger(__name__)

class InsightPublisher:
    """Publishes energy insights to Telegram and Google Sheets."""

    def __init__(self):
        self.telegram = TelegramBot()
        self.db = DatabaseManager()

    async def publish_sensor_insights(self, building_id: str, sensor_data: List[Dict]) -> Dict[str, Any]:
        """
        Generate and publish insights from sensor data.

        Sends to:
        1. Telegram: High-priority alerts and recommendations
        2. Google Sheets: Detailed logs in Audit_Ledger
        """
        try:
            # Run orchestrator analysis
            report = await orchestrator.process_building(building_id)

            if 'error' in report:
                logger.error(f"Analysis failed for {building_id}: {report['error']}")
                return {'status': 'error', 'message': report['error']}

            # Extract key findings
            recommendations = report.get('recommendations', {}).get('recommendations', [])
            violations = report.get('compliance', {}).get('violations', [])

            # Publish to Telegram
            telegram_alerts = await self._send_telegram_alerts(building_id, report)

            # Publish to Google Sheets
            sheets_logs = await self._log_to_google_sheets(building_id, report)

            return {
                'status': 'success',
                'building_id': building_id,
                'telegram_alerts': telegram_alerts,
                'sheets_logs': sheets_logs,
                'recommendations_count': len(recommendations),
                'violations_count': len(violations),
                'timestamp': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to publish insights for {building_id}: {e}")
            return {'status': 'error', 'message': str(e)}

    async def _send_telegram_alerts(self, building_id: str, report: Dict[str, Any]) -> int:
        """Send high-priority alerts to Telegram."""
        alert_count = 0

        try:
            recommendations = report.get('recommendations', {}).get('recommendations', [])
            violations = report.get('compliance', {}).get('violations', [])

            # Send critical recommendations
            for rec in recommendations:
                if rec['priority'] in ['critical', 'high']:
                    message = (
                        f"🏢 *{building_id}*\n\n"
                        f"📌 *Action:* {rec['action']}\n"
                        f"📝 *Description:* {rec['description']}\n"
                        f"💡 *Reason:* {rec['reason']}\n"
                        f"⚠️ *Priority:* {rec['priority'].upper()}"
                    )
                    self.telegram.send_alert(message)
                    alert_count += 1

            # Send compliance violations
            for violation in violations:
                if violation['severity'] == 'high':
                    message = (
                        f"⚖️ *Compliance Alert*\n\n"
                        f"🏢 *Building:* {building_id}\n"
                        f"❌ *Violation:* {violation['regulation'].replace('_', ' ').title()}\n"
                        f"📋 *Issue:* {violation['description']}\n"
                        f"✅ *Required Action:* {violation['required_action']}"
                    )
                    self.telegram.send_alert(message)
                    alert_count += 1

        except Exception as e:
            logger.error(f"Failed to send Telegram alerts: {e}")

        return alert_count

    async def _log_to_google_sheets(self, building_id: str, report: Dict[str, Any]) -> Dict[str, int]:
        """Log insights to Google Sheets."""
        results = {'recommendations_logged': 0, 'violations_logged': 0}

        try:
            recommendations = report.get('recommendations', {}).get('recommendations', [])
            violations = report.get('compliance', {}).get('violations', [])

            # Log recommendations to Audit_Ledger
            for rec in recommendations:
                row = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'building_id': building_id,
                    'anomaly_type': rec['action'],
                    'recommendation': f"{rec['description']} - {rec['reason']}",
                    'status': 'pending',
                    'priority': rec['priority']
                }

                try:
                    self.db.write_rows('Audit_Ledger', [row])
                    results['recommendations_logged'] += 1
                except Exception as e:
                    logger.warning(f"Failed to log recommendation: {e}")

            # Log violations separately
            for violation in violations:
                row = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'building_id': building_id,
                    'anomaly_type': f"COMPLIANCE_VIOLATION: {violation['regulation']}",
                    'recommendation': violation['required_action'],
                    'status': 'escalated',
                    'priority': 'high'
                }

                try:
                    self.db.write_rows('Audit_Ledger', [row])
                    results['violations_logged'] += 1
                except Exception as e:
                    logger.warning(f"Failed to log violation: {e}")

        except Exception as e:
            logger.error(f"Failed to log to Google Sheets: {e}")

        return results

    async def publish_daily_summary(self, buildings: Optional[List[str]] = None) -> Dict[str, Any]:
        """Generate and publish daily energy summary."""
        if buildings is None:
            buildings = ["Academic Building", "Admin Block", "Library", "Auditorium"]

        daily_summary = {
            'date': datetime.utcnow().date().isoformat(),
            'buildings_analyzed': 0,
            'total_issues': 0,
            'total_recommendations': 0,
            'critical_alerts': 0,
            'compliance_violations': 0,
            'details': []
        }

        for building in buildings:
            try:
                report = await orchestrator.process_building(building)
                if 'error' not in report:
                    daily_summary['buildings_analyzed'] += 1
                    daily_summary['total_issues'] += report.get('analysis', {}).get('issues_found', 0)
                    daily_summary['total_recommendations'] += report.get('recommendations', {}).get('recommendations_count', 0)
                    daily_summary['compliance_violations'] += report.get('compliance', {}).get('violations_count', 0)

                    # Count critical alerts
                    for rec in report.get('recommendations', {}).get('recommendations', []):
                        if rec['priority'] == 'critical':
                            daily_summary['critical_alerts'] += 1

                    daily_summary['details'].append({
                        'building': building,
                        'issues': report.get('analysis', {}).get('issues_found', 0),
                        'status': '✓' if report.get('compliance', {}).get('compliant', True) else '✗'
                    })

            except Exception as e:
                logger.error(f"Failed to analyze {building}: {e}")

        # Send daily summary to Telegram
        if daily_summary['total_issues'] > 0 or daily_summary['compliance_violations'] > 0:
            summary_message = (
                f"📊 *Daily Energy Summary*\n\n"
                f"📅 *Date:* {daily_summary['date']}\n"
                f"🏢 *Buildings Analyzed:* {daily_summary['buildings_analyzed']}\n"
                f"⚠️ *Total Issues:* {daily_summary['total_issues']}\n"
                f"💡 *Recommendations:* {daily_summary['total_recommendations']}\n"
                f"🔴 *Critical Alerts:* {daily_summary['critical_alerts']}\n"
                f"📋 *Compliance Violations:* {daily_summary['compliance_violations']}\n\n"
                f"👉 Check Google Sheets for detailed logs."
            )
            self.telegram.send_alert(summary_message)

        return daily_summary

# Global instance
publisher = InsightPublisher()