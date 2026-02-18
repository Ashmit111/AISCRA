# Phase 4 Implementation Summary: AI Agent with LangGraph

**Status:** ✅ Complete  
**Date:** February 18, 2026

## Overview

Phase 4 implements a conversational AI agent powered by Google Gemini Pro and LangGraph that enables natural language queries of supply chain risk data. The agent uses a ReAct (Reasoning + Acting) pattern with 5 specialized tools to answer questions about risks, alerts, suppliers, and trends.

## Components Implemented

### 1. Agent Tools (backend/src/agent/tools.py)

Five LangChain tools provide the agent with capabilities to query the system:

#### Tool 1: `query_risk_events`
- **Purpose:** Query recent risk events with filters
- **Parameters:**
  - `risk_type`: Filter by type (geopolitical, financial, etc.)
  - `severity`: Filter by severity band (critical, high, medium, low)
  - `days_back`: Number of days to look back (default: 7)
  - `limit`: Maximum results (default: 10)
- **Returns:** JSON string with list of risk events

#### Tool 2: `get_active_alerts`
- **Purpose:** Get currently unacknowledged alerts
- **Parameters:**
  - `severity`: Filter by severity
  - `limit`: Maximum results (default: 10)
- **Returns:** JSON with alerts including alternate suppliers and recommendations

#### Tool 3: `find_alternate_suppliers_tool`
- **Purpose:** Find and rank alternate suppliers
- **Parameters:**
  - `supplier_name`: Current supplier to find alternates for
  - `material`: Specific material (optional)
- **Returns:** Ranked list of alternates with 7-factor scores

#### Tool 4: `get_supply_chain_summary`
- **Purpose:** Get high-level supply chain status
- **No parameters**
- **Returns:** JSON with:
  - Company profile
  - Supplier statistics
  - Alert counts by severity
  - Recent risk event counts
  - Top risk types
  - Materials and geographies

#### Tool 5: `get_risk_trend`
- **Purpose:** Analyze risk trends over time
- **Parameters:**
  - `supplier_name`: Filter by supplier (optional)
  - `risk_type`: Filter by risk type (optional)
  - `days_back`: Number of days to analyze (default: 30)
- **Returns:** JSON with daily breakdown, trend direction, averages

### 2. Agent Orchestrator (backend/src/agent/agent.py)

#### SupplyChainAgent Class
- **LLM:** Gemini 1.5 Pro (temperature: 0.3 for factual responses)
- **Architecture:** LangGraph ReAct agent
- **Tools:** All 5 tools registered
- **Context:** Loads company profile and injects into system prompt

#### Key Methods:

**`query(user_query, conversation_history)`**
- Processes natural language queries
- Maintains conversation context
- Tracks tool usage
- Returns structured response with metadata

**`get_conversation_starters()`**
- Provides 8 suggested starter questions:
  - "What are the current critical alerts?"
  - "Show me risk trends for the past 30 days"
  - "What alternate suppliers are available for crude oil?"
  - "Give me a summary of our supply chain status"
  - "What are the top geopolitical risks this week?"
  - "Which suppliers are currently at high risk?"
  - "How many alerts do we have for financial risks?"
  - "What's the risk trend for Rosneft?"

#### System Prompt
Injects company-specific context:
- Company name and industry
- Key materials
- Key geographies
- Available tools and their purposes

### 3. Report Generator (backend/src/agent/report_generator.py)

#### ReportGenerator Class
Generates comprehensive reports using the AI agent.

**Daily Report Structure:**
1. Executive Summary
2. Critical Alerts
3. New Risk Events (24 hours)
4. Top Risk Types
5. Supplier Risk Status
6. Recommendations

**Weekly Report Structure:**
1. Executive Summary
2. Week in Review
3. Risk Trend Analysis
4. Supplier Risk Performance
5. Geographic Risk Distribution
6. Material Risk Analysis
7. Alternate Supplier Recommendations
8. Strategic Recommendations

**Custom Reports:**
- Accepts list of custom queries
- Generates sections for each query
- Flexible for ad-hoc analysis

#### Scheduled Tasks:
- **Daily:** 8:00 AM UTC
- **Weekly:** Mondays at 9:00 AM UTC
- Saved to MongoDB `reports` collection

### 4. API Endpoints (backend/src/api/main.py)

#### Agent Endpoints:

**POST /api/agent/query**
```json
Request:
{
  "query": "What are the current critical alerts?",
  "conversation_history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}

Response:
{
  "success": true,
  "response": "Here are the critical alerts...",
  "tool_calls": [
    {"tool": "get_active_alerts", "args": {"severity": "critical"}}
  ],
  "query": "..."
}
```

**GET /api/agent/starters**
```json
Response:
{
  "starters": [
    "What are the current critical alerts?",
    "Show me risk trends for the past 30 days",
    ...
  ]
}
```

#### Report Endpoints:

**GET /api/reports**
- Query params: `report_type` (daily/weekly/custom), `limit`
- Returns list of recent reports

**GET /api/reports/{report_id}**
- Returns specific report by ID

**POST /api/reports/generate**
```json
Request:
{
  "type": "daily" | "weekly" | "custom",
  "queries": ["query1", "query2"]  // For custom reports
}

Response:
{
  "success": true,
  "report_id": "...",
  "report": { ... }
}
```

### 5. Celery Integration (backend/src/ingestion/celery_app.py)

#### Scheduled Tasks Added:

**generate_daily_report_task**
- Runs daily at 8:00 AM UTC
- Generates daily report
- Saves to MongoDB

**generate_weekly_report_task**
- Runs Mondays at 9:00 AM UTC
- Generates weekly report
- Saves to MongoDB

## Example Interactions

### Example 1: Critical Alerts Query
```
User: "What are the current critical alerts?"

Agent: (Uses get_active_alerts tool with severity="critical")

Response: "There are currently 2 critical alerts:

1. High Risk: Geopolitical disruption affecting Rosneft (Score: 8.5)
   - Affected Materials: crude oil
   - Recommendation: Consider diversifying to Saudi Aramco (Score: 8.9) or ADNOC

2. Critical Risk: Financial instability at supplier XYZ (Score: 10.2)
   - Affected Materials: naphtha
   - Immediate action required..."
```

### Example 2: Risk Trend Analysis
```
User: "Show me the risk trend for Rosneft over the past month"

Agent: (Uses get_risk_trend tool with supplier_name="Rosneft", days_back=30)

Response: "Risk trends for Rosneft over the past 30 days:

- Total Events: 15
- Average per Day: 0.5
- Trend Direction: Increasing (recent 7-day avg: 0.86 vs earlier: 0.41)

Daily Breakdown:
- Feb 1: 0 events
- Feb 2: 1 event (avg score: 5.2)
- Feb 3: 2 events (max score: 7.5)
...

The increasing trend suggests elevated risk levels. Consider reviewing alternate suppliers."
```

### Example 3: Supply Chain Summary
```
User: "Give me a comprehensive supply chain status"

Agent: (Uses get_supply_chain_summary tool)

Response: "Supply Chain Status for Nayara Energy (Oil Refining):

Suppliers:
- Total: 6 suppliers
- Active: 2 suppliers
- At Risk: 2 suppliers (risk score ≥ 3.0)

Alerts:
- Total: 5 alerts
- Active: 3 alerts
- Critical: 0
- High: 2

Recent Activity (7 days):
- Risk Events: 12
- Top Risk Types:
  1. Geopolitical (5 events)
  2. Financial (4 events)
  3. Operational (3 events)

Key Materials: crude oil, naphtha, LPG
Key Geographies: Russia, UAE, India, USA, Saudi Arabia"
```

## Testing the Agent

### 1. Test Agent Query via API
```bash
# Test critical alerts query
curl -X POST http://localhost:8000/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the current critical alerts?"
  }'

# Test with conversation history
curl -X POST http://localhost:8000/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What about high severity alerts?",
    "conversation_history": [
      {"role": "user", "content": "What are the current critical alerts?"},
      {"role": "assistant", "content": "There are 2 critical alerts..."}
    ]
  }'
```

### 2. Test Conversation Starters
```bash
curl http://localhost:8000/api/agent/starters
```

### 3. Generate Reports
```bash
# Generate daily report
curl -X POST http://localhost:8000/api/reports/generate \
  -H "Content-Type: application/json" \
  -d '{"type": "daily"}'

# Generate weekly report
curl -X POST http://localhost:8000/api/reports/generate \
  -H "Content-Type: application/json" \
  -d '{"type": "weekly"}'

# Generate custom report
curl -X POST http://localhost:8000/api/reports/generate \
  -H "Content-Type: application/json" \
  -d '{
    "type": "custom",
    "queries": [
      "What are the top 3 risk types this week?",
      "Which suppliers are at elevated risk?",
      "What are the best alternate suppliers for crude oil?"
    ]
  }'
```

### 4. Get Reports
```bash
# Get recent reports
curl http://localhost:8000/api/reports?report_type=daily&limit=5

# Get specific report
curl http://localhost:8000/api/reports/{report_id}
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        User Query                          │
│         "What are the current critical alerts?"            │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
                ┌──────────────────┐
                │  FastAPI Endpoint │
                │  /api/agent/query │
                └────────┬──────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  SupplyChainAgent     │
              │  (LangGraph ReAct)    │
              └──────────┬────────────┘
                         │
           ┌─────────────┴─────────────┐
           │    Gemini 1.5 Pro         │
           │    (Reasoning Engine)     │
           └─────────────┬─────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
  ┌──────────┐    ┌──────────┐    ┌──────────┐
  │  Tool 1  │    │  Tool 2  │    │  Tool 3  │
  │   Query  │    │  Get     │    │  Find    │
  │  Risks   │    │ Alerts   │    │Alternates│
  └────┬─────┘    └────┬─────┘    └────┬─────┘
       │               │               │
       └───────────────┼───────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │   MongoDB       │
              │   Collections:  │
              │   - risk_events │
              │   - alerts      │
              │   - suppliers   │
              │   - companies   │
              └─────────────────┘
```

## Benefits

1. **Natural Language Interface:** Users can ask questions in plain English
2. **Context-Aware:** Agent understands company profile and supply chain structure
3. **Tool Orchestration:** Automatically selects and combines appropriate tools
4. **Conversation Memory:** Maintains context across multiple queries
5. **Automated Reporting:** Daily and weekly reports generated automatically
6. **Flexible Analysis:** Custom reports support ad-hoc queries
7. **API-Driven:** All functionality accessible via REST API

## Integration Points

- **MongoDB:** Tools query all collections for data
- **Gemini Pro:** Powers reasoning and tool selection
- **Celery Beat:** Schedules automated report generation
- **FastAPI:** Exposes agent via REST endpoints
- **Frontend (Phase 3):** Will add chat UI component

## Next Steps (Phase 3 - Frontend)

1. Create chat page component
2. Message history display with streaming
3. Integration with /api/agent/query endpoint
4. Report viewer component
5. Export reports as PDF

---

**Phase 4 Complete:** AI Agent fully functional with 5 tools, automated reporting, and REST API integration.
