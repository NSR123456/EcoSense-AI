# Anomaly Detection Evaluation Report

**Evaluation Date:** 2026-06-14T23:58:46.632096  
**Framework:** EcoSense Energy Management AI Platform  
**Evaluation Type:** Simulated / Demonstration

## Configuration

- **Number of Evaluation Runs:** 5
- **Samples per Run:** 900
- **Injection Rate:** 1 fault per 5 samples
- **Total Evaluated Samples:** 4500
- **Average Injected Faults per Run:** 180.0

## Results Summary

### Aggregated Performance Metrics

| Metric | Value |
|--------|-------|
| Detection Precision | 0.9910 |
| Detection Recall | 0.3633 |
| F1-Score | 0.5313 |
| Avg True Positives | 65.4 |
| Avg False Positives | 0.6 |
| Avg False Negatives | 114.6 |

### Interpretation

- **Precision 99.1%**: Of anomalies flagged by the system, ~99% are true positives
- **Recall 36.3%**: The system catches ~36% of actual injected faults
- **F1-Score 0.5313**: Balanced measure of precision and recall

## Per-Run Breakdown


### Run 1
- Injected Faults: 180
- True Positives: 66
- False Positives: 1
- False Negatives: 114
- Precision: 0.9851
- Recall: 0.3667
- F1-Score: 0.5344

### Run 2
- Injected Faults: 180
- True Positives: 64
- False Positives: 0
- False Negatives: 116
- Precision: 1.0000
- Recall: 0.3556
- F1-Score: 0.5246

### Run 3
- Injected Faults: 180
- True Positives: 60
- False Positives: 0
- False Negatives: 120
- Precision: 1.0000
- Recall: 0.3333
- F1-Score: 0.5000

### Run 4
- Injected Faults: 180
- True Positives: 64
- False Positives: 2
- False Negatives: 116
- Precision: 0.9697
- Recall: 0.3556
- F1-Score: 0.5203

### Run 5
- Injected Faults: 180
- True Positives: 73
- False Positives: 0
- False Negatives: 107
- Precision: 1.0000
- Recall: 0.4056
- F1-Score: 0.5771


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

