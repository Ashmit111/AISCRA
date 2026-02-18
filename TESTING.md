# Phase 2 Testing Guide

This guide walks you through testing the complete risk processing pipeline after Phase 2 implementation.

## Prerequisites

1. **Required API Keys** (set in `.env`):
   ```env
   GEMINI_API_KEY=your_key_here
   NEWSAPI_KEY=your_key_here
   SENDGRID_API_KEY=your_key_here  # Optional for email
   SLACK_WEBHOOK_URL=your_webhook_here  # Optional for Slack
   ```

2. **Docker & Docker Compose** installed

## Testing Steps

### Step 1: Start Services

```bash
# From project root
cd /home/ashmit/Downloads/aiscra

# Start all Docker services
docker-compose up -d

# Check services are running
docker-compose ps
```

Expected output:
```
NAME                  STATUS
aiscra-mongodb-1      Up (healthy)
aiscra-redis-1        Up (healthy)
aiscra-api-1          Up
aiscra-worker-1       Up
aiscra-beat-1         Up
```

### Step 2: Seed Database

```bash
# Populate MongoDB with Nayara Energy example data
docker-compose exec api python scripts/seed_data.py
```

Expected output:
```
✓ Seeded company: Nayara Energy
✓ Seeded 6 suppliers
Companies: 1
Suppliers: 6
```

Verify seeding:
```bash
# Check MongoDB
docker-compose exec mongodb mongosh supply_chain_risk --eval "db.companies.countDocuments()"
docker-compose exec mongodb mongosh supply_chain_risk --eval "db.suppliers.find({}, {name: 1, status: 1})"
```

### Step 3: Test News Ingestion

```bash
# Manually trigger news fetch
docker-compose exec worker celery -A src.ingestion.celery_app call src.ingestion.celery_app.fetch_all_sources
```

Expected behavior:
- NewsAPI fetches articles matching Nayara Energy keywords
- Articles normalized and deduplicated
- Pushed to `normalized_events` Redis stream

Verify ingestion:
```bash
# Check Redis stream
docker-compose exec redis redis-cli XLEN normalized_events

# Check articles in MongoDB
docker-compose exec mongodb mongosh supply_chain_risk --eval "db.articles.countDocuments()"
```

### Step 4: Test Risk Extraction Worker

The `process_risk_extraction_task` worker runs every 60 seconds via Celery Beat.

Monitor worker logs:
```bash
# Watch Celery worker logs
docker-compose logs -f worker
```

Expected log output:
```
[INFO] Consuming from normalized_events...
[INFO] Processing 5 events...
[INFO] Article relevance score: 0.72 (threshold: 0.3)
[INFO] Extracted risk: Financial risk affecting Rosneft
[INFO] Pushed to risk_entities stream
```

Verify extraction:
```bash
# Check risk_entities stream
docker-compose exec redis redis-cli XLEN risk_entities

# Check risk_events in MongoDB
docker-compose exec mongodb mongosh supply_chain_risk --eval "db.risk_events.find({}, {title: 1, risk_type: 1, risk_score: 1})"
```

### Step 5: Test Risk Scoring Worker

The `process_risk_scoring_task` worker consumes from `risk_entities` stream.

Expected behavior:
- Calculates risk score using formula: (Probability × Impact × Urgency) / Mitigation
- Risk score stored in MongoDB
- Pushed to `risk_scores` stream

Verify scoring:
```bash
# Check risk scores
docker-compose exec mongodb mongosh supply_chain_risk --eval "db.risk_events.find({risk_score: {\$gte: 3.0}}, {title: 1, risk_score: 1, severity_band: 1})"

# Check risk_scores stream
docker-compose exec redis redis-cli XLEN risk_scores
```

### Step 6: Test Alert Generation Worker

The `process_alerts_task` worker consumes from `risk_scores` stream.

Expected behavior:
- Builds supply chain graph (NetworkX)
- Propagates risk through supplier dependencies
- Creates alerts for risk_score ≥ 3.0
- Finds alternate suppliers (7-factor scoring)
- Generates recommendation text via Gemini
- Sends Slack/Email notifications
- Pushes to `new_alerts` stream

Monitor alert generation:
```bash
# Watch alert logs
docker-compose logs -f worker | grep "Alert created"
```

Verify alerts:
```bash
# Check alerts in MongoDB
docker-compose exec mongodb mongosh supply_chain_risk --eval "db.alerts.find({}, {title: 1, severity: 1, risk_score: 1, alternate_suppliers: 1})"

# Check new_alerts stream
docker-compose exec redis redis-cli XLEN new_alerts
```

Expected alert document:
```json
{
  "title": "High Risk: Geopolitical disruption affecting Rosneft",
  "severity": "high",
  "risk_score": 7.5,
  "affected_suppliers": ["Rosneft"],
  "affected_materials": ["crude oil"],
  "alternate_suppliers": [
    {
      "supplier_id": "supplier_saudi_aramco",
      "name": "Saudi Aramco",
      "score": 8.5,
      "reason": "High capacity, strong financial health"
    },
    // ... top 5
  ],
  "recommendation": "Immediate action required: Consider diversifying crude oil supply...",
  "notification_sent": true
}
```

### Step 7: Test REST API

```bash
# Dashboard summary
curl http://localhost:8000/api/dashboard/summary

# Get all alerts
curl http://localhost:8000/api/alerts

# Get specific alert
curl http://localhost:8000/api/alerts/{alert_id}

# Acknowledge alert
curl -X POST http://localhost:8000/api/alerts/{alert_id}/acknowledge

# Get suppliers
curl http://localhost:8000/api/suppliers

# Get supplier details
curl http://localhost:8000/api/suppliers/supplier_rosneft

# Get risk events
curl http://localhost:8000/api/risks
```

Expected `/api/dashboard/summary` response:
```json
{
  "summary": {
    "active_alerts": 3,
    "critical_alerts": 0,
    "high_alerts": 2,
    "medium_alerts": 1,
    "low_alerts": 0,
    "total_suppliers": 6,
    "active_suppliers": 2,
    "at_risk_suppliers": 2
  }
}
```

### Step 8: Test WebSocket Real-Time Updates

Using a WebSocket client (e.g., `wscat`):

```bash
# Install wscat
npm install -g wscat

# Connect to WebSocket
wscat -c ws://localhost:8000/ws/alerts
```

Expected behavior:
- When `process_alerts_task` creates a new alert, it pushes to `new_alerts` stream
- WebSocket broadcasts alert to all connected clients
- Client receives JSON alert object

Test by triggering news fetch while WebSocket is connected:
```bash
# In another terminal
docker-compose exec worker celery -A src.ingestion.celery_app call src.ingestion.celery_app.fetch_all_sources
```

### Step 9: Test Notifications

#### Slack Notifications
If `SLACK_WEBHOOK_URL` is configured:
1. Create alert (via Step 6)
2. Check Slack channel for rich formatted message with:
   - Severity emoji (🚨 critical, ⚠️ high, ⚡ medium, ℹ️ low)
   - Risk score, affected supplier, material
   - List of alternate suppliers
   - AI-generated recommendation

#### Email Notifications
If `SENDGRID_API_KEY` is configured:
1. Create alert
2. Check email inbox (addresses from `company.alert_contacts`)
3. Verify HTML email with:
   - Color-coded border (red=critical, orange=high, yellow=medium, green=low)
   - Alert details table
   - Alternate suppliers table
   - Recommendation section

### Step 10: End-to-End Flow Test

Test complete pipeline from news fetch → alert:

```bash
# 1. Trigger news fetch
docker-compose exec worker celery -A src.ingestion.celery_app call src.ingestion.celery_app.fetch_all_sources

# Wait 60-90 seconds (for workers to process)

# 2. Check each stage
echo "=== Articles ==="
docker-compose exec mongodb mongosh supply_chain_risk --eval "db.articles.countDocuments()"

echo "=== Risk Events ==="
docker-compose exec mongodb mongosh supply_chain_risk --eval "db.risk_events.countDocuments()"

echo "=== Alerts ==="
docker-compose exec mongodb mongosh supply_chain_risk --eval "db.alerts.countDocuments()"

# 3. View full alert pipeline
docker-compose logs worker --tail=100 | grep -E "(Consuming|Processing|Extracted|Scored|Alert created)"
```

## Troubleshooting

### No Articles Fetched
- Check `NEWSAPI_KEY` is valid
- Verify NewsAPI quota (free tier: 100 req/day)
- Check logs: `docker-compose logs api | grep newsapi`

### No Risk Extraction
- Verify `GEMINI_API_KEY` is valid
- Check Gemini API quota/rate limits
- Check relevance threshold: `NEWS_RELEVANCE_THRESHOLD=0.3` in `.env`
- View logs: `docker-compose logs worker | grep Gemini`

### No Alerts Generated
- Verify risk scores ≥ 3.0: `db.risk_events.find({risk_score: {$gte: 3.0}})`
- Check alert threshold: `ALERT_THRESHOLD=3.0` in `.env`
- Ensure supply chain graph is built: Check `db.suppliers.countDocuments()`

### Workers Not Running
```bash
# Check Celery worker status
docker-compose exec worker celery -A src.ingestion.celery_app inspect active

# Check Beat schedule
docker-compose exec beat celery -A src.ingestion.celery_app beat -l info

# Restart workers
docker-compose restart worker beat
```

### Redis Streams Stuck
```bash
# Check consumer groups
docker-compose exec redis redis-cli XINFO GROUPS normalized_events

# Delete and recreate consumer group
docker-compose exec redis redis-cli XGROUP DESTROY normalized_events risk_extraction_group
docker-compose restart worker
```

### MongoDB Connection Issues
```bash
# Check MongoDB status
docker-compose exec mongodb mongosh --eval "db.adminCommand({ping: 1})"

# View MongoDB logs
docker-compose logs mongodb --tail=50
```

## Performance Benchmarks

Expected processing times (for reference):

| Stage | Time | Notes |
|-------|------|-------|
| News fetch | 2-5s | Per API call |
| Article normalization | <100ms | Per article |
| Relevance filter | 200-400ms | Gemini embedding |
| Risk extraction | 2-4s | Gemini Flash |
| Risk scoring | <50ms | Formula calculation |
| Graph propagation | 100-300ms | BFS with 6 suppliers |
| Alert generation | 3-5s | Includes Gemini recommendation |
| Notification send | 500ms-1s | Slack + SendGrid |

## Success Criteria

Phase 2 is successfully implemented if:

- ✅ News articles fetched and normalized
- ✅ Relevance filtering reduces irrelevant articles
- ✅ Gemini extracts structured risk data
- ✅ Risk scores calculated correctly (see formula)
- ✅ Supply chain graph built from MongoDB
- ✅ Risk propagates through supply chain tiers
- ✅ Alerts created for risk_score ≥ 3.0
- ✅ Alternate suppliers ranked by 7-factor scoring
- ✅ Gemini generates natural language recommendations
- ✅ Notifications sent to Slack/Email
- ✅ WebSocket broadcasts new alerts
- ✅ REST API returns correct data
- ✅ All workers run without errors

## Next Steps

After validating Phase 2:

1. **Analyze Results**: Review generated alerts, check if recommendations are actionable
2. **Tune Thresholds**: Adjust `ALERT_THRESHOLD`, `NEWS_RELEVANCE_THRESHOLD` based on false positive rate
3. **Optimize Performance**: If processing is slow, increase worker count or batch sizes
4. **Phase 3 Prep**: Start frontend development (React dashboard)
5. **Phase 4 Prep**: Implement LangGraph AI agent for natural language queries

## Logs to Monitor

Key files/streams to watch:
- `/backend/src/risk_engine/workers.py` - Core worker logic
- `/backend/src/risk_engine/alert_generator.py` - Alert creation
- `/backend/src/recommender/supplier_finder.py` - Alternate supplier scoring
- `/backend/src/utils/notifications.py` - Slack/Email sending
- Redis streams: `normalized_events`, `risk_entities`, `risk_scores`, `new_alerts`
- MongoDB collections: `articles`, `risk_events`, `alerts`

---

**Testing Checklist:**
- [ ] Services started (Docker Compose)
- [ ] Database seeded (6 suppliers)
- [ ] News ingestion working
- [ ] Risk extraction working (Gemini)
- [ ] Risk scoring accurate
- [ ] Graph propagation working
- [ ] Alerts generated
- [ ] Alternate suppliers ranked
- [ ] Recommendations generated
- [ ] Notifications sent (Slack/Email)
- [ ] WebSocket broadcasting
- [ ] REST API endpoints responding
- [ ] End-to-end flow complete
