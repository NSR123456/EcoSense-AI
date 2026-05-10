import html
import time
import streamlit as st
from src.llm.client import generate

COLORS = {
    "Planner": "#4A63E7",
    "DetectIssues": "#0D7BD8",
    "RootCause": "#C0392B",
    "ActionPlanner": "#0C9D58",
    "Compliance": "#D97706",
    "Comparison": "#7C6CEB",
    "Critic": "#4B5563",
    "Synthesizer": "#1F2937",
}

ICONS = {
    "Planner": "🧭",
    "DetectIssues": "⚠️",
    "RootCause": "🔍",
    "ActionPlanner": "✅",
    "Compliance": "📋",
    "Comparison": "⚖️",
    "Critic": "🛠️",
    "Synthesizer": "📌",
}

TYPE_LABELS = {
    "plan": "Planning Complete",
    "finding": "Problems Found",
    "proposal": "Action Suggested",
    "critique": "Quality Check Done",
    "decision": "Final Decision Ready",
    "info": "System Update",
}

ROLE_DESCRIPTIONS = {
    "Planner": "Chooses the best way to analyze your building's energy use",
    "DetectIssues": "Finds unusual energy patterns and problems",
    "RootCause": "Figures out why energy problems are happening",
    "ActionPlanner": "Suggests practical steps to fix energy issues",
    "Critic": "Double-checks recommendations for safety and quality",
    "Synthesizer": "Puts everything together into one clear action plan",
}


def _step_index(agent: str) -> int:
    order = {
        "Planner": 1,
        "DetectIssues": 2,
        "RootCause": 3,
        "ActionPlanner": 4,
        "Critic": 5,
        "Synthesizer": 6,
    }
    return order.get(agent, 99)


def _next_step_hint(agent: str, mtype: str) -> str:
    if mtype == "proposal":
        return "💡 **What to do next:** Start this recommended action today for the best energy savings."
    if mtype == "decision":
        return "✅ **What to do next:** Go to the Decision Center tab to see the full action plan and start implementing."
    if mtype == "finding":
        return "🔍 **What to do next:** Look at the severity levels - focus on 'Urgent' issues first, then review confidence levels."
    if agent == "Critic":
        return "🛠️ **What to do next:** If any quality concerns are shown, the system will automatically improve the recommendations."
    if agent == "Synthesizer":
        return "📋 **What to do next:** The analysis is complete! Check the Decision Center for your final action plan."
    return "➡️ **What to do next:** Continue reading to see the complete analysis."


def _operator_text(agent: str, content: str) -> str:
    text = content.lower()
    if agent == "Planner":
        return "The system picked the best process to analyze your building."
    if agent == "DetectIssues":
        return "The system found unusual energy behavior."
    if agent == "RootCause":
        return "The system found the likely reason for the problem. Check schedule and equipment use."
    if agent == "ActionPlanner":
        return "The system selected the best action to do now."
    if agent == "Critic":
        if "0" in text and "critique" in text:
            return "Quality check passed. No major issues in this advice."
        return "The system checked if the advice is safe and useful."
    if agent == "Synthesizer":
        return "Final advice is ready for operator action. Start with high urgency actions."
    return "System update ready."


def _answer_operator_question(question: str) -> str:
    q = question.strip().lower()
    if not q:
        return "Ask: What should I do first?"
    if "how do i know" in q or ("how" in q and "inconsistent" in q):
        return (
            "Check 3 signs today: (1) power stays high after-hours, "
            "(2) big jumps at random hours, (3) same equipment runs when area is empty. "
            "If 2 signs are true, usage is inconsistent."
        )
    if "first" in q or "start" in q or "now" in q:
        return "Start with the top action from ActionPlanner. Do high urgency tasks today."
    if "why" in q or "cause" in q:
        return "Check RootCause card. It shows the likely reason behind the energy issue."
    if "safe" in q or "trust" in q or "reliable" in q:
        return "Check Critic card. If critiques are 0, advice passed a quality review."
    if "confidence" in q or "sure" in q:
        return "Use confidence score as guidance: higher confidence means stronger evidence."
    return "Follow the live agent chat from Planner to Synthesizer and execute the top action first."


def _build_context_for_qa(resp: dict) -> str:
    if not isinstance(resp, dict):
        return ""
    top_issue = resp.get("issue_card", {}).get("value", "unknown")
    top_cause = resp.get("cause_card", {}).get("value", "unknown")
    top_action = resp.get("action_card", {}).get("value", "unknown")
    risk = resp.get("risk_card", {}).get("value", "unknown")
    confidence = resp.get("confidence", "unknown")
    issues = resp.get("issues", [])
    actions = resp.get("actions", [])
    metrics = resp.get("metrics", {})
    top_action_what = actions[0].get("what", "") if actions else ""
    top_action_when = actions[0].get("when", "") if actions else ""
    return (
        f"Risk: {risk}\n"
        f"Top issue: {top_issue}\n"
        f"Top cause: {top_cause}\n"
        f"Top action: {top_action}\n"
        f"Confidence: {confidence}\n"
        f"Issues: {issues}\n"
        f"Actions: {actions}\n"
        f"Metrics: {metrics}\n"
        f"Top action details: what={top_action_what}, when={top_action_when}\n"
    )


def _looks_like_echo(question: str, answer: str) -> bool:
    q_words = {w for w in question.lower().split() if len(w) > 2}
    a_words = {w for w in answer.lower().split() if len(w) > 2}
    if not a_words:
        return True
    overlap = len(q_words & a_words) / max(1, len(q_words))
    # High overlap with very short answer usually means paraphrasing user text.
    return overlap > 0.75 and len(answer.split()) < 20


def _rule_based_operator_answer(question: str, resp: dict) -> str:
    q = question.strip().lower()
    issues = resp.get("issues", []) if isinstance(resp, dict) else []
    actions = resp.get("actions", []) if isinstance(resp, dict) else []
    metrics = resp.get("metrics", {}) if isinstance(resp, dict) else {}

    if "what are the issues" in q or ("issues" in q and "what" in q):
        if not issues:
            return "No major issue detected in this run."
        lines = []
        for issue in issues[:3]:
            name = issue.get("name", "Issue")
            sev = str(issue.get("severity", "unknown")).title()
            conf = issue.get("confidence")
            conf_txt = f"{int(round(float(conf) * 100))}%" if isinstance(conf, (int, float)) else "N/A"
            lines.append(f"- {name} ({sev}, confidence {conf_txt})")
        action_hint = actions[0].get("title", "follow top suggested action") if actions else "follow top suggested action"
        return "Current issues:\n" + "\n".join(lines) + f"\nFirst action: {action_hint}."

    if "anomal" in q:
        anomaly_count = metrics.get("anomaly_count")
        if anomaly_count is None:
            return "Anomaly means unusual energy reading versus normal pattern."
        return (
            f"There are {anomaly_count} anomalies. "
            "Anomaly means unusual energy behavior compared to normal days. "
            "Check after-hours load, sudden spikes, and irregular equipment runtime."
        )

    if "different" in q and ("building" in q or "flats" in q or "area" in q):
        return (
            "Good point. Current model uses absolute kWh, so building size differences can bias comparison. "
            "Best practice: add area and occupancy metadata, then compare normalized KPIs "
            "(kWh/sqft, kWh/flat, kWh/occupant). I can help you add this schema next."
        )

    return ""


def _specialized_takeaway(agent: str, content: str) -> str:
    c = content.lower()
    if agent == "Planner":
        return "Route selected so the system does detect -> cause -> action -> quality check."
    if agent == "DetectIssues":
        if "detected" in c and "issue" in c:
            return "Issue detection complete. Prioritize high severity first."
        return "Issue scanning complete for current building data."
    if agent == "RootCause":
        return "Root cause identified. Fixing this prevents repeated high usage."
    if agent == "ActionPlanner":
        return "Action is time-bound and impact-focused for operators."
    if agent == "Critic":
        return "Decision quality validated before final recommendation."
    if agent == "Synthesizer":
        return "All agent outputs merged into a single operator decision."
    return "Specialized output ready."


def _build_context_from_agent_messages() -> str:
    """Build a QA context string from accumulated agent messages in session state."""
    import streamlit as _st
    messages = _st.session_state.get("agent_messages", [])
    if not messages:
        return ""
    # Take the last 12 messages for context
    recent = messages[-12:]
    lines = []
    for m in recent:
        agent = m.get("agent", "Agent")
        content = m.get("content", "")
        lines.append(f"{agent}: {content}")
    return "\n".join(lines)


def _llm_operator_answer(question: str, resp: dict) -> str:
    ruled = _rule_based_operator_answer(question, resp or {})
    if ruled:
        return ruled

    # Build context from resp if available, otherwise from agent messages
    has_resp_data = (
        resp and isinstance(resp, dict)
        and any(key in resp for key in ['issues', 'actions', 'metrics', 'issue_card', 'cause_card', 'action_card'])
    )

    if has_resp_data:
        context = _build_context_for_qa(resp)
    else:
        # Fallback: use accumulated agent messages as context
        context = _build_context_from_agent_messages()
        if not context:
            # No data at all — give a useful fallback instead of "refresh"
            return _answer_operator_question(question)

    prompt = (
        "You are an energy operations assistant for low-literacy building operators. "
        "Answer in very simple English, 2-4 short lines, practical and action-first. "
        "If asked what to do, give clear today action and safety note. "
        "Never repeat the user's sentence. Give concrete checks and thresholds.\n\n"
        f"Current decision context:\n{context}\n"
        f"Operator question: {question}\n"
        "Answer:"
    )
    text = generate(prompt, max_length=120).strip()

    # Reject low-quality echo/paraphrase outputs
    if text and not _looks_like_echo(question, text):
        return text
    else:
        # Fallback to rule-based answer
        return _answer_operator_question(question)


def _rag_stats(resp: dict | None) -> dict:
    evidence = (resp or {}).get("evidence", []) if isinstance(resp, dict) else []
    by_source = {}
    for item in evidence:
        src = str(item.get("source", "unknown")).lower()
        by_source[src] = by_source.get(src, 0) + 1
    return {
        "total": len(evidence),
        "bm25": by_source.get("bm25", 0),
        "vector": by_source.get("vector", 0),
    }


def _agent_specific_value(agent: str, content: str) -> str:
    txt = content.strip()
    if not txt:
        return "No output captured."
    if agent == "Planner" and "nodes:" in txt:
        return txt.split("nodes:", 1)[-1].strip()
    if agent == "DetectIssues":
        return txt
    if agent == "RootCause":
        return txt.replace("Top cause:", "").strip()
    if agent == "ActionPlanner":
        return txt.replace("Top action:", "").strip()
    if agent == "Critic":
        return txt
    if agent == "Synthesizer":
        return txt
    return txt


def _get_operator_guidance(agent: str, content: str) -> str:
    """Provide specific guidance for operators based on agent type and content."""
    if agent == "Planner":
        return "This shows how the system thinks step-by-step. Next agents will follow this plan to give you the best analysis."
    elif agent == "DetectIssues":
        if "anomalies=" in content:
            anomaly_count = content.split("anomalies=")[1].split(",")[0].strip()
            return f"There are {anomaly_count} unusual energy patterns. Focus on the high-severity issues first - they need immediate attention."
        return "Energy problems found. Check the severity levels - red/urgent issues should be fixed soon to save energy costs."
    elif agent == "RootCause":
        return "This explains WHY the energy problem exists. Use this to understand the real issue, not just symptoms."
    elif agent == "ActionPlanner":
        return "This is your action plan! Start with the highest priority items. Each action tells you what to do and why it's important."
    elif agent == "Critic":
        if "0" in content and "critique" in content:
            return "Quality check passed! The recommendations are safe and reliable. You can confidently implement them."
        return "The system found some concerns. Don't worry - it will automatically improve the recommendations."
    elif agent == "Synthesizer":
        return "This is your complete energy action plan. Go to Decision Center to see all recommendations and start implementing."
    else:
        return "This is a system update. Continue reading to see the complete analysis."


def _generate_simple_explanation(agent: str, content: str) -> str:
    """Use LLM to generate simple explanations for technical agent outputs."""
    if not content or content.strip() == "":
        return ""
    
    # Create a prompt based on the agent type and content
    if agent == "Planner":
        prompt = f"Explain this technical planning decision in 1-2 simple sentences for a building operator: '{content}'. Focus on what route was chosen and why it's good for energy analysis."
    elif agent == "DetectIssues":
        prompt = f"Explain these energy issues in simple terms for a building operator: '{content}'. What problems were found and what do they mean for daily operations?"
    elif agent == "RootCause":
        prompt = f"Explain this root cause analysis in simple terms: '{content}'. What is the likely reason for the energy problem?"
    elif agent == "ActionPlanner":
        prompt = f"Explain this action recommendation in simple terms for a building operator: '{content}'. What should they do and why is it urgent?"
    elif agent == "Critic":
        prompt = f"Explain this quality check result in simple terms: '{content}'. Is the advice safe and reliable?"
    elif agent == "Synthesizer":
        prompt = f"Explain this final decision in simple terms for a building operator: '{content}'. What is the main recommendation?"
    else:
        prompt = f"Explain this technical update in simple terms: '{content}'. What does it mean for the operator?"
    
    explanation = generate(prompt, max_length=100)
    return explanation if explanation else ""


def _film_line(agent: str, content: str) -> str:
    if agent == "Planner":
        return "I picked the best analysis route for this building."
    if agent == "DetectIssues":
        return "I found energy-use problems that need attention."
    if agent == "RootCause":
        return "I found the likely reason behind the problem."
    if agent == "ActionPlanner":
        return "I chose the best action to start today."
    if agent == "Critic":
        return "I checked quality and safety before final advice."
    if agent == "Synthesizer":
        return "I combined everything into one clear decision."
    return content[:120] if content else "System update."


def _film_detail_line(agent: str, content: str) -> str:
    text = content.strip()
    if not text:
        return "No additional detail."
    if agent == "Planner":
        route = "unknown"
        nodes = ""
        if "Selected route:" in text:
            route = text.split("Selected route:", 1)[1].split(";", 1)[0].strip()
        if "nodes:" in text:
            nodes = text.split("nodes:", 1)[1].strip()
            # Convert technical node names to simple descriptions
            node_descriptions = {
                "retrieval": "Gather knowledge",
                "detect_issues": "Find problems", 
                "root_cause": "Find reasons",
                "action_planner": "Plan actions",
                "critic": "Check quality",
                "synthesizer": "Create summary"
            }
            simple_nodes = []
            for node in nodes.replace("[", "").replace("]", "").replace("'", "").split(","):
                node = node.strip()
                simple_nodes.append(node_descriptions.get(node, node))
            nodes = str(simple_nodes)
        if nodes:
            return f"Analysis approach: {route} | Process steps: {nodes}"
        return f"Analysis approach: {route}"
    if agent == "DetectIssues":
        # Make issue detection more readable
        text = text.replace("Detected", "Found:")
        text = text.replace("anomalies=", "unusual readings: ")
        text = text.replace("trend=", "usage pattern: ")
        return text
    if agent == "RootCause":
        return text.replace("Top cause:", "Most likely reason:")
    if agent == "ActionPlanner":
        return text.replace("Top action:", "Recommended action:")
    if agent == "Critic":
        return text.replace("Critiques:", "Quality concerns:")
    if agent == "Synthesizer":
        return text.replace("Finalized response", "Final recommendation")
    return text


def _detect_issue_numbers(content: str) -> tuple[int | None, int | None]:
    text = content.lower()
    issues = None
    anomalies = None
    if "detected" in text and "issue" in text:
        try:
            issues = int(text.split("detected", 1)[1].split("issue", 1)[0].strip())
        except Exception:
            issues = None
    if "anomalies=" in text:
        try:
            anomalies = int(text.split("anomalies=", 1)[1].split(",", 1)[0].strip())
        except Exception:
            anomalies = None
    return issues, anomalies


def _detail_chunks(agent: str, content: str) -> list[str]:
    detail = _film_detail_line(agent, content)
    raw_parts = [p.strip() for p in detail.replace("|", ";").split(";") if p.strip()]
    chunks = raw_parts if raw_parts else [detail]
    return chunks[:3]


def render_agent_theater(messages: list, resp: dict | None = None):
    if not messages:
        st.info("No agent messages.")
        return

    sorted_messages = sorted(messages, key=lambda m: _step_index(m.get("agent", "Agent")))

    st.markdown(
        """
    <style>
    .agent-train-banner {
        border-radius: 12px;
        background: linear-gradient(90deg, #ECFEFF 0%, #F0FDF4 100%);
        border: 1px solid #BAE6FD;
        color: #0F172A;
        padding: 10px 12px;
        margin-bottom: 12px;
        font-weight: 600;
    }
    .agent-card {
        padding: 12px 14px;
        margin: 10px 0;
        border-radius: 12px;
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        color: #111827;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.05);
        transition: transform 0.15s ease, box-shadow 0.2s ease;
    }
    .agent-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.12);
    }
    .agent-title {
        font-weight: 700;
        font-size: 1rem;
        margin-bottom: 6px;
    }
    .agent-type {
        display: inline-block;
        font-size: 0.78rem;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 999px;
        background: #F3F4F6;
        color: #111827;
        margin-bottom: 8px;
    }
    .agent-content {
        font-size: 1rem;
        line-height: 1.45;
        margin: 4px 0 8px;
    }
    .agent-hint {
        font-size: 0.9rem;
        color: #374151;
        background: #F9FAFB;
        border-left: 3px solid #D1D5DB;
        padding: 6px 10px;
        border-radius: 8px;
    }
    .agent-step {
        font-size: 0.82rem;
        font-weight: 700;
        color: #334155;
        margin-bottom: 4px;
    }
    .agent-icon {
        display: inline-block;
        animation: pulse 1.6s ease-in-out infinite;
        margin-right: 6px;
    }
    .timeline {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin: 8px 0 14px;
    }
    .timeline-pill {
        padding: 4px 8px;
        border-radius: 999px;
        border: 1px solid #93C5FD;
        font-size: 0.8rem;
        font-weight: 800;
        background: #DBEAFE;
        color: #0B1324;
        text-shadow: none;
    }
    .timeline-pill.active {
        color: #FFFFFF;
        border-color: transparent;
    }
    .agent-special {
        border-radius: 8px;
        background: #F8FAFC;
        border: 1px dashed #CBD5E1;
        padding: 7px 10px;
        margin: 8px 0;
        font-size: 0.88rem;
        color: #1E293B;
    }
    .agent-role {
        font-size: 0.8rem;
        color: #475569;
        margin-bottom: 5px;
    }
    .cartoon-wrap {
        display: flex;
        gap: 10px;
        align-items: center;
        overflow-x: auto;
        padding: 8px 2px 12px;
        margin-bottom: 6px;
    }
    .cartoon-agent {
        min-width: 92px;
        text-align: center;
        font-size: 0.78rem;
        color: #0B1324;
        font-weight: 800;
    }
    .cartoon-head {
        width: 38px;
        height: 38px;
        border-radius: 50%;
        margin: 0 auto 6px;
        border: 2px solid #ffffff;
        box-shadow: 0 0 0 2px rgba(15, 23, 42, 0.08);
        animation: bob 2s ease-in-out infinite;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
    }
    .cartoon-bubble {
        font-size: 0.72rem;
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 999px;
        padding: 2px 8px;
        display: inline-block;
    }
    .agent-live {
        border-radius: 10px;
        background: #DBEAFE;
        border: 1px solid #93C5FD;
        color: #0B1324;
        padding: 8px 10px;
        margin: 8px 0 10px;
        font-weight: 800;
        text-shadow: none;
        animation: glow 1.8s ease-in-out infinite;
    }
    .film-stage {
        position: relative;
        border-radius: 16px;
        border: 1px solid #C7D2FE;
        background: radial-gradient(circle at 50% 18%, #E0E7FF 0%, #F8FAFC 60%, #EEF2FF 100%);
        padding: 18px 16px 14px;
        margin: 12px 0;
        overflow: hidden;
    }
    .film-spot {
        position: absolute;
        left: 50%;
        top: -90px;
        width: 280px;
        height: 220px;
        transform: translateX(-50%);
        background: radial-gradient(ellipse at center, rgba(255,255,255,0.85) 0%, rgba(255,255,255,0.0) 70%);
        animation: sway 3.2s ease-in-out infinite;
        pointer-events: none;
    }
    .film-agent {
        position: relative;
        z-index: 2;
        text-align: center;
        margin-bottom: 8px;
    }
    .film-avatar {
        width: 64px;
        height: 64px;
        border-radius: 50%;
        margin: 0 auto 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 34px;
        border: 3px solid #fff;
        box-shadow: 0 8px 18px rgba(15,23,42,0.18);
        animation: bob 1.8s ease-in-out infinite;
    }
    .film-title {
        font-weight: 800;
        font-size: 1rem;
        margin-bottom: 6px;
    }
    .film-bubble {
        max-width: 760px;
        margin: 0 auto;
        border-radius: 14px;
        border: 1px solid #BFDBFE;
        background: #EFF6FF;
        padding: 10px 12px;
        font-size: 1.02rem;
        line-height: 1.45;
        color: #0B1324;
        font-weight: 700;
        text-shadow: none;
        box-shadow: 0 6px 14px rgba(15,23,42,0.08);
        animation: typein 0.45s ease-out;
    }
    .film-sub {
        margin-top: 10px;
        text-align: center;
        font-size: 0.87rem;
        color: #334155;
        font-weight: 700;
        letter-spacing: 0.2px;
    }
    .film-detail {
        margin-top: 8px;
        text-align: center;
        font-size: 0.88rem;
        color: #1E293B;
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 6px 10px;
    }
    .film-next {
        margin-top: 10px;
        text-align: center;
        font-size: 0.9rem;
        color: #0F172A;
        background: #DBEAFE;
        border: 1px solid #BFDBFE;
        border-radius: 999px;
        padding: 6px 10px;
        display: inline-block;
    }
    .cast-row {
        display: flex;
        justify-content: center;
        gap: 8px;
        margin-top: 10px;
        flex-wrap: wrap;
    }
    .cast-avatar {
        width: 34px;
        height: 34px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #FFFFFF;
        border: 1px solid #D1D5DB;
        font-size: 17px;
        animation: pulse 1.5s ease-in-out infinite;
        opacity: 0.6;
    }
    .cast-avatar.active {
        opacity: 1;
        transform: scale(1.12);
        box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.22);
    }
    .viz-strip {
        margin-top: 10px;
        display: flex;
        gap: 8px;
        justify-content: center;
        flex-wrap: wrap;
    }
    .viz-chip {
        border-radius: 999px;
        border: 1px solid #93C5FD;
        background: #DBEAFE;
        padding: 4px 10px;
        font-size: 0.8rem;
        font-weight: 700;
        color: #0B1324;
        text-shadow: none;
        animation: pulse 1.8s ease-in-out infinite;
    }
    .speech {
        margin: 10px auto 2px;
        max-width: 520px;
        border-radius: 14px;
        border: 1px solid #86EFAC;
        background: #ECFDF3;
        padding: 8px 10px;
        font-size: 0.9rem;
        color: #052E16;
        font-weight: 700;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.07);
    }
    .chat-scene {
        margin-top: 10px;
    }
    .chat-row {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        margin: 10px 0;
        animation: cardFadeIn 0.45s ease-out;
    }
    .chat-avatar {
        width: 42px;
        height: 42px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 2px solid #FFFFFF;
        box-shadow: 0 0 0 2px rgba(15,23,42,0.08);
        font-size: 22px;
        flex: 0 0 42px;
        animation: bob 2s ease-in-out infinite;
    }
    .chat-bubble {
        flex: 1;
        border-radius: 14px;
        border: 1px solid #BFDBFE;
        background: #EFF6FF;
        color: #0B1324;
        padding: 10px 12px;
        box-shadow: 0 5px 12px rgba(15,23,42,0.08);
    }
    .chat-head {
        font-size: 0.85rem;
        font-weight: 800;
        margin-bottom: 6px;
    }
    .chat-main {
        font-size: 1rem;
        font-weight: 700;
        margin-bottom: 6px;
    }
    .chat-detail {
        font-size: 0.9rem;
        border-radius: 10px;
        border: 1px solid #D1D5DB;
        background: #FFFFFF;
        padding: 6px 8px;
        margin: 4px 0;
    }
    .chat-handoff {
        margin: 2px 0 6px 54px;
        color: #334155;
        font-size: 0.84rem;
        font-weight: 700;
        animation: pulse 1.5s ease-in-out infinite;
    }
    .typing {
        display: inline-flex;
        gap: 4px;
        margin-left: 6px;
    }
    .dot {
        width: 5px;
        height: 5px;
        border-radius: 50%;
        background: #334155;
        animation: blink 1.1s infinite ease-in-out;
    }
    .dot:nth-child(2) { animation-delay: 0.15s; }
    .dot:nth-child(3) { animation-delay: 0.3s; }
    @keyframes blink {
        0%, 80%, 100% { opacity: 0.25; transform: translateY(0); }
        40% { opacity: 1; transform: translateY(-2px); }
    }
    @keyframes bob {
        0% { transform: translateY(0px); }
        50% { transform: translateY(-5px); }
        100% { transform: translateY(0px); }
    }
    @keyframes sway {
        0% { transform: translateX(-50%) rotate(0deg); }
        50% { transform: translateX(-50%) rotate(2deg); }
        100% { transform: translateX(-50%) rotate(0deg); }
    }
    @keyframes typein {
        from { opacity: 0; transform: translateY(10px) scale(0.98); }
        to { opacity: 1; transform: translateY(0) scale(1); }
    }
    @keyframes glow {
        0% { box-shadow: 0 0 0 rgba(79, 70, 229, 0.0); }
        50% { box-shadow: 0 0 14px rgba(79, 70, 229, 0.22); }
        100% { box-shadow: 0 0 0 rgba(79, 70, 229, 0.0); }
    }
    @keyframes pulse {
        0% { transform: scale(1); opacity: 0.8; }
        50% { transform: scale(1.12); opacity: 1; }
        100% { transform: scale(1); opacity: 0.8; }
    }
    .card-animate {
        animation: cardFadeIn 0.35s ease-out;
    }
    @keyframes cardFadeIn {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="agent-train-banner">Training mode: Follow cards from top to bottom. Each card explains one step in simple words.</div>',
        unsafe_allow_html=True,
    )

    # Technical transparency strip for architecture value
    rag = _rag_stats(resp)
    t1, t2, t3, t4 = st.columns(4)
    with t1:
        st.metric("Architecture", "Multi-Agent")
    with t2:
        st.metric("Reasoning Engine", "LangGraph")
    with t3:
        st.metric("RAG Retrieval", f"{rag['total']} evidence")
    with t4:
        st.metric("Sources", f"BM25 {rag['bm25']} | Vector {rag['vector']}")
    st.caption("System uses specialized agents with hybrid retrieval (BM25 + vector) before final synthesis.")

    with st.expander("Why multiple agents (not one LLM)?", expanded=False):
        st.markdown(
            """
            - **Better reliability:** each agent has one job, so fewer mixed-up outputs.
            - **Traceable decisions:** you can see where issue, cause, and action came from.
            - **Built-in quality gate:** the Critic checks before final advice.
            - **Operator readiness:** Synthesizer converts technical outputs into one clear decision.
            - **RAG grounding:** retrieval evidence supports decisions before final response.
            """
        )

    # ── Live group-chat mode ──────────────────────────────────────────
    # Track conversation changes without resetting live_count to 0 every
    # time new messages arrive (that was causing the "stuck at typing" bug).
    if "agent_user_thread" not in st.session_state:
        st.session_state["agent_user_thread"] = []

    sim_running = st.session_state.get("sim_running", False)
    selected_building = st.session_state.get("selected_building", "All")

    # When simulation is running, always show ALL messages (auto-advance)
    if sim_running:
        st.session_state["agent_live_count"] = len(sorted_messages)
    elif st.session_state.get("agent_live_count", 0) == 0 and sorted_messages:
        st.session_state["agent_live_count"] = 1

    st.subheader("Live Agent Group Chat")
    if sim_running:
        st.success(f"🟢 Live demo active for {selected_building}. Agents are producing insights in real-time as the stream grows.")
    else:
        st.info("Start the live demo to see agents respond in real-time to your building's energy data.")
    st.caption("Agents speak on every stream tick. Scroll down to see the latest messages.")

    c1, c2, c3 = st.columns([1, 1, 1.4])
    with c1:
        if st.button("Start / Restart Live", key="agent_live_restart"):
            st.session_state["agent_live_count"] = len(sorted_messages)
            st.session_state["agent_user_thread"] = []
            st.rerun()
    with c2:
        if st.button("Next Agent Reply", key="agent_live_next", disabled=st.session_state.get("agent_live_count", 0) >= len(sorted_messages)):
            st.session_state["agent_live_count"] = min(len(sorted_messages), st.session_state.get("agent_live_count", 0) + 1)
            st.rerun()
    with c3:
        auto_play = st.toggle("Auto-play replies", value=sim_running, key="agent_live_autoplay")

    live_count = st.session_state.get("agent_live_count", 0)
    st.progress(0 if not sorted_messages else min(1.0, live_count / max(1, len(sorted_messages))))
    st.caption(f"Showing {live_count} of {len(sorted_messages)} agent messages")

    # Render visible messages
    for idx, m in enumerate(sorted_messages[:live_count]):
        agent = m.get("agent", "Agent")
        icon = ICONS.get(agent, "🤖")
        mtype_raw = str(m.get("type", "info")).lower()
        mtype = TYPE_LABELS.get(mtype_raw, "Update")
        content_text = str(m.get("content", ""))
        role = ROLE_DESCRIPTIONS.get(agent, "Specialized assistant")

        with st.chat_message(name=agent, avatar=icon):
            st.markdown(f"**{agent} · {mtype}**")

            # Show the REAL content from the agent (the actual insight)
            st.markdown(content_text)

            # Role description (collapsed for brevity during live streaming)
            with st.expander(f"ℹ️ About {agent}", expanded=False):
                st.markdown(f"**Role:** {role}")
                guidance = _get_operator_guidance(agent, content_text)
                if guidance:
                    st.markdown(f"📝 {guidance}")

            # Special rendering for anomaly-related messages
            if agent == "DetectIssues" and mtype_raw == "finding":
                issue_list = (resp or {}).get("issues", []) if isinstance(resp, dict) else []
                if issue_list:
                    st.markdown("**🔍 Issues detected:**")
                    for issue in issue_list[:3]:
                        name = issue.get("name", "Unnamed issue")
                        sev = str(issue.get("severity", "unknown")).title()
                        conf = issue.get("confidence")
                        conf_text = f"{int(round(conf * 100))}%" if isinstance(conf, (int, float)) else "N/A"
                        sev_emoji = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(sev, "⚪")
                        st.markdown(f"  {sev_emoji} **{name}** — {sev} severity, {conf_text} confidence")

            if agent == "ActionPlanner" and mtype_raw == "proposal":
                st.info("⚡ Operator action: Start this task first today for best impact.")
            elif agent == "Synthesizer" and mtype_raw == "decision":
                st.success("📌 Summary ready. Check Decision Center for full action plan.")

        # Handoff indicator between different agents
        if idx < live_count - 1:
            next_agent = sorted_messages[idx + 1].get("agent", "Agent")
            if next_agent != agent:
                st.caption(f"→ Handoff to {next_agent}")

    # Live streaming indicator (only when sim is running and more data is expected)
    if sim_running and live_count > 0:
        st.markdown(
            '<div style="text-align:center; padding:8px; color:#059669; font-weight:700;">'
            '🔄 Waiting for next stream tick… agents will respond automatically'
            '</div>',
            unsafe_allow_html=True,
        )

    # User can chat in the same messenger thread
    for turn in st.session_state["agent_user_thread"][-8:]:
        with st.chat_message(name="user", avatar="🙂"):
            st.markdown(turn["q"])
        with st.chat_message(name="AI Team", avatar="🤝"):
            st.markdown(turn["a"])

    user_msg = st.chat_input(
        placeholder="Type in group: Ask anything about issue, cause, action, confidence, or building summary...",
        key="agent_user_input"
    )
    if user_msg and user_msg.strip():
        answer = _llm_operator_answer(user_msg.strip(), resp or {})
        st.session_state["agent_user_thread"].append({"q": user_msg.strip(), "a": answer})
        st.rerun()

    # Auto-play: advance one message at a time when not in sim mode
    if auto_play and not sim_running and live_count < len(sorted_messages):
        time.sleep(1.1)
        st.session_state["agent_live_count"] = min(len(sorted_messages), live_count + 1)
        st.rerun()

    return


    # Step playback controls
    max_steps = len(sorted_messages)
    if "agent_step_cursor" not in st.session_state:
        st.session_state["agent_step_cursor"] = 1
    st.session_state["agent_step_cursor"] = max(1, min(st.session_state["agent_step_cursor"], max_steps))

    left, middle, right = st.columns([1, 2, 1])
    with left:
        if st.button("Previous Step", key="agent_prev_step", disabled=st.session_state["agent_step_cursor"] <= 1):
            st.session_state["agent_step_cursor"] -= 1
            st.rerun()
    with middle:
        st.progress(st.session_state["agent_step_cursor"] / max_steps)
        st.caption(f"Step Play mode: {st.session_state['agent_step_cursor']} of {max_steps}")
    with right:
        if st.button("Next Step", key="agent_next_step", disabled=st.session_state["agent_step_cursor"] >= max_steps):
            st.session_state["agent_step_cursor"] += 1
            st.rerun()

    show_all = st.toggle("Show full conversation", value=False, key="agent_show_all")
    film_mode = st.toggle("Film Mode (simple animated view)", value=True, key="agent_film_mode")

    timeline_html = ['<div class="timeline">']
    for idx, m in enumerate(sorted_messages, start=1):
        agent = m.get("agent", "Agent")
        color = COLORS.get(agent, "#64748B")
        cls = "timeline-pill active" if idx == st.session_state["agent_step_cursor"] else "timeline-pill"
        style = f' style="background:{color};"' if idx == st.session_state["agent_step_cursor"] else ""
        timeline_html.append(f'<span class="{cls}"{style}>{idx}. {agent}</span>')
    timeline_html.append("</div>")
    st.markdown("".join(timeline_html), unsafe_allow_html=True)

    # Cartoon-style animated agent strip
    cartoon_html = ['<div class="cartoon-wrap">']
    for idx, m in enumerate(sorted_messages, start=1):
        agent = m.get("agent", "Agent")
        icon = ICONS.get(agent, "🤖")
        color = COLORS.get(agent, "#64748B")
        bubble = TYPE_LABELS.get(str(m.get("type", "info")).lower(), "Update")
        active = idx == st.session_state["agent_step_cursor"]
        bubble_text = "Working now..." if active else bubble
        cartoon_html.append(
            f'<div class="cartoon-agent">'
            f'<div class="cartoon-head" style="background:{color}22;">{icon}</div>'
            f'<div><strong>{agent}</strong></div>'
            f'<div class="cartoon-bubble">{html.escape(bubble_text)}</div>'
            f'</div>'
        )
    cartoon_html.append("</div>")
    st.markdown("".join(cartoon_html), unsafe_allow_html=True)

    active_msg = sorted_messages[st.session_state["agent_step_cursor"] - 1]
    st.markdown(
        f'<div class="agent-live">Live Agent: {ICONS.get(active_msg.get("agent", "Agent"), "🤖")} {active_msg.get("agent", "Agent")} is presenting this step.</div>',
        unsafe_allow_html=True,
    )

    visible_messages = sorted_messages if show_all else [sorted_messages[st.session_state["agent_step_cursor"] - 1]]

    if film_mode and visible_messages:
        current = visible_messages[0]
        agent = current.get("agent", "Agent")
        color = COLORS.get(agent, "#64748B")
        icon = ICONS.get(agent, "🤖")
        mtype_raw = str(current.get("type", "info")).lower()
        mtype = TYPE_LABELS.get(mtype_raw, "Update")
        short_line = html.escape(_film_line(agent, str(current.get("content", ""))))
        detail_line = html.escape(_film_detail_line(agent, str(current.get("content", ""))))
        hint = html.escape(_next_step_hint(agent, mtype_raw))
        raw_content = str(current.get("content", ""))

        cast_html = ['<div class="cast-row">']
        for idx, item in enumerate(sorted_messages, start=1):
            a = item.get("agent", "Agent")
            a_icon = ICONS.get(a, "🤖")
            cls = "cast-avatar active" if idx == st.session_state["agent_step_cursor"] else "cast-avatar"
            cast_html.append(f'<div class="{cls}" title="{html.escape(a)}">{a_icon}</div>')
        cast_html.append("</div>")

        st.markdown(
            f"""
            <div class="film-stage">
                <div class="film-spot"></div>
                <div class="film-agent">
                    <div class="film-avatar" style="background:{color}22;">{icon}</div>
                    <div class="film-title" style="color:{color};">Step {_step_index(agent)} · {agent} · {mtype}</div>
                    <div class="film-bubble">{short_line}</div>
                    <div class="film-detail">{detail_line}</div>
                    <div class="film-sub">Operator subtitle: follow this step, then move next.</div>
                    <div style="text-align:center;"><span class="film-next">{hint}</span></div>
                    {"".join(cast_html)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Visual-first scene widgets (not text-only)
        if agent == "DetectIssues":
            issues_n, anomalies_n = _detect_issue_numbers(raw_content)
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Issues Found", issues_n if issues_n is not None else "N/A")
            with c2:
                st.metric("Anomalies", anomalies_n if anomalies_n is not None else "N/A")
            if issues_n is not None:
                st.progress(min(1.0, max(0.0, issues_n / 10)))
            st.markdown(
                '<div class="viz-strip"><span class="viz-chip">Pattern Scan</span><span class="viz-chip">Anomaly Radar</span><span class="viz-chip">Trend Check</span></div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div class="speech">⚠️ I found unusual energy patterns. Please prioritize high-severity issues first.</div>',
                unsafe_allow_html=True,
            )
        elif agent == "Planner":
            st.markdown(
                '<div class="viz-strip"><span class="viz-chip">Route Selection</span><span class="viz-chip">Node Orchestration</span><span class="viz-chip">Execution Plan</span></div>',
                unsafe_allow_html=True,
            )
            st.progress(0.25)
            st.markdown(
                '<div class="speech">🧭 I arranged the expert agents in the best order for this question.</div>',
                unsafe_allow_html=True,
            )
        elif agent == "RootCause":
            st.markdown(
                '<div class="viz-strip"><span class="viz-chip">Cause Mapping</span><span class="viz-chip">Impact Link</span><span class="viz-chip">Root Check</span></div>',
                unsafe_allow_html=True,
            )
            st.progress(0.5)
            st.markdown(
                '<div class="speech">🔍 I traced the likely reason behind the issue so action is not random.</div>',
                unsafe_allow_html=True,
            )
        elif agent == "ActionPlanner":
            st.markdown(
                '<div class="viz-strip"><span class="viz-chip">Action Ranking</span><span class="viz-chip">Urgency Sort</span><span class="viz-chip">Impact Estimate</span></div>',
                unsafe_allow_html=True,
            )
            st.progress(0.75)
            st.markdown(
                '<div class="speech">✅ I selected the best action to do now for fastest improvement.</div>',
                unsafe_allow_html=True,
            )
        elif agent == "Critic":
            st.markdown(
                '<div class="viz-strip"><span class="viz-chip">Safety Check</span><span class="viz-chip">Consistency Check</span><span class="viz-chip">Risk Gate</span></div>',
                unsafe_allow_html=True,
            )
            st.progress(0.9)
            st.markdown(
                '<div class="speech">🛠️ I checked quality before the final recommendation is shown.</div>',
                unsafe_allow_html=True,
            )
        elif agent == "Synthesizer":
            st.markdown(
                '<div class="viz-strip"><span class="viz-chip">Merge Insights</span><span class="viz-chip">Final Decision</span><span class="viz-chip">Operator Output</span></div>',
                unsafe_allow_html=True,
            )
            st.progress(1.0)
            st.markdown(
                '<div class="speech">📌 I combined all agent outputs into one action-ready decision.</div>',
                unsafe_allow_html=True,
            )

        b1, b2, b3 = st.columns([1, 1, 1])
        with b1:
            if st.button("⏮ Previous Scene", key="film_prev_btn", disabled=st.session_state["agent_step_cursor"] <= 1):
                st.session_state["agent_step_cursor"] -= 1
                st.rerun()
        with b2:
            if st.button("▶ Next Scene", key="film_next_btn", disabled=st.session_state["agent_step_cursor"] >= max_steps):
                st.session_state["agent_step_cursor"] += 1
                st.rerun()
        with b3:
            if st.button("🔁 Replay Scene", key="film_replay_btn"):
                st.rerun()

        with st.expander("Show technical details for this step", expanded=False):
            st.write(f"System detail: {current.get('content', '')}")
            st.write(f"Specialized role: {ROLE_DESCRIPTIONS.get(agent, 'Specialized assistant')}")
            st.write(f"Specialized output: {_agent_specific_value(agent, str(current.get('content', '')))}")

        if not show_all:
            return

    for m in visible_messages:
        agent = m.get("agent", "Agent")
        color = COLORS.get(agent, "#999999")
        icon = ICONS.get(agent, "🤖")
        content = html.escape(str(m.get("content", "")))
        operator_text = html.escape(_operator_text(agent, str(m.get("content", ""))))
        mtype_raw = str(m.get("type", "info")).lower()
        mtype = html.escape(TYPE_LABELS.get(mtype_raw, "Update"))
        hint = html.escape(_next_step_hint(agent, mtype_raw))
        role = html.escape(ROLE_DESCRIPTIONS.get(agent, "Specialized assistant"))
        spec = html.escape(_specialized_takeaway(agent, str(m.get("content", ""))))
        step = f"Step {_step_index(agent)}"

        st.markdown(
            f"""
            <div class="agent-card card-animate" style="border-left: 6px solid {color}; background: linear-gradient(180deg, {color}08 0%, #FFFFFF 30%);">
                <div class="agent-step">{step}</div>
                <div class="agent-title" style="color:{color};"><span class="agent-icon">{icon}</span>{agent}</div>
                <div class="agent-role"><strong>Special role:</strong> {role}</div>
                <div class="agent-type">{mtype}</div>
                <div class="agent-content"><strong>Easy meaning:</strong> {operator_text}</div>
                <div class="agent-content"><strong>System detail:</strong> {content}</div>
                <div class="agent-content"><strong>Specialized output:</strong> {html.escape(_agent_specific_value(agent, str(m.get("content", ""))))}</div>
                <div class="agent-special"><strong>Agent output power:</strong> {spec}</div>
                <div class="agent-hint">{hint}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )