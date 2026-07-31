import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.generate_sample_data import generate_sample_data
from src.core.analytics import detect_anomalies_with_ml


def test_generate_sample_data_supports_randomized_faults(tmp_path):
    output_path = tmp_path / "building_energy.csv"
    df = generate_sample_data(output_path=output_path, fault_probability=1.0, random_seed=7)

    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "is_fault" in df.columns
    assert df["is_fault"].sum() > 0


def test_detect_anomalies_with_ml_marks_extreme_values():
    values = [100, 102, 101, 104, 103, 102, 105, 100, 99, 98, 97, 100, 450]
    labels = detect_anomalies_with_ml(values, contamination=0.05, window_size=6)

    assert bool(labels[-1])
