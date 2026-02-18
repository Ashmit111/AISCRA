# Implementation Plan: AI Supply Chain Risk Analysis System

**Project:** Real-time supply chain risk monitoring using Multi-Agent AI architecture  
**Based on:** [architecture.md](architecture.md)  
**Status:** ✅ Complete - All Phases Implemented  
**Started:** February 17, 2026  
**Phase 1 Completed:** February 18, 2026  
**Phase 2 Completed:** February 18, 2026  
**Phase 3 Completed:** February 18, 2026  
**Phase 4 Completed:** February 18, 2026

---

## Overview

Build a company-centric supply chain risk analysis system that:
- Ingests news, financial signals, and geopolitical data in real-time
- Uses Google Gemini LLM to extract and classify risks
- Propagates risks through supply chain graph using NetworkX
- Recommends alternate suppliers when disruptions occur
- Provides AI agent for natural language queries
- Delivers insights via interactive dashboard

---

## Phase 1: Foundation (Weeks 1-3)

**Goal:** Data flows from news API → MongoDB, basic Gemini extraction works

### 1.1 Project Structure Setup ✓
```
aiscra/
├── backend/
│   ├── src/
│   │   ├── ingestion/
│   │   │   ├── connectors/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py
│   │   │   │   └── newsapi.py
│   │   │   ├── __init__.py
│   │   │   ├── celery_app.py
│   │   │   ├── deduplicator.py
│   │   │   ├── normalizer.py
│   │   │   └── redis_streams.py
│   │   ├── risk_engine/
│   │   │   ├── __init__.py
│   │   │   ├── gemini_client.py
│   │   │   ├── relevance_filter.py
│   │   │   ├── scoring.py
│   │   │   └── graph_propagation.py
│   │   ├── recommender/
│   │   │   ├── __init__.py
│   │   │   ├── supplier_finder.py
│   │   │   └── recommendation_text.py
│   │   ├── agent/
│   │   │   ├── __init__.py
│   │   │   ├── tools.py
│   │   │   ├── agent.py
│   │   │   └── report_generator.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   └── models.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py
│   │   │   └── db.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── config.py
│   ├── scripts/
│   │   ├── seed_data.py
│   │   └── create_indexes.py
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── stores/
│   │   └── lib/
│   ├── public/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── .gitignore
├── README.md
├── architecture.md
└── plan.md
```

### 1.2 Backend Foundation
- [x] requirements.txt with core dependencies
- [x] .env.example with API keys template
- [x] config.py for environment variable management
- [x] MongoDB connection setup
- [x] Redis connection setup

### 1.3 Database Schema (MongoDB)
- [x] Define Pydantic models for all collections:
  - Company profile
  - Suppliers (Tier-1, Tier-2, alternates)
  - Articles (raw news data)
  - RiskEvents (extracted risks)
  - Alerts (generated alerts)
  - Reports (AI-generated reports)
- [x] MongoDB indexes for performance
- [x] Seed script with example data (Nayara Energy + suppliers)

### 1.4 Redis Streams Pipeline
- [x] Stream utilities (push_to_stream, consume_stream)
- [x] Create consumer groups
- [x] Deduplication using Redis SET NX
- [x] Stream names: raw_events, normalized_events, risk_entities, risk_scores, new_alerts

### 1.5 Data Ingestion Module
- [x] Base Connector class
- [x] NewsAPI connector with keyword building
- [x] Article normalizer
- [x] Celery app configuration
- [x] Celery Beat schedule (every 15 min)
- [x] Task: fetch_all_sources

### 1.6 Gemini Risk Extraction
- [x] Gemini client initialization (Flash + Pro models)
- [x] Relevance filter with embeddings
- [x] extract_risk() with structured JSON output
- [x] Risk type classification (8 categories)
- [x] Entity linking to supply chain nodes

### 1.7 Basic API Endpoints
- [x] GET /api/alerts
- [x] GET /api/suppliers
- [x] GET /api/risks
- [x] Health check endpoint

**Phase 1 Deliverable:** News articles → normalized → risk extracted → saved to MongoDB

---

## Phase 2: Risk Engine (Weeks 4-6) ✓

**Goal:** Full scoring, graph propagation, and alerts with recommendations

### 2.1 Risk Scoring ✓
- [x] Implement scoring formula (Probability × Impact × Urgency / Mitigation)
- [x] Calculate components:
  - Probability: 0-1 based on severity + confirmation
  - Impact: dependency_ratio × material_criticality × buffer_score × 10
  - Urgency: immediate=2.0, days=1.5, weeks=1.0, months=0.5
  - Mitigation: based on alternate supplier count
- [x] Map scores to bands (critical ≥10, high ≥6, medium ≥3, low <3)

### 2.2 Supply Chain Graph ✓
- [x] Build NetworkX graph from MongoDB suppliers
- [x] Node attributes: type, tier, supply_volume_pct, criticality
- [x] Edge weights: dependency ratios
- [x] Calculate betweenness centrality (critical nodes)
- [x] Find vulnerable paths (single-source dependencies)

### 2.3 Risk Propagation ✓
- [x] propagate_risk() function with BFS algorithm
- [x] Propagation formula: score × dependency_weight × (0.5 + vulnerability)
- [x] Update risk_events with propagation field
- [x] Store propagated scores per node

### 2.4 Alert Generation ✓
- [x] Alert threshold logic (score ≥ 3.0)
- [x] Create alert documents in MongoDB
- [x] Email notifications via SendGrid
- [x] Slack notifications via webhooks
- [x] WebSocket push to dashboard

### 2.5 Alternate Supplier Recommender ✓
- [x] Query MongoDB for candidate suppliers
- [x] Multi-factor scoring:
  - Geographic diversity: 20%
  - Capacity coverage: 25%
  - Existing relationship: 20%
  - ESG score: 10%
  - Financial stability: 10%
  - Switching cost: 5%
  - Lead time: 10%
- [x] Rank and return top 5 alternates
- [x] Generate recommendation text with Gemini
- [x] Update alert with recommendations

### 2.6 Workers & Pipeline Integration ✓
- [x] process_risk_extraction_task (consumes normalized_events)
- [x] process_risk_scoring_task (consumes risk_entities)
- [x] process_alerts_task (consumes risk_scores, produces new_alerts)
- [x] Celery Beat schedule (workers run every 60 seconds)

### 2.7 API Extensions ✓
- [x] POST /api/alerts/{id}/acknowledge
- [x] GET /api/suppliers/{id} with risk history
- [x] GET /api/dashboard/summary with aggregations
- [x] WS /ws/alerts for real-time

**Phase 2 Deliverable:** ✅ Complete risk pipeline from ingestion to actionable alerts

---

## Phase 3: Dashboard (Weeks 7-9) ✓

**Goal:** React frontend showing live supply chain risk

### 3.1 Frontend Setup ✓
- [x] Initialize Vite + React + TypeScript
- [x] Configure Tailwind CSS + Shadcn/ui
- [x] Set up React Router
- [x] Create layout components (navbar, sidebar)
- [x] Configure API client with axios

### 3.2 Dashboard Page ✓
- [x] Risk summary cards (critical/high/medium/low counts)
- [x] Active alerts table with sorting/filtering
- [x] Cytoscape.js supply chain graph
  - Nodes colored by risk score gradient
  - Click to view supplier details
  - Edge thickness = dependency weight
- [x] Live news feed with risk tags
- [x] Real-time WebSocket integration

### 3.3 Suppliers Page ✓
- [x] Supplier list with current risk scores
- [x] Search and filter controls
- [x] Supplier detail view:
  - Risk history chart (Recharts line graph)
  - Recent news affecting supplier
  - Upstream dependencies
  - Alternate suppliers comparison table

### 3.4 Alerts Page ✓
- [x] Timeline view of alerts
- [x] Multi-select filters:
  - Severity
  - Affected supplier
- [x] Alert detail modal:
  - Source information
  - Score breakdown visualization
  - Alternate suppliers
  - AI recommendations

### 3.5 AI Agent Chat Page ✓
- [x] Chat interface with message history
- [x] Natural language query input
- [x] Conversation starters
- [x] Real-time agent responses
- [x] Tool usage display

### 3.6 Reports Page ✓
- [x] Report archive list (daily/weekly/custom)
- [x] Generate custom report button
- [x] Report viewer with formatted sections

### 3.7 Real-Time Features ✓
- [x] Zustand store for alert state
- [x] WebSocket connection hook
- [x] Toast notifications for new alerts
- [x] Auto-refresh data every 30s
- [x] Browser notifications

**Phase 3 Deliverable:** ✅ Functional dashboard with live updates

---

## Phase 4: AI Agent (Weeks 10-12) ✓

**Goal:** Conversational agent + auto-reports

### 4.1 Agent Tools (LangChain) ✓
- [x] query_risk_events(risk_type, severity, days_back)
- [x] get_active_alerts(severity)
- [x] find_alternate_suppliers_tool(supplier_name, material)
- [x] get_supply_chain_summary()
- [x] get_risk_trend(supplier_name, risk_type, days_back)

### 4.2 LangGraph Multi-Agent ✓
- [x] Initialize Gemini 1.5 Pro LLM
- [x] Create ReAct agent with all tools
- [x] Conversational state management
- [x] Error handling and retries

### 4.3 Report Generator ✓
- [x] Celery task: generate_daily_report()
- [x] Celery task: generate_weekly_report()
- [x] Schedule: daily at 8am UTC, weekly on Mondays at 9am UTC
- [x] Report structure:
  - Executive summary
  - Active risks table
  - Recommendations
  - Risk trend analysis
- [x] Save to MongoDB reports collection
- [x] Support custom reports with user queries

### 4.4 Agent Chat Interface
- [ ] Chat page component (Frontend - Phase 3)
- [ ] Message history display
- [ ] Query input with auto-suggestions
- [ ] Streaming response support
- [ ] Export conversation as PDF

### 4.5 API Endpoints ✓
- [x] POST /api/agent/query
- [x] GET /api/agent/starters
- [x] POST /api/reports/generate
- [x] GET /api/reports
- [x] GET /api/reports/{id}

**Phase 4 Deliverable:** ✅ Complete system with AI agent and auto-reporting

---

## Phase 5: Deployment & Testing (Weeks 13-14)

### 5.1 Docker & Orchestration
- [ ] Complete docker-compose.yml
- [ ] Backend Dockerfile with multi-stage build
- [ ] Frontend Dockerfile with nginx
- [ ] Environment variable configuration
- [ ] Volume mounts for persistence

### 5.2 Testing
- [ ] Unit tests for core functions
- [ ] Integration tests for API endpoints
- [ ] End-to-end test: article → alert flow
- [ ] Load testing with 100 concurrent articles
- [ ] Agent query testing (all tool combinations)

### 5.3 Documentation
- [ ] README.md with setup instructions
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Environment variable reference
- [ ] Architecture diagram
- [ ] Demo walkthrough guide

### 5.4 Performance Optimization
- [ ] MongoDB query optimization
- [ ] Redis connection pooling
- [ ] Celery worker tuning
- [ ] Frontend code splitting
- [ ] API response caching

**Phase 5 Deliverable:** Production-ready system with full documentation

---

## Tech Stack Summary

### Backend
- **API:** FastAPI (async Python)
- **Task Queue:** Celery + Redis broker
- **Message Streaming:** Redis Streams (XADD/XREAD)
- **Database:** MongoDB Atlas (single cluster)
- **Vector Search:** MongoDB Atlas Vector Search
- **Graph:** NetworkX (in-memory)
- **LLM:** Google Gemini API (Flash + Pro)
- **Embeddings:** Gemini text-embedding-004
- **Agent:** LangGraph + LangChain Google GenAI
- **NLP:** spaCy (optional, for NER pre-filtering)

### Frontend
- **Framework:** React + TypeScript (Vite)
- **Styling:** Tailwind CSS + Shadcn/ui
- **Graph Viz:** Cytoscape.js
- **Charts:** Recharts
- **State:** Zustand
- **Real-time:** Native WebSocket API
- **Maps:** Leaflet.js (optional)

### Infrastructure
- **Containers:** Docker + Docker Compose
- **Database:** MongoDB Atlas M0 (free tier) or local Docker
- **Cache/Broker:** Redis (Docker)
- **CI/CD:** GitHub Actions (future)

---

## Key Implementation Notes

### Company Profile Drives Everything
The company profile (Nayara Energy example) contains:
- Suppliers list (Tier-1, Tier-2)
- Raw materials with criticality scores
- Key geographies
- Inventory buffer days
- Contract end dates

All keyword matching, relevance scoring, and impact calculations reference this profile.

### Redis Streams Flow
```
raw_events → normalized_events → risk_entities → risk_scores → new_alerts
```
Each stream has dedicated Celery workers consuming with XREADGROUP.

### Risk Score Formula
```
Score = (Probability × Impact × Urgency) / Mitigation

Where:
- Probability: 0-1 (severity + confirmation)
- Impact: 1-10 (dependency × criticality × buffer)
- Urgency: 0.5-2.0 (time horizon multiplier)
- Mitigation: 0.5-2.0 (alternate supplier availability)
```

### Graph Propagation
Uses NetworkX DiGraph with edges:
```
Tier-2 Supplier → Tier-1 Supplier → Company
(weight = supply_volume_pct / 100)
```

Risk propagates backward with decay based on dependency weight and vulnerability.

### Gemini Usage Strategy
- **Flash (gemini-1.5-flash):** Risk extraction, recommendation text (fast, cheap)
- **Pro (gemini-1.5-pro):** Complex geopolitical analysis, agent reasoning (slower, accurate)
- **Embeddings (text-embedding-004):** Relevance filtering, supplier similarity

### MongoDB Collections
1. `companies` - Company profile (1 doc)
2. `suppliers` - All suppliers (Tier-1, Tier-2, alternates)
3. `articles` - Raw news articles
4. `risk_events` - Extracted risks with scores
5. `alerts` - Generated alerts with recommendations
6. `reports` - AI-generated reports

---

## Success Criteria

### Phase 1 ✓
- [ ] News article fetched from NewsAPI
- [ ] Article normalized and deduplicated
- [ ] Risk extracted by Gemini and saved to MongoDB
- [ ] Basic API returns data

### Phase 2
- [ ] Risk score calculated correctly
- [ ] Graph propagation works (Tier-2 → Tier-1 → Company)
- [ ] Alert generated with recommendations
- [ ] Email/Slack notification sent

### Phase 3
- [ ] Dashboard loads with real data
- [ ] Supply chain graph visualizes correctly
- [ ] Real-time alert appears in dashboard
- [ ] All pages navigate properly

### Phase 4
- [ ] Agent answers: "What are our top 3 risks?"
- [ ] Agent uses multiple tools in sequence
- [ ] Daily report generated automatically
- [ ] Report sent via email

### Phase 5
- [ ] `docker-compose up` starts all services
- [ ] Complete flow test passes (15 min cycle)
- [ ] Load test: 100 articles processed in <2 min
- [ ] Documentation complete

---

## Current Status: Phase 1 - In Progress

**Next Steps:**
1. ✓ Create project structure
2. ✓ Set up backend foundation (requirements.txt, .env)
3. ✓ Define MongoDB schemas
4. ✓ Implement Redis Streams utilities
5. → **Current:** Build data ingestion connectors
6. → Implement Gemini risk extraction

**Estimated Completion:** Phase 1: 1 week | Full System: 8-10 weeks

---

## Quick Start (Once Complete)

```bash
# Clone and setup
git clone <repo>
cd aiscra

# Configure environment
cp backend/.env.example backend/.env
# Add: GEMINI_API_KEY, NEWSAPI_KEY

# Start services
docker-compose up -d

# Seed database
docker-compose exec api python scripts/seed_data.py

# Access
# Dashboard: http://localhost:3000
# API Docs: http://localhost:8000/docs
# Agent Chat: http://localhost:3000/agent
```

---

**Last Updated:** February 17, 2026  
**Contact:** Development Team  
**Architecture:** [architecture.md](architecture.md)
