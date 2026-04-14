import streamlit as st


def _risk_tone(risk_value: str):
    risk = str(risk_value).strip().lower()
    if risk == "high":
        return st.error, "RED ALERT"
    if risk == "medium":
        return st.warning, "WATCH CLOSELY"
    return st.success, "UNDER CONTROL"


def render_operator_brief(resp: dict):
    risk_card = resp.get("risk_card", {}) if isinstance(resp, dict) else {}
    issue_card = resp.get("issue_card", {}) if isinstance(resp, dict) else {}
    cause_card = resp.get("cause_card", {}) if isinstance(resp, dict) else {}
    action_card = resp.get("action_card", {}) if isinstance(resp, dict) else {}
    actions = resp.get("actions", []) if isinstance(resp, dict) else []

    risk_value = risk_card.get("value", "unknown")
    tone_fn, tone_text = _risk_tone(risk_value)
    tone_fn(f"{tone_text}: Risk is {str(risk_value).title()}")

    st.subheader("Operator Quick Guide")
    st.markdown(
        f"""
        **1) What is wrong?**  
        {issue_card.get("value", "Issue not available")}

        **2) Why did it happen?**  
        {cause_card.get("value", "Cause not available")}

        **3) What should I do now?**  
        {action_card.get("value", "Action not available")}
        """
    )

    st.subheader("Today Action Checklist")
    if not actions:
        st.info("No actions available for this run.")
        return

    for i, action in enumerate(actions[:3], start=1):
        title = action.get("title", "Unnamed action")
        when = action.get("when", "today")
        st.checkbox(f"{i}. {title} ({str(when).title()})", value=False, key=f"op_action_{i}_{title}")
