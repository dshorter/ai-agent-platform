# AI Agent Platform

> **n8n-based AI agent orchestration platform for long-running business transactions**

An end-to-end demonstration of intelligent automation for HVAC businesses, showcasing how AI agents can handle customer emergencies, schedule appointments, and drive measurable ROI — all while proving that "Everyone has AI, but not everyone has intelligence."

---

## 🎯 Overview

This platform demonstrates the **Intelligence Moat** concept: going beyond simple AI chatbots to build domain-specific, event-driven agent systems that create real competitive advantages. Built as a working HVAC business digital twin, it simulates realistic scenarios and tracks both operational metrics and financial impact.

**What it does:**
- Automatically handles HVAC emergencies, appointments, and customer inquiries via AI agents
- Tracks decision confidence, revenue captured, and time saved in real-time
- Provides live business dashboards showing ROI (revenue vs. AI costs)
- Simulates realistic customer scenarios to demonstrate value before deployment

**Tech Stack:**
- **n8n** - Workflow orchestration and agent coordination
- **PostgreSQL** - Event storage and business metrics tracking
- **Docker Compose** - Complete infrastructure as code
- **Nginx** - Static web hosting for demos and presentations
- **ngrok** - Secure tunneling for webhooks and remote access

---

## ✨ Key Features

### 🤖 Multi-Agent System
- **Primary Agent** - Routes incoming requests to specialized handlers
- **Emergency Agent** - Prioritizes high-urgency HVAC failures
- **Event Generator** - Simulates realistic customer scenarios for testing
- **Schedule Simulator** - Manages appointment booking and conflicts

### 📊 Real-Time Business Intelligence
- Revenue tracking by event type (emergencies, appointments, inquiries)
- Agent decision confidence metrics
- Time saved calculations (12 min average per handled event)
- Live ROI dashboard comparing AI costs to revenue captured

### 🔄 Event-Driven Architecture
- Webhook-based triggers for instant response
- PostgreSQL event storage with full audit trail
- Agent decision logging with confidence scores
- Workflow execution tracking

### 🌐 Public Demo Interface
- Portfolio presentation site showcasing the "Intelligence Moat" narrative
- Interactive maps showing customer locations
- Live business dashboard at `/hvac-dashboard`
- Problem/proof slides for stakeholder presentations

---

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- ngrok account with authtoken (for public webhook access)
- 4GB+ RAM recommended

### 1. Clone and Configure

```bash
git clone https://github.com/dshorter/ai-agent-platform.git
cd ai-agent-platform

# Set your ngrok auth token
export NGROK_AUTHTOKEN="your_token_here"

# Optional: Set custom PostgreSQL password
export POSTGRES_PASSWORD="your_secure_password"
```

### 2. Start the Stack

```bash
docker-compose up -d
```

This starts:
- **PostgreSQL** on `localhost:5432` (hvac_demo database)
- **n8n** on `localhost:5678` (workflow editor)
- **Nginx** on `localhost:8080` (public web interface)
- **ngrok** tunneling to `agents-platform.ngrok.io` (configurable in docker-compose.yml)

### 3. Initialize Database

```bash
docker exec -i hvac-postgres psql -U hvac_user -d hvac_demo < database/hvac_schema.sql
```

### 4. Import Workflows

1. Access n8n at `http://localhost:5678`
2. For each workflow in `n8n-workflows/`:
   - Click "Add workflow" → "Import from file"
   - Select the `.json` file
   - Configure credentials (PostgreSQL connection)
   - Activate the workflow

See [`n8n-workflows/README.md`](n8n-workflows/README.md) for detailed import instructions.

### 5. Test the System

```bash
# Generate a test event
curl -X POST https://agents-platform.ngrok.io/webhook/emergency \
  -H "Content-Type: application/json" \
  -d '{"customer_name": "John Doe", "issue": "AC unit failed", "urgency": 9}'

# View the dashboard
open http://localhost:8080/hvac-dashboard
```

---

## 📁 Project Structure

```
ai-agent-platform/
├── docker-compose.yml              # Complete infrastructure definition
├── database/
│   └── hvac_schema.sql             # PostgreSQL schema for events + metrics
├── n8n-workflows/                  # AI agent workflow definitions
│   ├── README.md                   # Workflow import/export guide
│   ├── primary-agent.json          # Main routing logic
│   ├── emergency-agent.json        # High-priority handler
│   ├── event-generator.json        # Scenario simulator
│   ├── hvac_business_dashboard_workflow.json  # Live metrics API
│   └── schedule-simulator.json     # Appointment management
├── nginx/
│   └── nginx.conf                  # Web server configuration
├── public/                         # Static website files
│   ├── index.html                  # "Intelligence Moat" landing page
│   ├── demo.html                   # Interactive demo
│   ├── portfolio-map.html          # Customer location visualizations
│   └── portfolio/                  # Portfolio template
├── scripts/                        # Operations utilities
│   ├── deploy.sh                   # Deployment automation
│   ├── backup.sh                   # Database backup script
│   └── monitor.sh                  # Health check monitoring
├── docs/                           # Comprehensive documentation
│   ├── 00-hopper/                  # Quick reference materials
│   ├── 01-infrastructure/          # Deployment, networking, monitoring
│   ├── 02-n8n-workflows/           # Workflow architecture and development
│   ├── 03-database/                # Schema docs and visualizations
│   ├── 04-customer-facing/         # Presentations and solution briefs
│   └── 05-development/             # Code examples and troubleshooting
├── create_readme_files.py          # Auto-generate README files for docs
└── migrate_project_to_docs.py      # Documentation reorganization tool
```

---

## 💼 Use Cases

This platform was built to demonstrate:

### 1. **HVAC Emergency Response**
- Customer calls with AC failure on a 95°F day
- AI assesses urgency, checks technician availability
- Books emergency slot, sends confirmation
- Logs estimated revenue and decision confidence

### 2. **Appointment Scheduling**
- Customer requests maintenance appointment
- AI checks availability, suggests time slots
- Handles rescheduling and cancellations
- Reduces phone time by 12 minutes per interaction

### 3. **Lead Qualification**
- Inquiry comes in via web form or SMS
- AI determines residential vs. commercial
- Routes to appropriate sales workflow
- Tracks conversion metrics

### 4. **Business Intelligence**
- Live dashboard shows today's revenue captured
- Calculates ROI: revenue / AI costs (typically 50-200x)
- Tracks agent confidence and decision quality
- Proves value before full deployment

---

## 📚 Documentation

Documentation is organized by audience and use case in the `docs/` directory:

- **[01-infrastructure/](docs/01-infrastructure/)** - Docker deployment, networking, monitoring setup
- **[02-n8n-workflows/](docs/02-n8n-workflows/)** - Workflow architecture, development guides, integration patterns
- **[03-database/](docs/03-database/)** - Schema documentation, ER diagrams, query examples
- **[04-customer-facing/](docs/04-customer-facing/)** - Presentations and solution briefs for stakeholders
- **[05-development/](docs/05-development/)** - Code examples, testing strategies, troubleshooting guides

**Tip:** Run `python create_readme_files.py` to auto-generate README files for all documentation folders.

---

## 🛠 Utilities

### Documentation Tools

```bash
# Generate README files for all doc folders
python create_readme_files.py

# Reorganize project documentation structure
python migrate_project_to_docs.py
```

### Operations Scripts

```bash
# Deploy to production server
./scripts/deploy.sh

# Backup PostgreSQL database
./scripts/backup.sh

# Monitor system health
./scripts/monitor.sh
```

---

## 🔧 Development

### Local Development Workflow

1. **Edit workflows** in n8n UI at `http://localhost:5678`
2. **Test changes** using the event generator workflow
3. **Export workflow** as JSON via n8n's download feature
4. **Save to** `n8n-workflows/` directory
5. **Commit** with descriptive message: `git commit -m "Add retry logic to emergency agent"`

### Database Migrations

```bash
# Connect to PostgreSQL
docker exec -it hvac-postgres psql -U hvac_user -d hvac_demo

# Run queries, add tables, etc.
# Export changes back to hvac_schema.sql when stable
```

### View Logs

```bash
# n8n logs
docker logs n8n -f

# PostgreSQL logs
docker logs hvac-postgres -f

# Nginx access logs
docker logs web-server -f
```

### Health Checks

All services include health checks. Monitor status:

```bash
docker ps  # Check STATUS column
curl http://localhost:5678/healthz  # n8n health check
```

---

## 🌐 Public Access

The platform is configured to use **ngrok** for secure tunneling, enabling:
- Webhook callbacks from external services
- Remote demos without VPN
- Shareable URLs for stakeholders

**Default domain:** `agents-platform.ngrok.io`

To use a different ngrok domain, edit `docker-compose.yml`:

```yaml
ngrok:
  command:
    - "http"
    - "web-server:80"
    - "--domain=your-custom-domain.ngrok.io"  # Change this
```

---

## 📈 Performance & Costs

Based on the HVAC demo simulation:

| Metric | Value |
|--------|-------|
| **Avg. Time Saved per Event** | 12 minutes |
| **Avg. AI Cost per Decision** | $0.004 |
| **Typical ROI** | 50-200x (revenue vs. AI cost) |
| **Agent Decision Confidence** | 85-95% |
| **Events Handled per Day** | 20-50 (in demo mode) |

These metrics are tracked in real-time via the business dashboard.

---

## 🎨 The "Intelligence Moat" Narrative

This project demonstrates a key thesis:

> **"Everyone Has AI. Not Everyone Has INTELLIGENCE."**

The portfolio site (`public/index.html`) presents this narrative:
1. **The Problem** - Generic AI chatbots provide no competitive advantage
2. **The Proof** - Domain-specific agents with business logic create moats
3. **The Demo** - Live HVAC digital twin showing measurable value

Presentation slides are available in `docs/04-customer-facing/presentations/`.

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

Copyright (c) 2025 dshorter

---

## 👤 Maintainer

**Daniel Shorter**
📧 codesurfer@gmail.com
🐙 [@dshorter](https://github.com/dshorter)

---

## 🙏 Acknowledgments

- **n8n.io** - Powerful open-source workflow automation
- **PostgreSQL** - Reliable database for event tracking
- **ngrok** - Secure tunneling for webhook testing
- **Docker** - Consistent deployment across environments

---

## 🚦 Status

**Current Version:** Early Demo (October 2025)
**Status:** Active Development
**Stability:** Proof of Concept - suitable for demos and evaluation

---

**Built to prove that intelligence beats generic AI every time. 🎯**
