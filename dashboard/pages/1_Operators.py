"""Admin page: operator accounts (full width)."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import streamlit as st

from dashboard.ui.admin_ops import render_operator_management
from dashboard.ui.app_shell import inject_theme
from dashboard.user_store import hash_password, load_users, save_users

st.set_page_config(page_title="Operators — EcoSense", page_icon="👥", layout="wide")
inject_theme()

if "auth_user" not in st.session_state or st.session_state.get("auth_role") != "admin":
    st.error("This page is only available to signed-in administrators.")
    st.page_link("app.py", label="← Back to EcoSense dashboard", icon="🏠")
    st.stop()

st.title("Operators & accounts")
st.caption("Approve pending operators and create new operator logins.")
st.page_link("app.py", label="← Back to EcoSense dashboard", icon="🏠")
st.divider()

render_operator_management(
    load_users=load_users,
    save_users=save_users,
    hash_password=hash_password,
    key_prefix="pg_ops_",
)
