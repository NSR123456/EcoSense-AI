import streamlit as st


def render_evidence_panel(evidence: list):
    st.subheader("Evidence Explorer")

    if not evidence:
        st.info("No evidence was returned for this run yet.")
        st.caption("Try running the workflow again or rephrase your question for more specific retrieval.")
        return

    for i, item in enumerate(evidence, start=1):
        text = item.get("text", "")
        source = item.get("source", "unknown")
        score = item.get("score", None)

        title = f"Evidence {i} · {source}"
        if score is not None:
            title += f" · score={round(score, 3)}"

        with st.expander(title, expanded=(i == 1)):
            st.write(text)