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
            Dict with prediction results or None if no model.
            Keys returned (all present for both failure & normal states, with
            ``None`` fillers where not applicable so the UI caller has a stable schema):

            - ``sensor_key``
            - ``days_to_failure``  (int or None)
            - ``predicted_failure_time``  (ISO str or None, also available via alias ``predicted_failure_date``)
            - ``predicted_value``  (float or None)
            - ``threshold``  (float or None)
            - ``confidence_score``  (float 0..1, also available via alias ``confidence``)
            - ``failure_reason``  (human-readable str or None)
            - ``forecast``  (Prophet forecast DataFrame or None)
            - ``status``  (``'normal'`` or ``'failure_predicted'``)
        """
        base_result = {
            'sensor_key': sensor_key,
            'days_to_failure': None,
            'predicted_failure_time': None,
            'predicted_failure_date': None,
            'predicted_value': None,
            'threshold': self.thresholds.get(sensor_key),
            'confidence_score': 0.0,
            'confidence': 0.0,
            'failure_reason': None,
            'forecast': None,
            'status': 'normal',
        }

        if sensor_key not in self.models and sensor_key not in self.thresholds:
            return None

        try:
            threshold = base_result['threshold']
            if not threshold:
                return base_result

            forecast_df = None
            exceeding_points = None

            if sensor_key in self.models and PROPHET_AVAILABLE:
                model = self.models[sensor_key]
                future_dates = pd.date_range(
                    start=datetime.now(),
                    periods=days_ahead * 24,
                    freq='H'
                )
                future_df = pd.DataFrame({'ds': future_dates})
                forecast_df = model.predict(future_df)
                exceeding_points = forecast_df[forecast_df['yhat_upper'] > threshold]
            else:
                exceeding_points = None

            base_result['forecast'] = forecast_df

            if exceeding_points is not None and not exceeding_points.empty:
                first_exceedance = exceeding_points.iloc[0]
                exceed_ts = first_exceedance['ds']
                days_to_failure = (exceed_ts - datetime.now()).days
                d2f_clamped = max(1, days_to_failure)
                pred_value = float(first_exceedance['yhat'])
                confidence = float(min(0.95, 1 - abs(pred_value - threshold) / threshold))
                fail_ts_iso = exceed_ts.isoformat() if hasattr(exceed_ts, 'isoformat') else str(exceed_ts)

                base_result.update({
                    'days_to_failure': d2f_clamped,
                    'predicted_failure_time': fail_ts_iso,
                    'predicted_failure_date': fail_ts_iso,
                    'predicted_value': pred_value,
                    'confidence_score': confidence,
                    'confidence': confidence,
                    'failure_reason': f'Predicted {sensor_key} reading of {pred_value:.2f} exceeds failure threshold {threshold:.2f} in ~{d2f_clamped} day(s).',
                    'status': 'failure_predicted',
                })
                return base_result

            return base_result

        except Exception as e:
            logger.error(f"Failed to predict for {sensor_key}: {e}")
            return base_result

    def get_maintenance_schedule(self, sensor_key: str) -> Optional[Dict]:
        """
        Generate maintenance schedule based on predictions.

        Returns a dict with stable keys consumed by the forecasting panel:
        ``action``, ``priority``, ``schedule_days`` (int), ``scheduled_date`` (ISO date str
        or ``None`` for routine checks), ``reason``.
        """
        prediction = self.predict_failure(sensor_key) or {}
        d2f = prediction.get('days_to_failure')

        def _sched_date(days_offset: int) -> str:
            return (datetime.now() + timedelta(days=days_offset)).strftime('%Y-%m-%d')

        if not prediction or prediction.get('status') == 'normal' or d2f is None:
            return {
                'action': 'routine_check',
                'priority': 'low',
                'schedule_days': 30,
                'scheduled_date': _sched_date(30),
                'reason': 'No failure predicted within the current forecast window.'
            }

        if d2f <= 1:
            return {
                'action': 'emergency_maintenance',
                'priority': 'critical',
                'schedule_days': 0,
                'scheduled_date': _sched_date(0),
                'reason': prediction.get('failure_reason') or f'Predicted failure in {d2f} day(s)'
            }
        elif d2f <= 3:
            return {
                'action': 'urgent_maintenance',
                'priority': 'high',
                'schedule_days': d2f,
                'scheduled_date': _sched_date(d2f),
                'reason': prediction.get('failure_reason') or f'Predicted failure in {d2f} day(s)'
            }
        else:
            sched_days = max(7, d2f - 3)
            return {
                'action': 'preventive_maintenance',
                'priority': 'medium',
                'schedule_days': sched_days,
                'scheduled_date': _sched_date(sched_days),
                'reason': prediction.get('failure_reason') or f'Predicted failure in {d2f} day(s)'
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