"""
Streaming Evaluation Framework for Anomaly Detection

Generates synthetic datasets, injects faults, and evaluates AnalystAgent
detection performance against ground truth.
"""

import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, asdict
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class EvaluationMetrics:
    """Container for confusion matrix and detection metrics"""
    total_samples: int
    total_injected_faults: int
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int
    auc: float | None = None
    average_detection_latency_ms: float | None = None
    total_runtime_ms: float | None = None
    
    @property
    def detection_precision(self) -> float:
        """TP / (TP + FP)"""
        denominator = self.true_positives + self.false_positives
        return self.true_positives / denominator if denominator > 0 else 0.0
    
    @property
    def detection_recall(self) -> float:
        """TP / (TP + FN)"""
        denominator = self.true_positives + self.false_negatives
        return self.true_positives / denominator if denominator > 0 else 0.0
    
    @property
    def f1_score(self) -> float:
        """2 * (precision * recall) / (precision + recall)"""
        p = self.detection_precision
        r = self.detection_recall
        denominator = p + r
        return (2 * p * r) / denominator if denominator > 0 else 0.0
    
    @property
    def specificity(self) -> float:
        """TN / (TN + FP)"""
        denominator = self.true_negatives + self.false_positives
        return self.true_negatives / denominator if denominator > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        output = {
            "total_samples": self.total_samples,
            "total_injected_faults": self.total_injected_faults,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "true_negatives": self.true_negatives,
            "precision": round(self.detection_precision, 4),
            "recall": round(self.detection_recall, 4),
            "f1_score": round(self.f1_score, 4),
            "specificity": round(self.specificity, 4),
        }
        if self.auc is not None:
            output["roc_auc"] = round(self.auc, 4)
        if self.average_detection_latency_ms is not None:
            output["average_detection_latency_ms"] = round(self.average_detection_latency_ms, 2)
        if self.total_runtime_ms is not None:
            output["total_runtime_ms"] = round(self.total_runtime_ms, 2)
        return output


class SyntheticStreamGenerator:
    """Generates synthetic energy consumption streams with injected faults"""
    
    def __init__(self, seed: int = 42, baseline_mean: float = 200.0, baseline_std: float = 30.0):
        """
        Initialize generator
        
        Args:
            seed: Random seed for reproducibility
            baseline_mean: Mean consumption kWh
            baseline_std: Standard deviation of baseline
        """
        self.rng = np.random.RandomState(seed)
        self.baseline_mean = baseline_mean
        self.baseline_std = baseline_std
    
    def generate_stream(self, 
                       num_samples: int = 900, 
                       injection_rate: float = 1/5) -> Tuple[List[Dict], List[bool]]:
        """
        Generate synthetic energy stream with injected faults
        
        Args:
            num_samples: Number of samples (default 900)
            injection_rate: Probability of fault at each step (default 1/5)
        
        Returns:
            Tuple of (stream_data, ground_truth_labels)
            - stream_data: List of dicts with timestamp, building_id, consumption_kwh, baseline
            - ground_truth_labels: List of bools indicating actual anomaly (True=fault, False=normal)
        """
        num_faults = int(num_samples * injection_rate)
        fault_indices = self.rng.choice(num_samples, size=num_faults, replace=False)
        fault_set = set(fault_indices)
        
        stream_data = []
        ground_truth = []
        
        base_time = datetime(2026, 1, 1, 0, 0, 0)
        
        for i in range(num_samples):
            timestamp = base_time + timedelta(minutes=i*15)  # 15-min intervals
            
            # Generate baseline consumption
            normal_consumption = self.rng.normal(self.baseline_mean, self.baseline_std)
            normal_consumption = max(50, normal_consumption)  # Ensure positive
            
            if i in fault_set:
                # Inject fault: spike or dip
                fault_type = self.rng.choice(['spike', 'dip'])
                if fault_type == 'spike':
                    consumption = normal_consumption * self.rng.uniform(1.5, 2.5)
                else:
                    consumption = normal_consumption * self.rng.uniform(0.1, 0.5)
                is_anomaly = True
            else:
                consumption = normal_consumption
                is_anomaly = False
            
            record = {
                "timestamp": timestamp.isoformat(),
                "building_id": "B001",
                "consumption_kwh": round(consumption, 2),
                "baseline": round(self.baseline_mean, 2),
                "sensor_type": "energy_meter"
            }
            
            stream_data.append(record)
            ground_truth.append(is_anomaly)
        
        return stream_data, ground_truth


class AnomalyDetector:
    """Implements z-score based anomaly detection (mimics AnalystAgent detection)"""
    
    def __init__(self, threshold: float = 2.0, window_size: int = 20):
        """
        Initialize detector
        
        Args:
            threshold: Z-score threshold (default 2.0 = ~95% confidence)
            window_size: Rolling window for mean/std calculation
        """
        self.threshold = threshold
        self.window_size = window_size
    
    def score_anomalies(self, stream_data: List[Dict]) -> List[float]:
        """Compute anomaly scores using rolling z-score."""
        consumptions = np.array([r["consumption_kwh"] for r in stream_data])
        scores = []

        for i in range(len(consumptions)):
            start_idx = max(0, i - self.window_size)
            window = consumptions[start_idx:i+1]
            if len(window) < 2:
                scores.append(0.0)
                continue

            mean = np.mean(window)
            std = np.std(window)
            z_score = abs((consumptions[i] - mean) / std) if std > 0 else 0.0
            scores.append(z_score)

        return scores

    def detect_anomalies(self, stream_data: List[Dict], return_scores: bool = False) -> List[bool] | Tuple[List[bool], List[float]]:
        """
        Detect anomalies using z-score method
        
        Args:
            stream_data: List of consumption records
            return_scores: If True, also return raw anomaly scores
        
        Returns:
            List of detection results or tuple(results, scores)
        """
        scores = self.score_anomalies(stream_data)
        detections = [score > self.threshold for score in scores]

        if return_scores:
            return detections, scores
        return detections


class StreamingEvaluator:
    """Evaluates anomaly detection on simulated streams"""
    
    def __init__(self, detector_threshold: float = 2.0):
        """
        Initialize evaluator
        
        Args:
            detector_threshold: Z-score threshold for anomaly detection
        """
        self.detector = AnomalyDetector(threshold=detector_threshold)
        self.generator = SyntheticStreamGenerator()
    
    def _compute_auc(self, ground_truth: List[bool], scores: List[float]) -> float:
        """Compute ROC AUC from ground truth labels and anomaly scores."""
        y_true = np.array(ground_truth, dtype=int)
        y_score = np.array(scores, dtype=float)

        # Sort by score descending
        desc_idx = np.argsort(-y_score)
        y_true = y_true[desc_idx]
        y_score = y_score[desc_idx]

        # True positive / false positive rates
        pos = y_true.sum()
        neg = len(y_true) - pos
        if pos == 0 or neg == 0:
            return 0.0

        tprs = [0.0]
        fprs = [0.0]
        tp = 0
        fp = 0
        last_score = None

        for yi, score in zip(y_true, y_score):
            if last_score is None or score != last_score:
                tprs.append(tp / pos)
                fprs.append(fp / neg)
                last_score = score
            if yi == 1:
                tp += 1
            else:
                fp += 1

        tprs.append(tp / pos)
        fprs.append(fp / neg)

        return float(np.trapz(tprs, fprs))

    def evaluate(self, num_samples: int = 900, injection_rate: float = 1/5) -> Tuple[EvaluationMetrics, List[Dict], List[bool], List[bool]]:
        """
        Run complete evaluation: generate stream, detect anomalies, compute metrics
        
        Args:
            num_samples: Number of samples in stream
            injection_rate: Fault injection rate
        
        Returns:
            EvaluationMetrics object with TP/FP/FN/TN and derived metrics
        """
        start_time = time.perf_counter()

        # Generate synthetic stream
        stream_data, ground_truth = self.generator.generate_stream(num_samples, injection_rate)

        detection_start = time.perf_counter()
        detections, scores = self.detector.detect_anomalies(stream_data, return_scores=True)
        detection_end = time.perf_counter()

        runtime_end = time.perf_counter()

        # Compute confusion matrix
        tp = sum(1 for gt, det in zip(ground_truth, detections) if gt and det)
        fp = sum(1 for gt, det in zip(ground_truth, detections) if not gt and det)
        fn = sum(1 for gt, det in zip(ground_truth, detections) if gt and not det)
        tn = sum(1 for gt, det in zip(ground_truth, detections) if not gt and not det)

        total_faults = sum(ground_truth)

        auc = self._compute_auc(ground_truth, scores)
        detection_latency_ms = ((detection_end - detection_start) / len(stream_data)) * 1000 if stream_data else 0.0
        total_runtime_ms = (runtime_end - start_time) * 1000

        metrics = EvaluationMetrics(
            total_samples=num_samples,
            total_injected_faults=total_faults,
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            true_negatives=tn,
            auc=auc,
            average_detection_latency_ms=detection_latency_ms,
            total_runtime_ms=total_runtime_ms,
        )

        return metrics, stream_data, ground_truth, detections
    
    def evaluate_multiple_runs(self, 
                              num_runs: int = 5, 
                              num_samples: int = 900,
                              injection_rate: float = 1/5) -> Dict[str, Any]:
        """
        Run multiple evaluation trials and aggregate results
        
        Args:
            num_runs: Number of evaluation runs
            num_samples: Samples per run
            injection_rate: Fault injection rate
        
        Returns:
            Aggregated metrics and statistics
        """
        all_metrics = []
        
        for run in range(num_runs):
            metrics, _, _, _ = self.evaluate(num_samples, injection_rate)
            all_metrics.append(metrics)
            logger.info(f"Run {run+1}/{num_runs}: P={metrics.detection_precision:.3f}, "
                       f"R={metrics.detection_recall:.3f}, F1={metrics.f1_score:.3f}")
        
        # Aggregate
        avg_precision = np.mean([m.detection_precision for m in all_metrics])
        avg_recall = np.mean([m.detection_recall for m in all_metrics])
        avg_f1 = np.mean([m.f1_score for m in all_metrics])
        avg_auc = np.mean([m.auc for m in all_metrics if m.auc is not None]) if any(m.auc is not None for m in all_metrics) else None
        avg_latency = np.mean([m.average_detection_latency_ms for m in all_metrics if m.average_detection_latency_ms is not None])
        avg_runtime = np.mean([m.total_runtime_ms for m in all_metrics if m.total_runtime_ms is not None])
        avg_tp = np.mean([m.true_positives for m in all_metrics])
        avg_fp = np.mean([m.false_positives for m in all_metrics])
        avg_fn = np.mean([m.false_negatives for m in all_metrics])
        
        result = {
            "num_runs": num_runs,
            "samples_per_run": num_samples,
            "injection_rate": injection_rate,
            "average_precision": round(avg_precision, 4),
            "average_recall": round(avg_recall, 4),
            "average_f1_score": round(avg_f1, 4),
            "average_tp": round(avg_tp, 2),
            "average_fp": round(avg_fp, 2),
            "average_fn": round(avg_fn, 2),
            "average_detection_latency_ms": round(avg_latency, 2),
            "average_total_runtime_ms": round(avg_runtime, 2),
            "all_runs": [m.to_dict() for m in all_metrics]
        }
        if avg_auc is not None:
            result["average_roc_auc"] = round(avg_auc, 4)
        return result


def print_evaluation_table(metrics: EvaluationMetrics):
    """Pretty print evaluation metrics as table"""
    print("\n" + "="*70)
    print("SIMULATED ANOMALY DETECTION PERFORMANCE METRICS")
    print("="*70)
    print(f"{'Evaluation Metric':<35} {'Parameter':<20} {'Value':<15}")
    print("-"*70)
    print(f"{'Total Injected Fault Events':<35} {'N_fault':<20} {metrics.total_injected_faults:<15}")
    print(f"{'True Positive Detections':<35} {'TP':<20} {metrics.true_positives:<15}")
    print(f"{'False Positive Classifications':<35} {'FP':<20} {metrics.false_positives:<15}")
    print(f"{'False Negative Misses':<35} {'FN':<20} {metrics.false_negatives:<15}")
    print(f"{'True Negative Correct Rejections':<35} {'TN':<20} {metrics.true_negatives:<15}")
    print("-"*70)
    print(f"{'Detection Precision':<35} {'TP/(TP+FP)':<20} {metrics.detection_precision:.4f}")
    print(f"{'Detection Recall':<35} {'TP/(TP+FN)':<20} {metrics.detection_recall:.4f}")
    print(f"{'Calculated F1-Score':<35} {'2*P*R/(P+R)':<20} {metrics.f1_score:.4f}")
    print(f"{'Specificity':<35} {'TN/(TN+FP)':<20} {metrics.specificity:.4f}")
    if metrics.auc is not None:
        print(f"{'ROC AUC':<35} {'AUC':<20} {metrics.auc:.4f}")
    if metrics.average_detection_latency_ms is not None:
        print(f"{'Avg Detection Latency':<35} {'ms/sample':<20} {metrics.average_detection_latency_ms:.2f}")
    if metrics.total_runtime_ms is not None:
        print(f"{'Total Runtime':<35} {'ms':<20} {metrics.total_runtime_ms:.2f}")
    print("="*70 + "\n")
