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
                "password_hash": "7d3c6b8d51ac8ec79a2adbf98045944f934c1279a57f689cd5ce997fc223b48e",
                "role": "operator",
                "active": 1,
                "approved": 1,
            },
            {
                "username": "operator2",
                "password_hash": "2465a128ca302ed5d3a3a2c232fa6895f02c62fb632deb33193ea12d4224dba7",
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


def list_operator_accounts() -> list[dict]:
    """Return all active, approved operator accounts ready to receive e-mail briefs.

    Each record contains at least ``username``, ``role``, ``active``, ``approved``,
    and an ``email`` field (derived from the username if no e-mail column is present).
    """

    users = load_users()
    if users.empty:
        return []

    operators = users[users["role"].astype(str).str.lower() == "operator"].copy()
    operators = operators[operators["active"].apply(is_active_row)]
    operators = operators[operators["approved"].apply(is_active_row)]

    if "email" not in operators.columns:
        operators["email"] = ""

    records = operators.to_dict(orient="records")
    for rec in records:
        uname = str(rec.get("username") or "").strip()
        email_val = str(rec.get("email") or "").strip()
        if not email_val and "@" not in uname:
            rec["email"] = f"{uname}@ecosense.local"
        elif not email_val:
            rec["email"] = uname
    return records
