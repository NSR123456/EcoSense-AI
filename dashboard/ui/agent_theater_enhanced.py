import html
import time
import streamlit as st
from src.llm.client import generate
from src.services.query_parser import EcoSenseQueryParser, ResponseCache

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
    "Planner": "",
    "DetectIssues": "",
    "RootCause": "",
    "ActionPlanner": "",
    "Compliance": "",
    "Comparison": "",
    "Critic": "",
    "Synthesizer": "",
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


def render_enhanced_agent_theater(messages: list, resp: dict | None = None, db_manager=None):
    """Enhanced Agent Theater with LLM-based Q&A functionality."""
    if not messages:
        st.info("No agent messages.")
        return
    
    # Sort messages by agent step order
    def step_index(agent: str) -> int:
        order = {
            "Planner": 1,
            "DetectIssues": 2,
            "RootCause": 3,
            "ActionPlanner": 4,
            "Critic": 5,
            "Synthesizer": 6,
        }
        return order.get(agent, 99)
    
    sorted_messages = sorted(messages, key=lambda m: step_index(m.get("agent", "Agent")))
    
    # Render original agent theater content
    st.markdown("## Agent Analysis Theater")
    st.caption("Watch AI agents analyze your energy data step by step")
    
    # Display agent messages in chat format
    for idx, message in enumerate(sorted_messages):
        agent = message.get("agent", "Agent")
        icon = ICONS.get(agent, "")
        content = message.get("content", "")
        msg_type = message.get("type", "info")
        
        with st.chat_message(name=agent, avatar=icon):
            st.markdown(f"**{agent}**")
            st.markdown(content)
            
            # Add role description
            role = ROLE_DESCRIPTIONS.get(agent, "AI Assistant")
            st.caption(f"Role: {role}")
    
    # Add intelligent Q&A section
    st.markdown("---")
    st.markdown("## Ask Questions About This Analysis")
    st.caption("Get intelligent answers about the agent analysis using AI")
    
    # Initialize query parser if available
    query_parser = None
    if db_manager:
        try:
            query_parser = EcoSenseQueryParser(db_manager)
        except Exception as e:
            st.warning(f"Query parser unavailable: {e}")
    
    # User question input
    user_question = st.text_input(
        "Ask anything about this energy analysis:",
        placeholder="e.g., What should I do first? Why is this happening? How serious are these issues?",
        key="enhanced_agent_theater_question"
    )
    
    if user_question and query_parser:
        # Generate intelligent response
        with st.spinner("Thinking..."):
            try:
                parsed_query = query_parser.parse_natural_language_query(user_question)
                response = query_parser.generate_contextual_response(parsed_query, "agent_theater")
                
                st.markdown("### AI Response")
                st.markdown(response)
                
                # Show query confidence if helpful
                confidence = parsed_query.get('confidence', 0)
                if confidence < 0.7:
                    st.caption(f"Confidence: {confidence:.0%} - Response may need clarification")
                    
            except Exception as e:
                st.error(f"Error generating response: {e}")
                # Provide fallback help
                st.markdown("### Help")
                st.markdown("""
                I'm having trouble with that question. Try asking about:
                - What actions to take first
                - Why issues were detected  
                - How serious the problems are
                - What the next steps should be
                """)
    
    elif user_question and not query_parser:
        st.warning("Query parser not available. Try restarting the session or contact support.")
    
    # Add example questions
    with st.expander("Example Questions", expanded=False):
        example_questions = [
            "What should I do first based on this analysis?",
            "Why were these energy issues detected?",
            "How serious are these problems?",
            "What's the most important action to take?",
            "Can you explain the root cause in simple terms?",
            "What happens if I don't fix these issues?",
            "How much energy could I save by following these recommendations?"
        ]
        
        for question in example_questions:
            if st.button(question, key=f"example_{question[:20]}"):
                st.session_state.enhanced_agent_theater_question = question
                st.rerun()


def render_intelligent_qa(resp: dict | None = None, db_manager=None):
    """Standalone intelligent Q&A component."""
    st.markdown("## Energy Analysis Q&A")
    st.caption("Ask questions about your building's energy performance")
    
    if not db_manager:
        st.error("Database manager not available for intelligent responses.")
        return
    
    # Initialize query parser
    try:
        query_parser = EcoSenseQueryParser(db_manager)
    except Exception as e:
        st.error(f"Could not initialize query parser: {e}")
        return
    
    # Question input
    user_question = st.text_area(
        "Your Question:",
        placeholder="e.g., How is FBS Building performing this week? Are there any anomalies?",
        key="intelligent_qa_question"
    )
    
    if st.button("Get AI Answer", type="primary"):
        if not user_question.strip():
            st.warning("Please enter a question.")
            return
        
        with st.spinner("Analyzing your question..."):
            try:
                # Parse the query
                parsed_query = query_parser.parse_natural_language_query(user_question)
                
                # Show parsing info in expander
                with st.expander("Query Analysis", expanded=False):
                    st.json(parsed_query)
                
                # Generate response
                response = query_parser.generate_contextual_response(parsed_query, "dashboard")
                
                st.markdown("### AI Analysis")
                st.markdown(response)
                
                # Show confidence
                confidence = parsed_query.get('confidence', 0)
                st.metric("Response Confidence", f"{confidence:.0%}")
                
            except Exception as e:
                st.error(f"Error processing question: {e}")
                st.info("Please try rephrasing your question or contact support if the issue persists.")
    
    # Show recent system context
    if db_manager:
        try:
            active_stream = db_manager.read_tab("Active_Stream") or []
            audit_ledger = db_manager.read_tab("Audit_Ledger") or []
            
            st.markdown("---")
            st.markdown("### Current System Context")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Data Points", len(active_stream))
            with col2:
                anomalies = len([row for row in active_stream if row.get('is_faulty') == 'YES'])
                st.metric("Active Anomalies", anomalies)
            with col3:
                st.metric("Audit Actions", len(audit_ledger))
                
        except Exception as e:
            st.warning(f"Could not load system context: {e}")
