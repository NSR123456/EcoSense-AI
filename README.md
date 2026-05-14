# EcoSense AI

The AI-powered energy operations cockpit for building owners and operators.

EcoSense AI is a modern, opinionated, Streamlit-based interface for energy monitoring, anomaly detection, recommendation generation, and automation. It combines simulated building energy streams, a local Ollama-backed agent theater, Telegram alerts, and Google Sheets persistence to turn raw energy data into actions.

No cloud lock-in. No black-box servers. Your building data stays local — EcoSense LG is the cockpit.

Python 3.8+ · Streamlit 1.30+ · Ollama 0.3+ · MIT · PRs Welcome · Built for sustainable operations

Quick Start · Configuration · Data sources · Architecture · Contributing

🚀 Why EcoSense AI

Building energy management is often split across spreadsheets, ad-hoc alerts, and manual review. Operators need a single place to see what is happening now, why it happened, and what to do next.

EcoSense LG fixes the operations workflow without inventing a new data source.

Legacy energy tooling    | EcoSense AI
------------------------|-------------------------------------------------
Static CSV reports      | Live simulation + real-time dashboards
Manual anomaly rules    | Multi-agent anomaly detection with local LLM
Delayed recommendations | Proactive energy-saving actions and alerts
Siloed integrations     | Telegram + Google Sheets + local LLM in one system
UI for operators        | Streamlit cockpit with agent theater and reports

🎯 Feature matrix

Energy operations
- ✅ Live building energy simulation with multi-building support
- ✅ Real-time anomaly detection across consumption patterns
- ✅ Forecasting and insight generation through generative agents
- ✅ Fault injection and event-driven energy scenarios

AI agent theater
- ✅ Multi-agent collaboration for analysis, root cause, planning, and validation
- ✅ Local Ollama model integration for on-prem inference
- ✅ Transparent decision flow for operator review

Integrations & automation
- ✅ Telegram alerts and control integration
- ✅ Google Sheets sync for cloud persistence and reporting
- ✅ PDF report generation for energy summaries
- ✅ Operator roles and admin workflows via Streamlit pages

Platform & developer experience
- ✅ Modular service architecture with agents, workflows, and helpers
- ✅ Clean separation of dashboard, agents, and services
- ✅ Python-first codebase for easy extension and experimentation
- ✅ Test suite with `pytest` for core logic validation

⚡ Quick start

Python 3.8+, Ollama installed, and a terminal in the repository root.

```bash
git clone https://github.com/your-username/ecosense-lg.git
cd "EcoSense LG"
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
ollama pull llama3.2:1b
copy .env.example .env
# edit .env with TELEGRAM_TOKEN, MY_CHAT_ID, GOOGLE_SHEET_ID, GOOGLE_APPLICATION_CREDENTIALS
streamlit run dashboard/app.py
```

Open http://localhost:8501 in your browser.

💡 No Telegram or Google Sheets configured? The dashboard still runs with local simulation and Ollama-backed agent reasoning.

🔧 Configuration

Variable | Required | Purpose
--------|----------|--------
`TELEGRAM_TOKEN` | No | Telegram bot API token for alerts and control
`MY_CHAT_ID` | No | Chat ID to send alerts to
`GOOGLE_SHEET_ID` | No | Google Sheets document ID for data sync
`GOOGLE_APPLICATION_CREDENTIALS` | No | Path to service account JSON for Google Sheets
`OLLAMA_MODEL` | No | Ollama model name to use (default: `llama3.2:1b`)

All runtime configuration is read from `.env` or environment variables at startup.

🔀 Data sources

EcoSense AI works with local sample data, Google Sheets, and optional SQL-backed sources.

Mode | Reads | Writes | When to use
-----|-------|--------|-----------
Sample data | CSV / in-memory | N/A | Local demos and testing
Google Sheets | Sheets API | Sheets API | Cloud persistence for reports and logs
Telegram | N/A | Telegram API | Operator alerts and manual control

Sample datasets live under `data/sample/` so you can get started without external dependencies.

🧠 Local LLM

The system uses Ollama locally for agent reasoning. That means your analysis stays on-premise and does not depend on an external LLM service.

🏗 Architecture

```
BROWSER / Streamlit UI
├─ dashboard/app.py
│  ├─ ui/                # charts, panels, controls
│  ├─ pages/             # admin and building pages
│  └─ agent theater
│
├─ src/
│  ├─ agents/            # multi-agent reasoning
│  ├─ core/              # analytics, digital twin, confidence
│  ├─ llm/               # Ollama client and fine-tuning helpers
│  ├─ nodes/             # workflow nodes and pipelines
│  ├─ rag/               # retrieval and vector search
│  ├─ services/          # automation, reporting, storage
│  └─ tools/             # utility helpers and evaluation tools
│
├─ integrations/
│  ├─ Telegram          # alerts and bot control
│  ├─ Google Sheets     # persistence and reporting
│  └─ CSV / sample data
```

The app brokers user actions through the dashboard to the agent system, which reasons over energy data and writes alerts or recommendations to Telegram and Google Sheets.

📂 Project layout

```
EcoSense AI/
├─ dashboard/
│  ├─ app.py
│  ├─ building_store.py
│  ├─ pages/
│  └─ ui/
├─ data/
│  └─ sample/
├─ scripts/
├─ src/
│  ├─ agents/
│  ├─ core/
│  ├─ ingestion/
│  ├─ llm/
│  ├─ nodes/
│  ├─ rag/
│  └─ services/
├─ tests/
├─ requirements.txt
├─ README.md
└─ service_account.json
```

🧰 Tech stack

Layer | Choice | Why
-----|--------|----
Framework | Streamlit | fast interactive dashboards for operators
Language | Python 3.8+ | easy extension and data science ecosystem
LLM | Ollama | local inference and offline privacy
UI | Streamlit pages + custom controls | simple, shareable interface
Messaging | Telegram Bot API | instant operator alerts
Data | Google Sheets / CSV / sample data | low-friction persistence layer
Testing | pytest | automated validation for core logic

🛠 Scripts

Command | What it does
--------|-------------
`streamlit run dashboard/app.py` | Launch the dashboard locally
`python -m pytest tests/` | Run the test suite
`python demo_generative_system.py` | Run a generative system demo
`python scripts/run_energy_analysis.py` | Run energy analysis workflow

🤝 Contributing

PRs welcome — small or large.

git clone https://github.com/<your-fork>/EcoSense-AI.git
cd "EcoSense-AI"
git checkout -b feat/<short-name>
# …make your changes…
python -m pytest tests/
git commit -m "feat(agent): add recommendation summary"
git push origin feat/<short-name>

Open a PR against `main`. Attach a screenshot or screen recording for any UI change.

Conventional commit prefixes: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`, `test:`.

📜 License & credits

MIT © EcoSense-AI

Built on Streamlit, Ollama, Telegram, and the Python data ecosystem.

If EcoSense-AI helps your team save energy, ⭐ star the repo — that is how it finds its next user.
