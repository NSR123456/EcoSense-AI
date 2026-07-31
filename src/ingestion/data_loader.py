import glob
import os
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("ENERGY_DATA_DIR", str(REPO_ROOT / "data" / "sample")))
METADATA_FILE = Path(
    os.getenv("BUILDING_METADATA_PATH", str(DATA_DIR / "ecosense_metadata.csv"))
)


def _normalize_energy_frame(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    if "timestamp" in df.columns and "date" not in df.columns:
        df = df.rename(columns={"timestamp": "date"})
    if "meter_reading" in df.columns and "consumption_kwh" not in df.columns:
        df = df.rename(columns={"meter_reading": "consumption_kwh"})

    if "building_id" in df.columns:
        df["building_id"] = df["building_id"].astype(str).str.strip()

    if "date" not in df.columns or "consumption_kwh" not in df.columns:
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if "meter" in df.columns:
        df = (
            df.groupby(["building_id", "date"], dropna=False)["consumption_kwh"]
            .sum()
            .reset_index()
        )

    return df[["building_id", "date", "consumption_kwh"]]


def _standardize_metadata(meta: pd.DataFrame) -> pd.DataFrame:
    meta = meta.copy()
    meta.columns = [c.strip().lower().replace(" ", "_") for c in meta.columns]

    if "square_feet" in meta.columns:
        meta = meta.rename(columns={"square_feet": "area_sqft"})
    if "primary_use" in meta.columns:
        meta = meta.rename(columns={"primary_use": "building_type"})
    if "floor_count" in meta.columns and "occupancy" not in meta.columns:
        meta["occupancy"] = meta["floor_count"]

    if "building_id" in meta.columns:
        meta["building_id"] = meta["building_id"].astype(str).str.strip()

    return meta


def load_dataset() -> pd.DataFrame:
    data_path = DATA_DIR
    files = sorted(glob.glob(str(data_path / "*.csv")))
    if not files:
        return pd.DataFrame()

    frames = []
    for f in files:
        try:
            df = pd.read_csv(f)
        except Exception as e:
            print(f"Failed to read {f}: {e}")
            continue

        normalized = _normalize_energy_frame(df)
        if normalized.empty:
            continue
        frames.append(normalized)

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)
    df = df.dropna(subset=["building_id", "date", "consumption_kwh"])
    df = df.sort_values(["building_id", "date"]).reset_index(drop=True)

    if os.path.exists(METADATA_FILE):
        try:
            meta = pd.read_csv(METADATA_FILE)
            meta = _standardize_metadata(meta)
            if "building_id" in meta.columns:
                keep = ["building_id", "area_sqft", "num_flats", "occupancy", "building_type"]
                keep = [c for c in keep if c in meta.columns]
                meta = meta[keep].drop_duplicates(subset=["building_id"])
                df = df.merge(meta, on="building_id", how="left")
        except Exception as e:
            print(f"Failed to load metadata {METADATA_FILE}: {e}")

    return df
