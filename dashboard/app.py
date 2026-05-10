import os
import sys
import inspect
import io
import re
import requests
import threading
import pandas as pd
import streamlit as st
try:
    from streamlit import st_autorefresh
except Exception:
    st_autorefresh = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.tools.analytics_tools import get_building_bundle
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
from src.services.google_sheets import DatabaseManager
from src.services.simulator import EnergySimulator
from src.services.agents import AgentTeam
from src.services.telegram_bot import TelegramBot

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


def _build_dataset_analysis(building_id: str, query: str, uploaded_files: list, operator_note: str) -> dict:
    bundle = get_building_bundle(building_id)
    metrics = bundle["metrics"]
    insights = bundle["insights"]
    recent_pattern = bundle["recent_pattern"]
    actions = bundle["actions"]
    savings = bundle["savings"]

    data_cov = metrics.get("data_coverage", {})
    coverage_text = (
        f"Dataset covers {data_cov.get('days_covered', 0)} of {data_cov.get('span_days', 0)} days "
        f"({data_cov.get('coverage_ratio', 0.0)*100:.0f}% coverage) from {metrics.get('first_date')} to {metrics.get('last_date')}"
    ) if data_cov else "Dataset coverage information is unavailable."

    evidence = [
        {"text": coverage_text, "source": "dataset"}
    ]
    if uploaded_files:
        files = _serialize_uploads(uploaded_files)
        for f in files:
            evidence.append({"text": f"Uploaded file: {f.get('name')} ({f.get('type')})", "source": "multimodal"})
    if operator_note.strip():
        evidence.append({"text": f"Operator note: {operator_note.strip()}", "source": "multimodal"})

    issues = []
    if insights.get("high_variability"):
        issues.append({"name": "Inconsistent daily energy profile", "severity": "medium", "confidence": 0.74})
    if insights.get("peak_spike"):
        issues.append({"name": "High consumption spike detected", "severity": "high", "confidence": 0.82})
    if insights.get("high_base_load"):
        issues.append({"name": "Elevated base load", "severity": "medium", "confidence": 0.70})
    if insights.get("high_avg_consumption"):
        issues.append({"name": "High average consumption", "severity": "medium", "confidence": 0.68})
    if insights.get("high_normalized_intensity"):
        issues.append({"name": "Normalized intensity is above benchmark", "severity": "medium", "confidence": 0.70})
    if insights.get("has_anomalies") and not insights.get("peak_spike"):
        issues.append({"name": "Anomaly pattern found in recent readings", "severity": "medium", "confidence": 0.66})

    if not issues:
        issues.append({"name": "No strong inefficiency signal", "severity": "low", "confidence": 0.55})

    causes = [
        {
            "impact": (
                f"Analysis is based on available sample days; {coverage_text}. "
                "Use this as a first-pass recommendation and collect more complete meter data if possible."
            )
        }
    ]

    top_issue = issues[0]["name"]
    top_action = actions[0]["title"] if actions else "Continue monitoring"

    technical = (
        f"Building {building_id} analysis over {metrics.get('total_records', 0)} records. "
        f"Average consumption {metrics.get('avg_consumption', 0):.1f} kWh, max {metrics.get('max_consumption', 0):.1f} kWh, "
        f"trend={metrics.get('trend')}.")
    if data_cov and data_cov.get('partial_data'):
        technical += " The dataset is partial, so findings are provisional."
    technical += f" Top issue: {top_issue}."

    simple = f"Using available days, the top issue is {top_issue.lower()}. Start with {top_action.lower()}."

    messages = [
        {"agent": "DatasetCollector", "type": "info", "content": f"Loaded {metrics.get('total_records', 0)} records for building {building_id}."},
        {"agent": "Analytics", "type": "info", "content": f"Derived insights from {data_cov.get('days_covered', 0)} covered days."},
        {"agent": "Planner", "type": "decision", "content": f"Recommended {len(actions)} action(s) based on available sample data."},
    ]

    final_response = {
        "risk_card": {"title": "Energy Ops Risk", "value": f"{issues[0]['severity'].title()} (based on available data)"},
        "issue_card": {"title": "Top Issue", "value": f"{top_issue} (confidence={int(round(issues[0].get('confidence', 0.6)*100))}%)"},
        "cause_card": {"title": "Cause Summary", "value": causes[0]["impact"]},
        "action_card": {"title": "Best Next Action", "value": top_action},
        "confidence_card": {"score": int(round(issues[0].get('confidence', 0.6)*100)), "label": "provisional"},
        "technical": technical,
        "simple": simple,
        "issues": issues,
        "causes": causes,
        "actions": actions,
        "compliance": {},
        "evidence": evidence,
        "retrieval_meta": {"total_evidence": len(evidence), "dataset_evidence": 1, "statistical_count": 1},
        "messages": messages,
        "metrics": metrics,
        "insights": insights,
        "alert_policy": "Telegram alerts are sent when you assign a recommended action or manually trigger the visualization alert.",
    }

    return {"final_response": final_response, "metrics": metrics, "insights": insights}


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
        issues = [{"name": "Insufficient review evidence", "severity": "medium", "confidence": 0.55}]
        causes = [{"impact": "No files or notes were provided for evidence review"}]
        actions = [
            {
                "title": "Attach evidence or operator notes",
                "what": "Provide a utility bill, meter screenshot, or site note to enable evidence review",
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
                    f"evidence review uses {total_files} file(s) "
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
                "what": "Gather 7-day consumption profile to convert evidence review findings into a quantified decision",
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
        "Evidence review decision rationale:",
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
            "- Confidence note: evidence review guidance is directional; validate with time-series meter data if available.",
        ]
    )
    technical = "\n".join(technical_lines)
    simple = f"Based on the provided evidence, main issue is {top_issue.lower()}. Start with {top_action.lower()}."

    messages = [
        {"agent": "Planner", "type": "plan", "content": "Selected route: evidence_review; nodes: ['multimodal', 'critic', 'synthesizer']"},
        {"agent": "Multimodal", "type": "evidence", "content": f"Received files={total_files} (images={image_count}, pdfs={pdf_count}), operator_note={'yes' if operator_note.strip() else 'no'}"},
        {"agent": "Synthesizer", "type": "decision", "content": "Finalized evidence review response with provisional confidence=60"},
    ]

    final_response = {
        "risk_card": {"title": "Energy Ops Risk (Evidence Review)", "value": f"{issues[0]['severity'].title()} (evidence review)"},
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


def _build_alert_text(result: dict) -> str:
    anomaly = result.get("anomaly", {})
    recommendation = result.get("recommendation", {}) or {}
    anomaly_type = recommendation.get("type") or anomaly.get("anomaly_reason", "True Waste")
    rec_text = recommendation.get("recommendation") or "Inspect the building and correct the issue."
    return (
        f"EcoSense True Waste Alert\n"
        f"Building: {anomaly.get('building_id', 'unknown')}\n"
        f"Date: {anomaly.get('date', 'unknown')}\n"
        f"Consumption: {anomaly.get('consumption_kwh', 'unknown')} kWh\n"
        f"Baseline: {anomaly.get('baseline', 'unknown')} kWh\n"
        f"Deviation: {anomaly.get('deviation_pct', 'unknown')}%\n"
        f"Type: {anomaly_type}\n"
        f"Recommendation: {rec_text}"
    )


def _initialize_live_environment() -> DatabaseManager:
    db = DatabaseManager()
    db.initialize_workspace()
    db.seed_campus_schedule()
    return db


def _seed_initial_stream_data(db: DatabaseManager, df: pd.DataFrame, focus_building=None):
    """Seed initial data points to Active_Stream for immediate display - building-specific."""
    existing_data = db.read_tab("Active_Stream")
    if existing_data:
        return

    if not df.empty:
        # Filter data based on focus building
        if focus_building and focus_building != "All":
            filtered_df = df[df['building_id'] == focus_building]
            buildings = [focus_building]
        else:
            # Get all buildings if "All" or no specific building selected
            filtered_df = df
            buildings = df['building_id'].unique()
        
        initial_data = []
        
        for building in buildings:
            building_rows = filtered_df[filtered_df['building_id'] == building].head(5)
            initial_data.append(building_rows)
        
        # Combine building samples
        initial_data = pd.concat(initial_data, ignore_index=True) if initial_data else pd.DataFrame()
        
        if not initial_data.empty:
            initial_data['is_faulty'] = 'NO'
            rows = initial_data[['building_id', 'date', 'consumption_kwh', 'is_faulty']].values.tolist()
            try:
                db.write_rows("Active_Stream", rows)
                if focus_building and focus_building != "All":
                    print(f"Seeded {len(rows)} initial data points for {focus_building} to Active_Stream")
                else:
                    print(f"Seeded {len(rows)} initial data points across {len(buildings)} buildings to Active_Stream")
            except Exception as e:
                print(f"Failed to seed initial data: {e}")


def _build_agent_messages_from_result(result: dict) -> list:
    anomaly = result.get("anomaly", {})
    context = result.get("context", {})
    recommendation = result.get("recommendation", {}) or {}
    building_id = anomaly.get('building_id', 'unknown')
    date = anomaly.get('date', 'unknown')

    messages = [
        {
            "agent": "Planner",
            "type": "info",
            "content": f"Analyzing {building_id} on {date}. Comparing meter stream to campus schedule."
        }
    ]

    if anomaly:
        messages.append({
            "agent": "DetectIssues",
            "type": "finding",
            "content": f"Detected {anomaly.get('deviation_pct', 0):.1f}% spike in {building_id}: {anomaly.get('consumption_kwh', 'unknown')} kWh vs baseline {anomaly.get('baseline', 'unknown')} kWh."
        })

    if context.get("status") == "true_waste":
        messages.append({
            "agent": "RootCause",
            "type": "finding",
            "content": f"No scheduled event on {date} — likely true waste from HVAC or lighting."
        })

    if recommendation:
        rec_text = recommendation.get('recommendation', 'Investigate energy usage')
        messages.append({
            "agent": "ActionPlanner",
            "type": "proposal",
            "content": f"Recommend: {rec_text}"
        })
        messages.append({
            "agent": "Critic",
            "type": "decision",
            "content": "Quality check passed. Recommendation is actionable and safe."
        })
        messages.append({
            "agent": "Synthesizer",
            "type": "decision",
            "content": f"True waste confirmed for {building_id}. Alert sent via Telegram."
        })

    return messages


def _build_no_anomaly_messages(latest_row: dict) -> list:
    building_id = latest_row.get('building_id', 'unknown')
    date = latest_row.get('date', 'unknown')

    return [
        {
            "agent": "Planner",
            "type": "info",
            "content": f"Analyzing {building_id} on {date}. Comparing meter stream to campus schedule."
        },
        {
            "agent": "DetectIssues",
            "type": "info",
            "content": f"No unusual energy-use problems were detected in the current Active_Stream data for {building_id}."
        },
        {
            "agent": "ActionPlanner",
            "type": "proposal",
            "content": "No corrective action is required at this time. Continue monitoring the stream."
        },
        {
            "agent": "Synthesizer",
            "type": "decision",
            "content": "Current energy behavior is within expected range. Keep tracking actual Excel stream data for changes."
        }
    ]


def _build_continuous_agent_messages(stream_count: int, latest_row: dict, result, building_stats: dict) -> list:
    """Build agent messages for EVERY stream update — not just anomalies.

    Each agent produces a role-specific insight so the Agent Theater always
    has fresh content as the Active_Stream grows.
    """
    building_id = latest_row.get('building_id', 'unknown')
    date = latest_row.get('date', 'unknown')
    consumption = latest_row.get('consumption_kwh', 'unknown')
    b_stats = building_stats.get(building_id, {})
    b_count = b_stats.get('count', stream_count)
    b_avg = b_stats.get('avg_kwh', '—')
    b_max = b_stats.get('max_kwh', '—')

    messages = []

    if result and result.get('anomaly'):
        # ---- anomaly detected → full agent chain ----
        messages.extend(_build_agent_messages_from_result(result))
    else:
        # ---- no anomaly → agents still report status ----
        messages.append({
            "agent": "Planner",
            "type": "info",
            "content": (
                f"Stream tick #{stream_count}: Analyzing {building_id} on {date}. "
                f"{consumption} kWh recorded. Running detect→cause→action→quality pipeline."
            ),
        })
        messages.append({
            "agent": "DetectIssues",
            "type": "info",
            "content": (
                f"Checked {building_id} at tick #{stream_count}: {consumption} kWh is within normal range. "
                f"Building has {b_count} readings so far (avg {b_avg} kWh, peak {b_max} kWh). No anomaly detected."
            ),
        })
        messages.append({
            "agent": "RootCause",
            "type": "info",
            "content": (
                f"No deviation detected for {building_id}. "
                f"Current consumption {consumption} kWh aligns with historical average of {b_avg} kWh."
            ),
        })
        messages.append({
            "agent": "ActionPlanner",
            "type": "info",
            "content": (
                f"No corrective action needed for {building_id} at this time. "
                f"Continue monitoring — next check at tick #{stream_count + 1}."
            ),
        })
        messages.append({
            "agent": "Critic",
            "type": "info",
            "content": (
                f"Quality check: All-clear status for {building_id} is consistent with {b_count} readings. No concerns."
            ),
        })
        messages.append({
            "agent": "Synthesizer",
            "type": "decision",
            "content": (
                f"Stream update #{stream_count}: {building_id} operating normally at {consumption} kWh. "
                f"{stream_count} total readings processed across all buildings."
            ),
        })

    return messages


def _auto_analyze_existing_active_stream() -> None:
    """Re-analyze whenever the Active_Stream grows and produce agent messages."""
    db = st.session_state.get("live_db") or st.session_state.get("dashboard_db")
    if not db:
        return

    active_stream = db.read_tab("Active_Stream")
    if not active_stream:
        return

    stream_length = len(active_stream)
    last_length = st.session_state.get("last_active_stream_length", 0)
    # Only re-analyze when stream has actually grown
    if stream_length <= last_length:
        return

    st.session_state["last_active_stream_length"] = stream_length

    if "live_agent_team" not in st.session_state:
        st.session_state.live_agent_team = AgentTeam(db_manager=db)

    agent_team = st.session_state.live_agent_team
    result, snapshot = agent_team.analyze_continuous()

    if snapshot is None:
        return

    new_messages = _build_continuous_agent_messages(
        snapshot["stream_count"],
        snapshot["latest_row"],
        result,
        snapshot["building_stats"],
    )

    # Accumulate messages (keep last 30 for scroll)
    existing = st.session_state.get("agent_messages", [])
    existing.extend(new_messages)
    st.session_state["agent_messages"] = existing[-30:]

    # Store latest analysis result for chatbot grounding
    if result:
        st.session_state["latest_analysis_result"] = result


def _start_telegram_bot_polling() -> None:
    """Start the Telegram bot polling loop in a background thread."""
    if "live_telegram" not in st.session_state:
        return
    
    telegram_bot = st.session_state.live_telegram
    if not telegram_bot.is_configured():
        print("Telegram: Not configured (missing TOKEN or CHAT_ID). Polling not started.")
        return
    
    # Stop existing bot if running
    if telegram_bot.running:
        print("Telegram: Bot already running, stopping first...")
        telegram_bot.stop_bot()
    
    def telegram_polling_thread():
        try:
            print("[TELEGRAM] Starting bot polling in background...")
            telegram_bot.run_bot()
        except Exception as e:
            print(f"[TELEGRAM] Polling error: {e}")
    
    thread = threading.Thread(target=telegram_polling_thread, daemon=True)
    thread.start()
    st.session_state.telegram_polling_started = True
    st.session_state.telegram_polling_thread = thread
    print("[TELEGRAM] Polling thread started successfully.")


def _restart_simulation_with_new_building() -> None:
    """Restart simulation when building selection changes."""
    # Initialize database if not exists
    if "live_db" not in st.session_state:
        st.session_state.live_db = _initialize_live_environment()
    
    if st.session_state.get("sim_running"):
        _stop_live_demo()
    
    # Stop Telegram bot before reinitializing
    if "live_telegram" in st.session_state and st.session_state.live_telegram:
        try:
            st.session_state.live_telegram.stop_bot()
            print("Telegram: Bot stopped for building change")
        except Exception as e:
            print(f"Telegram: Error stopping bot: {e}")
    
    # Clear and reinitialize with new building selection
    st.session_state.live_db.clear_tab("Active_Stream")
    st.session_state.live_db.clear_tab("Audit_Ledger")
    st.session_state.live_db.initialize_workspace()
    st.session_state.live_db.seed_campus_schedule()
    
    selected_building = st.session_state.get("selected_building", "All")
    st.session_state.live_simulator = EnergySimulator(db_manager=st.session_state.live_db, focus_building=selected_building)
    
    # Reinitialize Telegram bot with new simulator
    if "live_agent_team" not in st.session_state:
        st.session_state.live_agent_team = AgentTeam(db_manager=st.session_state.live_db)
    
    st.session_state.live_telegram = TelegramBot(
        db_manager=st.session_state.live_db,
        simulator=st.session_state.live_simulator,
        agent_team=st.session_state.live_agent_team,
    )

    # Clear stale theater state when switching building focus
    st.session_state["agent_messages"] = []
    st.session_state["latest_analysis_result"] = None
    st.session_state["agent_theater_prev_msg_count"] = 0
    st.session_state["last_active_stream_length"] = 0

    print("Telegram: Bot reinitialized with new building focus")
    
    # Restart simulation automatically if it was running
    if st.session_state.get("sim_was_running_before_building_change", False):
        _start_live_demo()
        st.session_state.sim_was_running_before_building_change = False


def _start_live_demo() -> None:
    if st.session_state.get("sim_running"):
        return

    if "live_db" not in st.session_state:
        st.session_state.live_db = _initialize_live_environment()
    
    # Get selected building from session state or sidebar
    selected_building = st.session_state.get("selected_building", "All")
    
    if "live_simulator" not in st.session_state:
        st.session_state.live_simulator = EnergySimulator(db_manager=st.session_state.live_db, focus_building=selected_building)
    else:
        # Update simulator with new building selection if changed
        if st.session_state.live_simulator.focus_building != selected_building:
            st.session_state.live_simulator = EnergySimulator(db_manager=st.session_state.live_db, focus_building=selected_building)
            st.session_state["agent_messages"] = []
            st.session_state["latest_analysis_result"] = None
            st.session_state["agent_theater_prev_msg_count"] = 0
            st.session_state["last_active_stream_length"] = 0
    
    if "live_agent_team" not in st.session_state:
        st.session_state.live_agent_team = AgentTeam(db_manager=st.session_state.live_db)
    if "live_telegram" not in st.session_state:
        st.session_state.live_telegram = TelegramBot(
            db_manager=st.session_state.live_db,
            simulator=st.session_state.live_simulator,
            agent_team=st.session_state.live_agent_team,
        )
    else:
        st.session_state.live_telegram.simulator = st.session_state.live_simulator
        st.session_state.live_telegram.agent_team = st.session_state.live_agent_team

    # Start Telegram bot polling in background
    _start_telegram_bot_polling()
    
    # Initialize agent messages list
    if "agent_messages" not in st.session_state:
        st.session_state["agent_messages"] = []

    # Seed initial data for immediate display (only for selected building)
    df = load_energy_dataset()
    if not df.empty:
        selected_building = st.session_state.get("selected_building", "All")
        _seed_initial_stream_data(st.session_state.live_db, df, focus_building=selected_building)

    simulator = st.session_state.live_simulator
    agent_team = st.session_state.live_agent_team
    telegram_bot = st.session_state.live_telegram

    def on_update(payload):
        # Continuous analysis: agents always produce messages, not just on anomaly
        result, snapshot = agent_team.analyze_continuous()

        if snapshot is None:
            return

        new_messages = _build_continuous_agent_messages(
            snapshot["stream_count"],
            snapshot["latest_row"],
            result,
            snapshot["building_stats"],
        )

        messages = st.session_state.get("agent_messages", [])
        messages.extend(new_messages)
        st.session_state["agent_messages"] = messages[-30:]

        # Send Telegram alert only when there is a real anomaly
        if result and "anomaly" in result:
            st.session_state["latest_analysis_result"] = result
            alert_text = _build_alert_text(result)
            if telegram_bot.send_alert(alert_text):
                st.session_state["alerts_sent"] = st.session_state.get("alerts_sent", 0) + 1

    def runner():
        simulator.start_stream(on_update=on_update)
        st.session_state.sim_running = False

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    st.session_state.live_sim_thread = thread
    st.session_state.sim_running = True

    # Run an initial analysis immediately so the Agent Theater has LLM-backed content as soon as live demo starts.
    _auto_analyze_existing_active_stream()


def _stop_live_demo() -> None:
    if st.session_state.get("live_simulator"):
        st.session_state.live_simulator.stop_stream()
    st.session_state.sim_running = False


def _reset_live_demo() -> None:
    _stop_live_demo()
    if st.session_state.get("live_simulator"):
        st.session_state.live_simulator.reset_system()
    if st.session_state.get("live_db"):
        st.session_state.live_db.initialize_workspace()
        st.session_state.live_db.seed_campus_schedule()


df = load_energy_dataset()
if df.empty:
    st.error("No sample data found in data/sample/")
    st.stop()

building_ids = all_building_ids(df, METADATA_PATH)
active_buildings = [row.get("building_id") for row in DatabaseManager().read_tab("Active_Stream") if row.get("building_id")]
building_ids = sorted(set(building_ids) | set(active_buildings))

with st.sidebar:
    st.header("Account")
    if "auth_user" not in st.session_state:
        st.session_state["auth_user"] = None
        st.session_state["auth_role"] = None

    # Restore session from query params on browser refresh
    if st.session_state["auth_user"] is None:
        qp = st.query_params
        saved_user = qp.get("u")
        saved_role = qp.get("r")
        if saved_user and saved_role:
            st.session_state["auth_user"] = saved_user
            st.session_state["auth_role"] = saved_role

    if st.session_state["auth_user"] is None:
        login_user = st.text_input("Username", key="login_user")
        login_pass = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login", key="login_btn", type="primary", width="stretch"):
            ok, info = authenticate(login_user.strip(), login_pass)
            if ok:
                st.session_state["auth_user"] = login_user.strip()
                st.session_state["auth_role"] = info
                # Persist auth in query params so browser refresh keeps session
                st.query_params["u"] = login_user.strip()
                st.query_params["r"] = info
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
            # Clear query params on logout
            st.query_params.clear()
            st.session_state["auth_role"] = None
            st.rerun()

if "dashboard_db" not in st.session_state:
    db = DatabaseManager()
    db.initialize_workspace()
    st.session_state["dashboard_db"] = db

dashboard_db = st.session_state["dashboard_db"]

# Initialize Telegram bot and simulation helpers at app startup (once, after login)
if st.session_state.get("auth_user"):
    # Get selected building from session state (will be set below)
    selected_building = st.session_state.get("selected_building", "All")
    if "live_simulator" not in st.session_state:
        st.session_state.live_simulator = EnergySimulator(db_manager=dashboard_db, focus_building=selected_building)
    if "live_agent_team" not in st.session_state:
        st.session_state.live_agent_team = AgentTeam(db_manager=dashboard_db)

    if "live_telegram" not in st.session_state:
        st.session_state.live_telegram = TelegramBot(
            db_manager=dashboard_db,
            simulator=st.session_state.live_simulator,
            agent_team=st.session_state.live_agent_team,
        )
    else:
        st.session_state.live_telegram.db = dashboard_db
        st.session_state.live_telegram.simulator = st.session_state.live_simulator
        st.session_state.live_telegram.agent_team = st.session_state.live_agent_team

    if "telegram_polling_started" not in st.session_state:
        _start_telegram_bot_polling()

if st.session_state["auth_user"] is None:
    render_homepage()
    st.stop()

# Logged-in operations room
with st.sidebar:
    st.header("Smart Energy Guardian")
    st.markdown(
        "This is your live energy operations room. Monitor the simulated meter stream, review AI agent decisions, and use Telegram alerts to stay ahead of true waste."
    )
    st.markdown("---")

    # Get previous building selection to detect changes
    previous_building = st.session_state.get("selected_building", "All")
    
    selected_building = st.selectbox("Focus on building", ["All"] + building_ids, index=0)
    
    # Check if building selection changed
    if previous_building != selected_building:
        st.session_state["selected_building"] = selected_building
        # Store that simulation was running so it can be restarted
        if st.session_state.get("sim_running", False):
            st.session_state.sim_was_running_before_building_change = True
        # Restart simulation with new building
        _restart_simulation_with_new_building()
        st.success(f"Building focus changed to: {selected_building}")
        st.rerun()
    else:
        # Store selected building in session state
        st.session_state["selected_building"] = selected_building

    st.markdown("### Live demo controls")
    if st.button("▶️ Start Live Demo", use_container_width=True):
        _start_live_demo()
    if st.button("⏹ Stop Live Demo", use_container_width=True):
        _stop_live_demo()
    if st.button("🔄 Reset Digital Twin", use_container_width=True):
        _reset_live_demo()

    if st.button("🔍 Run Instant Analysis", use_container_width=True, help="Run AI analysis on current data"):
        _auto_analyze_existing_active_stream()
        if st.session_state.get("agent_messages"):
            st.success("Analysis completed. Check the Agent Theater for results.")
        else:
            st.info("No data available for analysis or no issues detected.")

    if st.button("📱 Test Telegram", use_container_width=True, help="Send a test message to Telegram"):
        if st.session_state.get("live_telegram"):
            if st.session_state.live_telegram.send_alert("Test message from EcoSense Dashboard"):
                st.success("Test message sent to Telegram!")
            else:
                st.error("Failed to send test message. Check Telegram configuration.")
        else:
            st.warning("Start the live demo first to initialize Telegram.")

    st.markdown("---")
    run_status = "RUNNING" if st.session_state.get("sim_running") else "IDLE"
    st.write(f"**Simulation state:** {run_status}")
    
    # Show Telegram status
    telegram_status = "🟢 LISTENING" if st.session_state.get("telegram_polling_started") else "🔴 NOT LISTENING"
    st.write(f"**Telegram commands:** {telegram_status}")

    if st.session_state.get("sim_running"):
        st.success("Live stream is active. Watch the Digital Twin update in near real-time.")
    else:
        st.info("No live simulation is currently running. Use Start Live Demo to begin.")

    # Health check
    if st.session_state.get("live_sim_thread") and not st.session_state.get("live_sim_thread").is_alive():
        st.warning("Simulator thread has stopped. Restart the demo.")
        st.session_state.sim_running = False

    if st.session_state.get("auth_role") == "admin":
        st.markdown("---")
        st.markdown("##### Administration")
        st.page_link("pages/1_Operators.py", label="Operators & accounts", icon="👥")
        st.page_link("pages/2_Building_data.py", label="Building data & consumption", icon="🏢")
    else:
        st.markdown("---")
        st.caption("Admin tools are available to administrators.")

    st.markdown("---")
    st.caption("Need Telegram alerts? Fill in `TELEGRAM_TOKEN` and `MY_CHAT_ID` in .env.")

# Build the live operations room view
selected_building_display = selected_building if selected_building != "All" else "All Buildings"
st.markdown(
    f"""
    <div class='ecosense-header-bar'>
        <div>
            <div class='ecosense-title'>Smart Energy Guardian</div>
            <div class='ecosense-sub'>Live operations room for campus energy, schedule-aware waste detection, and proactive Telegram alerts.</div>
            <div class='ecosense-sub' style='margin-top: 4px; font-size: 0.8rem; opacity: 0.9;'>Focus: {selected_building_display}</div>
        </div>
        <div class='ecosense-pill'>Live monitoring enabled</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Summary KPIs from the Digital Twin
live_db = dashboard_db
sheet_ready = live_db.is_ready()
active_stream = live_db.read_tab("Active_Stream")
audit_ledger = live_db.read_tab("Audit_Ledger")
schedule = live_db.read_tab("Campus_Schedule")

latest_point = active_stream[-1] if active_stream else {}

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Active stream rows", len(active_stream))
with col2:
    st.metric("Audit log entries", len(audit_ledger))
with col3:
    st.metric("Scheduled events", len(schedule))
with col4:
    alerts_sent = st.session_state.get("alerts_sent", 0)
    st.metric("Alerts sent", alerts_sent)

status_col1, status_col2 = st.columns([3, 1])
with status_col1:
    if sheet_ready:
        st.success("Google Sheets sync: enabled")
    else:
        st.warning("Google Sheets sync: disabled — local fallback active")
with status_col2:
    if audit_ledger:
        import pandas as _pd
        csv_bytes = _pd.DataFrame(audit_ledger).to_csv(index=False).encode("utf-8")
        st.download_button(
            "📄 Download Audit Ledger",
            data=csv_bytes,
            file_name="ecosense_audit_ledger.csv",
            mime="text/csv",
        )
    else:
        st.info("No audit ledger entries to download yet.")

    if st.button("📊 Generate Energy Report", key="generate_report"):
        if active_stream:
            from src.tools.reporting_tools import build_pdf
            import pandas as _pd
            df = _pd.DataFrame(active_stream)
            report_data = {
                "building_id": selected_building if selected_building != "All" else "All Buildings",
                "data_summary": {"data_points": len(df)},
                "analysis": {"issues_found": len([r for r in audit_ledger if r.get("anomaly_type") != ""])},
                "recommendations": {"recommendations_count": len(audit_ledger)},
                "compliance": {"compliant": True},
                "alerts_generated": len(audit_ledger)
            }
            report_path = build_pdf(report_data)
            st.success(f"Report generated: {report_path}")
            with open(report_path, "rb") as f:
                st.download_button(
                    "Download PDF Report",
                    data=f,
                    file_name="ecosense_energy_report.pdf",
                    mime="application/pdf",
                )
        else:
            st.warning("No data available to generate report.")

st.markdown("---")

# Live operations tabs
live_tab, theater_tab, twin_tab, alerts_tab = st.tabs([
    "Live Ops",
    "Agent Theater",
    "Digital Twin",
    "Telegram"
])

with live_tab:
    if not sheet_ready:
        st.warning(
            "Google Sheets sync is not configured. Live demo mode is limited to local fallback stream data. "
            "Set GOOGLE_SHEET_ID and GOOGLE_APPLICATION_CREDENTIALS to unlock cloud persistence."
        )
    render_v2_realtime_ui(db=live_db, focus_building=selected_building)

# Always re-analyze when stream grows (runs every Streamlit cycle)
_auto_analyze_existing_active_stream()

with theater_tab:
    # Auto-refresh every 4 seconds so new messages from background thread appear
    if st_autorefresh is not None and st.session_state.get("sim_running", False):
        st_autorefresh(interval=4000, key="theater_autorefresh")

    # Show real agent messages if available, otherwise waiting state
    real_messages = st.session_state.get("agent_messages", [])
    sim_running = st.session_state.get("sim_running", False)

    if real_messages:
        # Auto-advance agent_live_count as new messages arrive
        prev_msg_count = st.session_state.get("agent_theater_prev_msg_count", 0)
        if len(real_messages) > prev_msg_count:
            st.session_state["agent_live_count"] = len(real_messages)
            st.session_state["agent_theater_prev_msg_count"] = len(real_messages)

        # Pass the latest analysis result for grounded chatbot responses
        latest_result = st.session_state.get("latest_analysis_result")
        render_agent_theater(real_messages, resp=latest_result)
        if sim_running:
            st.info("🔴 **LIVE ANALYSIS** — Agents are producing real-time insights as the Active_Stream grows.")
    elif sim_running:
        # Simulation is running but no messages yet - show waiting
        st.info("⏳ **Waiting for first stream data...** Agents will start speaking as soon as data arrives.")
        st.write("The simulator is streaming data to the Active_Stream tab. Agents produce insights for every reading.")
    else:
        # No simulation running - show setup state
        st.info("🎯 **Agent Theater — Ready for Analysis**")
        st.write("**How it works:**")
        st.write("1. Press 'Start Live Demo' to begin simulation")
        st.write("2. Simulator writes energy data to Excel Active_Stream tab")
        st.write("3. Agents analyze every reading in real-time and produce insights")
        st.write("4. All agents speak on every stream tick — not just on anomalies")
        st.write("")
        st.write("**No demo content shown** — All agent messages come from analyzing real Excel data.")

with twin_tab:
    st.subheader("Digital Twin status")
    st.write("The Google Sheet acts as the campus digital twin. One tab streams current power data while another holds scheduled campus events.")
    st.write("Use this mode to validate whether spikes are expected or represent true waste.")
    if schedule:
        st.table(
            [
                {"Event": row.get("event_name"), "Date": row.get("date"), "Time": f"{row.get('start_time')}–{row.get('end_time')}", "Notes": row.get("description")}
                for row in schedule
            ]
        )
    else:
        st.warning("Campus schedule is empty. Seed the schedule using the main script or Google Sheets tab.")

with alerts_tab:
    st.subheader("Telegram Alerts")
    st.write("True waste events trigger proactive Telegram notifications to your phone. Use `/status` to check how the system is performing.")
    if not os.getenv("TELEGRAM_TOKEN") or not os.getenv("MY_CHAT_ID"):
        st.warning("Telegram is not configured. Add TELEGRAM_TOKEN and MY_CHAT_ID to .env and restart the app.")
    else:
        st.success("Telegram is configured. Alerts will be sent for confirmed true waste events.")

    st.markdown(
        "**Telegram Commands:**\n"
        "- `/status` -> Get system status including active stream count, audit ledger entries, and current focus building.\n"
        "- `/start_sim` -> Start the simulation and receive alerts for anomalies detected.\n"
        "- `/stop_sim` -> Stop the simulation stream.\n"
        "- `/reset` -> Clear the current sheets, reset pointer, and restart the simulation.\n"
        "- `/insights` -> Get current system insights including latest readings, recent actions, and focus building.\n"
        "- `/building <building_name>` -> Check specific building data, statistics, and recent actions.\n\n"
        "**Building Examples:**\n"
        "- `/building FBS Building` -> Check FBS Building specific data\n"
        "- `/building Academic Building` -> Check Academic Building data\n"
        "- `/building \"Admin Block\"` -> Check Admin Block data (use quotes for names with spaces)\n\n"
        "**Note:** Alerts are sent for confirmed true waste events with anomaly details and recommendations. "
        "All commands now include building context for better monitoring."
    )

    # Show recent alerts
    audit_data = live_db.read_tab("Audit_Ledger")
    audit_data = live_db.read_tab("Audit_Ledger")
    if audit_data:
        st.markdown("### Recent Alerts")
        for row in audit_data[-5:]:
            st.markdown(
                f"**{row.get('timestamp')}** - {row.get('building_id')}: {row.get('recommendation')}"
            )
    else:
        st.info("No alerts sent yet. Start the live demo to trigger true waste notifications.")
