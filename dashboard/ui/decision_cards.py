import html
import streamlit as st
from src.services.automation_services import log_action_to_sheets, send_telegram_alert

def _send_action_to_n8n(action_details: dict):
    building_id = action_details.get("building_id") or "Unknown"
    source_doc = action_details.get("source_doc") or "EcoSense Analysis"
    finding_type = action_details.get("finding_type") or "Energy Optimization"
    savings_kwh = action_details.get("savings_kwh") or 0.0
    action = action_details.get("action") or action_details.get("title") or "Unknown"

    # Call Logging Service (Python-based)
    log_res = log_action_to_sheets(building_id, source_doc, finding_type, savings_kwh, action)
    if log_res["status"] == "success":
        st.success(f"Action '{action}' logged to Google Sheets!")
    else:
        st.error(log_res["message"])

    # Call Alerting Service (Python-based)
    alert_res = send_telegram_alert(building_id, source_doc, finding_type, savings_kwh, action)
    if alert_res["status"] == "success":
        st.info(f"Telegram alert sent for '{action}'!")
    else:
        st.error(alert_res["message"])

def _computed_risk_text(resp: dict) -> str:
    issues = resp.get("issues", [])
    metrics = resp.get("metrics", {})
    risk_level = str(issues[0].get("severity", "low")).title() if issues else "Low"
    anomalies = metrics.get("anomaly_count", 0)
    variability = metrics.get("variability_ratio", 0.0)
    return f"{risk_level} (anomalies={anomalies}, variability={variability:.2f})"


def _computed_top_issue_text(resp: dict) -> str:
    issues = resp.get("issues", [])
    if not issues:
        return "No issue"
    issue = issues[0]
    conf = issue.get("confidence")
    conf_txt = f"{int(round(conf * 100))}%" if isinstance(conf, (int, float)) else "N/A"
    return f"{issue.get('name', 'Issue')} (confidence={conf_txt})"


def render_decision_cards(resp: dict):
    st.markdown(
        """
        <style>
        .dc-card {
            position: relative;
            border: 1px solid #bbf7d0;
            border-radius: 14px;
            padding: 12px 14px 14px;
            background: linear-gradient(180deg, #f7fefb 0%, #ecfdf5 100%);
            min-height: 102px;
            box-shadow: 0 10px 26px rgba(5, 150, 105, 0.09);
            overflow: hidden;
        }
        .dc-card::before {
            content: "";
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 4px;
            background: var(--dc-accent, #94a3b8);
            opacity: 0.9;
        }
        .dc-title {
            font-size: 0.68rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #64748b;
            margin-bottom: 8px;
        }
        .dc-value {
            font-size: 0.98rem;
            font-weight: 700;
            color: #0f172a;
            line-height: 1.35;
            white-space: normal;
            word-break: break-word;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        risk = resp.get("risk_card", {})
        risk_title = html.escape(str(risk.get("title", "Energy Ops Risk (This Building)")))
        risk_value = str(risk.get("value", "N/A"))
        if "(" not in risk_value:
            risk_value = _computed_risk_text(resp)
        risk_value = html.escape(str(risk_value))
        st.markdown(
            f"<div class='dc-card' style='--dc-accent:#f97316'><div class='dc-title'>{risk_title}</div>"
            f"<div class='dc-value'>{risk_value}</div></div>",
            unsafe_allow_html=True,
        )

    with c2:
        card = resp.get("issue_card", {})
        issue_value = str(card.get("value", "N/A"))
        if "(confidence=" not in issue_value:
            issue_value = _computed_top_issue_text(resp)
        issue_title = html.escape(str(card.get("title", "Top Issue")))
        issue_value = html.escape(str(issue_value))
        st.markdown(
            f"<div class='dc-card' style='--dc-accent:#ef4444'><div class='dc-title'>{issue_title}</div>"
            f"<div class='dc-value'>{issue_value}</div></div>",
            unsafe_allow_html=True,
        )

    with c3:
        card = resp.get("cause_card", {})
        cause_title = html.escape(str(card.get("title", "Likely Cause")))
        cause_value = html.escape(str(card.get("value", "N/A")))
        st.markdown(
            f"<div class='dc-card' style='--dc-accent:#6366f1'><div class='dc-title'>{cause_title}</div>"
            f"<div class='dc-value'>{cause_value}</div></div>",
            unsafe_allow_html=True,
        )

    with c4:
        card = resp.get("action_card", {})
        act_title = html.escape(str(card.get("title", "Best Next Action")))
        act_value = html.escape(str(card.get("value", "N/A")))
        st.markdown(
            f"<div class='dc-card' style='--dc-accent:#059669'><div class='dc-title'>{act_title}</div>"
            f"<div class='dc-value'>{act_value}</div></div>",
            unsafe_allow_html=True,
        )

    st.caption(
        "Risk meaning: likelihood of operational energy inefficiency in the selected building "
        "(not financial, business, or grid risk)."
    )


def _label_color(level: str) -> str:
    color_map = {
        "high": "red",
        "medium": "orange",
        "low": "green",
    }
    return color_map.get(str(level).strip().lower(), "blue")


def render_issues_ui(issues: list):
    if not issues:
        st.info("No issues detected.")
        return

    for issue in issues:
        title = issue.get("name", "Unnamed issue")
        severity = str(issue.get("severity", "unknown")).lower()
        confidence = issue.get("confidence")

        with st.container(border=True):
            st.markdown(f"**{title}**")
            st.markdown(
                f":{_label_color(severity)}[Severity: {severity.title()}]"
            )
            if isinstance(confidence, (int, float)):
                st.caption(f"Confidence: {confidence:.0%}")
                st.progress(max(0.0, min(1.0, float(confidence))))
            else:
                st.caption("Confidence: N/A")


def render_actions_ui(actions: list, building_id: str = None):
    if not actions:
        st.info("No recommended actions.")
        return

    for idx, action in enumerate(actions, start=1):
        title = action.get("title", "Untitled action")
        what = action.get("what", "No details provided.")
        when = action.get("when", "unspecified")
        impact = str(action.get("impact", "unknown")).lower()
        urgency = str(action.get("urgency", "unknown")).lower()

        with st.container(border=True):
            st.markdown(f"**{idx}. {title}**")
            st.write(what)
            st.markdown(
                f":{_label_color(urgency)}[Urgency: {urgency.title()}]  "
                f":{_label_color(impact)}[Impact: {impact.title()}]"
            )
            st.caption(f"When: {when.title()}")
            
            # Add "Assign this task" button
            if st.button(
                f"Assign '{title}'",
                key=f"assign_action_{idx}",
                help="Log action and trigger alert via n8n."
            ):
                action_details = {
                    "action": title,
                    "building_id": building_id,
                    "source_doc": "EcoSense Report",
                    "finding_type": impact.title(),
                    "savings_kwh": 0.0, # Placeholder
                }
                _send_action_to_n8n(action_details)