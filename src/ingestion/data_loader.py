import os
import glob
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sample")
METADATA_FILE = os.path.join(DATA_DIR, "building_metadata.csv")


def load_dataset() -> pd.DataFrame:
    files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    if not files:
        return pd.DataFrame()

    frames = []
    for f in files:
        try:
            df = pd.read_csv(f)
            cols = [c.strip().lower().replace(" ", "_") for c in df.columns]
            # Keep only time-series energy files in the primary dataset load path.
            if "building_id" in cols and "consumption_kwh" in cols and "date" in cols:
                frames.append(df)
        except Exception as e:
            print(f"Failed to load {f}: {e}")

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"]).sort_values(["building_id", "date"])

    # Optional metadata merge for normalization-friendly comparisons.
    if os.path.exists(METADATA_FILE):
        try:
            meta = pd.read_csv(METADATA_FILE)
            meta.columns = [c.strip().lower().replace(" ", "_") for c in meta.columns]
            if "building_id" in meta.columns:
                keep = ["building_id", "area_sqft", "num_flats", "occupancy", "building_type"]
                keep = [c for c in keep if c in meta.columns]
                meta = meta[keep].drop_duplicates(subset=["building_id"])
                df = df.merge(meta, on="building_id", how="left")
        except Exception as e:
            print(f"Failed to load metadata {METADATA_FILE}: {e}")

    return df