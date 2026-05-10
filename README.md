# EcoSense LG: AI-Powered Energy Management System

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red.svg)](https://streamlit.io/)
[![Ollama](https://img.shields.io/badge/Ollama-0.3+-green.svg)](https://ollama.ai/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

EcoSense LG is an intelligent energy management platform that leverages AI agents and machine learning to monitor, analyze, and optimize building energy consumption. The system provides real-time anomaly detection, proactive recommendations, and automated alerts through Telegram integration.

## 🌟 Key Features

### Core Capabilities
- **Real-time Energy Monitoring**: Live simulation of building energy consumption with configurable focus on specific buildings
- **AI-Powered Anomaly Detection**: Multi-agent system using Ollama LLM for intelligent energy pattern analysis
- **Proactive Recommendations**: Automated generation of energy-saving suggestions based on detected anomalies
- **Interactive Dashboard**: Streamlit-based web interface for comprehensive energy operations management

### Advanced Features
- **Agent Theater**: Watch AI agents collaborate in real-time analysis with generative conversations
- **Telegram Bot Integration**: Receive instant alerts and control the system via Telegram
- **Google Sheets Sync**: Cloud-based data persistence and reporting
- **Multi-Building Support**: Analyze energy patterns across multiple buildings simultaneously
- **Simulation Engine**: Realistic energy consumption simulation with fault injection capabilities

### Technical Highlights
- **Local LLM Integration**: Uses Ollama for privacy-preserving, offline AI capabilities
- **Modular Architecture**: Clean separation of concerns with agents, services, and UI components
- **Extensible Pipeline**: Pluggable nodes for detection, root cause analysis, action planning, and quality assurance
- **Database Agnostic**: Supports SQLite, PostgreSQL, and Google Sheets backends

## 🏗️ Architecture

```
EcoSense LG/
├── dashboard/          # Streamlit web interface
│   ├── app.py         # Main application entry point
│   ├── ui/            # UI components (charts, theater, etc.)
│   └── pages/         # Admin and data management pages
├── src/               # Core application logic
│   ├── agents/        # AI agent implementations
│   ├── core/          # Digital twin and analytics
│   ├── llm/           # LLM client and fine-tuning
│   ├── nodes/         # Workflow pipeline nodes
│   ├── rag/           # Retrieval-augmented generation
│   ├── services/      # Business logic services
│   └── tools/         # Utility tools
├── data/              # Sample data and configurations
├── scripts/           # Utility scripts
└── tests/             # Test suites
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+**
- **Ollama** (for local LLM capabilities)
- **Git** (for cloning the repository)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/ecosense-lg.git
   cd ecosense-lg
   ```

2. **Set up Python environment:**
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate  # On Windows
   # source .venv/bin/activate  # On macOS/Linux
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install and configure Ollama:**
   ```bash
   # Download Ollama from https://ollama.ai/
   ollama pull llama3.2:1b
   ```

5. **Configure environment variables:**
   Create a `.env` file in the project root:
   ```env
   # Telegram Bot (optional)
   TELEGRAM_TOKEN=your_telegram_bot_token
   MY_CHAT_ID=your_telegram_chat_id

   # Google Sheets (optional)
   GOOGLE_SHEET_ID=your_google_sheet_id
   GOOGLE_APPLICATION_CREDENTIALS=service_account.json
   ```

### Running the Application

1. **Start the Streamlit dashboard:**
   ```bash
   streamlit run dashboard/app.py
   ```

2. **Access the application:**
   Open your browser to `http://localhost:8501`

3. **Login credentials:**
   - **Admin**: `admin` / `admin123`
   - **Operator 1**: `operator1` / `op1`
   - **Operator 2**: `operator2` / `op2`

## 📖 Usage Guide

### Dashboard Overview

1. **Login**: Use the credentials above to access the system
2. **Building Selection**: Choose a specific building or "All Buildings" from the sidebar
3. **Live Demo**: Start the simulation to see real-time energy monitoring
4. **Agent Theater**: Observe AI agents analyzing energy patterns
5. **Telegram Integration**: Receive alerts and control via Telegram bot

### Key Workflows

#### Energy Anomaly Detection
1. Start live simulation
2. Agents automatically analyze energy streams
3. View results in Agent Theater
4. Receive Telegram alerts for anomalies

#### Building-Specific Analysis
1. Select target building from sidebar
2. Restart simulation for focused analysis
3. Review building-specific insights

#### Report Generation
1. Access admin panel (admin role required)
2. Generate PDF reports with energy analytics

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TELEGRAM_TOKEN` | Telegram bot API token | No |
| `MY_CHAT_ID` | Telegram chat ID for alerts | No |
| `GOOGLE_SHEET_ID` | Google Sheets document ID | No |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON | No |

### Simulation Settings

Modify `src/services/simulator.py` to adjust:
- Simulation speed (seconds per hour)
- Fault injection frequency
- Data filtering parameters

## 🤖 AI Agents

EcoSense LG employs a sophisticated multi-agent system:

- **Analyst Agent**: Detects energy consumption anomalies
- **Planner Agent**: Cross-references anomalies with schedules
- **Recommender Agent**: Generates actionable energy-saving recommendations
- **Action Planner**: Creates implementation plans
- **Critic Agent**: Quality assurance and validation
- **Synthesizer Agent**: Final decision synthesis

All agents leverage Ollama's local LLM for intelligent analysis.

## 🧪 Testing

Run the test suite:
```bash
python -m pytest tests/
```

## 📊 Data Sources

The system includes sample datasets:
- `data/sample/building_energy_multi.csv`: Multi-building energy consumption data
- `data/sample/users.csv`: User account management
- `data/sample/building_metadata.csv`: Building specifications

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add tests for new features
- Update documentation as needed
- Ensure compatibility with Python 3.8+

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋 Support

For questions, issues, or contributions:

- **Issues**: [GitHub Issues](https://github.com/your-username/ecosense-lg/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/ecosense-lg/discussions)
- **Email**: your-email@example.com

## 🔄 Changelog

### [v1.0.0] - 2026-05-11
- Initial release with core energy management features
- Ollama LLM integration
- Multi-agent analysis system
- Streamlit dashboard
- Telegram bot integration

---

**Built with ❤️ for sustainable energy management**