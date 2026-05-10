import streamlit as st


def render_homepage():
    st.markdown(
        """
        <style>
        .hero-section {
            background-image: linear-gradient(rgba(4, 120, 87, 0.9), rgba(6, 78, 59, 0.95)), url('https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&q=80&w=2070');
            background-size: cover;
            background-position: center;
            padding: 80px 40px;
            border-radius: 18px;
            color: white;
            text-align: center;
            margin-bottom: 30px;
            box-shadow: 0 14px 50px rgba(0, 0, 0, 0.18);
        }
        .hero-title {
            font-size: 3.2rem;
            font-weight: 800;
            margin-bottom: 10px;
            letter-spacing: -0.03em;
        }
        .hero-subtitle {
            font-size: 1.4rem;
            font-weight: 400;
            margin-bottom: 24px;
            max-width: 900px;
            margin-left: auto;
            margin-right: auto;
            line-height: 1.5;
        }
        .hero-pill {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 18px;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.16);
            border: 1px solid rgba(255, 255, 255, 0.24);
            font-weight: 700;
            color: #ECFDF5;
            font-size: 0.95rem;
        }
        .story-card {
            border-radius: 18px;
            background: #ffffff;
            padding: 28px;
            box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08);
            border: 1px solid #E2E8F0;
            margin-bottom: 18px;
        }
        .story-step {
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 6px;
        }
        .story-body {
            color: #475569;
            line-height: 1.7;
        }
        .feature-pill {
            display: inline-flex;
            gap: 10px;
            align-items: center;
            background: #ECFDF5;
            color: #065F46;
            border-radius: 999px;
            padding: 10px 16px;
            margin-bottom: 10px;
            font-weight: 700;
        }
        </style>
        <div class="hero-section">
            <div class="hero-title">Smart Energy Guardian</div>
            <div class="hero-subtitle">Turn your campus energy CSV into a live building operations room. Track simulated hours, verify calendar context, and let AI alert you when true waste appears.</div>
            <div class="hero-pill">Live simulation • schedule-aware • Ollama-powered • Telegram alerts</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### How the Smart Energy Guardian operates")
    st.write("From historic meters to proactive alerts, this system is designed to feel like a real operations command center.")

    step1, step2 = st.columns(2)
    with step1:
        st.markdown("<div class='story-card'><div class='story-step'>1. Time-Travel Engine</div><div class='story-body'>Your ASHRAE dataset is replayed row by row, like a VCR. The simulator writes hourly meter readings into a live Google Sheet to create a realistic, unfolding energy stream.</div></div>", unsafe_allow_html=True)
        st.markdown("<div class='story-card'><div class='story-step'>3. The Brain Trust</div><div class='story-body'>Three AI agents work together: Analyst, Strategic Planner, and Recommender. They detect anomalies, compare against events, and suggest the best corrective action.</div></div>", unsafe_allow_html=True)
    with step2:
        st.markdown("<div class='story-card'><div class='story-step'>2. Digital Twin</div><div class='story-body'>Your Google Sheet becomes a live campus twin. One tab streams current meter data, another stores the campus schedule, and the system interprets numbers in context.</div></div>", unsafe_allow_html=True)
        st.markdown("<div class='story-card'><div class='story-step'>4. Proactive Messenger</div><div class='story-body'>When a true waste event is confirmed, the system sends a Telegram alert and keeps you in the loop. You can also query `/status` to see current performance at any time.</div></div>", unsafe_allow_html=True)

    st.divider()

    st.markdown("### Our features")
    st.markdown("- **Autonomous audit workflow**: The agents do the work, we build the system.")
    st.markdown("- **Context-aware intelligence**: Schedule data makes the AI smarter than raw threshold alerts.")
    st.markdown("- **Low resource, high impact**: Uses cloud APIs sparingly with a demo-ready student laptop profile.")
    st.success("Ready to start your live energy operations demo? Log in from the sidebar to enter the command center.")
