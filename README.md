# AI Supply Chain Risk Analysis System

> **Real-time supply chain risk monitoring using Multi-Agent AI architecture**

An intelligent system that monitors supply chain disruptions, quantifies risks, propagates impact through supply networks, and recommends mitigations using Google Gemini AI.

## 🎯 Features

- **Real-time News Ingestion**: Monitors news APIs for supply chain disruptions
- **AI Risk Extraction**: Uses Google Gemini to classify and extract risks
- **Graph-based Propagation**: Propagates risks through multi-tier supply chains using NetworkX
- **Alternate Supplier Recommendations**: Finds and ranks backup suppliers automatically
- **Multi-Agent AI System**: LangGraph agents for natural language queries
- **Live Dashboard**: Real-time WebSocket updates with interactive visualizations

## 📋 Prerequisites

- Docker & Docker Compose
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))
- NewsAPI key ([Get one here](https://newsapi.org/register))
- 4GB RAM minimum

## 🚀 Quick Start

### 1. Clone and Setup

```bash
cd aiscra
cp backend/.env.example backend/.env
```

### 2. Configure Environment

Edit `backend/.env` and add your API keys:

```env
GEMINI_API_KEY=your_gemini_api_key_here
NEWSAPI_KEY=your_newsapi_key_here
```

### 3. Start Services

```bash
docker-compose up -d
```

This will start:
- MongoDB (port 27017)
- Redis (port 6379)
- FastAPI API (port 8000)
- Celery Worker (background processing)
- Celery Beat (scheduler)

### 4. Seed Database

```bash
docker-compose exec api python scripts/seed_data.py
```

This creates example data for **Nayara Energy** with suppliers including Rosneft, ADNOC, and alternates.

### 5. Access Services

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Dashboard API**: http://localhost:8000/api/dashboard/summary

## 📁 Project Structure

```
aiscra/
├── backend/
│   ├── src/
│   │   ├── ingestion/        # News fetching & normalization
│   │   ├── risk_engine/      # Gemini extraction & scoring
│   │   ├── recommender/      # Alternate supplier finder
│   │   ├── agent/            # LangGraph AI agent
│   │   ├── api/              # FastAPI endpoints
│   │   ├── models/           # MongoDB schemas
│   │   └── utils/            # Config & utilities
│   ├── scripts/              # Seed data & utilities
│   └── requirements.txt
├── frontend/                 # (To be implemented)
├── docker-compose.yml
├── architecture.md
└── plan.md
```

## 🔧 API Endpoints

### Dashboard
- `GET /api/dashboard/summary` - Overview statistics

### Alerts
- `GET /api/alerts` - List all alerts
- `GET /api/alerts/{id}` - Get alert details
- `POST /api/alerts/{id}/acknowledge` - Acknowledge alert

### Suppliers
- `GET /api/suppliers` - List suppliers
- `GET /api/suppliers/{id}` - Supplier details

### Risk Events
- `GET /api/risks` - List risk events

### WebSocket
- `WS /ws/alerts` - Real-time alert stream

## 🧪 Testing the System

### 1. Trigger News Fetch

```bash
docker-compose exec worker celery -A src.ingestion.celery_app call src.ingestion.celery_app.fetch_all_sources
```

### 2. Check Logs

```bash
# API logs
docker-compose logs -f api

# Worker logs
docker-compose logs -f worker

# Beat (scheduler) logs
docker-compose logs -f beat
```

### 3. Query MongoDB

```bash
docker-compose exec mongodb mongosh supply_risk_db

# Inside mongosh:
db.articles.countDocuments()
db.risk_events.find().pretty()
db.alerts.find().pretty()
```

### 4. Check Redis Streams

```bash
docker-compose exec redis redis-cli

# Inside redis-cli:
XLEN normalized_events
XREAD COUNT 5 STREAMS normalized_events 0-0
```

## 🏗️ Architecture

### Data Flow

```
NewsAPI → Connector → Normalizer → Deduplicator → Redis Stream
   ↓
Gemini Risk Extraction (relevance filter → LLM)
   ↓
Risk Scoring (Probability × Impact × Urgency / Mitigation)
   ↓
Graph Propagation (NetworkX)
   ↓
Alert Generation → Alternate Supplier Recommendations
   ↓
Dashboard / AI Agent
```

### Tech Stack

- **Backend**: FastAPI, Celery, Redis Streams
- **Database**: MongoDB Atlas
- **AI**: Google Gemini (Flash + Pro)
- **Graph**: NetworkX
- **Agent**: LangGraph + LangChain

## 📊 Risk Scoring Formula

```
Risk Score = (Probability × Impact × Urgency) / Mitigation

Where:
- Probability: 0.0-1.0 (based on severity + confirmation)
- Impact: 1-10 (dependency × criticality × buffer)
- Urgency: 0.5-2.0 (time horizon multiplier)
- Mitigation: 0.5-2.0 (alternate supplier availability)

Severity Bands:
- Critical: ≥ 10.0
- High: 6.0-9.9
- Medium: 3.0-5.9
- Low: < 3.0
```

## 🔍 Monitoring & Debugging

### View Container Status
```bash
docker-compose ps
```

### Restart a Service
```bash
docker-compose restart api
docker-compose restart worker
```

### View Real-time Logs
```bash
docker-compose logs -f --tail=100 api worker
```

### Execute Commands in Container
```bash
# Python shell
docker-compose exec api python

# Bash shell
docker-compose exec api bash
```

## 🛠️ Development

### Install Dependencies Locally (Optional)
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Run API Locally
```bash
cd backend
uvicorn src.api.main:app --reload
```

### Run Worker Locally
```bash
cd backend
celery -A src.ingestion.celery_app worker --loglevel=info
```

## 📝 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | **Required** |
| `NEWSAPI_KEY` | NewsAPI.org API key | **Required** |
| `MONGO_URI` | MongoDB connection string | `mongodb://localhost:27017` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `NEWS_FETCH_INTERVAL_MINUTES` | News fetch frequency | `15` |
| `NEWS_RELEVANCE_THRESHOLD` | Relevance filter threshold | `0.3` |
| `ALERT_THRESHOLD_SCORE` | Minimum score for alerts | `3.0` |

## 🚧 Roadmap

### Phase 1: Foundation ✅ (Current)
- [x] Data ingestion from NewsAPI
- [x] Gemini risk extraction
- [x] Risk scoring engine
- [x] Graph propagation
- [x] FastAPI backend
- [x] Docker setup

### Phase 2: Risk Engine (Next)
- [ ] Alert generation system
- [ ] Alternate supplier recommender
- [ ] Email/Slack notifications
- [ ] Risk propagation workers

### Phase 3: Dashboard
- [ ] React frontend
- [ ] Cytoscape.js supply chain graph
- [ ] Real-time WebSocket updates
- [ ] Interactive risk visualization

### Phase 4: AI Agent
- [ ] LangGraph multi-agent system
- [ ] Conversational interface
- [ ] Auto daily reports
- [ ] Advanced analytics

## 🐛 Troubleshooting

### MongoDB Connection Failed
```bash
docker-compose restart mongodb
docker-compose logs mongodb
```

### Redis Connection Failed
```bash
docker-compose restart redis
redis-cli ping
```

### Worker Not Processing Tasks
```bash
docker-compose logs worker
# Check Celery broker connection
docker-compose exec redis redis-cli PING
```

### API Returns 500 Error
```bash
docker-compose logs api
# Check MongoDB is accessible
docker-compose exec api python -c "from src.models.db import db_manager; db_manager.connect(); print('OK')"
```

## 📚 Documentation

- [Architecture Guide](architecture.md) - Detailed system design
- [Implementation Plan](plan.md) - Development roadmap
- [API Documentation](http://localhost:8000/docs) - Interactive API docs (when running)

## 🤝 Contributing

This is an educational/demonstration project. Feel free to fork and customize for your needs.

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- Google Gemini AI for risk extraction
- NewsAPI.org for news data
- MongoDB, Redis, FastAPI communities

---

**Status**: Phase 1 Complete | **Next**: Phase 2 Implementation  
**Last Updated**: February 2026
