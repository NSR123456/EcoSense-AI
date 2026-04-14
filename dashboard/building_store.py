"""Building metadata, energy CSV, and cached dataset load."""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

import sys

from dashboard.paths import METADATA_PATH, ROOT
from src.ingestion.data_loader import load_dataset

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@st.cache_data
def load_energy_dataset():
    return load_dataset()


def clear_dataset_cache() -> None:
    load_energy_dataset.clear()


def load_metadata() -> pd.DataFrame:
    cols = ["building_id", "area_sqft", "num_flats", "occupancy", "building_type"]
    if os.path.exists(METADATA_PATH):
        try:
            meta = pd.read_csv(METADATA_PATH)
            meta.columns = [c.strip().lower().replace(" ", "_") for c in meta.columns]
            for col in cols:
                if col not in meta.columns:
                    meta[col] = None
            return meta[cols].copy()
        except Exception:
            pass
    return pd.DataFrame(columns=cols)


def save_metadata(meta_df: pd.DataFrame) -> None:
    os.makedirs(os.path.dirname(METADATA_PATH), exist_ok=True)
    meta_df.to_csv(METADATA_PATH, index=False)


def all_building_ids(energy_df: pd.DataFrame, meta_path: str) -> list:
    ids = set()
    if energy_df is not None and not energy_df.empty and "building_id" in energy_df.columns:
        ids |= set(energy_df["building_id"].astype(str).str.strip().unique())
    if os.path.exists(meta_path):
        try:
            m = pd.read_csv(meta_path)
            m.columns = [c.strip().lower().replace(" ", "_") for c in m.columns]
            if "building_id" in m.columns:
                ids |= set(m["building_id"].astype(str).str.strip().dropna().unique())
        except Exception:
            pass
    return sorted(ids)
