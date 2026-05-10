"""Performance optimization utilities for Streamlit app."""

import streamlit as st
import pandas as pd
from functools import lru_cache
import time

# Cache expensive data operations
@st.cache_data(ttl=300)  # 5 minutes TTL
def get_cached_building_bundle(building_id: str):
    """Cached version of get_building_bundle to avoid repeated data loading."""
    from src.tools.analytics_tools import get_building_bundle
    return get_building_bundle(building_id)

@st.cache_data(ttl=60)  # 1 minute TTL for live data
def get_cached_stream_data(_db_manager, focus_building: str = None):
    """Cached stream data with building filter."""
    stream_data = _db_manager.read_tab("Active_Stream")
    if not stream_data:
        return pd.DataFrame()
    
    df = pd.DataFrame(stream_data)
    if focus_building and focus_building != "All":
        df = df[df["building_id"] == focus_building]
    return df

@st.cache_data(ttl=180)  # 3 minutes TTL
def get_cached_audit_data(_db_manager, focus_building: str = None):
    """Cached audit ledger data."""
    ledger_data = _db_manager.read_tab("Audit_Ledger")
    if not ledger_data:
        return pd.DataFrame()
    
    df = pd.DataFrame(ledger_data)
    if focus_building and focus_building != "All":
        df = df[df["building_id"] == focus_building]
    return df

@st.cache_resource
def load_ml_models():
    """Cache ML models to avoid reloading."""
    # Lazy load models only when needed
    models = {}
    try:
        # Add your model loading here
        # models['transformer'] = load_transformer_model()
        pass
    except Exception as e:
        print(f"Model loading failed: {e}")
    return models

class PerformanceMonitor:
    """Monitor and log performance metrics."""
    
    @staticmethod
    def time_function(func_name: str):
        """Decorator to time function execution."""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start = time.time()
                result = func(*args, **kwargs)
                duration = time.time() - start
                if duration > 1.0:  # Log slow operations
                    print(f"PERF: {func_name} took {duration:.2f}s")
                return result
            return wrapper
        return decorator

# Optimized data processing
def optimize_dataframe_memory(df: pd.DataFrame) -> pd.DataFrame:
    """Reduce memory usage of DataFrames."""
    for col in df.select_dtypes(include=['int64']).columns:
        df[col] = pd.to_numeric(df[col], downcast='integer')
    
    for col in df.select_dtypes(include=['float64']).columns:
        df[col] = pd.to_numeric(df[col], downcast='float')
    
    for col in df.select_dtypes(include=['object']).columns:
        if df[col].nunique() / len(df) < 0.5:  # Low cardinality
            df[col] = df[col].astype('category')
    
    return df
