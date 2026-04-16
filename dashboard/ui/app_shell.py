"""Shared layout, theme, and assistant-style surfaces for the Streamlit dashboard."""

from __future__ import annotations

import html
import json
from datetime import datetime


def inject_theme() -> None:
    import streamlit as st

    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&display=swap');

        /* Fonts only — colors come from .streamlit/config.toml [theme] / [theme.sidebar]. */
        .stApp {
            font-family: "DM Sans", system-ui, -apple-system, sans-serif;
            scroll-behavior: smooth;
        }

        /* Backup: soft green sidebar shell only (do not paint every nested div — keeps inputs white). */
        section[data-testid="stSidebar"] {
            background-color: #d1fae5 !important;
            color: #000000 !important;
        }
        section[data-testid="stSidebar"] > div {
            background-color: #d1fae5 !important;
        }
        section[data-testid="stSidebar"] .stMarkdown,
        section[data-testid="stSidebar"] .stMarkdown p,
        section[data-testid="stSidebar"] .stCaption,
        section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {
            color: #000000 !important;
        }
        /* Inputs / select: white field, black text */
        section[data-testid="stSidebar"] input,
        section[data-testid="stSidebar"] textarea,
        section[data-testid="stSidebar"] [data-baseweb="select"] > div {
            background-color: #ffffff !important;
            color: #000000 !important;
            border-color: #94a3b8 !important;
        }

        /* Buttons (not tabs, not radio segments): red background, white label */
        section[data-testid="stSidebar"] button:not([data-baseweb="tab"]):not([role="radio"]),
        [data-testid="stAppViewContainer"] > .main button:not([data-baseweb="tab"]):not([role="tab"]) {
            background-color: #dc2626 !important;
            color: #ffffff !important;
            border: 1px solid #b91c1c !important;
        }
        section[data-testid="stSidebar"] button:not([data-baseweb="tab"]):not([role="radio"]):hover,
        [data-testid="stAppViewContainer"] > .main button:not([data-baseweb="tab"]):not([role="tab"]):hover {
            background-color: #b91c1c !important;
            border-color: #991b1b !important;
        }

        /* Analysis mode & other radios: black text; segmented pills are not red CTAs */
        section[data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stWidgetLabel"] p,
        section[data-testid="stSidebar"] [data-testid="stRadio"] label,
        section[data-testid="stSidebar"] [data-testid="stRadio"] label p,
        section[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label,
        section[data-testid="stSidebar"] [data-testid="stRadio"] [data-baseweb="radio"] label,
        section[data-testid="stSidebar"] [data-testid="stRadio"] span,
        section[data-testid="stSidebar"] [data-testid="stRadio"] p {
            color: #000000 !important;
        }
        section[data-testid="stSidebar"] [data-testid="stRadio"] button {
            background-color: #ffffff !important;
            color: #000000 !important;
            border: 1px solid #475569 !important;
            font-weight: 700 !important;
        }
        section[data-testid="stSidebar"] [data-testid="stRadio"] button:hover {
            background-color: #f1f5f9 !important;
            color: #000000 !important;
        }
        section[data-testid="stSidebar"] [data-testid="stRadio"] button[aria-checked="true"] {
            background-color: #ecfdf5 !important;
            color: #000000 !important;
            border: 2px solid #000000 !important;
            box-shadow: none !important;
        }

        [data-testid="stAppViewContainer"] > .main {
            color: #000000 !important;
        }
        [data-testid="stAppViewContainer"] > .main .stMarkdown,
        [data-testid="stAppViewContainer"] > .main .stMarkdown p {
            color: #000000 !important;
        }
        /* Do not let global black text override hero strip / chart title (HTML blocks). */
        [data-testid="stAppViewContainer"] > .main .stMarkdown .ecosense-header-bar,
        [data-testid="stAppViewContainer"] > .main .stMarkdown .ecosense-header-bar p,
        [data-testid="stAppViewContainer"] > .main .stMarkdown .ecosense-header-bar span {
            color: #ffffff !important;
        }
        [data-testid="stAppViewContainer"] > .main .stMarkdown .ecosense-chart-title-bar {
            color: #ffffff !important;
        }

        [data-testid="stAppViewContainer"] > .main div[data-testid="stVerticalBlockBorderWrapper"] > div {
            border-radius: 14px !important;
        }

        /* Tabs: breathing room (Decision Center / Agent Theater / …) */
        [data-testid="stTabs"] {
            margin-top: 0.5rem;
        }
        [data-baseweb="tab-list"] {
            gap: 12px !important;
            padding: 12px 14px !important;
            flex-wrap: wrap !important;
            border-radius: 12px !important;
        }
        button[data-baseweb="tab"] {
            border-radius: 10px !important;
            font-weight: 600 !important;
            padding: 10px 18px !important;
            margin: 2px !important;
            min-height: 2.75rem !important;
            /* Undo global red-button rule for tabs */
            background-color: #ecfdf5 !important;
            color: #000000 !important;
            border: 1px solid #bbf7d0 !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            background-color: #ffffff !important;
            color: #000000 !important;
            border: 1px solid #86efac !important;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08);
        }

        /* Hero strip: bold white text on dark green for contrast */
        .ecosense-header-bar {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 16px;
            margin-bottom: 8px;
            background: linear-gradient(135deg, #064e3b 0%, #047857 45%, #0f766e 100%);
            padding: 14px 18px;
            border-radius: 12px;
            box-shadow: 0 6px 20px rgba(6, 78, 59, 0.35);
            border: 1px solid rgba(255, 255, 255, 0.14);
        }
        .ecosense-header-bar .ecosense-title {
            font-size: 1.55rem;
            font-weight: 800 !important;
            letter-spacing: -0.02em;
            color: #ffffff !important;
            margin: 0;
            line-height: 1.25;
        }
        .ecosense-header-bar .ecosense-sub {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 8px;
            font-size: 0.88rem;
            font-weight: 700 !important;
            color: #ffffff !important;
        }
        .ecosense-header-bar .ecosense-sub span:not(.ecosense-dot) {
            color: #ffffff !important;
        }
        .ecosense-header-bar .ecosense-dot {
            width: 8px;
            height: 8px;
            border-radius: 999px;
            background: #4ade80;
            box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.45);
        }
        .ecosense-header-bar .ecosense-dot.idle {
            background: #e2e8f0;
            box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.35);
        }
        .ecosense-header-bar .ecosense-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 12px;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.16);
            border: 1px solid rgba(255, 255, 255, 0.38);
            color: #ffffff !important;
            font-size: 0.72rem;
            font-weight: 800 !important;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }

        .ecosense-chart-title-bar {
            background: linear-gradient(135deg, #064e3b 0%, #047857 45%, #0f766e 100%);
            color: #ffffff !important;
            font-weight: 800 !important;
            font-size: 1.05rem;
            padding: 12px 16px;
            border-radius: 10px;
            margin: 0 0 10px 0;
            letter-spacing: 0.02em;
            border: 1px solid rgba(255, 255, 255, 0.14);
            box-shadow: 0 4px 12px rgba(6, 78, 59, 0.25);
        }

        /* Signed-in badge (sidebar): dark green bar, white text */
        .session-badge {
            background: linear-gradient(135deg, #064e3b 0%, #047857 55%, #0f766e 100%);
            color: #ffffff !important;
            padding: 12px 14px;
            border-radius: 10px;
            margin-bottom: 12px;
            font-size: 0.95rem;
            line-height: 1.45;
            border: 1px solid rgba(255, 255, 255, 0.18);
            box-shadow: 0 4px 14px rgba(6, 78, 59, 0.28);
        }
        .session-badge strong {
            color: #ffffff !important;
            font-weight: 800 !important;
        }
        .session-badge .session-role {
            color: #ecfdf5 !important;
            font-weight: 700 !important;
        }
        section[data-testid="stSidebar"] .session-badge,
        section[data-testid="stSidebar"] .session-badge span {
            color: #ffffff !important;
        }

        .assistant-user-bubble {
            background: linear-gradient(180deg, #e8f5e9 0%, #ecfdf5 100%);
            border: 1px solid #bbf7d0;
            border-radius: 16px;
            padding: 14px 16px;
            max-width: min(720px, 92%);
            margin-left: auto;
            box-shadow: 0 6px 18px rgba(15, 23, 42, 0.06);
        }
        .assistant-user-text {
            color: #0f172a;
            font-size: 0.98rem;
            line-height: 1.55;
            font-weight: 500;
        }
        .assistant-user-meta {
            margin-top: 10px;
            color: #64748b;
            font-size: 0.78rem;
            font-weight: 600;
        }
        .assistant-row {
            display: flex;
            gap: 12px;
            align-items: flex-start;
            margin-top: 14px;
        }
        .assistant-avatar {
            width: 44px;
            height: 44px;
            border-radius: 12px;
            background: linear-gradient(145deg, #22c55e, #059669);
            display: flex;
            align-items: center;
            justify-content: center;
            color: #fff;
            font-size: 1.15rem;
            font-weight: 800;
            box-shadow: 0 10px 22px rgba(5, 150, 105, 0.35);
            flex: 0 0 44px;
        }
        .assistant-card {
            flex: 1;
            background: linear-gradient(180deg, #f7fefb 0%, #f0fdf4 100%);
            border: 1px solid #bbf7d0;
            border-radius: 16px;
            padding: 14px 16px 16px;
            box-shadow: 0 12px 30px rgba(5, 150, 105, 0.1);
        }
        .assistant-card p {
            margin: 0 0 10px;
            color: #1e293b;
            font-size: 0.98rem;
            line-height: 1.55;
        }
        .assistant-metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 10px;
            margin-top: 12px;
        }
        .mini-metric {
            border-radius: 12px;
            border: 1px solid #d1fae5;
            background: #ecfdf5;
            padding: 10px 12px;
        }
        .mini-metric .label {
            font-size: 0.65rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            color: #64748b;
        }
        .mini-metric .value {
            margin-top: 6px;
            font-size: 1.05rem;
            font-weight: 800;
            color: #0f172a;
        }
        .mini-metric .value.warn { color: #dc2626; }
        .mini-metric .value.ok { color: #059669; }
        .mini-metric .sub {
            margin-top: 6px;
            font-size: 0.72rem;
            color: #64748b;
            font-weight: 600;
        }
        .mini-bars {
            display: flex;
            gap: 4px;
            align-items: flex-end;
            height: 36px;
            margin-top: 8px;
        }
        .mini-bars span {
            flex: 1;
            border-radius: 4px;
            background: #e2e8f0;
        }
        .mini-bars span.on {
            background: linear-gradient(180deg, #34d399, #059669);
        }
        .mini-bar-track {
            margin-top: 8px;
            height: 8px;
            border-radius: 999px;
            background: #e2e8f0;
            overflow: hidden;
        }
        .mini-bar-fill {
            height: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg, #34d399, #059669);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _confidence_ratio(resp: dict) -> float | None:
    card = resp.get("confidence_card") if isinstance(resp, dict) else None
    if not isinstance(card, dict):
        return None
    score = card.get("score")
    if isinstance(score, (int, float)):
        return max(0.0, min(1.0, float(score) / 100.0))
    return None


def render_assistant_brief(query: str, simple: str, technical: str, resp: dict) -> None:
    import streamlit as st

    ts = datetime.now().strftime("%I:%M %p")
    q = html.escape(query or "")
    s = html.escape(simple or "")
    tech = html.escape(technical or "")

    conf = _confidence_ratio(resp) or 0.72
    pct = int(round(conf * 100))
    issues = resp.get("issues", []) if isinstance(resp, dict) else []
    top_sev = str(issues[0].get("severity", "low")).lower() if issues else "low"
    sev_label = top_sev.title()
    delta_color = "warn" if top_sev == "high" else ("ok" if top_sev == "low" else "")

    bar_on = [False, top_sev != "low", top_sev == "high", top_sev == "high", False]
    bars_html = "".join(
        f"<span class='{'on' if on else ''}' style='height:{18 + i * 4}px;'></span>"
        for i, on in enumerate(bar_on)
    )

    st.markdown(
        f"""
        <div class="assistant-user-bubble">
            <div class="assistant-user-text">{q}</div>
            <div class="assistant-user-meta">🕒 {html.escape(ts)}</div>
        </div>
        <div class="assistant-row">
            <div class="assistant-avatar">✦</div>
            <div class="assistant-card">
                <p><strong>Operator brief:</strong> {s}</p>
                <p style="color:#475569;font-size:0.9rem;"><strong>Technical trace:</strong> {tech[:280]}{'…' if len(technical or '') > 280 else ''}</p>
                <div class="assistant-metrics">
                    <div class="mini-metric">
                        <div class="label">Decision strength</div>
                        <div class="value {delta_color}">{pct}%</div>
                        <div class="mini-bars">{bars_html}</div>
                    </div>
                    <div class="mini-metric">
                        <div class="label">Issue signal</div>
                        <div class="value {delta_color}">{html.escape(sev_label)}</div>
                        <div class="sub">Grounded on retrieval + meter statistics</div>
                        <div class="mini-bar-track"><div class="mini-bar-fill" style="width:{min(100, max(12, pct))}%;"></div></div>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_top_header(*, user: str, building_label: str | None, has_result: bool) -> None:
    """Hero header with status and session actions."""
    import streamlit as st

    node = building_label or "SESSION"
    status_idle = not has_result
    dot_cls = "ecosense-dot idle" if status_idle else "ecosense-dot"
    line = (
        f"RAG + LangGraph online · {html.escape(node)}"
        if not status_idle
        else "Awaiting workflow run — attach context in the rail, then execute"
    )

    transcript: bytes | None = None
    if has_result:
        payload = st.session_state.get("result")
        try:
            transcript = json.dumps(payload, indent=2, default=str).encode("utf-8")
        except Exception:
            transcript = str(payload).encode("utf-8")

    left, btn_export, btn_clear = st.columns([4.2, 1, 1], gap="small")
    with left:
        st.markdown(
            f"""
            <div class="ecosense-header-bar" style="margin-bottom:0;">
                <div>
                    <p class="ecosense-title">EcoSense Interactive Assistant</p>
                    <div class="ecosense-sub">
                        <span class="{dot_cls}"></span>
                        <span>{line}</span>
                        <span class="ecosense-pill">Signed in · {html.escape(user or '')}</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with btn_export:
        st.write("")  # align with title block
        if transcript:
            st.download_button(
                label="Export transcript",
                data=transcript,
                file_name=f"ecosense_transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True,
                key="hdr_export_transcript",
                type="primary",
            )
        else:
            st.caption(" ")
    with btn_clear:
        st.write("")
        if st.button("Clear session", use_container_width=True, key="hdr_clear_session", type="primary"):
            for k in ("result", "last_run_query", "last_run_building", "pdf_path", "last_mm_inputs", "last_operator_note"):
                st.session_state.pop(k, None)
            for k in ("agent_conv_key", "agent_live_count", "agent_user_thread", "agent_step_cursor"):
                st.session_state.pop(k, None)
            st.rerun()
