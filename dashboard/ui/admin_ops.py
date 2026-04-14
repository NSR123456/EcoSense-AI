"""Admin-only UI: session badge, operators, building data."""

from __future__ import annotations

import html
import os
from collections.abc import Callable
from datetime import date

import pandas as pd
import streamlit as st


def render_session_badge(username: str, role: str) -> None:
    u = html.escape(username or "")
    r = html.escape(role or "")
    st.markdown(
        f"""
        <div class="session-badge">
            Signed in: <strong>{u}</strong> <span class="session-role">({r})</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_operator_management(
    *,
    load_users: Callable[[], pd.DataFrame],
    save_users: Callable[[pd.DataFrame], None],
    hash_password: Callable[[str], str],
    key_prefix: str = "",
) -> None:
    kp = key_prefix
    st.subheader("Operators")
    users = load_users()
    if users.empty:
        st.warning("No users file.")
        return

    show = users.drop(columns=["password_hash"], errors="ignore").copy()
    show["approved"] = show["approved"].apply(lambda x: "yes" if _truthy(x) else "pending")
    show["active"] = show["active"].apply(lambda x: "yes" if _truthy(x) else "no")
    st.dataframe(show, use_container_width=True, hide_index=True)

    pending = users[
        (users["role"].str.lower() == "operator")
        & (users["approved"].apply(lambda x: not _truthy(x)))
    ]
    if not pending.empty:
        st.caption("Pending approval (cannot sign in until approved)")
        for _, row in pending.iterrows():
            uname = str(row["username"])
            c1, c2 = st.columns([3, 1])
            with c1:
                st.write(f"**{uname}** — operator")
            with c2:
                if st.button("Approve", key=f"{kp}approve_op_{uname}", type="primary"):
                    u2 = load_users()
                    u2.loc[u2["username"] == uname, "approved"] = 1
                    save_users(u2)
                    st.success(f"Approved {uname}.")
                    st.rerun()

    with st.expander("Add operator account", expanded=False):
        new_u = st.text_input("Username", key=f"{kp}admin_new_op_user")
        new_p = st.text_input("Temporary password", type="password", key=f"{kp}admin_new_op_pass")
        approve_now = st.checkbox("Approve immediately (can sign in)", value=True, key=f"{kp}admin_new_op_apr")
        if st.button("Create operator", key=f"{kp}admin_create_op", type="primary"):
            if not new_u.strip() or not new_p.strip():
                st.error("Username and password required.")
            else:
                u2 = load_users()
                if new_u.strip() in u2["username"].values:
                    st.error("Username already exists.")
                else:
                    ap = 1 if approve_now else 0
                    row = {
                        "username": new_u.strip(),
                        "password_hash": hash_password(new_p),
                        "role": "operator",
                        "active": 1,
                        "approved": ap,
                    }
                    u2 = pd.concat([u2, pd.DataFrame([row])], ignore_index=True)
                    save_users(u2)
                    st.success("Operator created.")
                    st.rerun()


def render_building_data_admin(
    *,
    metadata_path: str,
    energy_path: str,
    building_ids: list,
    load_metadata: Callable[[], pd.DataFrame],
    save_metadata: Callable[[pd.DataFrame], None],
    clear_dataset_cache: Callable[[], None],
    key_prefix: str = "",
) -> None:
    kp = key_prefix
    st.subheader("Building data")
    t1, t2 = st.tabs(["Metadata table", "Consumption rows"])

    with t1:
        meta = load_metadata()
        st.caption("Edit cells or add rows. Save applies to building_metadata.csv.")
        edited = st.data_editor(
            meta,
            num_rows="dynamic",
            use_container_width=True,
            key=f"{kp}admin_meta_editor",
        )
        if st.button("Save metadata table", key=f"{kp}admin_save_meta_tbl", type="primary"):
            if edited.empty or "building_id" not in edited.columns:
                st.error("Need at least building_id column.")
            else:
                edited = edited.copy()
                edited["building_id"] = edited["building_id"].astype(str).str.strip()
                edited = edited[edited["building_id"] != ""]
                save_metadata(edited)
                clear_dataset_cache()
                st.success("Metadata saved.")
                st.rerun()

    with t2:
        if not os.path.exists(energy_path):
            st.error(f"Missing file: {energy_path}")
            return
        eng = pd.read_csv(energy_path)
        eng.columns = [c.strip().lower().replace(" ", "_") for c in eng.columns]
        st.caption("Append a daily kWh row. Date format: YYYY-MM-DD.")
        c1, c2, c3 = st.columns(3)
        with c1:
            bid = st.selectbox("Building", options=building_ids or ["B001"], key=f"{kp}admin_eng_bid")
        with c2:
            d_default = date.today().isoformat()
            ds = st.text_input("Date", value=d_default, key=f"{kp}admin_eng_date")
        with c3:
            kwh = st.number_input("kWh", min_value=0.0, value=200.0, step=1.0, key=f"{kp}admin_eng_kwh")

        if st.button("Append consumption row", key=f"{kp}admin_append_eng", type="primary"):
            try:
                pd.to_datetime(ds)
            except Exception:
                st.error("Invalid date. Use YYYY-MM-DD.")
                return
            new = pd.DataFrame(
                [{"building_id": bid, "date": ds, "consumption_kwh": float(kwh)}]
            )
            out = pd.concat([eng, new], ignore_index=True)
            if "date" in out.columns:
                out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
            out.to_csv(energy_path, index=False)
            clear_dataset_cache()
            st.success(f"Row added for {bid} on {ds}.")
            st.rerun()

        st.markdown("**Recent rows (preview)**")
        tail = eng.sort_values("date", ascending=False).head(25) if "date" in eng.columns else eng.tail(25)
        st.dataframe(tail, use_container_width=True, hide_index=True)


def _truthy(val) -> bool:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return False
    s = str(val).strip().lower()
    return s in ("1", "1.0", "true", "yes")
