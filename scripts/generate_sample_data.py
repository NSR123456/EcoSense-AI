import os
import numpy as np
import pandas as pd

np.random.seed(42)

base_dir = os.path.join(os.path.dirname(__file__), "..", "data", "sample")
os.makedirs(base_dir, exist_ok=True)
out_path = os.path.join(base_dir, "building_energy.csv")

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
        val = cfg["base"] + cfg["trend"] * i + np.random.normal(0, cfg["var"])
        if i in cfg["spikes"]:
            val += np.random.uniform(80, 150)
        if d.weekday() >= 5:
            val -= 15
        rows.append({
            "building_id": bid,
            "date": d.strftime("%Y-%m-%d"),
            "consumption_kwh": round(max(10, val), 2),
        })

pd.DataFrame(rows).to_csv(out_path, index=False)
print(f"Created {out_path}")