# Intelligence Moat Project - Current State
**Created:** November 13, 2025 at 2:53 PM EST  
**Last Updated:** November 13, 2025 at 2:53 PM EST  
**Project Stage:** Pre-Revenue, Post-Technical-Validation  
**Status:** HVAC Demo Backend Operational, Seeking Pilot Partners  
**Founder:** Dan (Technical founder with 300 hours PTO runway)

---

## 🔥 TIMESTAMP: November 13, 2025 - 2:53 PM EST

**Where We Actually Are Right Now:**
- Backend infrastructure: ✅ DEPLOYED AND WORKING
- Event generator: ✅ PRODUCING REALISTIC DATA
- Customer-facing demos: ❌ NOT BUILT YET
- Paying customers: ❌ ZERO (pre-revenue)
- Cold emails sent: ❌ ZERO (need to start)

**The Reality:**
We have a working backend that can simulate a realistic HVAC business generating 30+ event types with intelligent patterns. We DO NOT have customer-facing dashboards or any customers. We're at the "backend works, now need to sell it" stage.

---

## 📊 Executive Summary

**What We Have:**
- ✅ Production-ready n8n automation platform on Hetzner VPS
- ✅ PostgreSQL database with HVAC Digital Twin event generator
- ✅ Multi-LLM orchestration (Grok, OpenAI, Claude) configured
- ✅ SMS integration via Twilio working
- ✅ LOG003 sequence-aware logging system
- ✅ Idempotency patterns preventing duplicate events
- ✅ Git-based version control and CI/CD pipeline
- ✅ Predictor pipeline web UI live at `/predictor/` via ngrok (Feb 2026)

**What We Don't Have:**
- ❌ Paying customers (zero revenue)
- ❌ Customer-facing dashboards (Business Owner or Technologist views)
- ❌ Completed Primary Agent workflow
- ❌ Specialist agent workflows (Emergency, Scheduling, Billing, etc.)
- ❌ Case studies or testimonials
- ❌ Cold email campaign started

**Current Focus:**
Building customer-facing demos (Business Owner + Technologist dashboards) and starting customer acquisition through cold email outreach to secure 3 pilot partners.

---

## ✅ What's Deployed (RIGHT NOW)

### Production Infrastructure (Unchanged from Oct 21)
- ✅ **Hetzner VPS CX11** - €4.51/month (~$5 USD)
  - Ubuntu 22.04 LTS
  - 1 vCPU, 2GB RAM, 20GB SSD
  - SSH key authentication only
  - UFW firewall configured

- ✅ **n8n Workflow Engine** - Running in Docker
  - Community Edition (free)
  - Accessed via SSH tunnel
  - PostgreSQL backend
  - Redis for state management
  - Auto-restart health monitoring

- ✅ **CI/CD Pipeline** - GitHub Actions
  - Auto-deploy on push to main
  - Daily backups at 3 AM
  - Git-based workflow version control

- ✅ **Predictor Pipeline Integration** (Feb 2026)
  - RSS trend analysis with graph visualizations
  - Web UI served at `/predictor/` via nginx/ngrok
  - Sibling repo (`predictor_ingest`) mounted into nginx container
  - Pipeline container available via `docker compose --profile predictor`
  - Safe-reboot and health check scripts updated for predictor awareness

- ✅ **SMS Integration** - Twilio
  - Real phone number configured
  - Bidirectional SMS capability
  - Message buffering (3-second window)
  - Signature validation for security

### LLM Integrations (Unchanged)
- ✅ **Grok (X.AI)** - Primary model
- ✅ **OpenAI GPT-4o-mini** - Cost-optimized
- ✅ **OpenAI GPT-4o** - Full capability
- ✅ **Claude (Anthropic)** - Alternative for specific use cases
- ✅ **Model Selector Pattern** - Dynamic routing based on confidence

---

## 🆕 NEW: What's Built Since October 21

### 1. PostgreSQL Database Infrastructure (Oct 28, 2025)

**Deployed via Docker Compose:**
```yaml
postgres:
  image: postgres:15-alpine
  container_name: hvac-postgres
  database: hvac_demo
  user: hvac_user
  port: 5432 (localhost only)
```

**Database Schema:**
- 7 tables: customers, technicians, hvac_events, workflow_executions, agent_decisions, business_metrics, schema_version
- 3 helper views: v_recent_events, v_agent_performance, v_daily_metrics
- 1 utility function: get_decision_depth
- Complete with indexes, constraints, and seed data

**Seed Data Loaded:**
- 5 demo customers (residential + commercial)
- 4 demo technicians (various skill levels)

**Status:** ✅ OPERATIONAL (deployed October 28, 2025)

---

### 2. HVAC Event Generator - "Probabilistic Meta-Scheduler"

**Purpose:** Generate realistic HVAC business events using scenario-based patterns with full observability.

**Key Features:**
- ✅ Weighted event distribution (85% routine, 10% winter emergency, 5% summer heatwave)
- ✅ Time-pattern awareness (emergencies more common at night, appointments during business hours)
- ✅ Customer pool management (residential vs commercial patterns)
- ✅ Revenue estimation per event type
- ✅ Idempotency to prevent duplicate events
- ✅ LOG003 sequence-aware logging

**Three Built-In Scenarios:**

1. **Winter Emergency Surge**
   - 50 events over 2 hours
   - 60% emergencies, 25% inquiries
   - High urgency bias (7-10 out of 10)
   - Revenue range: $250-600 per event

2. **Routine Maintenance Day**
   - 30 events over 8 hours (business day)
   - 50% appointments, 25% inquiries, 15% follow-ups
   - Low urgency bias (2-5 out of 10)
   - Revenue range: $150-350 per event

3. **Summer Heatwave**
   - 75 events over 3 hours
   - 70% emergencies (AC failures)
   - Extreme urgency bias (8-10 out of 10)
   - Revenue range: $300-800 per event

**Workflow Structure:**
- 14 nodes in n8n
- ~90 minutes to build
- Performance: 100 events in <10 seconds
- Includes validation, idempotency gate, logging

**Status:** ✅ OPERATIONAL (can trigger via webhook or manual)

---

### 3. LOG003 Sequence-Aware Logging System

**What It Does:**
Provides comprehensive observability for multi-agent workflows with proper parent-child relationships.

**Key Features:**
- ✅ Unique `workflow_sequence_id` per execution
- ✅ Step numbering for chronological ordering
- ✅ Decision confidence tracking
- ✅ Classification tags (ARRAY type in PostgreSQL)
- ✅ Decision payload (JSONB for flexible data)
- ✅ Automatic timestamp recording

**Database Table:**
```sql
CREATE TABLE agent_decisions (
  decision_id SERIAL PRIMARY KEY,
  event_id INT REFERENCES hvac_events(event_id),
  workflow_execution_id UUID REFERENCES workflow_executions(execution_id),
  workflow_sequence_id UUID NOT NULL,  -- Key for grouping related decisions
  agent_name VARCHAR(100) NOT NULL,
  decision_type VARCHAR(50) NOT NULL,
  step_number INT NOT NULL,           -- Chronological ordering
  routing_reason TEXT,
  decision_confidence DECIMAL(3,2),
  classification_tags TEXT[],          -- ARRAY for flexible tagging
  action_taken VARCHAR(200),
  outcome_status VARCHAR(50),
  decision_payload JSONB,              -- Flexible JSON data
  decision_timestamp TIMESTAMP DEFAULT NOW(),
  created_at TIMESTAMP DEFAULT NOW()
);
```

**Status:** ✅ IMPLEMENTED (event generator uses this pattern)

---

### 4. Idempotency System

**Purpose:** Prevent duplicate event creation if workflow re-runs within TTL window.

**How It Works:**
- Content-based hashing of event data (type, customer, timestamp, urgency)
- In-memory cache with configurable TTL (default: 5 minutes)
- Cache hit returns existing event_id without database insert
- Cache miss creates new event and adds to cache

**Performance:**
- Reduces database load on retries
- Prevents data contamination from duplicate submissions
- Automatic cache expiration and cleanup

**Status:** ✅ WORKING (tested with duplicate scenario requests)

---

### 5. n8n Workflow Version Control

**Created Structure:**
```
ai-agent-platform/
└── n8n-workflows/
    ├── README.md (150+ line comprehensive guide)
    ├── primary-agent.json (template - not built yet)
    └── emergency-agent.json (template - not built yet)
    └── event-generator.json (✅ OPERATIONAL)
```

**Version Control Process:**
1. Build workflow in n8n visual UI
2. Export as JSON
3. Save to Git repo
4. Auto-deploy to VPS via GitHub Actions

**Status:** ✅ ESTABLISHED (workflow files can be versioned and deployed)

---

### 6. Demo Account Planning

**HVAC Demo Account Tree Created:**
- 1 business operations email
- 3 customer personas (2 residential, 1 commercial)
- 2 technician personas (1 senior, 1 junior)
- 1 demo admin account

**Purpose:** Isolated demo environment with zero personal info contamination.

**Status:** ❌ PLANNED BUT NOT CREATED (Gmail accounts not set up yet)

---

## ❌ What's Still NOT Done

### Customer-Facing Deliverables (CRITICAL GAP)

1. **Business Owner Dashboard** ❌
   - Purpose: Show P&L impact in non-technical language
   - Target: HVAC business owners who care about headcount/savings/ROI
   - Status: NOT STARTED

2. **Technologist Dashboard** ❌
   - Purpose: Show architecture, agent routing, LLM optimization
   - Target: Technical decision-makers evaluating the platform
   - Status: NOT STARTED

### Agent Workflows (CORE SYSTEM)

3. **Primary Agent Workflow** ❌
   - Purpose: Intelligent event classification and routing
   - Status: Template exists, not built

4. **Specialist Agents** ❌ (6 total needed)
   - Emergency Agent
   - Customer Service Agent
   - Scheduling Agent
   - Billing Agent
   - Operations Agent
   - Inventory Agent
   - Status: Templates exist, none built

### Business Development (REVENUE BLOCKERS)

5. **No Paying Customers** ❌
   - Revenue: $0
   - Pilot partners: 0
   - Discovery calls: 0

6. **No Customer Acquisition Started** ❌
   - Cold email template: Not written
   - Target business list: Not identified
   - Emails sent: 0
   - CRM setup: None

7. **No Marketing Assets** ❌
   - Demo video: Not recorded
   - Case studies: None
   - Testimonials: None
   - Landing page: None
   - Domain: None (using ngrok)

---

## 🎯 Business Stage Update

### Current Reality (November 13, 2025)
**Stage:** Pre-Revenue, Backend Operational, Customer-Facing Demos Missing  
**Runway:** Employed full-time + 300 hours PTO available  
**Infrastructure:** Deployed and operational ($5/month)  
**Team:** Solo technical founder

### Risk Assessment
- ✅ **Technical Risk:** Largely de-risked (backend works, event generator proves concept)
- ⚠️ **Market Risk:** Completely un-validated (no customers, no conversations)
- ⚠️ **Execution Risk:** Time-constrained (need efficient customer acquisition)
- ⚠️ **Demo Risk:** NEW - Backend works but nothing to show prospects yet
- ✅ **Financial Risk:** Low (minimal burn rate)

### The Uncomfortable Truth
**We have a working backend with NO customer-facing interface.** This is the classic "ascension by repo" trap - building infrastructure while avoiding the hard part (talking to customers).

**What Changed Since October 21:**
- Technical capabilities INCREASED (event generator is impressive)
- Customer-facing readiness UNCHANGED (still can't demo to prospects)
- Time to first customer UNCHANGED (still haven't started outreach)

---

## 🚨 Priority Order (November 13, 2025)

### IMMEDIATE (This Week) - Get Demo-Ready

**Option A: Quick & Dirty (Recommended)**
1. **Send 10 cold emails FIRST** - Before building anything else
   - Target: HVAC businesses, coffee shops, or dental offices
   - Message: "I built this, want to see it work?"
   - Honest positioning: "Backend works, building demo based on your feedback"

2. **Build minimal Business Owner Dashboard** (4 hours max)
   - ONE PAGE HTML
   - Show: Events generated today, revenue captured, time saved
   - Use: PostgreSQL queries to fetch real data from event generator
   - Polish: ZERO (functional beats pretty)

**Option B: Build First, Sell Later (NOT Recommended)**
1. Complete Business Owner Dashboard (2 days)
2. Complete Technologist Dashboard (2 days)
3. Build Primary Agent (1-2 days)
4. Build 2 Specialist Agents (2 days)
5. Then start customer outreach (Week 2)

**Why Option A Wins:**
- Validates customer interest BEFORE building dashboards
- Gets conversations started immediately
- Allows building demos based on real prospect feedback
- Breaks the "ascension by repo" pattern

---

### Week 2-3: Demo Building

After getting 2-3 interested prospects from cold emails:

1. **Build Business Owner Dashboard** - Tailored to what prospects care about
2. **Build simplified demo workflow** - Just enough to show intelligence
3. **Create 3-minute demo video** - Screen recording with narration
4. **Set up simple CRM** - Track conversations (Airtable or Notion)

### Week 4-6: Customer Discovery

1. **Run discovery calls** - Understand data sources and pain points
2. **Create custom proposals** - Sector-specific brief + pricing
3. **Build pilot workflow** - First actual customer implementation
4. **Document everything** - Screenshots, conversations, learnings

### Month 2-3: First Pilot

1. **Sign first pilot partner** - Discounted rate for case study rights
2. **Deploy first customer workflow** - Real business using real data
3. **Gather metrics** - Track usage, costs, ROI indicators
4. **Create case study draft** - Document results (even if small)
5. **Use case study to secure pilots 2 & 3**

---

## 💰 Cost Structure (Still Valid)

### Fixed Costs (Unchanged)
- Infrastructure: $5/month (Hetzner VPS)
- GitHub: $0/month
- n8n: $0/month
- Twilio: ~$1/month
- **TOTAL: ~$6/month**

### Variable Costs (API Usage)
- GPT-4o-mini: ~$0.01 per simple interaction
- Claude Haiku: ~$0.05 per moderate interaction
- GPT-4o / Claude Sonnet: ~$0.10 per complex interaction

### Proven Unit Economics
**Event Generator Example:**
- Generated 50 events in ~8 seconds
- Database storage: negligible
- API costs: $0 (no LLM calls in generator)
- **Cost per event: <$0.001**

---

## 📚 Documentation Status

### Technical Documentation (Mostly Complete)
- ✅ Complete Hetzner VPS Setup Guide
- ✅ Production Baseline Architecture
- ✅ n8n Agent Project - Pure JSON Contract
- ✅ Technical Validation Report
- ✅ n8n Version Control Strategy
- ✅ Event Generator Deployment Guide (NEW)
- ✅ Event Generator Workflow Structure (NEW)

### Business Documentation (Needs Update)
- ✅ Solution Brief Benchmarking Analysis
- ✅ Intelligence Moat Solution Brief (has placeholders)
- ✅ Core Concepts - Intelligence Moat Philosophy
- ✅ 90-Day Side Hustle to Startup Master Plan
- ❌ Template Learnings (exists but not in project knowledge yet)

---

## 🎓 Lessons Learned (Updated November 13)

### What Worked
1. **Building backend infrastructure first** - De-risked technical execution
2. **Event generator as proof of concept** - Shows we can build complex systems
3. **Multi-LLM strategy** - Not locked to one provider
4. **LOG003 logging pattern** - Provides excellent observability
5. **Idempotency patterns** - Prevents data contamination

### What Hasn't Worked
1. **Building without customer input** - Backend works but no validation
2. **Avoiding customer conversations** - Classic "ascension by repo" trap
3. **Over-engineering before selling** - Should have started with MVP dashboard

### New Insights (Since Oct 21)
1. **Backend can be impressive without being perfect** - Event generator is good enough
2. **"Ascension by repo is a lie"** - More code ≠ more customers
3. **Customer conversations trump technical perfection** - Need to start outreach NOW
4. **Demo-ability matters more than completeness** - One working dashboard > six perfect agents

---

## 🔑 Key Mantras (Reinforced)

### "Ascension by Repo is a Lie"
- ✅ Backend is done enough - STOP polishing
- ❌ Don't build more before talking to customers
- ✅ One customer conversation > 100 GitHub commits

### "Ship beats perfect"
- Event generator works ✅
- Dashboards can be rough ✅
- Cold emails can be simple ✅

### "Customers beat code"
- Backend proves we can build ✅
- Now we need to SELL ✅
- Revenue validates everything else ✅

### "Reality beats fantasy"
- Have: Working backend
- Need: Customer conversations
- Reality: Can't hide behind code anymore

---

## 📊 What Actually Matters Right Now

### This Week (November 13-20)
**ONE GOAL: Start customer conversations**

Success = 10 cold emails sent + 2 responses

Everything else (dashboards, agents, polish) is SECONDARY until we have interested prospects.

### Next 30 Days
**PRIMARY GOAL: 1 pilot partner signed**

Success = One business agrees to pilot (even at discounted/free rate)

### Next 90 Days
**PRIMARY GOAL: 3 pilot partners + 1 case study**

Success = Three businesses using the platform + documented results

---

## 🔄 Update Log

**October 21, 2025**
- ✅ Initial PROJECT_STATE document created
- ✅ Honest assessment of pre-revenue stage
- ✅ Infrastructure inventory complete

**October 25, 2025**
- ✅ HVAC Digital Twin project scoped
- ✅ Dual-dashboard strategy designed
- ✅ Demo scenarios created
- ✅ Account tree planned

**October 28, 2025**
- ✅ PostgreSQL database deployed
- ✅ Database schema + seed data loaded
- ✅ n8n workflow version control established
- ✅ Git pipeline operational

**October 30, 2025** (estimated)
- ✅ Event Generator built and deployed
- ✅ LOG003 logging implemented
- ✅ Idempotency system working
- ✅ Three test scenarios operational

**November 13, 2025 - 2:53 PM EST**
- ✅ PROJECT_STATE document updated
- ✅ Reality check: Backend works, customer-facing missing
- ✅ Priority clarified: Customer conversations > more code
- 🚨 NEW MANDATE: Send cold emails THIS WEEK

**February 6, 2026**
- ✅ Predictor pipeline integrated into Docker Compose (profile-gated)
- ✅ Predictor web UI live at `/predictor/` via ngrok
- ✅ nginx configured to serve predictor_ingest/web/ from /srv/predictor
- ✅ Safe-reboot script: pipeline lock wait + SQLite pre-reboot backup
- ✅ Health check script: predictor container, DB size, backup freshness
- ✅ Fixed ngrok `--domain` → `--url` (deprecated flag broke tunnel)
- ✅ Dockerfile uses pyproject.toml (not requirements.txt)

**Next Update:** After first cold email responses OR after first pilot signed

---

## 📞 Access & Credentials (Unchanged)

### Access Points
- **VPS SSH:** `ssh agent-vps`
- **n8n UI:** http://localhost:5678 (via SSH tunnel)
- **GitHub Repo:** github.com/[YOUR_USERNAME]/ai-agent-platform
- **Twilio Dashboard:** twilio.com/console
- **Hetzner Console:** console.hetzner.cloud

### Environment Health Check
```bash
# SSH into VPS
ssh agent-vps

# Check all containers
docker ps

# Expected output:
# - hvac-postgres (running)
# - n8n (running)
# - nginx (running)
# - ngrok (running)

# Test event generator
curl -X POST http://localhost:5678/webhook/hvac/generate-events \
  -H "Content-Type: application/json" \
  -d '{"scenario_name": "routine_maintenance_day", "event_count": 10}'

# Check events created
docker exec hvac-postgres psql -U hvac_user -d hvac_demo -c \
  "SELECT COUNT(*) FROM hvac_events WHERE created_at > NOW() - INTERVAL '1 hour';"
```

---

## 🎯 The Hard Truth

**We're at the classic "build vs. sell" inflection point.**

**What we've proven:**
- ✅ Can build complex infrastructure
- ✅ Can integrate multiple LLMs
- ✅ Can create realistic simulations
- ✅ Can implement production-grade patterns

**What we haven't proven:**
- ❌ Anyone wants this
- ❌ Anyone will pay for it
- ❌ We can sell it
- ❌ We can support customers

**The Next Move:**
Stop building. Start selling.

The backend works. The event generator proves we can build complex systems. Now we need to find out if anyone actually wants this.

**Action This Week:**
1. Write cold email template (1 hour)
2. Find 20 target businesses (1 hour)
3. Send 10 emails (30 minutes)
4. Wait for responses
5. Build dashboards ONLY if people respond

**The Mantra:**
"Customers validate. Code doesn't."

---

## 📚 Related Documents

**Technical:**
- Complete_Hetzner_VPS_Setup_Guide_for_AI_Agent_Platform
- Production_Baseline__Twilio_SMS___n8n_Integration_Architecture.md
- n8n_Agent_Project___Pure_JSON_Contract_
- event_generator_workflow_structure.md (NEW)
- event_generator_deployment_guide.md (NEW)

**Business:**
- Intelligence_Moat_Solution_Brief.docx
- Core_Concepts__The_Intelligence_Moat_Philosophy.md
- 90-Day_Side_Hustle_to_Startup_Master_Plan
- HVAC_Digital_Twin_Conversation_Context.md (NEW)
- HVAC_Demo_Account_Tree.md (NEW)

**Planning:**
- HVAC_Digital_Twin_Project_Plan.xlsx (NEW)

---

**END OF DOCUMENT**

*This document is the authoritative source of truth for the Intelligence Moat project as of November 13, 2025 at 2:53 PM EST. Backend is operational. Customer-facing demos missing. Customer conversations needed. Stop building, start selling.*
