#!/usr/bin/env python3
"""
Anomaly Detection Evaluation Runner

Executes the streaming evaluation framework and generates performance reports
matching the structure described in research papers.

Usage:
    python scripts/run_anomaly_evaluation.py --num-samples 900 --injection-rate 0.2 --runs 5
"""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from src.evaluation.streaming_evaluator import (
    StreamingEvaluator,
    print_evaluation_table
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EvaluationReporter:
    """Generates evaluation reports and saves results"""
    
    def __init__(self, output_dir: str = "outputs/evaluation"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_report(self, metrics: Dict[str, Any], single_run_metrics=None):
        """Generate comprehensive evaluation report"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        print("\n" + "="*80)
        print("ECOSENSE ANOMALY DETECTION EVALUATION - RESULTS REPORT")
        print("="*80)
        print(f"Evaluation Date: {datetime.now().isoformat()}")
        print(f"Framework: EcoSense Energy Management AI Platform")
        print(f"Evaluation Type: Simulated / Demonstration\n")
        
        # If single run provided, print detailed table
        if single_run_metrics:
            print_evaluation_table(single_run_metrics)
        
        # Print aggregated results
        print("AGGREGATED RESULTS FROM MULTIPLE RUNS")
        print("-"*80)
        print(f"Number of Evaluation Runs: {metrics['num_runs']}")
        print(f"Samples per Run: {metrics['samples_per_run']}")
        print(f"Injection Rate: 1 fault per {int(1/metrics['injection_rate'])} samples")
        print(f"Total Evaluated Samples: {metrics['num_runs'] * metrics['samples_per_run']}")
        print(f"Average Injected Faults per Run: {metrics['samples_per_run'] * metrics['injection_rate']:.1f}")
        print()
        print(f"Average Detection Precision: {metrics['average_precision']:.4f}")
        print(f"Average Detection Recall: {metrics['average_recall']:.4f}")
        print(f"Average F1-Score: {metrics['average_f1_score']:.4f}")
        if "average_roc_auc" in metrics:
            print(f"Average ROC AUC: {metrics['average_roc_auc']:.4f}")
        print(f"Average Detection Latency: {metrics['average_detection_latency_ms']:.2f} ms/sample")
        print(f"Average Total Runtime: {metrics['average_total_runtime_ms']:.2f} ms")
        print()
        print(f"Average TP per Run: {metrics['average_tp']:.1f}")
        print(f"Average FP per Run: {metrics['average_fp']:.1f}")
        print(f"Average FN per Run: {metrics['average_fn']:.1f}")
        print("="*80 + "\n")
        
        # Save to JSON
        report_data = {
            "timestamp": timestamp,
            "framework": "EcoSense",
            "evaluation_type": "Simulated / Demonstration",
            "evaluation_configuration": {
                "num_runs": metrics['num_runs'],
                "samples_per_run": metrics['samples_per_run'],
                "injection_rate": metrics['injection_rate'],
            },
            "aggregated_metrics": {
                "precision": metrics['average_precision'],
                "recall": metrics['average_recall'],
                "f1_score": metrics['average_f1_score'],
                "roc_auc": metrics.get('average_roc_auc'),
                "average_detection_latency_ms": metrics['average_detection_latency_ms'],
                "average_total_runtime_ms": metrics['average_total_runtime_ms'],
            },
            "per_run_results": metrics['all_runs']
        }
        
        json_file = self.output_dir / f"anomaly_evaluation_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        logger.info(f"Evaluation report saved to: {json_file}")
        
        # Also save as markdown for documentation
        md_file = self.output_dir / f"anomaly_evaluation_{timestamp}.md"
        try:
            self._save_markdown_report(md_file, metrics, single_run_metrics)
        except UnicodeEncodeError:
            # Fallback for systems with limited character encoding
            logger.warning("Could not save markdown report with full Unicode support")
        
        return report_data
    
    def _save_markdown_report(self, filepath: Path, metrics: Dict[str, Any], single_run_metrics=None):
        """Save results as markdown for documentation"""
        
        content = f"""# Anomaly Detection Evaluation Report

**Evaluation Date:** {datetime.now().isoformat()}  
**Framework:** EcoSense Energy Management AI Platform  
**Evaluation Type:** Simulated / Demonstration

## Configuration

- **Number of Evaluation Runs:** {metrics['num_runs']}
- **Samples per Run:** {metrics['samples_per_run']}
- **Injection Rate:** 1 fault per {int(1/metrics['injection_rate'])} samples
- **Total Evaluated Samples:** {metrics['num_runs'] * metrics['samples_per_run']}
- **Average Injected Faults per Run:** {metrics['samples_per_run'] * metrics['injection_rate']:.1f}

## Results Summary

### Aggregated Performance Metrics

| Metric | Value |
|--------|-------|
| Detection Precision | {metrics['average_precision']:.4f} |
| Detection Recall | {metrics['average_recall']:.4f} |
| F1-Score | {metrics['average_f1_score']:.4f} |
| ROC AUC | {metrics.get('average_roc_auc', 0.0):.4f} |
| Avg Detection Latency (ms/sample) | {metrics['average_detection_latency_ms']:.2f} |
| Avg Total Runtime (ms) | {metrics['average_total_runtime_ms']:.2f} |
| Avg True Positives | {metrics['average_tp']:.1f} |
| Avg False Positives | {metrics['average_fp']:.1f} |
| Avg False Negatives | {metrics['average_fn']:.1f} |

### Interpretation

- **Precision {metrics['average_precision']:.1%}**: Of anomalies flagged by the system, ~{metrics['average_precision']*100:.0f}% are true positives
- **Recall {metrics['average_recall']:.1%}**: The system catches ~{metrics['average_recall']*100:.0f}% of actual injected faults
- **F1-Score {metrics['average_f1_score']:.4f}**: Balanced measure of precision and recall

## Per-Run Breakdown

"""
        
        for i, run_metrics in enumerate(metrics['all_runs'], 1):
            content += f"""
### Run {i}
- Injected Faults: {run_metrics['total_injected_faults']}
- True Positives: {run_metrics['true_positives']}
- False Positives: {run_metrics['false_positives']}
- False Negatives: {run_metrics['false_negatives']}
- Precision: {run_metrics['precision']:.4f}
- Recall: {run_metrics['recall']:.4f}
- F1-Score: {run_metrics['f1_score']:.4f}
- ROC AUC: {run_metrics.get('roc_auc', 0.0):.4f}
- Avg Detection Latency (ms/sample): {run_metrics.get('average_detection_latency_ms', 0.0):.2f}
- Total Runtime (ms): {run_metrics.get('total_runtime_ms', 0.0):.2f}
"""
        
        content += f"""

## System Description

The AnalystAgent detection pipeline combines:
1. **Deterministic flag monitoring** - Real-time threshold checks
2. **Automated baseline deviation checks** - Z-score statistical analysis (threshold: 2 standard deviations)

Anomalies are detected when consumption readings deviate from rolling baseline by >2 standard deviations.

## Notes

- Evaluation is conducted on simulated/synthetic data injected into the streaming pipeline
- Ground truth labels are known for accuracy calculation
- Fault injection follows a uniform random distribution across the stream
- Each fault is either a consumption spike (1.5-2.5x normal) or dip (0.1-0.5x normal)

"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Markdown report saved to: {filepath}")


def main():
    parser = argparse.ArgumentParser(
        description="Run anomaly detection evaluation on simulated streams"
    )
    parser.add_argument(
        "--num-samples",
        type=int,
        default=900,
        help="Number of samples per evaluation run (default: 900)"
    )
    parser.add_argument(
        "--injection-rate",
        type=float,
        default=0.2,
        help="Fault injection rate (default: 0.2 = 1 fault per 5 samples)"
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=5,
        help="Number of evaluation runs to aggregate (default: 5)"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=2.0,
        help="Z-score threshold for anomaly detection (default: 2.0)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs/evaluation",
        help="Output directory for reports (default: outputs/evaluation)"
    )
    
    args = parser.parse_args()
    
    logger.info("="*80)
    logger.info("EcoSense Anomaly Detection Evaluation")
    logger.info("="*80)
    logger.info(f"Configuration:")
    logger.info(f"  - Samples per run: {args.num_samples}")
    logger.info(f"  - Injection rate: {args.injection_rate} (1 fault per {int(1/args.injection_rate)} samples)")
    logger.info(f"  - Number of runs: {args.runs}")
    logger.info(f"  - Z-score threshold: {args.threshold}")
    logger.info("")
    
    # Initialize evaluator and run evaluation
    evaluator = StreamingEvaluator(detector_threshold=args.threshold)
    
    # Run single evaluation for detailed output
    logger.info("Running detailed single evaluation...")
    single_metrics, stream_data, ground_truth, detections = evaluator.evaluate(
        num_samples=args.num_samples,
        injection_rate=args.injection_rate
    )
    
    logger.info(f"Single run results:")
    logger.info(f"  - Precision: {single_metrics.detection_precision:.4f}")
    logger.info(f"  - Recall: {single_metrics.detection_recall:.4f}")
    logger.info(f"  - F1-Score: {single_metrics.f1_score:.4f}")
    
    # Run multiple evaluations for aggregated metrics
    logger.info(f"\nRunning {args.runs} evaluation runs for aggregation...")
    aggregated_metrics = evaluator.evaluate_multiple_runs(
        num_runs=args.runs,
        num_samples=args.num_samples,
        injection_rate=args.injection_rate
    )
    
    # Generate and save reports
    reporter = EvaluationReporter(output_dir=args.output_dir)
    report_data = reporter.generate_report(aggregated_metrics, single_metrics)
    
    # Save stream data for analysis
    stream_file = Path(args.output_dir) / f"evaluation_stream_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(stream_file, 'w') as f:
        json.dump({
            "ground_truth": [bool(x) for x in ground_truth],
            "detections": [bool(x) for x in detections],
            "stream_sample": stream_data[:100]  # Save first 100 records as sample
        }, f, indent=2)
    logger.info(f"Stream data saved to: {stream_file}")
    
    logger.info("\n" + "="*80)
    logger.info("Evaluation Complete!")
    logger.info("="*80)
    
    return report_data


if __name__ == "__main__":
    main()
