# Quick Start Guide
## Get the Supply Chain Risk Analysis System Running in 5 Minutes

### Prerequisites
- Docker and Docker Compose installed
- Google Gemini API key
- NewsAPI key

---

## Step 1: Get API Keys

### Google Gemini API Key
1. Go to https://makersuite.google.com/app/apikey
2. Sign in with Google account
3. Click "Create API Key"
4. Copy the key

### NewsAPI Key
1. Go to https://newsapi.org/register
2. Sign up for free account
3. Copy your API key from dashboard

---

## Step 2: Configure Environment

Edit the `.env` file in the `backend/` directory:

```bash
nano backend/.env
```

Add your API keys:
```env
GEMINI_API_KEY=your_actual_gemini_key_here
NEWSAPI_KEY=your_actual_newsapi_key_here
```

Save and exit (Ctrl+X, then Y, then Enter).

---

## Step 3: Start the System

```bash
docker-compose up -d
```

This will start 5 services:
- `mongodb` - Database
- `redis` - Message broker
- `api` - REST API server
- `worker` - Background task processor
- `beat` - Task scheduler

Wait ~30 seconds for all services to be healthy.

---

## Step 4: Seed the Database

```bash
docker-compose exec api python scripts/seed_data.py
```

You should see:
```
✓ Seeded company: Nayara Energy
✓ Seeded 6 suppliers
```

---

## Step 5: Verify Everything Works

### Check Health
```bash
curl http://localhost:8000/health
```

Should return:
```json
{
  "status": "healthy",
  "timestamp": "...",
  "database": "connected",
  "company": "company_nayara_energy"
}
```

### View API Documentation
Open in browser: http://localhost:8000/docs

### Get Dashboard Summary
```bash
curl http://localhost:8000/api/dashboard/summary
```

### List Suppliers
```bash
curl http://localhost:8000/api/suppliers
```

You should see Rosneft, ADNOC, Saudi Aramco, ONGC, BP, Shell.

---

## Step 6: Trigger News Fetch (Manual Test)

```bash
docker-compose exec worker celery -A src.ingestion.celery_app call src.ingestion.celery_app.fetch_all_sources
```

This will:
1. Fetch news from NewsAPI
2. Normalize and deduplicate articles
3. Push to Redis stream for processing

---

## Step 7: Monitor Activity

### Watch API Logs
```bash
docker-compose logs -f api
```

### Watch Worker Logs
```bash
docker-compose logs -f worker
```

### Watch All Logs
```bash
docker-compose logs -f
```

---

## Common Commands

### Stop All Services
```bash
docker-compose down
```

### Restart a Service
```bash
docker-compose restart api
docker-compose restart worker
```

### View Running Containers
```bash
docker-compose ps
```

### Access MongoDB Shell
```bash
docker-compose exec mongodb mongosh supply_risk_db
```

Inside mongosh:
```javascript
// Count articles
db.articles.countDocuments()

// View suppliers
db.suppliers.find().pretty()

// View company profile
db.companies.findOne()
```

### Access Redis CLI
```bash
docker-compose exec redis redis-cli
```

Inside redis-cli:
```
# Check stream length
XLEN normalized_events

# View stream content
XREAD COUNT 5 STREAMS normalized_events 0-0
```

---

## Testing the Full Pipeline

### 1. Fetch News
```bash
docker-compose exec worker celery -A src.ingestion.celery_app call src.ingestion.celery_app.fetch_all_sources
```

### 2. Check Articles Were Saved
```bash
docker-compose exec mongodb mongosh supply_risk_db --eval "db.articles.countDocuments()"
```

### 3. View Recent Articles
```bash
docker-compose exec mongodb mongosh supply_risk_db --eval "db.articles.find().limit(2).pretty()"
```

---

## Troubleshooting

### Error: "Cannot connect to MongoDB"
```bash
# Check MongoDB is running
docker-compose ps mongodb

# Restart MongoDB
docker-compose restart mongodb

# Check logs
docker-compose logs mongodb
```

### Error: "GEMINI_API_KEY not set"
```bash
# Verify .env file exists
cat backend/.env | grep GEMINI

# Restart API to reload env vars
docker-compose restart api worker
```

### Error: "NewsAPI rate limit"
NewsAPI free tier allows 100 requests/day. Space out your manual tests.

### Worker Not Processing Tasks
```bash
# Check worker is running
docker-compose ps worker

# Check worker logs
docker-compose logs worker

# Restart worker
docker-compose restart worker
```

---

## Next Steps

### Automatic News Fetching
By default, Celery Beat will fetch news every 15 minutes automatically. No manual intervention needed!

### Build Risk Processing
The system currently:
- ✅ Fetches and stores news articles
- ✅ Deduplicates articles
- ✅ Has Gemini risk extraction ready
- ✅ Has scoring and graph propagation ready
- ⏳ Needs worker implementation for risk extraction

To process articles through the full pipeline, workers need to be connected to consume from Redis streams and process through:
1. Relevance filtering
2. Gemini extraction
3. Risk scoring
4. Graph propagation
5. Alert generation

See `architecture.md` for the complete implementation plan.

---

## Production Deployment

For production use:

1. **Use MongoDB Atlas** (cloud MongoDB):
   - Create cluster at https://mongodb.com/atlas
   - Replace `MONGO_URI` in `.env`

2. **Use Redis Cloud**:
   - Sign up at https://redis.com/cloud
   - Replace `REDIS_URL` in `.env`

3. **Set Strong Secrets**:
   - Use proper CORS origins
   - Add authentication to API
   - Use HTTPS

4. **Scale Workers**:
   ```bash
   docker-compose up -d --scale worker=3
   ```

---

## Support

- Architecture: See `architecture.md`
- Implementation Plan: See `plan.md`
- API Docs: http://localhost:8000/docs (when running)

---

**Status**: ✅ Phase 1 Complete - Data ingestion operational  
**Next**: Phase 2 - Complete risk processing pipeline
