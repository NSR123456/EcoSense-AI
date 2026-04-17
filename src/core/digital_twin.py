"""
Digital Twin Engine for Energy Intelligence

Constructs a building-level state from sensor data and metadata,
computes analytics metrics, and generates human-readable summaries.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from src.ingestion.data_pipeline import get_recent_sensor_data, get_building_metadata

logger = logging.getLogger(__name__)

class DigitalTwinEngine:
    """Builds and reasons over the current energy model state."""

    def __init__(self):
        pass

    async def build_state(self, building_id: str, hours: int = 24) -> Dict[str, Any]:
        """Fetch the latest state for a building."""
        metadata = await get_building_metadata(building_id)
        sensor_data = await get_recent_sensor_data(building_id, hours)
        metrics = self.compute_metrics(sensor_data, metadata)
        summary = self.create_natural_language_summary(sensor_data, metadata, metrics)

        return {
            'building_id': building_id,
            'metadata': metadata,
            'sensor_data': sensor_data,
            'metrics': metrics,
            'summary': summary,
            'timestamp': datetime.utcnow().isoformat()
        }

    def compute_metrics(self, sensor_data: List[Dict], metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute analytics metrics from sensor data."""
        metrics = {
            'data_points': len(sensor_data),
            'peak_load_kw': 0.0,
            'avg_load_kw': 0.0,
            'power_factor': None,
            'thd_estimate': None,
            'load_trend': 'stable',
            'anomaly_count': 0
        }

        if not sensor_data:
            return metrics

        # Compute load metrics for energy_meter readings
        loads = [reading['value'] for reading in sensor_data if reading['sensor_type'] == 'energy_meter']
        if loads:
            metrics['peak_load_kw'] = max(loads)
            metrics['avg_load_kw'] = sum(loads) / len(loads)

            trend = metrics['peak_load_kw'] - metrics['avg_load_kw']
            if trend > metrics['avg_load_kw'] * 0.2:
                metrics['load_trend'] = 'increasing'
            elif trend < -metrics['avg_load_kw'] * 0.2:
                metrics['load_trend'] = 'decreasing'
            else:
                metrics['load_trend'] = 'stable'

        # Placeholder power factor and THD using electrical sensor proxies
        voltages = [reading['value'] for reading in sensor_data if reading['sensor_type'] == 'voltage_phase']
        currents = [reading['value'] for reading in sensor_data if reading['sensor_type'] == 'current_phase']
        if voltages and currents:
            pf = min(1.0, max(0.5, sum(voltages) / max(1.0, sum(currents)) / 10.0))
            metrics['power_factor'] = round(pf, 3)
            metrics['thd_estimate'] = round(abs(max(voltages) - min(voltages)) / max(1.0, sum(voltages)/len(voltages)), 3)

        # Count simple anomalies
        anomalies = [r for r in sensor_data if r.get('metadata', {}).get('source_type') == 'Simulated' and r.get('value', 0) > metrics['avg_load_kw'] * 1.5]
        metrics['anomaly_count'] = len(anomalies)

        if metadata and metadata.get('building_type') == 'industrial' and metrics['peak_load_kw'] > 500:
            metrics['peak_load_flag'] = True
        else:
            metrics['peak_load_flag'] = False

        return metrics

    def create_natural_language_summary(
        self,
        sensor_data: List[Dict],
        metadata: Optional[Dict[str, Any]],
        metrics: Dict[str, Any]
    ) -> str:
        """Create a natural language summary of the current energy state."""
        if not sensor_data:
            return "No recent sensor data available for this building."

        building_name = metadata.get('building_name') if metadata else 'Unknown Building'
        building_type = metadata.get('building_type', 'general facility') if metadata else 'facility'
        sqft = metadata.get('square_footage', 'unknown') if metadata else 'unknown'

        summary = (
            f"{building_name} is operating as a {building_type} with approximately {sqft} sqft. "
            f"Over the last {len(sensor_data)} readings, peak load reached {metrics['peak_load_kw']:.1f} kW and average load was {metrics['avg_load_kw']:.1f} kW. "
            f"The load trend appears {metrics['load_trend']}."
        )

        if metrics.get('power_factor') is not None:
            summary += f" Estimated power factor is {metrics['power_factor']}."

        if metrics.get('thd_estimate') is not None:
            summary += f" Total harmonic distortion estimate is {metrics['thd_estimate']}."

        if metrics.get('peak_load_flag'):
            summary += " This exceeds the expected industrial peak load threshold and should be investigated."

        if metrics['anomaly_count'] > 0:
            summary += f" {metrics['anomaly_count']} simulated anomalies were detected in the current window."

        return summary

# Global instance
digital_twin = DigitalTwinEngine()