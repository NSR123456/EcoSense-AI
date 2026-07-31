import os
from pathlib import Path

import numpy as np
import pandas as pd


def generate_sample_data(output_path=None, fault_probability=0.08, random_seed=42, buildings=None):
    """Generate synthetic energy data with randomized fault injection."""
    rng = np.random.default_rng(random_seed)

    base_dir = Path(__file__).resolve().parent.parent / "data" / "sample"
    base_dir.mkdir(parents=True, exist_ok=True)

    if buildings is None:
        buildings = {
            "B001": {"base": 220, "trend": 0.15, "var": 35, "spikes": [30, 90]},
            "B002": {"base": 180, "trend": -0.05, "var": 20, "spikes": []},
            "B003": {"base": 310, "trend": 0.25, "var": 55, "spikes": [15, 60, 120]},
            "B004": {"base": 150, "trend": 0.0, "var": 15, "spikes": []},
            "B005": {"base": 270, "trend": 0.10, "var": 45, "spikes": [45]},
        }

    rows = []
    for bid, cfg in buildings.items():
        dates = pd.date_range("2024-01-01", periods=180, freq="D")
        for i, d in enumerate(dates):
            val = cfg["base"] + cfg["trend"] * i + rng.normal(0, cfg["var"])
            if i in cfg["spikes"]:
                val += rng.uniform(80, 150)
            if d.weekday() >= 5:
                val -= 15

            injected_fault = bool(rng.random() < fault_probability)
            if injected_fault:
                val *= 1.0 + rng.uniform(0.2, 0.6)

            rows.append({
                "building_id": bid,
                "date": d.strftime("%Y-%m-%d"),
                "consumption_kwh": round(max(10, val), 2),
                "is_fault": injected_fault,
            })

    df = pd.DataFrame(rows)

    if output_path is None:
        output_path = base_dir / "building_energy.csv"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    if output_path.name == "building_energy.csv":
        multi_output = base_dir / "building_energy_multi.csv"
        df.to_csv(multi_output, index=False)

    return df


if __name__ == "__main__":
    output_dir = Path(__file__).resolve().parent.parent / "data" / "sample"
    generated = generate_sample_data()
    print(f"Created {output_dir / 'building_energy.csv'}")
    print(f"Generated {len(generated)} rows with {generated['is_fault'].sum()} fault injections")