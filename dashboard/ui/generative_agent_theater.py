"""
Generative Agent Theater UI
Showcases multi-agent conversations with Hugging Face models
"""

import streamlit as st
import time
from datetime import datetime
import json

def render_generative_agent_theater(agent_team, focus_building=None):
    """Render the generative agent theater interface"""
    
    st.markdown("## " + ("Generative" if focus_building else "Multi-Agent") + " Theater")
    st.markdown("Watch AI agents collaborate on energy analysis using generative models!")
    
    # Initialize session state for chat
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    if 'agent_conversation' not in st.session_state:
        st.session_state.agent_conversation = []
    if 'analysis_mode' not in st.session_state:
        st.session_state.analysis_mode = "hybrid"
    
    # Sidebar controls
    with st.sidebar:
        st.markdown("### " + ("Generative" if focus_building else "Agent") + " Controls")
        
        # Analysis mode selection
        st.session_state.analysis_mode = st.selectbox(
            "Analysis Mode",
            ["hybrid", "ml_only", "generative_only"],
            help="Choose how agents analyze energy anomalies"
        )
        
        # System status
        if agent_team:
            status = agent_team.get_system_status()
            st.markdown("### System Status")
            st.json(status)
        
        # Trigger analysis button
        if st.button("Run Agent Analysis", type="primary", use_container_width=True):
            _run_agent_analysis(agent_team, focus_building)
        
        # Chat interface
        st.markdown("### Chat with Energy Assistant")
        user_message = st.text_input("Ask about energy management...")
        if st.button("Send", key="chat_send", use_container_width=True) and user_message:
            _handle_chat(agent_team, user_message, focus_building)
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Agent conversation display
        st.markdown("### " + ("Generative" if st.session_state.analysis_mode != "ml_only" else "Agent") + " Conversation")
        
        if st.session_state.agent_conversation:
            for i, msg in enumerate(st.session_state.agent_conversation):
                _display_agent_message(msg, i)
        else:
            st.info("No agent conversation yet. Click 'Run Agent Analysis' to start!")
        
        # Chat history
        if st.session_state.chat_messages:
            st.markdown("### Chat History")
            for msg in st.session_state.chat_messages[-5:]:  # Show last 5 messages
                if msg["role"] == "user":
                    st.markdown(f"**You:** {msg['content']}")
                else:
                    st.markdown(f"**Assistant:** {msg['content']}")
                st.markdown("---")
    
    with col2:
        # Suggestions panel
        st.markdown("### Energy Suggestions")
        if focus_building and agent_team:
            try:
                # Get energy profile for suggestions
                energy_profile = {
                    "building_id": focus_building,
                    "avg_consumption": 200.0,
                    "baseline": 180.0,
                    "status": "normal"
                }
                
                suggestions = agent_team.get_energy_suggestions(focus_building, energy_profile)
                
                for i, suggestion in enumerate(suggestions, 1):
                    st.markdown(f"{i}. {suggestion}")
            except Exception as e:
                st.error(f"Could not load suggestions: {e}")
        else:
            st.info("Select a building to get suggestions")
        
        # Analysis info
        if st.session_state.agent_conversation:
            last_analysis = st.session_state.agent_conversation[-1]
            if "timestamp" in last_analysis:
                st.markdown("### Last Analysis")
                st.markdown(f"**Time:** {last_analysis['timestamp']}")
                st.markdown(f"**Mode:** {st.session_state.analysis_mode}")
            
            if "full_conversation" in last_analysis:
                conv_count = len(last_analysis["full_conversation"])
                st.markdown(f"**Agent Messages:** {conv_count}")

def _run_agent_analysis(agent_team, focus_building):
    """Run the agent analysis and update conversation"""
    if not agent_team:
        st.error("Agent team not available")
        return
    
    with st.spinner("Agents are analyzing energy data..."):
        try:
            # Simulate anomaly data for demonstration
            anomaly_data = {
                "building_id": focus_building or "Building_A",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "consumption_kwh": 250.5,
                "baseline": 200.0,
                "deviation_pct": 25.3
            }
            
            # Run analysis with selected mode
            result = agent_team.handle_stream_event(
                None,  # No event row needed for demo
                analysis_mode=st.session_state.analysis_mode
            )
            
            if result and "recommendation" in result:
                recommendation = result["recommendation"]
                
                # Create conversation entry
                conversation_entry = {
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "mode": st.session_state.analysis_mode,
                    "building": focus_building or "Building_A",
                    "anomaly": anomaly_data,
                    "recommendation": recommendation
                }
                
                # Add full conversation if available
                if isinstance(recommendation, dict) and "full_conversation" in recommendation:
                    conversation_entry["full_conversation"] = recommendation["full_conversation"]
                    conversation_entry["recommendation"] = recommendation.get("recommendation", "Analysis completed")
                
                st.session_state.agent_conversation.append(conversation_entry)
                st.success("Agent analysis completed!")
                st.rerun()
            else:
                st.warning("No anomaly detected for analysis")
                
        except Exception as e:
            st.error(f"Analysis failed: {e}")

def _handle_chat(agent_team, user_message, focus_building):
    """Handle user chat with energy assistant"""
    if not agent_team:
        st.error("Chat system not available")
        return
    
    with st.spinner("Assistant is thinking..."):
        try:
            building_context = f"Building: {focus_building}" if focus_building else "General energy management"
            response = agent_team.chat_with_user(user_message, building_context)
            
            # Add to chat history
            st.session_state.chat_messages.append({
                "role": "user",
                "content": user_message,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            })
            
            st.session_state.chat_messages.append({
                "role": "assistant", 
                "content": response,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            })
            
            st.rerun()
            
        except Exception as e:
            st.error(f"Chat failed: {e}")

def _display_agent_message(msg, index):
    """Display a single agent message with styling"""
    
    # Agent colors and icons
    agent_styles = {
        "Data Analyst": {"color": "#3498db", "icon": "data"},
        "Strategic Planner": {"color": "#9b59b6", "icon": "plan"},
        "Energy Expert": {"color": "#2ecc71", "icon": "energy"},
        "Systems Critic": {"color": "#e74c3c", "icon": "critic"},
        "Solution Synthesizer": {"color": "#f39c12", "icon": "synthesis"},
        "ML Classifier": {"color": "#1abc9c", "icon": "ml"},
        "ML Recommender": {"color": "#16a085", "icon": "ml"}
    }
    
    # Handle different message types
    if "full_conversation" in msg and msg["full_conversation"]:
        # Display full generative conversation
        st.markdown(f"#### {msg.get('building', 'Unknown')} - {msg.get('mode', 'hybrid').title()} Analysis")
        
        for agent_msg in msg["full_conversation"]:
            agent_name = agent_msg.get("agent", "Unknown")
            style = agent_styles.get(agent_name, {"color": "#95a5a6", "icon": "agent"})
            
            with st.container():
                st.markdown(
                    f"""
                    <div style="border-left: 4px solid {style['color']}; padding: 10px; margin: 5px 0; background-color: #f8f9fa;">
                    <strong><span style="color: {style['color']};">{style['icon']}</span> {agent_name}</strong>
                    <br><small>{agent_msg.get('timestamp', '')}</small>
                    <br>{agent_msg.get('content', '')}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
    else:
        # Display single recommendation
        agent_name = msg.get("recommendation", {}).get("type", "System")
        style = agent_styles.get(agent_name, {"color": "#95a5a6", "icon": "agent"})
        
        with st.container():
            st.markdown(
                f"""
                <div style="border-left: 4px solid {style['color']}; padding: 10px; margin: 5px 0; background-color: #f8f9fa;">
                <strong><span style="color: {style['color']};">{style['icon']}</span> {agent_name}</strong>
                <br><small>{msg.get('timestamp', '')}</small>
                <br>{msg.get('recommendation', {}).get('recommendation', 'No recommendation available')}
                </div>
                """,
                unsafe_allow_html=True
            )
    
    st.markdown("---")

def render_agent_comparison(agent_team):
    """Render comparison between different analysis modes"""
    st.markdown("### Agent Mode Comparison")
    
    if not agent_team:
        st.warning("Agent team not available for comparison")
        return
    
    modes = ["ml_only", "generative_only", "hybrid"]
    results = {}
    
    with st.spinner("Running comparison analysis..."):
        for mode in modes:
            try:
                result = agent_team.handle_stream_event(None, analysis_mode=mode)
                results[mode] = result
                time.sleep(1)  # Small delay to prevent overwhelming
            except Exception as e:
                results[mode] = {"error": str(e)}
    
    # Display comparison table
    comparison_data = []
    for mode, result in results.items():
        if "error" in result:
            comparison_data.append({
                "Mode": mode.replace("_", " ").title(),
                "Status": "Error",
                "Response": result["error"]
            })
        elif result and "recommendation" in result:
            rec = result["recommendation"]
            response = rec.get("recommendation", "No response") if isinstance(rec, dict) else str(rec)
            comparison_data.append({
                "Mode": mode.replace("_", " ").title(),
                "Status": "Success",
                "Response": response[:100] + "..." if len(response) > 100 else response
            })
        else:
            comparison_data.append({
                "Mode": mode.replace("_", " ").title(),
                "Status": "No Result",
                "Response": "No anomaly detected"
            })
    
    st.dataframe(comparison_data, use_container_width=True)
