import streamlit as st


def render_homepage():
    st.title("EcoSense Operator Hub")
    st.caption("Monitor building performance, detect issues early, and act quickly.")

    st.info(
        "Start in the Decision Workspace to run the AI workflow for a building and get prioritized actions."
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Primary Goal", "Reduce energy waste")
    with c2:
        st.metric("Workflow Time", "~10-20 sec")
    with c3:
        st.metric("Output", "Issues + Actions")

    st.subheader("What You Can Do Here")
    st.markdown(
        """
        - Detect high-impact anomalies and inefficiencies quickly
        - See likely root causes in operator-friendly language
        - Get prioritized actions with urgency and expected impact
        - Generate a PDF report for audit and management updates
        """
    )

    with st.expander("Recommended Daily Routine", expanded=True):
        st.markdown(
            """
            1. Open **Decision Workspace**
            2. Select the building you are managing
            3. Run the decision workflow
            4. Execute high-urgency actions first
            5. Export the report for tracking
            """
        )
