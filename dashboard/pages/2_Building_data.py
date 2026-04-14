"""Admin page: building metadata and consumption (full width)."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import streamlit as st

from dashboard.building_store import (
    all_building_ids,
    clear_dataset_cache,
    load_energy_dataset,
    load_metadata,
    save_metadata,
)
from dashboard.paths import ENERGY_CSV_PATH, METADATA_PATH
from dashboard.ui.admin_ops import render_building_data_admin
from dashboard.ui.app_shell import inject_theme

st.set_page_config(page_title="Building data — EcoSense", page_icon="🏢", layout="wide")
inject_theme()

if "auth_user" not in st.session_state or st.session_state.get("auth_role") != "admin":
    st.error("This page is only available to signed-in administrators.")
    st.page_link("app.py", label="← Back to EcoSense dashboard", icon="🏠")
    st.stop()

df = load_energy_dataset()
building_ids = all_building_ids(df, METADATA_PATH)

st.title("Building data & consumption")
st.caption("Edit metadata in the table, append daily kWh rows, and review recent consumption.")
st.page_link("app.py", label="← Back to EcoSense dashboard", icon="🏠")
st.divider()

render_building_data_admin(
    metadata_path=METADATA_PATH,
    energy_path=ENERGY_CSV_PATH,
    building_ids=building_ids,
    load_metadata=load_metadata,
    save_metadata=save_metadata,
    clear_dataset_cache=clear_dataset_cache,
    key_prefix="pg_bd_",
)
