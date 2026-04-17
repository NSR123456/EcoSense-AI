"""
Predictive Maintenance Model for Energy Management

Uses time-series forecasting to predict equipment failures and maintenance needs.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    Prophet = None

logger = logging.getLogger(__name__)

class PredictiveMaintenanceModel:
    """Predictive maintenance using time-series forecasting."""

    def __init__(self):
        self.models: Dict[str, Prophet] = {}  # sensor_key -> model
        self.thresholds: Dict[str, float] = {}  # sensor_key -> failure threshold

    def train_model(self, sensor_key: str, data: List[Dict]) -> bool:
        """
        Train a Prophet model for a specific sensor.

        Args:
            sensor_key: Unique identifier for the sensor (e.g., 'building_equipment')
            data: List of sensor readings with 'timestamp' and 'value'

        Returns:
            bool: True if training successful
        """
        if not PROPHET_AVAILABLE:
            logger.warning("Prophet not installed. Using statistical fallback.")
            return self._train_statistical_model(sensor_key, data)

        try:
            if len(data) < 50:  # Need minimum data points
                logger.warning(f"Insufficient data for {sensor_key}: {len(data)} points")
                return self._train_statistical_model(sensor_key, data)

            # Prepare data for Prophet
            df = pd.DataFrame(data)
            df['ds'] = pd.to_datetime(df['timestamp'])
            df['y'] = df['value']
            df = df[['ds', 'y']].sort_values('ds')

            # Initialize and fit model
            model = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=True,
                daily_seasonality=True,
                changepoint_prior_scale=0.05  # Flexible trend changes
            )

            model.fit(df)
            self.models[sensor_key] = model

            # Calculate dynamic threshold based on historical data
            # Failure threshold: mean + 2*std of residuals or 95th percentile
            forecast = model.predict(df[['ds']])
            residuals = df['y'] - forecast['yhat']
            threshold = max(
                forecast['yhat'].mean() + 2 * residuals.std(),
                np.percentile(df['y'], 95)
            )
            self.thresholds[sensor_key] = threshold

            logger.info(f"Trained model for {sensor_key} with threshold {threshold:.2f}")
            return True

        except Exception as e:
            logger.error(f"Failed to train model for {sensor_key}: {e}")
            return self._train_statistical_model(sensor_key, data)

    def _train_statistical_model(self, sensor_key: str, data: List[Dict]) -> bool:
        """Fallback: Train using simple statistical approach."""
        try:
            if len(data) < 10:
                return False

            values = [d['value'] for d in data]
            mean = np.mean(values)
            std = np.std(values)

            # Threshold: mean + 2*std (95th percentile)
            threshold = mean + 2 * std
            self.thresholds[sensor_key] = threshold

            logger.info(f"Trained statistical model for {sensor_key} with threshold {threshold:.2f}")
            return True
        except Exception as e:
            logger.error(f"Failed to train statistical model: {e}")
            return False

    def predict_failure(self, sensor_key: str, days_ahead: int = 7) -> Optional[Dict]:
        """
        Predict if equipment failure is likely in the next days.

        Args:
            sensor_key: Sensor identifier
            days_ahead: Number of days to forecast

        Returns:
            Dict with prediction results or None if no model
        """
        if sensor_key not in self.models and sensor_key not in self.thresholds:
            return None

        try:
            threshold = self.thresholds.get(sensor_key)
            if not threshold:
                return None

            # If Prophet model exists, use it
            if sensor_key in self.models and PROPHET_AVAILABLE:
                model = self.models[sensor_key]
                future_dates = pd.date_range(
                    start=datetime.now(),
                    periods=days_ahead * 24,  # Hourly predictions
                    freq='H'
                )
                future_df = pd.DataFrame({'ds': future_dates})
                forecast = model.predict(future_df)
                exceeding_points = forecast[forecast['yhat_upper'] > threshold]
            else:
                # Fallback: Simple threshold check
                exceeding_points = None

            if exceeding_points is not None and not exceeding_points.empty:
                first_exceedance = exceeding_points.iloc[0]
                days_to_failure = (first_exceedance['ds'] - datetime.now()).days

                return {
                    'sensor_key': sensor_key,
                    'predicted_failure_date': first_exceedance['ds'].isoformat(),
                    'days_to_failure': max(1, days_to_failure),
                    'predicted_value': first_exceedance['yhat'],
                    'threshold': threshold,
                    'confidence': min(0.95, 1 - abs(first_exceedance['yhat'] - threshold) / threshold)
                }

            return {
                'sensor_key': sensor_key,
                'status': 'normal',
                'next_check_days': days_ahead
            }

        except Exception as e:
            logger.error(f"Failed to predict for {sensor_key}: {e}")
            return None

    def get_maintenance_schedule(self, sensor_key: str) -> Optional[Dict]:
        """
        Generate maintenance schedule based on predictions.

        Returns:
            Dict with recommended maintenance actions
        """
        prediction = self.predict_failure(sensor_key)
        if not prediction or prediction.get('status') == 'normal':
            return {
                'action': 'routine_check',
                'priority': 'low',
                'schedule_days': 30
            }

        days_to_failure = prediction['days_to_failure']

        if days_to_failure <= 1:
            return {
                'action': 'emergency_maintenance',
                'priority': 'critical',
                'schedule_days': 0,
                'reason': f'Predicted failure in {days_to_failure} day(s)'
            }
        elif days_to_failure <= 3:
            return {
                'action': 'urgent_maintenance',
                'priority': 'high',
                'schedule_days': days_to_failure,
                'reason': f'Predicted failure in {days_to_failure} day(s)'
            }
        else:
            return {
                'action': 'preventive_maintenance',
                'priority': 'medium',
                'schedule_days': max(7, days_to_failure - 3),
                'reason': f'Predicted failure in {days_to_failure} day(s)'
            }

    def update_model(self, sensor_key: str, new_data: List[Dict]) -> bool:
        """
        Update model with new data points.

        Args:
            new_data: New sensor readings

        Returns:
            bool: True if update successful
        """
        if sensor_key not in self.models:
            return self.train_model(sensor_key, new_data)

        try:
            # Retrain with combined data (simplified - in production, use incremental learning)
            # For now, just retrain
            return self.train_model(sensor_key, new_data)

        except Exception as e:
            logger.error(f"Failed to update model for {sensor_key}: {e}")
            return False

# Global instance
predictive_model = PredictiveMaintenanceModel()