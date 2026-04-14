"""User accounts CSV (operators, admin, approval)."""

from __future__ import annotations

import hashlib
import os

import pandas as pd

from dashboard.paths import USERS_PATH


def _ensure_users_file():
    if os.path.exists(USERS_PATH):
        return
    os.makedirs(os.path.dirname(USERS_PATH), exist_ok=True)
    defaults = pd.DataFrame(
        [
            {
                "username": "admin",
                "password_hash": "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9",
                "role": "admin",
                "active": 1,
                "approved": 1,
            },
            {
                "username": "operator1",
                "password_hash": "ec6e1c25258002eb1c67d15c7f45da7945fa4c58778fd7d88faa5e53e3b4698d",
                "role": "operator",
                "active": 1,
                "approved": 1,
            },
            {
                "username": "operator2",
                "password_hash": "b0047eb4e18d64c5fd32b310f604764da43a61d8a9a742c158fb8f3e6119b869",
                "role": "operator",
                "active": 1,
                "approved": 1,
            },
        ]
    )
    defaults.to_csv(USERS_PATH, index=False)


def load_users() -> pd.DataFrame:
    _ensure_users_file()
    try:
        users = pd.read_csv(USERS_PATH, comment="#")
    except Exception:
        return pd.DataFrame(columns=["username", "password_hash", "role", "active", "approved"])
    users.columns = [c.strip().lower().replace(" ", "_") for c in users.columns]
    for col in ["username", "password_hash", "role", "active", "approved"]:
        if col not in users.columns:
            users[col] = 1 if col == "approved" else ""
    users = users[["username", "password_hash", "role", "active", "approved"]].copy()
    users["username"] = users["username"].astype(str).str.strip()
    users["password_hash"] = users["password_hash"].astype(str).str.strip()
    users["approved"] = pd.to_numeric(users["approved"], errors="coerce").fillna(1).astype(int)
    users.loc[users["role"].str.lower() == "admin", "approved"] = 1
    users = users[~users["username"].str.startswith("#", na=False)]
    users = users[users["username"].notna() & (users["username"] != "nan")]
    return users


def save_users(users: pd.DataFrame) -> None:
    os.makedirs(os.path.dirname(USERS_PATH), exist_ok=True)
    out = users.copy()
    for col in ["username", "password_hash", "role", "active", "approved"]:
        if col not in out.columns:
            out[col] = 1 if col == "approved" else ""
    out = out[["username", "password_hash", "role", "active", "approved"]]
    out.to_csv(USERS_PATH, index=False)


def hash_password(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def is_active_row(val) -> bool:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return False
    s = str(val).strip().lower()
    return s in ("1", "1.0", "true", "yes")


def authenticate(username: str, password: str) -> tuple[bool, str]:
    """Returns (ok, role_or_reason). role is admin/operator on success; 'pending' if operator not approved."""
    users = load_users()
    uname = username.strip()
    rec = users[(users["username"] == uname) & (users["active"].apply(is_active_row))]
    if rec.empty:
        return False, ""
    expected = str(rec["password_hash"].iloc[0]).strip()
    if hash_password(password) != expected:
        return False, ""
    role = str(rec["role"].iloc[0]).strip().lower()
    if role == "operator":
        ap = rec["approved"].iloc[0]
        if not is_active_row(ap):
            return False, "pending"
    return True, role
