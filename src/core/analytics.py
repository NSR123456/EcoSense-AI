import numpy as np
import pandas as pd


def _safe_scalar(bdf: pd.DataFrame, col: str) -> float | None:
    if col not in bdf.columns:
        return None
    series = bdf[col].dropna()
    if series.empty:
        return None
    try:
        return float(series.iloc[0])
    except Exception:
        return None


def compute_building_metrics(bdf: pd.DataFrame) -> dict:
    if bdf.empty:
        return _empty_metrics()

    col = "consumption_kwh" if "consumption_kwh" in bdf.columns else bdf.select_dtypes("number").columns[0]
    values = bdf[col].dropna()

    if values.empty:
        return _empty_metrics()

    avg_val = float(values.mean())
    min_val = float(values.min())
    max_val = float(values.max())
    std_val = float(values.std()) if len(values) > 1 else 0.0
    var_ratio = std_val / avg_val if avg_val > 0 else 0.0

    if len(values) >= 3:
        x = np.arange(len(values))
        slope = np.polyfit(x, values.values, 1)[0]
        if slope > 0.5:
            trend = "increasing"
        elif slope < -0.5:
            trend = "decreasing"
        else:
            trend = "stable"
    else:
        slope = 0.0
        trend = "stable"

    if std_val > 0:
        z_scores = np.abs((values - avg_val) / std_val)
        anomaly_count = int((z_scores > 2).sum())
    else:
        anomaly_count = 0

    first_date = last_date = peak_day = ""
    if "date" in bdf.columns:
        first_date = str(bdf["date"].min().date())
        last_date = str(bdf["date"].max().date())
        peak_idx = values.idxmax()
        peak_day = str(bdf.loc[peak_idx, "date"].date()) if peak_idx in bdf.index else ""

    area_sqft = _safe_scalar(bdf, "area_sqft")
    num_flats = _safe_scalar(bdf, "num_flats")
    occupancy = _safe_scalar(bdf, "occupancy")
    building_type = str(bdf["building_type"].dropna().iloc[0]) if "building_type" in bdf.columns and not bdf["building_type"].dropna().empty else "unknown"

    avg_per_sqft = avg_val / area_sqft if area_sqft and area_sqft > 0 else None
    avg_per_flat = avg_val / num_flats if num_flats and num_flats > 0 else None
    avg_per_occupant = avg_val / occupancy if occupancy and occupancy > 0 else None

    return {
        "total_records": len(bdf),
        "first_date": first_date,
        "last_date": last_date,
        "avg_consumption": avg_val,
        "min_consumption": min_val,
        "max_consumption": max_val,
        "std_dev": std_val,
        "variability_ratio": var_ratio,
        "trend": trend,
        "trend_slope": float(slope),
        "anomaly_count": anomaly_count,
        "peak_day": peak_day,
        "building_context": {
            "building_type": building_type,
            "area_sqft": area_sqft,
            "num_flats": num_flats,
            "occupancy": occupancy,
        },
        "normalized_kpis": {
            "avg_kwh_per_sqft": avg_per_sqft,
            "avg_kwh_per_flat": avg_per_flat,
            "avg_kwh_per_occupant": avg_per_occupant,
            "normalization_available": any(v is not None for v in [avg_per_sqft, avg_per_flat, avg_per_occupant]),
        },
    }


def _empty_metrics() -> dict:
    return {
        "total_records": 0,
        "first_date": "",
        "last_date": "",
        "avg_consumption": 0.0,
        "min_consumption": 0.0,
        "max_consumption": 0.0,
        "std_dev": 0.0,
        "variability_ratio": 0.0,
        "trend": "stable",
        "trend_slope": 0.0,
        "anomaly_count": 0,
        "peak_day": "",
        "building_context": {
            "building_type": "unknown",
            "area_sqft": None,
            "num_flats": None,
            "occupancy": None,
        },
        "normalized_kpis": {
            "avg_kwh_per_sqft": None,
            "avg_kwh_per_flat": None,
            "avg_kwh_per_occupant": None,
            "normalization_available": False,
        },
    }