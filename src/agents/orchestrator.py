"""
Multi-Agent Orchestrator for Energy Management

Coordinates data collection, analysis, recommendation, and compliance agents.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from src.ingestion.data_pipeline import get_recent_sensor_data
from src.models.predictive_model import predictive_model
from src.models.vision_model import vision_model
from src.services.telegram_bot import TelegramBot
from src.services.google_sheets import DatabaseManager

logger = logging.getLogger(__name__)

class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    COMPLETED = "completed"

@dataclass
class AgentTask:
    task_id: str
    agent_type: str
    building_id: str
    priority: str  # 'low', 'medium', 'high', 'critical'
    status: AgentStatus
    created_at: datetime
    data: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None

class DataCollectorAgent:
    """Collects and validates sensor data."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.status = AgentStatus.IDLE

    async def collect_data(self, building_id: str, hours: int = 24) -> Dict[str, Any]:
        """Collect recent sensor data for a building."""
        self.status = AgentStatus.RUNNING
        try:
            data = await get_recent_sensor_data(building_id, hours)

            # Validate data quality
            valid_readings = [r for r in data if r.get('value') is not None]

            result = {
                'building_id': building_id,
                'data_points': len(valid_readings),
                'time_range_hours': hours,
                'data_quality': len(valid_readings) / max(1, len(data)),
                'latest_timestamp': max((r['timestamp'] for r in valid_readings), default=None)
            }

            self.status = AgentStatus.COMPLETED
            return result

        except Exception as e:
            logger.error(f"DataCollectorAgent error: {e}")
            self.status = AgentStatus.ERROR
            return {'error': str(e)}

class AnalystAgent:
    """Analyzes data for anomalies and predicts maintenance needs."""

    def __init__(self):
        self.status = AgentStatus.IDLE

    async def analyze_building(self, building_id: str, sensor_data: List[Dict]) -> Dict[str, Any]:
        """Analyze building data for issues."""
        self.status = AgentStatus.RUNNING
        try:
            issues = []

            # Group data by sensor type
            sensor_groups = {}
            for reading in sensor_data:
                sensor_type = reading['sensor_type']
                if sensor_type not in sensor_groups:
                    sensor_groups[sensor_type] = []
                sensor_groups[sensor_type].append(reading)

            # Analyze each sensor type
            for sensor_type, readings in sensor_groups.items():
                sensor_key = f"{building_id}_{sensor_type}"

                # Train/update predictive model
                if len(readings) >= 50:
                    predictive_model.train_model(sensor_key, readings)

                # Get maintenance prediction
                prediction = predictive_model.predict_failure(sensor_key)
                if prediction and 'predicted_failure_date' in prediction:
                    issues.append({
                        'type': 'predictive_maintenance',
                        'sensor_type': sensor_type,
                        'severity': 'high' if prediction['days_to_failure'] <= 3 else 'medium',
                        'description': f"Equipment failure predicted in {prediction['days_to_failure']} days",
                        'recommendation': predictive_model.get_maintenance_schedule(sensor_key)
                    })

                # Check for immediate anomalies (simple threshold)
                values = [r['value'] for r in readings[-10:]]  # Last 10 readings
                if values:
                    mean_val = sum(values) / len(values)
                    std_val = (sum((x - mean_val) ** 2 for x in values) / len(values)) ** 0.5

                    for reading in readings[-5:]:  # Check recent readings
                        if abs(reading['value'] - mean_val) > 2 * std_val:
                            issues.append({
                                'type': 'anomaly',
                                'sensor_type': sensor_type,
                                'severity': 'medium',
                                'description': f"Unusual reading: {reading['value']} {reading['unit']}",
                                'timestamp': reading['timestamp']
                            })

            result = {
                'building_id': building_id,
                'issues_found': len(issues),
                'issues': issues,
                'analysis_timestamp': datetime.utcnow().isoformat()
            }

            self.status = AgentStatus.COMPLETED
            return result

        except Exception as e:
            logger.error(f"AnalystAgent error: {e}")
            self.status = AgentStatus.ERROR
            return {'error': str(e)}

class RecommenderAgent:
    """Generates personalized recommendations using NLP."""

    def __init__(self):
        self.status = AgentStatus.IDLE

    async def generate_recommendations(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate actionable recommendations."""
        self.status = AgentStatus.RUNNING
        try:
            issues = analysis_result.get('issues', [])
            building_id = analysis_result.get('building_id')

            recommendations = []

            for issue in issues:
                if issue['type'] == 'predictive_maintenance':
                    maint = issue['recommendation']
                    rec = {
                        'priority': maint['priority'],
                        'action': maint['action'],
                        'description': f"Schedule {maint['action']} in {maint['schedule_days']} days",
                        'reason': maint['reason'],
                        'building_id': building_id
                    }
                    recommendations.append(rec)

                elif issue['type'] == 'anomaly':
                    rec = {
                        'priority': issue['severity'],
                        'action': 'investigate_anomaly',
                        'description': f"Investigate unusual {issue['sensor_type']} reading",
                        'reason': issue['description'],
                        'building_id': building_id
                    }
                    recommendations.append(rec)

            # Sort by priority
            priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
            recommendations.sort(key=lambda x: priority_order.get(x['priority'], 3))

            result = {
                'building_id': building_id,
                'recommendations_count': len(recommendations),
                'recommendations': recommendations,
                'generated_at': datetime.utcnow().isoformat()
            }

            self.status = AgentStatus.COMPLETED
            return result

        except Exception as e:
            logger.error(f"RecommenderAgent error: {e}")
            self.status = AgentStatus.ERROR
            return {'error': str(e)}

class ComplianceAgent:
    """Monitors regulatory compliance."""

    def __init__(self):
        self.status = AgentStatus.IDLE
        # Simplified compliance rules
        self.compliance_rules = {
            'energy_efficiency': {'max_kwh_per_sqft': 50, 'period': 'monthly'},
            'peak_demand': {'max_kw': 1000},
            'carbon_footprint': {'max_kg_co2_per_day': 1000}
        }

    async def check_compliance(self, building_id: str, sensor_data: List[Dict]) -> Dict[str, Any]:
        """Check building compliance against regulations."""
        self.status = AgentStatus.RUNNING
        try:
            violations = []

            # Group by sensor type
            energy_readings = [r for r in sensor_data if r['sensor_type'] == 'energy_meter']

            if energy_readings:
                # Calculate metrics
                total_energy = sum(r['value'] for r in energy_readings)
                avg_daily = total_energy / max(1, len(energy_readings))

                # Check energy efficiency (simplified)
                if avg_daily > self.compliance_rules['energy_efficiency']['max_kwh_per_sqft'] * 10000:  # Assume 10000 sqft
                    violations.append({
                        'regulation': 'energy_efficiency',
                        'severity': 'high',
                        'description': f"Energy consumption {avg_daily:.1f} kWh/day exceeds limit",
                        'required_action': 'Implement energy conservation measures'
                    })

            result = {
                'building_id': building_id,
                'compliant': len(violations) == 0,
                'violations_count': len(violations),
                'violations': violations,
                'checked_at': datetime.utcnow().isoformat()
            }

            self.status = AgentStatus.COMPLETED
            return result

        except Exception as e:
            logger.error(f"ComplianceAgent error: {e}")
            self.status = AgentStatus.ERROR
            return {'error': str(e)}

class OrchestratorAgent:
    """Coordinates all agents and manages workflows."""

    def __init__(self, db_manager: DatabaseManager, telegram_bot: Optional[TelegramBot] = None):
        self.db = db_manager
        self.telegram = telegram_bot
        self.tasks: List[AgentTask] = []
        self.agents = {
            'data_collector': DataCollectorAgent(db_manager),
            'analyst': AnalystAgent(),
            'recommender': RecommenderAgent(),
            'compliance': ComplianceAgent()
        }

    async def process_building(self, building_id: str) -> Dict[str, Any]:
        """Run full analysis pipeline for a building."""
        logger.info(f"Orchestrator: Starting analysis for {building_id}")

        try:
            # Step 1: Collect data
            data_result = await self.agents['data_collector'].collect_data(building_id)
            if 'error' in data_result:
                return data_result

            sensor_data = await get_recent_sensor_data(building_id, 24)

            # Step 2: Analyze data
            analysis_result = await self.agents['analyst'].analyze_building(building_id, sensor_data)

            # Step 3: Generate recommendations
            recommendations = await self.agents['recommender'].generate_recommendations(analysis_result)

            # Step 4: Check compliance
            compliance = await self.agents['compliance'].check_compliance(building_id, sensor_data)

            # Compile final report
            report = {
                'building_id': building_id,
                'timestamp': datetime.utcnow().isoformat(),
                'data_summary': data_result,
                'analysis': analysis_result,
                'recommendations': recommendations,
                'compliance': compliance,
                'alerts_generated': 0
            }

            # Send alerts for critical issues
            await self._send_alerts(report)

            # Log to database
            await self._log_to_database(report)

            logger.info(f"Orchestrator: Completed analysis for {building_id}")
            return report

        except Exception as e:
            logger.error(f"Orchestrator error for {building_id}: {e}")
            return {'error': str(e)}

    async def _send_alerts(self, report: Dict[str, Any]):
        """Send alerts for critical findings."""
        if not self.telegram:
            return

        alerts = []

        # Critical recommendations
        for rec in report['recommendations'].get('recommendations', []):
            if rec['priority'] in ['critical', 'high']:
                alerts.append(f"🚨 {rec['priority'].upper()}: {rec['description']} - {rec['reason']}")

        # Compliance violations
        for violation in report['compliance'].get('violations', []):
            if violation['severity'] == 'high':
                alerts.append(f"⚠️ COMPLIANCE: {violation['description']} - {violation['required_action']}")

        # Send alerts
        for alert in alerts[:3]:  # Limit to 3 alerts
            self.telegram.send_alert(f"Building {report['building_id']}: {alert}")
            report['alerts_generated'] += 1

    async def _log_to_database(self, report: Dict[str, Any]):
        """Log key findings to database."""
        try:
            # Log recommendations
            for rec in report['recommendations'].get('recommendations', []):
                # In a real implementation, you'd have a recommendations table
                pass

            # Log compliance issues
            for violation in report['compliance'].get('violations', []):
                # Log to compliance table
                pass

        except Exception as e:
            logger.error(f"Failed to log to database: {e}")

# Global instance
orchestrator = OrchestratorAgent(DatabaseManager())