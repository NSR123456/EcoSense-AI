import os
import sys
import inspect
import io
import re
import requests
import pandas as pd
import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.graph.workflow import run_workflow
from src.tools.evaluation_tools import evaluate_response
from src.tools.reporting_tools import build_pdf, send_report_email
from src.llm.client import generate_with_gemini

from dashboard.ui.homepage import render_homepage
from dashboard.ui.decision_cards import (
    render_decision_cards,
    render_issues_ui,
    render_actions_ui,
)
from dashboard.ui.agent_theater import render_agent_theater
from dashboard.ui.evidence_panel import render_evidence_panel
from dashboard.ui.simulator_panel import render_simulator_panel
from dashboard.ui.v2_realtime import render_v2_realtime_ui
from dashboard.ui.charts import render_consumption_chart, render_issue_bar
from dashboard.ui.app_shell import inject_theme, render_assistant_brief, render_top_header
from dashboard.ui.admin_ops import render_session_badge
from dashboard.building_store import all_building_ids, load_energy_dataset
from dashboard.paths import METADATA_PATH
from dashboard.user_store import authenticate
from src.services.automation_services import update_visualization_alert

st.set_page_config(page_title="EcoSense AI", page_icon="🌿", layout="wide")
inject_theme()


def _build_decision_rationale(resp: dict) -> str:
    metrics = resp.get("metrics", {}) if isinstance(resp, dict) else {}
    normalized = metrics.get("normalized_kpis", {}) if isinstance(metrics, dict) else {}
    bctx = metrics.get("building_context", {}) if isinstance(metrics, dict) else {}
    causes = resp.get("causes", []) if isinstance(resp, dict) else []
    actions = resp.get("actions", []) if isinstance(resp, dict) else []
    confidence = resp.get("confidence_card", {}) if isinstance(resp, dict) else {}

    avg = metrics.get("avg_consumption", 0)
    mn = metrics.get("min_consumption", 0)
    mx = metrics.get("max_consumption", 0)
    vr = metrics.get("variability_ratio", 0)
    anomalies = metrics.get("anomaly_count", 0)
    trend = metrics.get("trend", "stable")
    cause_text = causes[0].get("impact", "no strong cause signal identified") if causes else "no strong cause signal identified"
    action_text = actions[0].get("title", "Continue monitoring") if actions else "Continue monitoring"

    lines = ["Decision logic for selected building:"]
    lines.append(
        (
            f"Based on measured values (avg={avg:.1f} kWh, min={mn:.1f} kWh, max={mx:.1f} kWh, "
            f"variability ratio={vr:.2f}, anomalies={anomalies}, trend={trend}), "
            "the model identifies a statistically meaningful inefficiency pattern."
        )
    )
    lines.append(f"For this reason, the strongest cause signal is: {cause_text}.")

    if normalized.get("normalization_available"):
        lines.append(
            (
                f"Using building-normalized logic (kWh/sqft={normalized.get('avg_kwh_per_sqft')}, "
                f"kWh/flat={normalized.get('avg_kwh_per_flat')}, "
                f"kWh/occupant={normalized.get('avg_kwh_per_occupant')}), "
                "the decision is adjusted for building size and occupancy."
            )
        )
    else:
        lines.append(
            "Metadata (area/flats/occupancy) is not available, so normalization is not applied. "
            "Decision is still possible using time-series consumption statistics, but cross-building fairness is limited."
        )

    lines.append(f"Therefore, the recommended priority decision is: {action_text}.")
    lines.append(
        f"Confidence in this decision: {confidence.get('score', 'N/A')}/100 ({confidence.get('label', 'unknown')})."
    )
    return "\n".join(lines)


def _serialize_uploads(uploaded_files: list) -> list:
    def _extract_pdf_text(data: bytes) -> tuple[str, str]:
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            text = "\n".join([(p.extract_text() or "") for p in reader.pages]).strip()
            return text, "pypdf"
        except Exception:
            return "", ""

    def _extract_image_text(data: bytes) -> tuple[str, str]:
        try:
            from PIL import Image
            import pytesseract
            img = Image.open(io.BytesIO(data))
            text = (pytesseract.image_to_string(img) or "").strip()
            return text, "pytesseract"
        except Exception:
            return "", ""

    items = []
    for f in uploaded_files or []:
        raw = b""
        try:
            raw = f.getvalue()
        except Exception:
            raw = b""
        mime = getattr(f, "type", "application/octet-stream")
        extracted_text = ""
        extractor = ""
        if raw and "pdf" in str(mime).lower():
            extracted_text, extractor = _extract_pdf_text(raw)
        elif raw and "image" in str(mime).lower():
            extracted_text, extractor = _extract_image_text(raw)

        items.append(
            {
                "name": getattr(f, "name", "uploaded_file"),
                "type": mime,
                "size": int(getattr(f, "size", 0) or 0),
                "extracted_text": extracted_text[:6000] if extracted_text else "",
                "extractor": extractor,
            }
        )
    return items


def _extract_flat_rates(text: str) -> list[tuple[str, float]]:
    if not text:
        return []
    rates = []
    # Matches patterns like:
    # Flat F101: 18.4 kWh
    # Flat 101 - 18.4
    pattern = re.compile(r"(?:flat|apt)\s*([a-z]?\d{2,4})\s*[:\-]\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
    for m in pattern.finditer(text):
        flat_id = m.group(1).upper()
        val = float(m.group(2))
        rates.append((flat_id, val))
    return rates


def _flat_insight(flat_rates: list[tuple[str, float]]) -> dict:
    if not flat_rates:
        return {}
    vals = [v for _, v in flat_rates]
    avg = sum(vals) / len(vals)
    mn = min(vals)
    mx = max(vals)
    # simple std without numpy dependency
    var = sum((v - avg) ** 2 for v in vals) / max(1, len(vals))
    std = var ** 0.5
    threshold = avg + 1.5 * std
    high_flats = [fid for fid, v in flat_rates if v > threshold]
    return {
        "flat_count": len(flat_rates),
        "avg_kwh": round(avg, 2),
        "min_kwh": round(mn, 2),
        "max_kwh": round(mx, 2),
        "std_kwh": round(std, 2),
        "high_flats": high_flats[:10],
    }


def _run_upload_only_analysis(query: str, uploaded_files: list, operator_note: str) -> dict:
    files = _serialize_uploads(uploaded_files)
    image_count = sum(1 for f in files if "image" in str(f.get("type", "")))
    pdf_count = sum(1 for f in files if "pdf" in str(f.get("type", "")))
    total_files = len(files)

    extracted_chunks = [str(f.get("extracted_text", "")).strip() for f in files if str(f.get("extracted_text", "")).strip()]
    combined_text = "\n".join(extracted_chunks + ([operator_note.strip()] if operator_note.strip() else [])).lower()
    flat_rates = _extract_flat_rates("\n".join(extracted_chunks))
    flat_stats = _flat_insight(flat_rates)

    evidence = []
    for f in files:
        extractor = f.get("extractor")
        extracted_text = str(f.get("extracted_text", "")).strip()
        evidence.append(
            {
                "text": f"Uploaded file: {f.get('name')} ({f.get('type')}, {f.get('size', 0)} bytes)",
                "source": "multimodal",
            }
        )
        if extracted_text:
            ev_text = extracted_text[:400] + ("..." if len(extracted_text) > 400 else "")
            suffix = f" [extracted via {extractor}]" if extractor else ""
            evidence.append({"text": f"Extracted content from {f.get('name')}{suffix}: {ev_text}", "source": "multimodal"})
    if operator_note.strip():
        evidence.append({"text": f"Operator note: {operator_note.strip()}", "source": "multimodal"})

    if total_files == 0 and not operator_note.strip():
        issues = [{"name": "Insufficient upload evidence", "severity": "medium", "confidence": 0.55}]
        causes = [{"impact": "No files or notes were provided for upload-only analysis"}]
        actions = [
            {
                "title": "Upload at least one image or PDF",
                "what": "Attach utility bill, meter screenshot, or site note to enable upload-only analysis",
                "when": "now",
                "impact": "high",
                "urgency": "high",
            }
        ]
    else:
        issues = []
        if image_count > 0:
            issues.append({"name": "Visual evidence indicates possible load anomaly", "severity": "medium", "confidence": 0.72})
        if pdf_count > 0:
            issues.append({"name": "Document evidence suggests bill optimization opportunity", "severity": "medium", "confidence": 0.69})
        if operator_note.strip():
            issues.append({"name": "Operator-reported concern requires verification", "severity": "medium", "confidence": 0.66})
        if "after-hours" in combined_text or "always-on" in combined_text:
            issues.append({"name": "Possible after-hours energy waste", "severity": "high", "confidence": 0.78})
        if "peak demand" in combined_text or "peak load" in combined_text:
            issues.append({"name": "Potential peak demand cost risk", "severity": "medium", "confidence": 0.71})
        if "hvac" in combined_text or "cooling" in combined_text:
            issues.append({"name": "HVAC schedule optimization opportunity", "severity": "medium", "confidence": 0.70})
        if flat_stats:
            issues.append(
                {
                    "name": f"Inter-flat consumption imbalance ({flat_stats['flat_count']} flats analyzed)",
                    "severity": "high" if flat_stats.get("high_flats") else "medium",
                    "confidence": 0.82,
                }
            )
        if not issues:
            issues.append({"name": "General upload-based inefficiency signal", "severity": "low", "confidence": 0.60})

        causes = [
            {
                "impact": (
                    f"upload-only assessment uses {total_files} file(s) "
                    f"(images={image_count}, pdfs={pdf_count}) and operator note={'yes' if operator_note.strip() else 'no'}; "
                    "indicates potential schedule/base-load inefficiency from uploaded content that needs meter-data validation"
                )
            }
        ]
        actions = [
            {
                "title": "Validate uploaded findings against meter logs",
                "what": "Cross-check uploaded evidence with hourly meter trend and after-hours equipment runtime",
                "when": "today",
                "impact": "high",
                "urgency": "high",
            },
            {
                "title": "Collect one-week interval data",
                "what": "Gather 7-day consumption profile to convert upload-only findings into quantified decision",
                "when": "this week",
                "impact": "medium",
                "urgency": "medium",
            },
        ]
        if flat_stats:
            top_flats = ", ".join(flat_stats.get("high_flats", [])[:5]) if flat_stats.get("high_flats") else "none"
            actions.insert(
                0,
                {
                    "title": "Investigate high-consumption flats",
                    "what": (
                        f"From upload data: avg={flat_stats['avg_kwh']} kWh/flat, max={flat_stats['max_kwh']} kWh. "
                        f"Review top outlier flats: {top_flats}."
                    ),
                    "when": "today",
                    "impact": "high",
                    "urgency": "high",
                },
            )

    top_issue = issues[0]["name"] if issues else "No issue"
    top_action = actions[0]["title"] if actions else "Continue monitoring"
    top_cause = causes[0]["impact"] if causes else "No major cause identified"

    technical_lines = [
        "Upload-only decision rationale:",
        f"- Query: {query}",
        f"- Inputs: files={total_files}, images={image_count}, pdfs={pdf_count}, operator_note={'yes' if operator_note.strip() else 'no'}",
    ]
    if flat_stats:
        technical_lines.append(
            f"- Flat-level stats: flats={flat_stats.get('flat_count')}, avg={flat_stats.get('avg_kwh')} kWh, "
            f"min={flat_stats.get('min_kwh')} kWh, max={flat_stats.get('max_kwh')} kWh, std={flat_stats.get('std_kwh')} kWh"
        )
    technical_lines.extend(
        [
            f"- Top issue: {top_issue}",
            f"- Cause signal: {top_cause}",
            f"- Priority action: {top_action}",
            "- Confidence note: upload-only path gives directional guidance; validate with time-series meter data.",
        ]
    )
    technical = "\n".join(technical_lines)
    simple = f"Based on uploaded evidence, main issue is {top_issue.lower()}. Start with {top_action.lower()}."

    messages = [
        {"agent": "Planner", "type": "plan", "content": "Selected route: upload_only; nodes: ['multimodal', 'critic', 'synthesizer']"},
        {"agent": "Multimodal", "type": "evidence", "content": f"Received files={total_files} (images={image_count}, pdfs={pdf_count}), operator_note={'yes' if operator_note.strip() else 'no'}"},
        {"agent": "Synthesizer", "type": "decision", "content": "Finalized upload-only response with provisional confidence=60"},
    ]

    final_response = {
        "risk_card": {"title": "Energy Ops Risk (Uploaded Evidence)", "value": f"{issues[0]['severity'].title()} (upload-only)"},
        "issue_card": {"title": "Top Issue", "value": f"{top_issue} (confidence={int(round(issues[0].get('confidence', 0.6)*100))}%)"},
        "cause_card": {"title": "Likely Cause", "value": top_cause},
        "action_card": {"title": "Best Next Action", "value": top_action},
        "confidence_card": {"score": 60, "label": "provisional"},
        "technical": technical,
        "simple": simple,
        "issues": issues,
        "causes": causes,
        "actions": actions,
        "compliance": {},
        "evidence": evidence,
        "retrieval_meta": {"total_evidence": len(evidence), "multimodal_count": len(evidence), "bm25_count": 0, "vector_count": 0, "statistical_count": 0, "route": "upload_only"},
        "critiques": [],
        "messages": messages,
        "metrics": {"upload_flat_stats": flat_stats} if flat_stats else {},
        "insights": {},
    }

    return {"final_response": final_response, "metrics": {}, "insights": {}}


df = load_energy_dataset()
if df.empty:
    st.error("No sample data found in data/sample/")
    st.stop()

building_ids = all_building_ids(df, METADATA_PATH)

with st.sidebar:
    st.header("Account")
    if "auth_user" not in st.session_state:
        st.session_state["auth_user"] = None
        st.session_state["auth_role"] = None

    if st.session_state["auth_user"] is None:
        login_user = st.text_input("Username", key="login_user")
        login_pass = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login", key="login_btn", type="primary", width="stretch"):
            ok, info = authenticate(login_user.strip(), login_pass)
            if ok:
                st.session_state["auth_user"] = login_user.strip()
                st.session_state["auth_role"] = info
                st.success(f"Logged in as {info}.")
                st.rerun()
            elif info == "pending":
                st.error("Account pending admin approval. Contact an administrator.")
            else:
                st.error("Invalid username or password.")
        st.caption("Default demo users: admin / operator1 / operator2")
    else:
        render_session_badge(st.session_state["auth_user"], st.session_state["auth_role"])
        if st.button("Logout", key="logout_btn", type="primary", width="stretch"):
            st.session_state["auth_user"] = None
            st.session_state["auth_role"] = None
            st.rerun()

if st.session_state["auth_user"] is None:
    render_homepage()
    st.stop()

with st.sidebar:
    st.header("Controls")
    analysis_mode = st.radio("Analysis mode", ["Building-based", "Upload-only", "v2 Real-time (Google Sheets)"], index=0)
    building_id = None
    if analysis_mode == "Building-based":
        building_id = st.selectbox("Select building", building_ids)
    query = st.text_input("Ask a question", value="What should I do first for this building?")
    other = ""
    if analysis_mode == "Building-based" and building_id:
        other = st.selectbox("Optional compare building", [""] + [b for b in building_ids if b != building_id])
    uploaded_files = st.file_uploader(
        "Attach image/PDF evidence (optional)",
        type=["png", "jpg", "jpeg", "pdf"],
        accept_multiple_files=True,
        key="mm_uploads",
    )
    operator_note = st.text_area(
        "Operator note (optional)",
        value="",
        placeholder="Add observations from site, complaints, incidents, or special events...",
        key="operator_note",
    )
    if uploaded_files:
        st.caption(f"Attached files: {len(uploaded_files)}")
    run = st.button("Run Decision Workflow", type="primary", width="stretch")
    reset_result = st.button("Reset Last Result", key="reset_result_btn", type="primary", width="stretch")

    if st.session_state.get("auth_role") == "admin":
        st.markdown("##### Administration")
        st.page_link("pages/1_Operators.py", label="Operators & accounts", icon="👥")
        st.page_link("pages/2_Building_data.py", label="Building data & consumption", icon="🏢")
    else:
        st.caption("Administration pages are available when signed in as an administrator.")

if reset_result:
    st.session_state.pop("result", None)
    st.session_state.pop("last_run_query", None)
    st.session_state.pop("last_run_building", None)
    for k in ("agent_conv_key", "agent_live_count", "agent_user_thread", "agent_step_cursor", "pdf_path", "awaiting_report_permission", "last_mm_inputs", "last_operator_note"):
        st.session_state.pop(k, None)
    st.success("Cleared previous result. Run workflow again.")

if run:
    mm_inputs = _serialize_uploads(uploaded_files)
    st.session_state["last_mm_inputs"] = mm_inputs
    st.session_state["last_operator_note"] = operator_note
    with st.spinner("Running agent workflow..."):
        if analysis_mode == "Upload-only":
            result = _run_upload_only_analysis(query=query, uploaded_files=uploaded_files or [], operator_note=operator_note)
        else:
            wf_params = inspect.signature(run_workflow).parameters
            base_kwargs = {
                "query": query,
                "building_id": building_id,
                "compare_building_id": other if other else None,
            }
            if mm_inputs and "multimodal_inputs" not in wf_params:
                st.warning("Backend runtime does not support multimodal args yet. Restart Streamlit to enable file evidence ingestion.")
            if "multimodal_inputs" in wf_params:
                base_kwargs["multimodal_inputs"] = mm_inputs
            if "operator_note" in wf_params:
                base_kwargs["operator_note"] = operator_note
            result = run_workflow(**base_kwargs)
    st.session_state["result"] = result
    st.session_state["last_run_query"] = query
    st.session_state["last_run_building"] = building_id
    st.session_state["awaiting_report_permission"] = True  # New state for permission flow
    
    # Auto-scroll to results using JS injection
    st.markdown(
        """
        <script>
        var mainContainer = window.parent.document.querySelector('section.main');
        if (mainContainer) {
            mainContainer.scrollTo({
                top: mainContainer.scrollHeight,
                behavior: 'smooth'
            });
        }
        </script>
        """,
        unsafe_allow_html=True
    )

result = st.session_state.get("result")
_building_label = (
    str(building_id)
    if analysis_mode == "Building-based" and building_id
    else ("Upload-only" if analysis_mode == "Upload-only" else ("Real-time Audit" if analysis_mode == "v2 Real-time (Google Sheets)" else None))
)
render_top_header(
    user=str(st.session_state.get("auth_user") or ""),
    building_label=_building_label,
    has_result=bool(result),
)

if analysis_mode == "v2 Real-time (Google Sheets)":
    render_v2_realtime_ui()
elif result:
    resp = result.get("final_response", {})
    # Backward compatibility: upgrade old cached cause wording in session results.
    if resp.get("cause_card", {}).get("value") == "daily usage is inconsistent":
        metrics_for_patch = resp.get("metrics", result.get("metrics", {}))
        vr = metrics_for_patch.get("variability_ratio", 0)
        ac = metrics_for_patch.get("anomaly_count", 0)
        patched = (
            f"high day-to-day variability (ratio={vr:.2f}, anomalies={ac}) "
            "indicates inconsistent operating schedule"
        )
        resp["cause_card"]["value"] = patched
        causes = resp.get("causes", [])
        if causes and isinstance(causes[0], dict):
            causes[0]["impact"] = patched

    technical = resp.get("technical", "")
    if technical.strip().startswith("Top issue:"):
        technical = _build_decision_rationale(resp)
        resp["technical"] = technical
    simple = resp.get("simple", "")
    evaluation = evaluate_response(technical, simple)

    # Tab state management to prevent unwanted switching
    tab_names = ["Decision Center", "Agent Theater", "Evaluation & Report"]
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = 0
    
    # Tab selector that maintains state
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("🏠 Decision Center", use_container_width=True, 
                    type="primary" if st.session_state.active_tab == 0 else "secondary"):
            st.session_state.active_tab = 0
            st.rerun()
    with col2:
        if st.button("🎭 Agent Theater", use_container_width=True,
                    type="primary" if st.session_state.active_tab == 1 else "secondary"):
            st.session_state.active_tab = 1
            st.rerun()
    with col3:
        if st.button("📊 Evaluation & Report", use_container_width=True,
                    type="primary" if st.session_state.active_tab == 2 else "secondary"):
            st.session_state.active_tab = 2
            st.rerun()
    st.markdown("---")
    
    # Display selected tab content
    if st.session_state.active_tab == 0:
        render_decision_cards(resp)
        
        # Integrated 3D Agent Simulation
        st.divider()
        metrics = result.get("metrics", result.get("final_response", {}).get("metrics"))
        insights = result.get("insights", {})
        if not metrics:
            metrics = result.get("metrics", {})
        if not insights:
            insights = result.get("insights", {})
        # fallback from workflow state
        metrics = result.get("metrics", metrics or {})
        insights = result.get("insights", insights or {})

        if metrics:
            render_simulator_panel(metrics, insights, resp)
        else:
            st.info("No metrics available for simulation.")
        st.divider()

        c1, c2 = st.columns([1, 1])

        with c1:
            q_text = st.session_state.get("last_run_query") or query
            render_assistant_brief(str(q_text), simple, technical, resp)
            with st.expander("Full technical summary", expanded=False):
                st.text(technical)

            if building_id:
                building_df = df[df["building_id"] == building_id].copy()
                render_consumption_chart(building_df, building_id, key=f"cons_chart_{building_id}")
            else:
                st.info("Consumption chart is available in Building-based mode.")

        with c2:
            st.subheader("Operational Focus")
            issue_bar_key = f"issue_bar_{building_id}" if building_id else "issue_bar_upload_only"
            render_issue_bar(resp.get("issues", []), key=issue_bar_key)
            right_tabs = st.tabs(["Detected Issues", "Recommended Actions"])
            with right_tabs[0]:
                render_issues_ui(resp.get("issues", []))
            with right_tabs[1]:
                render_actions_ui(resp.get("actions", []), building_id=building_id)

        # Key Insights & Evidence
        st.divider()
        st.subheader("🔍 Key Insights & Evidence")
        
        retrieval_meta = resp.get("retrieval_meta", {})
        rag_count = int(retrieval_meta.get("bm25_count", 0)) + int(retrieval_meta.get("vector_count", 0))
        stat_count = retrieval_meta.get("statistical_count", 0)
        mm_count = int(retrieval_meta.get("multimodal_count", 0) or 0)
        
        # Simple evidence summary
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📚 Knowledge Sources", rag_count, help="AI knowledge and best practices used")
        with col2:
            st.metric("📊 Data Analysis", stat_count, help="Statistical patterns found")
        with col3:
            st.metric("📎 File Insights", mm_count, help="Uploaded documents and images analyzed")
        
        # Show key evidence in simple language
        evidence = resp.get("evidence", [])
        if evidence:
            st.markdown("**What the AI found helpful:**")
            # Group evidence by type and show top insights
            rag_evidence = [e for e in evidence if 'bm25' in str(e.get('source', '')).lower() or 'vector' in str(e.get('source', '')).lower()]
            stat_evidence = [e for e in evidence if 'statistical' in str(e.get('source', '')).lower()]
            
            if rag_evidence:
                with st.expander("💡 Smart Recommendations", expanded=True):
                    for i, ev in enumerate(rag_evidence[:3], 1):  # Show top 3
                        text = ev.get('text', '')
                        # Simplify the language
                        simple_text = text.replace('should prioritize', 'focus on').replace('buildings with', 'buildings that have')
                        st.markdown(f"• {simple_text}")
            
            if stat_evidence:
                with st.expander("📈 Energy Patterns Found", expanded=True):
                    for ev in stat_evidence:
                        text = ev.get('text', '')
                        # Make stats more readable
                        if 'avg=' in text:
                            st.markdown(f"• **Average consumption:** {text.split('avg=')[1].split(',')[0]} kWh per day")
                        elif 'variability ratio' in text:
                            ratio = text.split('variability ratio=')[1].split(',')[0]
                            st.markdown(f"• **Energy consistency:** {ratio} (lower is more stable)")
                        elif 'anomalies=' in text:
                            count = text.split('anomalies=')[1].split(',')[0]
                            st.markdown(f"• **Unusual days:** {count} days with abnormal usage")
                        else:
                            st.markdown(f"• {text}")

        # Compliance section (moved from separate tab)
        st.subheader("✅ Energy Compliance Check")
        compliance = resp.get("compliance", {})
        if compliance and isinstance(compliance, dict) and any(compliance.values()):
            score = compliance.get("score")
            status = compliance.get("status", "Unknown")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Compliance Score", score if score is not None else "N/A")
            with c2:
                st.metric("Status", status)
                # Add NLP explanation for status
                status_prompt = (
                    f"Explain what a '{status}' compliance status means for building energy efficiency in simple terms. "
                    "Keep it under 50 words, encouraging and actionable."
                )
                status_explanation = generate_with_gemini(status_prompt, safety_delay=1)
                if status_explanation:
                    st.caption(status_explanation)

            comp_evidence = compliance.get("evidence", [])
            if comp_evidence:
                with st.expander("Compliance Evidence", expanded=False):
                    # Generate NLP summary of evidence
                    evidence_texts = [item.get("text", "") for item in comp_evidence if item.get("text")]
                    if evidence_texts:
                        summary_prompt = (
                            f"Summarize these compliance evidence points in simple language for non-experts: {evidence_texts[:3]}. "
                            "Explain what they mean for energy efficiency and building operations. Keep under 150 words."
                        )
                        summary = generate_with_gemini(summary_prompt, safety_delay=1)
                        if summary:
                            st.markdown(f"**Summary**: {summary}")
                            st.divider()
                    for item in comp_evidence:
                        text = item.get("text", "")
                        src = item.get("source", "unknown")
                        st.markdown(f"- {text} (`{src}`)")
            else:
                st.caption("No specific compliance issues found.")
        else:
            # Generate NLP-based explanation for no compliance results
            explanation_prompt = (
                "Explain in simple, everyday language why there might be no compliance results for this building energy analysis. "
                "Keep it under 100 words, helpful, and reassuring. Focus on what compliance means for energy efficiency."
            )
            explanation = generate_with_gemini(explanation_prompt, safety_delay=1)
            if explanation:
                st.info(f"💡 **Compliance Insights**: {explanation}")
            else:
                st.info("No compliance results for this run.")

    elif st.session_state.active_tab == 1:
        render_agent_theater(resp.get("messages", []), resp)

    elif st.session_state.active_tab == 2:
        st.subheader("Decision Quality Check")
        quality = evaluation.get("quality", {}) if isinstance(evaluation, dict) else {}
        faithfulness = evaluation.get("faithfulness", {}) if isinstance(evaluation, dict) else {}

        e1, e2 = st.columns(2)
        with e1:
            q_score = quality.get("score")
            score_label = "Strong" if isinstance(q_score, (int, float)) and q_score >= 80 else ("Moderate" if isinstance(q_score, (int, float)) and q_score >= 60 else "Weak")
            st.metric("Response Strength", f"{q_score if q_score is not None else 'N/A'} ({score_label})")
            reasons = quality.get("reasons", [])
            if reasons:
                st.caption("Why this looks strong/weak")
                for reason in reasons:
                    st.write(f"- {reason}")
            else:
                st.caption("No quality explanation available.")

        with e2:
            faithful = faithfulness.get("faithful")
            ratio = faithfulness.get("ratio")
            status = "Aligned" if faithful else "Needs review"
            st.metric("Data Alignment", status)
            if ratio is not None:
                st.caption(f"How much summary matches technical numbers: {ratio:.2f}")
            tnum = faithfulness.get("technical_numbers")
            snum = faithfulness.get("simple_numbers")
            if tnum is not None and snum is not None:
                st.caption(f"Numbers found -> technical: {tnum}, simple explanation: {snum}")

        st.info(
            "Operator meaning: if Data Alignment says 'Needs review', verify numbers before acting. "
            "Use the Technical Summary and Detected Issues tabs for confirmation."
        )

        st.subheader("Review Flags")
        critiques = resp.get("critiques", [])
        if critiques:
            for i, critique in enumerate(critiques, start=1):
                with st.container(border=True):
                    st.markdown(f"**Flag {i}**")
                    st.write(str(critique))
        else:
            st.success("No review flags. Decision is ready for operator action.")

        if st.button("Generate PDF Report", key="pdf_btn", type="primary"):
            pdf_path = build_pdf(result)
            st.session_state["pdf_path"] = pdf_path
            st.success(f"Report generated: {os.path.basename(pdf_path)}")

        # --- Python-based VISUALIZATION ENGINE ---
        if st.button("📊 Update Consumption Alert", key="viz_btn", help="Send live metrics to the Telegram via Python"):
            with st.spinner("Updating visualization..."):
                metrics = result.get("metrics", {})
                actual = metrics.get("avg_consumption", 0.0)
                
                # Try to get estimated savings to calculate optimized value
                savings_kwh = 0.0
                if "insights" in result:
                    from src.core.reasoning import estimate_savings
                    savings = estimate_savings(metrics, result["insights"])
                    savings_kwh = savings.get("estimated_daily_kwh", 0.0)
                
                optimized = actual - savings_kwh
                
                viz_res = update_visualization_alert(
                    building_id=building_id or "All Buildings",
                    actual=actual,
                    optimized=optimized
                )
                
                if viz_res["status"] == "success":
                    st.success("Alert updated successfully!")
                else:
                    st.error(viz_res["message"])
        # ---------------------------------

        pdf_path = st.session_state.get("pdf_path")
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                st.download_button(
                    "Download PDF",
                    f.read(),
                    file_name=os.path.basename(pdf_path),
                    mime="application/pdf",
                    key="download_pdf",
                    type="primary",
                )

    # Automated PDF and Notification Flow
    if st.session_state.get("awaiting_report_permission") and result:
        st.divider()
        st.subheader("📋 Finalize Decision")
        st.write("The analysis is complete. Would you like to generate the official PDF report and notify the database team?")
        
        c1, c2 = st.columns([1, 4])
        with c1:
            if st.button("✅ Yes, Generate & Send", type="primary", use_container_width=True):
                with st.spinner("Generating PDF and logging to database..."):
                    pdf_path = build_pdf(result)
                    st.session_state["pdf_path"] = pdf_path
                    
                    # Send simulated email/log to database
                    user = st.session_state.get("auth_user", "Unknown User")
                    success = send_report_email(result, pdf_path, user)
                    
                    if success:
                        st.success(f"Report generated and database notified successfully! {os.path.basename(pdf_path)}")
                        st.session_state["awaiting_report_permission"] = False
                        st.rerun()
        with c2:
            if st.button("❌ No, Just View Results", use_container_width=True):
                st.session_state["awaiting_report_permission"] = False
                st.rerun()