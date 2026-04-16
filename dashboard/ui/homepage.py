import streamlit as st


def render_homepage():
    # Hero section with a beautiful background image
    st.markdown(
        """
        <style>
        .hero-section {
            background-image: linear-gradient(rgba(0,0,0,0.5), rgba(0,0,0,0.5)), url('https://images.unsplash.com/photo-1473341304170-971dccb5ac1e?auto=format&fit=crop&q=80&w=2070');
            background-size: cover;
            background-position: center;
            padding: 80px 40px;
            border-radius: 15px;
            color: white;
            text-align: center;
            margin-bottom: 30px;
        }
        .hero-title {
            font-size: 3.5rem;
            font-weight: 800;
            margin-bottom: 10px;
        }
        .hero-subtitle {
            font-size: 1.5rem;
            font-weight: 400;
            margin-bottom: 20px;
        }
        .stButton > button {
            border-radius: 50% !important;
            width: 45px !important;
            height: 45px !important;
            padding: 0px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            font-size: 20px !important;
            background-color: rgba(255, 255, 255, 0.2) !important;
            color: white !important;
            border: 2px solid white !important;
            transition: all 0.2s ease-in-out !important;
        }
        .stButton > button:hover {
            background-color: rgba(255, 255, 255, 0.5) !important;
            transform: scale(1.1);
        }
        </style>
        <div class="hero-section">
            <div class="hero-title">🌿 EcoSense AI</div>
            <div class="hero-subtitle">Next-Generation Building Energy Intelligence</div>
            <p style="font-size: 1.2rem; max-width: 800px; margin: 0 auto;">
                Empowering operators with AI-driven insights to reduce waste, optimize consumption, and drive sustainability across every floor.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # First Slider: Core Utilities
    st.subheader("Explore Our Core Utilities")
    utility_options = [
        "🔍 Smart Anomaly Detection",
        "📊 Real-time Consumption Analytics",
        "💡 AI-Powered Recommendations",
        "🏢 Building Comparison & Normalization",
        "📄 Automated Compliance Reporting"
    ]

    if "utility_index" not in st.session_state:
        st.session_state.utility_index = 0

    selected_utility = utility_options[st.session_state.utility_index]

    image_urls = {
        "🔍 Smart Anomaly Detection": "https://images.unsplash.com/photo-1551288049-bbbda536339a?auto=format&fit=crop&q=80&w=800",
        "📊 Real-time Consumption Analytics": "https://images.unsplash.com/photo-1551288049-bbbda536339a?auto=format&fit=crop&q=80&w=800",
        "💡 AI-Powered Recommendations": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&q=80&w=800",
        "🏢 Building Comparison & Normalization": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&q=80&w=800",
        "📄 Automated Compliance Reporting": "https://images.unsplash.com/photo-1450101499163-c8848c66ca85?auto=format&fit=crop&q=80&w=800"
    }

    # Navigation logic for Utility Slider
    col_l, col_m, col_r = st.columns([1, 10, 1])
    with col_l:
        st.write("<div style='height: 180px;'></div>", unsafe_allow_html=True)
        if st.button("←", key="util_prev"):
            st.session_state.utility_index = (st.session_state.utility_index - 1) % len(utility_options)
            st.rerun()
    with col_m:
        st.image(image_urls[selected_utility], use_container_width=True, caption=selected_utility)
        if selected_utility == "🔍 Smart Anomaly Detection":
            st.markdown("### 🔍 Smart Anomaly Detection")
            st.write("Never miss a spike again. Our AI monitors your building's energy pulse 24/7, identifying patterns that humans might overlook.")
            st.info("✅ Detects leaks, equipment malfunctions, and schedule drifts instantly.")
        elif selected_utility == "📊 Real-time Consumption Analytics":
            st.markdown("### 📊 Real-time Consumption Analytics")
            st.write("Visualize your energy data like never before. From high-level building trends to individual flat consumption.")
            st.info("✅ Dynamic charts with hourly, daily, and weekly granularity.")
        elif selected_utility == "💡 AI-Powered Recommendations":
            st.markdown("### 💡 AI-Powered Recommendations")
            st.write("Don't just see the problems—solve them. EcoSense provides prioritized, actionable steps to reduce your energy bill.")
            st.info("✅ Tailored advice based on your building's unique consumption profile.")
        elif selected_utility == "🏢 Building Comparison & Normalization":
            st.markdown("### 🏢 Building Comparison & Normalization")
            st.write("Compare apples to apples. Our normalization engine adjusts for building size, occupancy, and climate.")
            st.info("✅ Benchmark your portfolio and identify top performers.")
        elif selected_utility == "📄 Automated Compliance Reporting":
            st.markdown("### 📄 Automated Compliance Reporting")
            st.write("Generate professional energy audit reports in seconds. Perfect for management updates and regulatory compliance.")
            st.info("✅ One-click PDF export with full data visualization.")
    with col_r:
        st.write("<div style='height: 180px;'></div>", unsafe_allow_html=True)
        if st.button("→", key="util_next"):
            st.session_state.utility_index = (st.session_state.utility_index + 1) % len(utility_options)
            st.rerun()

    st.divider()

    # Second Slider: App Walkthrough (Replacing the private video)
    st.subheader("How EcoSense Works")
    walkthrough_steps = [
        "Step 1: Ingest Data",
        "Step 2: AI Collaboration",
        "Step 3: Root Cause Analysis",
        "Step 4: Execute Actions",
        "Step 5: Verify Savings"
    ]
    walkthrough_images = {
        "Step 1: Ingest Data": "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?auto=format&fit=crop&q=80&w=800",
        "Step 2: AI Collaboration": "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?auto=format&fit=crop&q=80&w=800",
        "Step 3: Root Cause Analysis": "https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&q=80&w=800",
        "Step 4: Execute Actions": "https://images.unsplash.com/photo-1513506003901-1e6a229e2d15?auto=format&fit=crop&q=80&w=800",
        "Step 5: Verify Savings": "https://images.unsplash.com/photo-1554224155-1696413565d3?auto=format&fit=crop&q=80&w=800"
    }
    
    if "walkthrough_index" not in st.session_state:
        st.session_state.walkthrough_index = 0
    
    selected_step = walkthrough_steps[st.session_state.walkthrough_index]
    
    col_wl, col_wm, col_wr = st.columns([1, 10, 1])
    with col_wl:
        st.write("<div style='height: 180px;'></div>", unsafe_allow_html=True)
        if st.button("←", key="walk_prev"):
            st.session_state.walkthrough_index = (st.session_state.walkthrough_index - 1) % len(walkthrough_steps)
            st.rerun()
    with col_wm:
        st.image(walkthrough_images[selected_step], use_container_width=True, caption=selected_step)
        if selected_step == "Step 1: Ingest Data":
            st.write("Connect your meters and upload utility bills. EcoSense handles structured and unstructured data seamlessly.")
        elif selected_step == "Step 2: AI Collaboration":
            st.write("Watch specialized agents—Planner, Multimodal, Synthesizer—work together to interpret your building's data.")
        elif selected_step == "Step 3: Root Cause Analysis":
            st.write("Identify exactly why inefficiencies occur, from equipment schedule drifts to occupancy-based waste.")
        elif selected_step == "Step 4: Execute Actions":
            st.write("Get prioritized, actionable tasks with clear urgency and expected impact for your facility team.")
        elif selected_step == "Step 5: Verify Savings":
            st.write("Monitor the impact of your actions and generate reports to demonstrate ROI to management.")
    with col_wr:
        st.write("<div style='height: 180px;'></div>", unsafe_allow_html=True)
        if st.button("→", key="walk_next"):
            st.session_state.walkthrough_index = (st.session_state.walkthrough_index + 1) % len(walkthrough_steps)
            st.rerun()

    st.divider()

    # Features Grid
    st.subheader("Key Features at a Glance")
    f1, f2, f3 = st.columns(3)
    with f1:
        st.markdown("#### 🤖 Agent Theater")
        st.write("Watch our AI agents collaborate to solve complex energy puzzles in real-time.")
    with f2:
        st.markdown("#### 🔄 Decision Workflow")
        st.write("A structured path from issue detection to root cause and finally, action.")
    with f3:
        st.markdown("#### 📱 Mobile Ready")
        st.write("Monitor your buildings and receive alerts on the go with our responsive design.")

    st.caption("Ready to transform your energy management? Sign in using the sidebar to begin.")

    st.divider()

    # Features Grid
    st.subheader("Key Features at a Glance")
    f1, f2, f3 = st.columns(3)
    with f1:
        st.markdown("#### 🤖 Agent Theater")
        st.write("Watch our AI agents collaborate to solve complex energy puzzles in real-time.")
    with f2:
        st.markdown("#### 🔄 Decision Workflow")
        st.write("A structured path from issue detection to root cause and finally, action.")
    with f3:
        st.markdown("#### 📱 Mobile Ready")
        st.write("Monitor your buildings and receive alerts on the go with our responsive design.")

    st.caption("Ready to transform your energy management? Sign in using the sidebar to begin.")
