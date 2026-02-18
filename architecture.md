# AI-Powered Supply Chain Risk Analysis System
## Architecture & Implementation Guide

> **Project Type:** Company-centric, real-time supply chain risk monitoring using Multi-Agent AI architecture
> **Core Goal:** Detect disruptions, quantify risk, propagate impact, and recommend mitigations — as fast as possible.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Module 1 — Data Ingestion Layer](#3-module-1--data-ingestion-layer)
4. [Module 2 — Data Processing & Risk Engine](#4-module-2--data-processing--risk-engine)
5. [Module 3 — Alternate Supplier Recommender](#5-module-3--alternate-supplier-recommender)
6. [Module 4 — AI Agent & Report Generator](#6-module-4--ai-agent--report-generator)
7. [Database Design (MongoDB)](#7-database-design-mongodb)
8. [Multi-Agent Architecture Design](#8-multi-agent-architecture-design)
9. [Frontend Dashboard](#9-frontend-dashboard)
10. [Tech Stack Summary](#10-tech-stack-summary)
11. [Implementation Roadmap](#11-implementation-roadmap)
12. [Data Flow — End to End Example](#12-data-flow--end-to-end-example)

---

## 1. System Overview

This system monitors a **single company's** entire supply chain in real time. It ingests news, financial signals, and geopolitical data, analyzes them for risks, scores and propagates those risks through the supply graph, recommends alternatives, and delivers everything to decision makers via a dashboard and AI agent.

### Key Design Principles
- **Real-time first** — risks must surface within minutes of a news event
- **Graph-aware** — risk is not isolated; a Tier-2 supplier failure can cascade to you
- **Explainable** — every alert must be traceable: "Why is this a risk to ME?"
- **Actionable** — every alert comes with a mitigation recommendation

---

## 2. High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                                 │
│  ┌──────────────────────┐   ┌───────────────────────────────────┐   │
│  │ Internal: ERP, CRM,  │   │ External: News APIs, Financial    │   │
│  │ Supplier DB, Contracts│   │ Reports, ESG Ratings, Social Media│   │
│  └──────────┬───────────┘   └──────────────┬────────────────────┘   │
└─────────────┼────────────────────────────────┼────────────────────────┘
              │                                │
              ▼                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    MODULE 1: DATA INGESTION LAYER                    │
│   Redis Streams │ Scrapers │ API Connectors │ Normalizer │ Deduper   │
└────────────────────────────────┬────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                MODULE 2: PROCESSING & RISK ENGINE                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │ Gemini LLM Risk  │  │  Risk Scoring    │  │  Risk Propagation│  │
│  │ Extraction &     │  │  (Prob × Impact) │  │  (Graph Algo)    │  │
│  │ Classification   │  │                  │  │                  │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
└────────────────────────────────┬────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│           KNOWLEDGE BASE — MongoDB Atlas (Single Cluster)            │
│   supply_graph │ risk_events │ suppliers │ alerts │ articles         │
└────────────────────────────────┬────────────────────────────────────┘
                                  │
              ┌───────────────────┼────────────────────┐
              ▼                   ▼                     ▼
┌─────────────────┐  ┌────────────────────┐  ┌────────────────────────┐
│  MODULE 3       │  │   MODULE 4         │  │  DASHBOARD             │
│  Alternate      │  │   Gemini Agent     │  │  Real-time Alerts      │
│  Supplier Finder│  │   Report Generator │  │  Graph Viz             │
└─────────────────┘  └────────────────────┘  └────────────────────────┘
              │                   │                     │
              └───────────────────┼─────────────────────┘
                                  ▼
                         DECISION MAKERS
```

---

## 3. Module 1 — Data Ingestion Layer

### What It Does
Pulls data from many sources on a schedule, normalizes it, deduplicates it, and pushes it onto a **Redis Stream** for the risk engine to consume.

### Data Sources to Connect

| Source Type | Examples | How to Connect |
|---|---|---|
| News APIs | NewsAPI, GDELT, GNews | REST API polling (every 10–15 min) |
| Social Media | Twitter/X (breaking news signals) | Streaming API |
| Financial Data | Yahoo Finance, Alpha Vantage | REST API |
| ESG Ratings | Sustainalytics, MSCI | API or periodic CSV import |
| Internal ERP | SAP, Oracle, custom | MongoDB import / REST connector |
| Regulatory Feeds | US Federal Register, EU sanction lists | RSS / scraping |

### Architecture — Redis Streams as the Queue

Instead of Kafka, we use **Redis Streams** — simpler to set up, runs in the same Redis instance you're already using for caching, and handles the throughput of a news ingestion system easily.

```
News APIs ──────┐
Social Media ───┤──► Celery Beat (scheduler) ──► Connectors ──► XADD to Redis Stream "raw_events"
ERP / Internal ─┤                                                        │
Financial APIs ─┘                                                        │
                                                                         ▼
                                                          Celery Workers read stream
                                                          → Normalize → Deduplicate
                                                          → XADD to Redis Stream "normalized_events"
                                                                         │
                                                                         ▼
                                                          Risk Engine Workers consume
```

### How to Implement

**Step 1 — Build individual connectors** (one Python class per source)
```python
import requests
from datetime import datetime

class NewsAPIConnector:
    def __init__(self, api_key: str, company_profile: dict):
        self.api_key = api_key
        self.keywords = self._build_keywords(company_profile)

    def _build_keywords(self, profile: dict) -> list[str]:
        # Auto-build from supplier names, raw materials, geographies
        keywords = [profile["company_name"]]
        keywords += [s["name"] for s in profile["suppliers"]]
        keywords += profile["raw_materials"]
        keywords += profile["key_geographies"]
        return keywords

    def fetch(self) -> list[dict]:
        query = " OR ".join(self.keywords[:5])  # NewsAPI limits query length
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={"q": query, "sortBy": "publishedAt", "apiKey": self.api_key}
        )
        return resp.json().get("articles", [])
```

**Step 2 — Company Profile** (stored in MongoDB, drives all relevance filtering)
```json
{
  "_id": "company_nayara_energy",
  "company_name": "Nayara Energy",
  "industry": "Oil Refining",
  "suppliers": [
    {
      "name": "Rosneft",
      "country": "Russia",
      "supplies": ["crude oil"],
      "tier": 1,
      "supply_volume_pct": 65,
      "contract_end": "2026-12-31"
    },
    {
      "name": "ADNOC",
      "country": "UAE",
      "supplies": ["crude oil"],
      "tier": 1,
      "supply_volume_pct": 35
    }
  ],
  "raw_materials": ["crude oil", "naphtha", "LPG"],
  "key_geographies": ["Russia", "UAE", "India", "USA"],
  "dependencies": ["US dollar exchange rate", "India import policy", "OPEC decisions"],
  "inventory_days": {
    "crude oil": 15,
    "naphtha": 7
  },
  "material_criticality": {
    "crude oil": 10,
    "naphtha": 6
  }
}
```

**Step 3 — Normalizer** — convert all sources to one standard schema
```python
def normalize_newsapi_article(raw: dict) -> dict:
    return {
        "event_id": generate_uuid(),
        "timestamp": raw["publishedAt"],
        "source": "NewsAPI",
        "headline": raw["title"],
        "body": raw.get("content") or raw.get("description", ""),
        "url": raw["url"],
        "entities_mentioned": [],   # filled by NER in Module 2
        "raw_relevance_score": 0.0, # filled by relevance filter
        "processed": False
    }
```

**Step 4 — Deduplication using Redis**
```python
import redis
import hashlib

r = redis.Redis()

def is_duplicate(article: dict) -> bool:
    # Hash the headline (normalized) as a fingerprint
    fingerprint = hashlib.md5(article["headline"].lower().strip().encode()).hexdigest()
    key = f"dedup:{fingerprint}"
    # SET NX (only set if not exists), expire after 48 hours
    if r.set(key, 1, nx=True, ex=172800):
        return False  # Not a duplicate — we just set it
    return True       # Already seen this
```

**Step 5 — Push to Redis Stream**
```python
def push_to_stream(r: redis.Redis, event: dict):
    # XADD adds a new entry to the stream
    r.xadd("normalized_events", event)

# Worker reading from stream
def consume_stream(r: redis.Redis, last_id="$"):
    while True:
        # XREAD blocks for up to 5 seconds waiting for new messages
        messages = r.xread({"normalized_events": last_id}, block=5000, count=10)
        for stream, entries in (messages or []):
            for entry_id, data in entries:
                process_event(data)
                last_id = entry_id
```

### Celery Setup for Scheduling

```python
# celery_app.py
from celery import Celery
from celery.schedules import crontab

app = Celery("ingestion", broker="redis://localhost:6379/0")

app.conf.beat_schedule = {
    "fetch-news-every-15-min": {
        "task": "tasks.fetch_all_sources",
        "schedule": crontab(minute="*/15"),
    },
}

@app.task
def fetch_all_sources():
    connectors = [NewsAPIConnector(...), GDELTConnector(...)]
    for connector in connectors:
        articles = connector.fetch()
        for article in articles:
            normalized = normalize(article)
            if not is_duplicate(normalized):
                push_to_stream(redis_client, normalized)
```

### Technologies for Module 1
- **Queue:** Redis Streams (`XADD` / `XREAD`)
- **Scheduler:** Celery Beat + Redis as broker
- **Connectors:** Python `requests`, `feedparser` (for RSS), `playwright` (for scraping)
- **Dedup:** Redis `SET NX` with TTL

---

## 4. Module 2 — Data Processing & Risk Engine

This is the most technically complex module. It has three parallel sub-systems that run as Celery workers consuming from `normalized_events`.

### 4a. Gemini LLM Risk Extraction & Classification

**What it does:** Takes a normalized article, determines if it is a risk, and extracts structured risk data.

**Flow:**
```
normalized_events stream
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  RELEVANCE FILTER (fast, cheap — runs first)             │
│  Keyword match + embedding cosine similarity             │
│  against company profile keywords                        │
│  → Skip if score < 0.3 (irrelevant news)                │
└─────────────────────────┬───────────────────────────────┘
                          │ (relevant only)
                          ▼
┌─────────────────────────────────────────────────────────┐
│  GEMINI RISK EXTRACTION                                  │
│  Model: gemini-1.5-flash (fast + cheap for extraction)  │
│  or gemini-1.5-pro (for complex geopolitical articles)  │
│  → Structured JSON output via response_schema           │
└─────────────────────────┬───────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────┐
│  SUPPLY CHAIN LINKER                                     │
│  Match extracted entities → MongoDB supplier docs        │
│  "crude oil" + "Russia" → Rosneft → Tier-1 Supplier     │
└─────────────────────────────────────────────────────────┘
```

**Risk Types to Classify:**

| Category | Examples |
|---|---|
| Geopolitical | Sanctions, trade wars, political instability |
| Natural Disaster | Earthquakes, floods, wildfires, pandemics |
| Financial | Bankruptcy, credit downgrade, currency collapse |
| Regulatory | Export bans, tariffs, compliance failures |
| Operational | Factory fire, port closure, labor strike |
| Cybersecurity | Supplier data breach, ransomware attack |
| ESG / Reputational | Human rights violations, environmental damage |

**Gemini API Integration:**
```python
import google.generativeai as genai
import json

genai.configure(api_key="YOUR_GEMINI_API_KEY")

# Use Flash for speed/cost, Pro for complex analysis
model_flash = genai.GenerativeModel("gemini-1.5-flash")
model_pro   = genai.GenerativeModel("gemini-1.5-pro")

EXTRACTION_PROMPT = """
You are a supply chain risk analyst for {company_name}.

Company's key suppliers: {supplier_list}
Company's raw materials: {materials_list}
Key geographies: {geographies}

Analyze the following news article and return a JSON object ONLY (no explanation):

Article:
{article_text}

JSON schema to follow:
{{
  "is_risk": true or false,
  "risk_type": "geopolitical | natural_disaster | financial | regulatory | operational | cybersecurity | esg",
  "affected_entities": ["list of companies, countries, or materials mentioned"],
  "affected_supply_chain_nodes": ["names matching our supplier list exactly"],
  "severity": "critical | high | medium | low",
  "is_confirmed": true or false or "uncertain",
  "time_horizon": "immediate | days | weeks | months",
  "reasoning": "one sentence explaining the link to our supply chain",
  "recommended_action": "one sentence immediate action"
}}
"""

def extract_risk(article: dict, company_profile: dict) -> dict:
    prompt = EXTRACTION_PROMPT.format(
        company_name=company_profile["company_name"],
        supplier_list=", ".join(s["name"] for s in company_profile["suppliers"]),
        materials_list=", ".join(company_profile["raw_materials"]),
        geographies=", ".join(company_profile["key_geographies"]),
        article_text=article["headline"] + "\n\n" + article["body"]
    )

    # Use Flash by default; upgrade to Pro for geopolitical/complex events
    response = model_flash.generate_content(prompt)
    text = response.text.strip()

    # Strip markdown code fences if Gemini wraps the JSON
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]

    return json.loads(text.strip())
```

**Using Gemini's Native JSON Mode (recommended for production):**
```python
import google.generativeai as genai
from google.generativeai.types import GenerationConfig

response = model_flash.generate_content(
    prompt,
    generation_config=GenerationConfig(
        response_mime_type="application/json"
    )
)
# response.text is guaranteed to be valid JSON
risk_data = json.loads(response.text)
```

**Gemini Embeddings for Relevance Filtering:**
```python
def get_embedding(text: str) -> list[float]:
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="SEMANTIC_SIMILARITY"
    )
    return result["embedding"]

def relevance_score(article_text: str, company_keywords: list[str]) -> float:
    article_emb = get_embedding(article_text)
    keyword_emb = get_embedding(" ".join(company_keywords))
    # Cosine similarity
    dot = sum(a * b for a, b in zip(article_emb, keyword_emb))
    mag_a = sum(a**2 for a in article_emb) ** 0.5
    mag_b = sum(b**2 for b in keyword_emb) ** 0.5
    return dot / (mag_a * mag_b)
```

---

### 4b. Risk Scoring (Probability × Impact)

**Formula:**
```
Risk Score = (Probability × Impact × Urgency) / Mitigation_Availability

Where:
- Probability:              0.0 – 1.0  (how likely is disruption given this news?)
- Impact:                   1 – 10     (how badly does this affect the company?)
- Urgency:                  0.5 – 2.0  (multiplier: is this immediate or weeks away?)
- Mitigation_Availability:  0.5 – 2.0  (can we easily switch suppliers?)
```

**Scoring Implementation:**
```python
def calculate_risk_score(risk_data: dict, supplier: dict, company_profile: dict) -> dict:

    # --- Probability ---
    prob_map = {
        "critical": 0.95, "high": 0.80, "medium": 0.55, "low": 0.25
    }
    probability = prob_map[risk_data["severity"]]
    if risk_data["is_confirmed"] == "uncertain":
        probability *= 0.7

    # --- Impact ---
    # How much of our supply of this material comes from this supplier?
    dependency_ratio = supplier["supply_volume_pct"] / 100.0

    # How critical is this material to operations?
    material = supplier["supplies"][0]
    material_criticality = company_profile["material_criticality"].get(material, 5)

    # How long can we survive without this supplier?
    inventory_days = company_profile["inventory_days"].get(material, 0)
    buffer_score = 1.0 / (1.0 + inventory_days / 30.0)

    impact = dependency_ratio * (material_criticality / 10.0) * buffer_score * 10

    # --- Urgency ---
    urgency_map = {"immediate": 2.0, "days": 1.5, "weeks": 1.0, "months": 0.5}
    urgency = urgency_map.get(risk_data.get("time_horizon", "weeks"), 1.0)

    # --- Mitigation ---
    # Count available pre-qualified alternate suppliers
    num_alternates = count_alternate_suppliers(material, company_profile)
    mitigation = 1.0 + min(num_alternates * 0.2, 1.0)  # max 2.0

    score = (probability * impact * urgency) / mitigation

    return {
        "risk_score": round(score, 2),
        "components": {
            "probability": probability,
            "impact": round(impact, 2),
            "urgency": urgency,
            "mitigation": mitigation
        },
        "severity_band": score_to_band(score)
    }

def score_to_band(score: float) -> str:
    if score >= 10:  return "critical"
    if score >= 6:   return "high"
    if score >= 3:   return "medium"
    return "low"
```

---

### 4c. Risk Propagation (Graph Algorithms)

**The Supply Chain as a Directed Graph stored in MongoDB:**

Each supplier document contains its upstream dependencies, allowing us to build and traverse the graph using NetworkX in Python — no separate graph database needed.

```
Your Company ◄── Tier-1 Supplier A ◄── Tier-2 Supplier X
                                    ◄── Tier-2 Supplier Y
             ◄── Tier-1 Supplier B ◄── Tier-2 Supplier Z
```

**Building the Graph from MongoDB:**
```python
import networkx as nx
from pymongo import MongoClient

def build_supply_graph(db) -> nx.DiGraph:
    G = nx.DiGraph()

    # Add company node
    company = db.companies.find_one({})
    G.add_node(company["_id"], type="company", name=company["company_name"])

    # Add supplier nodes and edges
    for supplier in db.suppliers.find({"company_id": company["_id"]}):
        G.add_node(supplier["_id"], type="supplier", **supplier)
        G.add_edge(
            supplier["_id"],
            company["_id"],
            weight=supplier["supply_volume_pct"] / 100.0,
            material=supplier["supplies"][0]
        )

        # Add Tier-2 upstream suppliers
        for upstream in supplier.get("upstream_suppliers", []):
            G.add_node(upstream["_id"], type="supplier", **upstream)
            G.add_edge(
                upstream["_id"],
                supplier["_id"],
                weight=upstream["supply_volume_pct"] / 100.0
            )

    return G
```

**Risk Propagation Algorithm:**
```python
def propagate_risk(G: nx.DiGraph, risk_node_id: str, initial_score: float) -> dict:
    """
    Propagate risk backward through the supply chain.
    risk_node_id: the supplier/country node where the risk originates
    Returns: dict mapping node_id -> propagated risk score
    """
    propagated = {risk_node_id: initial_score}
    queue = [(risk_node_id, initial_score)]
    THRESHOLD = 1.0  # Don't propagate negligible risk

    while queue:
        node, score = queue.pop(0)
        # Who depends on this node? (predecessors in directed graph)
        for successor in G.successors(node):
            edge = G[node][successor]
            dep_weight = edge.get("weight", 0.5)

            # Vulnerability: nodes with fewer alternates are more vulnerable
            node_data = G.nodes[successor]
            vulnerability = 1.0 - node_data.get("mitigation_score", 0.5)

            propagated_score = score * dep_weight * (0.5 + vulnerability)

            if propagated_score > THRESHOLD:
                if successor not in propagated or propagated[successor] < propagated_score:
                    propagated[successor] = round(propagated_score, 2)
                    queue.append((successor, propagated_score))

    return propagated

# Key graph analysis functions to run periodically
def find_critical_nodes(G: nx.DiGraph) -> list:
    """Find single-points-of-failure (high betweenness centrality)"""
    bc = nx.betweenness_centrality(G, weight="weight")
    return sorted(bc.items(), key=lambda x: x[1], reverse=True)[:5]

def find_vulnerable_paths(G: nx.DiGraph, company_node: str) -> list:
    """Find all paths to company and their cumulative risk"""
    all_paths = []
    for node in G.nodes:
        if node != company_node:
            try:
                path = nx.shortest_path(G, node, company_node, weight="weight")
                all_paths.append(path)
            except nx.NetworkXNoPath:
                pass
    return all_paths
```

### Technologies for Module 2
- **LLM:** Google Gemini API (`gemini-1.5-flash` for extraction, `gemini-1.5-pro` for deep analysis)
- **Embeddings:** Gemini `text-embedding-004`
- **Graph:** NetworkX (in-memory graph built from MongoDB)
- **Workers:** Celery consuming from Redis Stream `normalized_events`

---

## 5. Module 3 — Alternate Supplier Recommender

### What It Does
When a Tier-1 or Tier-2 supplier is flagged as disrupted, this module finds and ranks alternatives.

### Recommendation Flow

```
Risk Alert: Supplier X disrupted
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│  REQUIREMENT EXTRACTION                                              │
│  - What material is at risk? (from risk_event)                       │
│  - What volume is needed? (from supplier doc)                        │
│  - What are the quality specs? (from company profile)                │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  CANDIDATE GENERATION (MongoDB queries)                              │
│  - db.suppliers.find({ supplies: material, status: "alternate" })   │
│  - Also query by similar geography / industry cluster               │
│  - Use Gemini embeddings for semantic similarity search              │
│    (MongoDB Atlas Vector Search on supplier descriptions)            │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  RANKING — Weighted multi-factor score                               │
│  Factors: geo diversity, capacity, relationship, ESG, financial,    │
│  switching cost, lead time                                           │
└─────────────────────────────────────────────────────────────────────┘
```

**Scoring Implementation:**
```python
def score_alternate_supplier(
    candidate: dict,
    disrupted: dict,
    required_volume: float
) -> dict:

    # Geographic diversity (prefer different country/region from disrupted)
    geo_score = 1.0 if candidate["country"] != disrupted["country"] else 0.3

    # Capacity coverage
    cap_score = min(candidate.get("max_capacity", 0) / required_volume, 1.0)

    # Existing relationship
    rel_score = 1.0 if candidate.get("approved_vendor") else 0.4
    if candidate.get("pre_qualified"): rel_score = 0.8

    # ESG (normalize 0–100 rating to 0–1)
    esg_score = candidate.get("esg_score", 50) / 100.0

    # Financial stability (normalize credit rating)
    fin_score = credit_rating_to_score(candidate.get("credit_rating", "BBB"))

    # Switching cost (lower is better — invert)
    switch_score = 1.0 - (candidate.get("switching_cost_estimate", 5) / 10.0)

    # Lead time score (faster = better — invert)
    lead_time_weeks = candidate.get("lead_time_weeks", 8)
    lead_score = 1.0 / (1.0 + lead_time_weeks / 4.0)

    final_score = (
        geo_score   * 0.20 +
        cap_score   * 0.25 +
        rel_score   * 0.20 +
        esg_score   * 0.10 +
        fin_score   * 0.10 +
        switch_score* 0.05 +
        lead_score  * 0.10
    ) * 10  # scale to 0–10

    return {
        "supplier_id": candidate["_id"],
        "name": candidate["name"],
        "score": round(final_score, 2),
        "lead_time_weeks": lead_time_weeks,
        "approved_vendor": candidate.get("approved_vendor", False),
        "country": candidate["country"],
        "score_breakdown": {
            "geographic_diversity": geo_score,
            "capacity": cap_score,
            "relationship": rel_score,
            "esg": esg_score,
            "financial": fin_score,
        }
    }

def find_alternates(disrupted_supplier_id: str, db) -> list[dict]:
    disrupted = db.suppliers.find_one({"_id": disrupted_supplier_id})
    material = disrupted["supplies"][0]
    required_volume = disrupted["supply_volume_pct"]

    candidates = list(db.suppliers.find({
        "supplies": material,
        "_id": {"$ne": disrupted_supplier_id},
        "status": {"$in": ["active", "alternate", "pre_qualified"]}
    }))

    scored = [score_alternate_supplier(c, disrupted, required_volume) for c in candidates]
    return sorted(scored, key=lambda x: x["score"], reverse=True)[:5]
```

**Use Gemini to Generate Reasoning:**
```python
def generate_recommendation_text(alert: dict, alternates: list, company_profile: dict) -> str:
    prompt = f"""
    You are a supply chain advisor for {company_profile['company_name']}.

    ALERT: {alert['description']}
    Risk Score: {alert['risk_score']} ({alert['severity_band'].upper()})

    Top alternate suppliers identified:
    {json.dumps(alternates[:3], indent=2)}

    Write a concise (3–4 sentences) recommendation for the supply chain manager.
    Include: urgency, top recommendation, and why. No bullet points.
    """
    response = model_flash.generate_content(prompt)
    return response.text
```

---

## 6. Module 4 — AI Agent & Report Generator

### What It Does
A multi-agent system that:
1. Answers natural language questions from supply chain managers
2. Generates automatic risk reports (daily, weekly, or on-demand)
3. Proactively pushes recommendations when critical events occur

### Agent Architecture (LangGraph)

```
User Query / Scheduled Trigger / New Critical Alert
                      │
                      ▼
          ┌─────────────────────────┐
          │   ORCHESTRATOR AGENT    │
          │   (Gemini 1.5 Pro)      │
          │   Plans which sub-agents│
          │   to invoke and in what │
          │   order                 │
          └──────┬──────────────────┘
                 │
    ┌────────────┼──────────────────────────────┐
    ▼            ▼                ▼              ▼
┌────────┐ ┌───────────────┐ ┌──────────┐ ┌───────────────┐
│ Search │ │ Risk Analysis │ │Supplier  │ │    Report     │
│ Agent  │ │ Agent         │ │Rec Agent │ │    Agent      │
│        │ │               │ │          │ │               │
│Queries │ │Queries MongoDB│ │Calls     │ │Generates      │
│MongoDB │ │risk_events,   │ │find_     │ │structured     │
│articles│ │runs graph     │ │alternates│ │summary from   │
│        │ │analysis       │ │()        │ │all agent data │
└────────┘ └───────────────┘ └──────────┘ └───────────────┘
                            │
                  ┌─────────▼──────────┐
                  │  RESPONSE SYNTH    │
                  │  (Gemini 1.5 Flash)│
                  │  Combines outputs  │
                  │  into final answer │
                  └────────────────────┘
```

### Agent Tools

```python
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
from langgraph.graph import StateGraph
from pymongo import MongoClient

db = MongoClient()["supply_risk_db"]

@tool
def query_risk_events(entity: str, time_range_days: int = 7) -> list:
    """Get recent risk events affecting a supplier, country, or material."""
    from datetime import datetime, timedelta
    since = datetime.utcnow() - timedelta(days=time_range_days)
    results = db.risk_events.find({
        "$or": [
            {"affected_supply_chain_nodes": {"$regex": entity, "$options": "i"}},
            {"affected_entities": {"$regex": entity, "$options": "i"}}
        ],
        "timestamp": {"$gte": since}
    }).sort("risk_score", -1).limit(10)
    return list(results)

@tool
def get_active_alerts(severity: str = "all") -> list:
    """Get currently active risk alerts, optionally filtered by severity."""
    query = {"is_acknowledged": False}
    if severity != "all":
        query["severity_band"] = severity
    return list(db.alerts.find(query).sort("created_at", -1).limit(20))

@tool
def find_alternate_suppliers(material: str, disrupted_supplier_name: str) -> list:
    """Find ranked alternate suppliers for a given material."""
    disrupted = db.suppliers.find_one({"name": disrupted_supplier_name})
    if not disrupted:
        return []
    return find_alternates(disrupted["_id"], db)

@tool
def get_supply_chain_summary() -> dict:
    """Get a summary of the company's supply chain structure."""
    company = db.companies.find_one({})
    suppliers = list(db.suppliers.find({"tier": 1}))
    critical_nodes = db.suppliers.find({"is_single_source": True})
    return {
        "company": company["company_name"],
        "tier1_supplier_count": len(suppliers),
        "single_source_materials": [s["supplies"] for s in critical_nodes],
        "active_alert_count": db.alerts.count_documents({"is_acknowledged": False})
    }

@tool
def get_risk_trend(days: int = 30) -> dict:
    """Get risk score trend over the past N days."""
    from datetime import datetime, timedelta
    since = datetime.utcnow() - timedelta(days=days)
    pipeline = [
        {"$match": {"created_at": {"$gte": since}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "avg_score": {"$avg": "$risk_score"},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    return list(db.alerts.aggregate(pipeline))
```

**LangGraph Agent Setup:**
```python
from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0)

tools = [
    query_risk_events,
    get_active_alerts,
    find_alternate_suppliers,
    get_supply_chain_summary,
    get_risk_trend
]

agent = create_react_agent(llm, tools)

# Example usage
response = agent.invoke({
    "messages": [("user", "What are our top 3 risks this week and what should we do?")]
})
print(response["messages"][-1].content)
```

### Auto-Report Generation (Celery Beat, daily at 8am)

```python
@app.task
def generate_daily_report():
    prompt = """
    Generate a daily supply chain risk report for the supply chain team.
    Use the available tools to gather: active alerts, top risk events from last 24h,
    any new critical suppliers at risk, and top recommendations.
    Format as: Executive Summary | Active Risks Table | Recommendations.
    """
    response = agent.invoke({"messages": [("user", prompt)]})
    report_text = response["messages"][-1].content

    # Save to MongoDB
    db.reports.insert_one({
        "type": "daily",
        "content": report_text,
        "generated_at": datetime.utcnow()
    })

    # Send via email / Slack
    send_slack_message(report_text)
```

---

## 7. Database Design (MongoDB)

### Why MongoDB for This Project
MongoDB is a great fit here because:
- Supply chain data is hierarchical and nested (suppliers have sub-suppliers, events have arrays of affected entities) — maps naturally to documents
- Schema-free means you can add new risk types, fields, or supplier attributes without migrations
- MongoDB Atlas offers built-in Vector Search (for semantic article/supplier search) — no separate vector DB needed
- Aggregation pipeline handles the analytics queries you need

### Collections

**`companies`** — The company being monitored
```json
{
  "_id": "ObjectId",
  "company_name": "Nayara Energy",
  "industry": "Oil Refining",
  "raw_materials": ["crude oil", "naphtha"],
  "key_geographies": ["Russia", "UAE", "India"],
  "inventory_days": { "crude oil": 15, "naphtha": 7 },
  "material_criticality": { "crude oil": 10, "naphtha": 6 },
  "alert_contacts": [
    { "name": "John Doe", "email": "john@company.com", "role": "Supply Chain Manager" }
  ]
}
```

**`suppliers`** — All suppliers (Tier 1, 2, and alternates)
```json
{
  "_id": "ObjectId",
  "company_id": "ObjectId (ref companies)",
  "name": "Rosneft",
  "country": "Russia",
  "region": "Eastern Europe",
  "tier": 1,
  "supplies": ["crude oil"],
  "supply_volume_pct": 65,
  "status": "active",
  "approved_vendor": true,
  "pre_qualified": true,
  "is_single_source": false,
  "esg_score": 42,
  "credit_rating": "BB+",
  "financial_health_score": 5.8,
  "max_capacity": 50000,
  "lead_time_weeks": 3,
  "contract_end": "2026-12-31",
  "upstream_suppliers": [
    { "name": "Siberian Oil Fields", "country": "Russia", "supply_volume_pct": 100 }
  ],
  "risk_score_current": 7.2,
  "description_embedding": [0.12, -0.34, ...]  // for Atlas Vector Search
}
```

**`articles`** — Raw + normalized news articles
```json
{
  "_id": "ObjectId",
  "event_id": "UUID",
  "timestamp": "ISODate",
  "source": "NewsAPI",
  "headline": "Trump threatens new sanctions on India over Russian oil",
  "body": "...",
  "url": "https://...",
  "entities_mentioned": ["Trump", "India", "Russia", "crude oil", "sanctions"],
  "raw_relevance_score": 0.87,
  "processed": true,
  "risk_extracted": true,
  "risk_event_id": "ObjectId (ref risk_events)"
}
```

**`risk_events`** — Processed risk records (output of Module 2)
```json
{
  "_id": "ObjectId",
  "article_id": "ObjectId (ref articles)",
  "company_id": "ObjectId",
  "timestamp": "ISODate",
  "risk_type": "geopolitical",
  "affected_entities": ["India", "Russia", "crude oil"],
  "affected_supply_chain_nodes": ["Rosneft"],
  "severity": "high",
  "is_confirmed": "uncertain",
  "time_horizon": "weeks",
  "reasoning": "Sanctions could restrict Rosneft crude oil imports to India",
  "risk_score_components": {
    "probability": 0.56,
    "impact": 7.8,
    "urgency": 1.5,
    "mitigation": 1.2
  },
  "risk_score": 5.46,
  "severity_band": "high",
  "propagation": {
    "Rosneft": 5.46,
    "Nayara Energy": 3.55
  }
}
```

**`alerts`** — Active alerts sent to decision makers
```json
{
  "_id": "ObjectId",
  "risk_event_id": "ObjectId (ref risk_events)",
  "company_id": "ObjectId",
  "severity_band": "high",
  "risk_score": 5.46,
  "title": "Geopolitical Risk: Sanctions threat on Russian crude oil imports",
  "description": "...",
  "affected_supplier": "Rosneft",
  "affected_material": "crude oil",
  "recommendations": [
    { "supplier_id": "ObjectId", "name": "ADNOC", "score": 8.1, "lead_time_weeks": 2 }
  ],
  "is_acknowledged": false,
  "acknowledged_by": null,
  "created_at": "ISODate",
  "resolved_at": null,
  "notification_sent": true
}
```

**`reports`** — AI-generated reports
```json
{
  "_id": "ObjectId",
  "type": "daily | weekly | on_demand",
  "content": "Executive Summary: ...",
  "generated_at": "ISODate",
  "period_start": "ISODate",
  "period_end": "ISODate",
  "alert_count": 3,
  "critical_count": 0
}
```

### Key MongoDB Indexes

```javascript
// articles — fast lookup of unprocessed items
db.articles.createIndex({ "processed": 1, "timestamp": -1 })

// risk_events — query by supplier, type, date
db.risk_events.createIndex({ "affected_supply_chain_nodes": 1, "timestamp": -1 })
db.risk_events.createIndex({ "risk_type": 1, "severity_band": 1 })

// alerts — fast open-alerts dashboard query
db.alerts.createIndex({ "is_acknowledged": 1, "severity_band": 1, "created_at": -1 })

// suppliers — lookup by material and status
db.suppliers.createIndex({ "supplies": 1, "status": 1 })

// MongoDB Atlas Vector Search index (for semantic search)
// Create via Atlas UI on suppliers.description_embedding field
```

### MongoDB Aggregation — Risk Summary Dashboard

```python
def get_dashboard_summary(db, company_id: str) -> dict:
    pipeline = [
        {"$match": {"company_id": ObjectId(company_id), "is_acknowledged": False}},
        {"$group": {
            "_id": "$severity_band",
            "count": {"$sum": 1},
            "avg_score": {"$avg": "$risk_score"}
        }}
    ]
    severity_counts = {doc["_id"]: doc for doc in db.alerts.aggregate(pipeline)}

    return {
        "critical": severity_counts.get("critical", {}).get("count", 0),
        "high":     severity_counts.get("high",     {}).get("count", 0),
        "medium":   severity_counts.get("medium",   {}).get("count", 0),
        "low":      severity_counts.get("low",      {}).get("count", 0),
        "total_open_alerts": db.alerts.count_documents({"is_acknowledged": False})
    }
```

---

## 8. Multi-Agent Architecture Design

### Agent Roles

| Agent | Model | Role | Trigger |
|---|---|---|---|
| **Ingestion Agent** | — (rule-based) | Polls sources, filters, pushes to Redis Stream | Celery Beat every 15 min |
| **Extraction Agent** | Gemini 1.5 Flash | Runs LLM on articles, extracts risk JSON | New event in Redis Stream |
| **Scoring Agent** | — (rule-based) | Calculates scores, runs NetworkX propagation | After extraction |
| **Alert Agent** | — (rule-based) | Applies thresholds, writes alerts, notifies | After scoring |
| **Recommendation Agent** | Gemini 1.5 Flash | Finds alternates, writes recommendations | Alert created |
| **Report Agent** | Gemini 1.5 Pro | Compiles reports, answers queries | Scheduled + user message |
| **Orchestrator** | Gemini 1.5 Pro | LangGraph multi-step reasoning | Complex user queries |

### Communication via Redis Streams

```
Ingestion Agent  → XADD "raw_events"
                        │
Extraction Agent ← XREAD "raw_events"
Extraction Agent → XADD "risk_entities"
                        │
Scoring Agent    ← XREAD "risk_entities"
Scoring Agent    → XADD "risk_scores"
                        │
Alert Agent      ← XREAD "risk_scores"
Alert Agent      → writes to MongoDB alerts
Alert Agent      → XADD "new_alerts"
                        │
Recommendation Agent ← XREAD "new_alerts"
Recommendation Agent → updates MongoDB alerts with recommendations
```

---

## 9. Frontend Dashboard

### Pages & Components

```
Dashboard Layout
├── /dashboard          ← Main overview
│   ├── Risk Score Summary Cards (Critical/High/Medium/Low counts)
│   ├── Supply Chain Graph (Cytoscape.js — nodes colored by risk)
│   ├── Live News Feed (filtered, tagged with risk type)
│   └── Active Alerts Table (sortable, filterable)
│
├── /suppliers          ← Supplier detail view
│   ├── Supplier List with current risk scores
│   ├── Individual Supplier Page (risk history, news, alternates)
│   └── Alternate Supplier Comparison Table
│
├── /risks              ← Risk event browser
│   ├── Risk Event Timeline (chronological)
│   ├── Filter by: type, severity, geography, supplier
│   └── Risk Event Detail (article, score breakdown, propagation path)
│
├── /reports            ← AI-generated reports
│   ├── Report Archive (daily/weekly)
│   └── Generate Custom Report
│
└── /agent              ← Chat with AI agent
    └── Conversational interface backed by LangGraph agent
```

### Real-Time Updates
```
FastAPI Backend
  └── /ws/alerts  (WebSocket endpoint)
        │
        └── Celery worker pushes new alerts here
              │
              ▼
        React Frontend (Socket.io or native WebSocket)
              └── Alert toast notification + updates dashboard state
```

### Tech Stack for Frontend
- **Framework:** React + TypeScript (Vite for fast builds)
- **Graph Viz:** Cytoscape.js (excellent for supply chain graphs)
- **Charts:** Recharts (risk score trends, severity distribution)
- **Real-time:** Native WebSocket API or Socket.io
- **UI Components:** Shadcn/ui + Tailwind CSS
- **Maps:** Leaflet.js (geographic risk overlay — show which countries are affected)
- **State:** Zustand (lightweight, perfect for alert state)

---

## 10. Tech Stack Summary

### Backend

| Component | Technology | Notes |
|---|---|---|
| API Server | FastAPI (Python) | Async endpoints, WebSocket support |
| Task Queue / Scheduler | Celery + Redis | Background jobs, cron scheduling |
| Message Streaming | Redis Streams | Replaces Kafka — simpler, same Redis instance |
| Cache & Dedup | Redis | TTL-based dedup fingerprints, live score cache |
| Database | **MongoDB Atlas** | All collections in one cluster |
| Vector Search | MongoDB Atlas Vector Search | Built-in; no separate Qdrant/Pinecone needed |
| Graph Computation | NetworkX (Python) | In-memory graph built from MongoDB docs |
| LLM | **Google Gemini API** | Flash for extraction, Pro for agent reasoning |
| Embeddings | Gemini `text-embedding-004` | For relevance scoring and supplier similarity |
| NLP (Entity Linking) | spaCy | Fast NER to pre-filter before Gemini call |
| Agent Framework | LangGraph + LangChain Google GenAI | Multi-agent orchestration |

### Frontend

| Component | Technology |
|---|---|
| Framework | React + TypeScript (Vite) |
| Graph Visualization | Cytoscape.js |
| Real-time | WebSocket (FastAPI + native browser WS) |
| State Management | Zustand |
| Styling | Tailwind CSS + Shadcn/ui |
| Charts | Recharts |
| Maps | Leaflet.js |

### Infrastructure

| Component | Technology |
|---|---|
| Containerization | Docker + Docker Compose |
| Database | MongoDB Atlas (cloud) or local Docker |
| Cache / Broker | Redis (Docker) |
| CI/CD | GitHub Actions |
| Environment Variables | python-dotenv + `.env` file |

### Minimal `docker-compose.yml`

```yaml
version: "3.9"
services:
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  mongodb:
    image: mongo:7
    ports: ["27017:27017"]
    volumes: ["mongo_data:/data/db"]

  api:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - MONGO_URI=mongodb://mongodb:27017
      - REDIS_URL=redis://redis:6379
    depends_on: [redis, mongodb]

  worker:
    build: ./backend
    command: celery -A celery_app worker --loglevel=info
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - MONGO_URI=mongodb://mongodb:27017
      - REDIS_URL=redis://redis:6379
    depends_on: [redis, mongodb]

  beat:
    build: ./backend
    command: celery -A celery_app beat --loglevel=info
    depends_on: [redis]

  frontend:
    build: ./frontend
    ports: ["3000:3000"]

volumes:
  mongo_data:
```

---

## 11. Implementation Roadmap

### Phase 1 — Foundation (Weeks 1–3)
**Goal:** Data flows from news API → MongoDB, basic Gemini extraction works

- [ ] Set up Docker Compose: MongoDB + Redis + FastAPI
- [ ] Define MongoDB collections and seed company profile + supplier data
- [ ] Build NewsAPI connector + normalizer
- [ ] Set up Redis Streams pipeline (`raw_events` → `normalized_events`)
- [ ] Implement deduplication (Redis SET NX)
- [ ] Integrate Gemini API — single article → structured risk JSON
- [ ] Save extracted risk events to MongoDB
- [ ] Basic REST API: `GET /alerts`, `GET /suppliers`, `GET /risks`

**Deliverable:** Feed news into the system, see risk events appear in MongoDB

---

### Phase 2 — Risk Engine (Weeks 4–6)
**Goal:** Full scoring, graph propagation, and alerts working

- [ ] Implement risk scoring formula in a Celery worker
- [ ] Build supply chain graph from MongoDB using NetworkX
- [ ] Implement `propagate_risk()` function
- [ ] Run `find_critical_nodes()` and store betweenness centrality in MongoDB
- [ ] Build alert generation logic (thresholds → write to `alerts` collection)
- [ ] Email/Slack notification via SendGrid + Slack webhooks
- [ ] Build alternate supplier recommendation engine
- [ ] `POST /alerts/{id}/acknowledge` endpoint

**Deliverable:** News → risk extraction → scoring → graph propagation → alert with alternate suppliers

---

### Phase 3 — Dashboard (Weeks 7–9)
**Goal:** React frontend showing live supply chain risk

- [ ] React + Vite scaffold, Tailwind CSS, routing
- [ ] Dashboard page: summary cards + alerts table
- [ ] Cytoscape.js supply chain graph (seed with 10–15 nodes)
- [ ] Risk event browser with filters
- [ ] Supplier detail page
- [ ] WebSocket connection for real-time alert toasts
- [ ] Leaflet map showing risk by country

**Deliverable:** Functional dashboard updating in real-time as news comes in

---

### Phase 4 — AI Agent (Weeks 10–12)
**Goal:** Conversational agent + auto-reports

- [ ] Set up LangGraph multi-agent with all 5 tools
- [ ] Chat interface in `/agent` page
- [ ] Auto daily report generation (Celery Beat)
- [ ] Report archive page
- [ ] Polish, end-to-end testing, demo scenarios
- [ ] README and setup documentation

**Deliverable:** Working system from ingestion to agent chat; demo-ready

---

## 12. Data Flow — End to End Example

**Scenario:** "Trump threatens sanctions on India over Russian oil imports"
*(Real risk for Nayara Energy, which depends heavily on Rosneft crude)*

```
1. INGESTION (Module 1)
   Celery Beat triggers NewsAPIConnector every 15 minutes
   Article found: "Trump threatens new sanctions on India over Russian oil imports"
   Relevance check: "India" + "Russian" + "oil" → matches Nayara profile keywords
   Fingerprint hash → Redis SET NX → not a duplicate
   XADD "normalized_events" with normalized article JSON

2. EXTRACTION (Module 2a)
   Celery Worker reads from "normalized_events" via XREAD
   Calls Gemini 1.5 Flash with structured prompt:
   {
     "is_risk": true,
     "risk_type": "geopolitical",
     "affected_entities": ["USA", "India", "Russia", "crude oil", "Trump"],
     "affected_supply_chain_nodes": ["Rosneft"],
     "severity": "high",
     "is_confirmed": "uncertain",
     "time_horizon": "weeks",
     "reasoning": "US sanctions on Indian crude oil imports from Russia would
                   directly restrict Nayara Energy's primary supply source Rosneft",
     "recommended_action": "Begin qualifying alternate crude oil suppliers immediately"
   }
   Saved to MongoDB risk_events collection

3. SCORING (Module 2b)
   Probability: 0.56 (high severity but uncertain/political posturing)
   Impact: 8.1  (Rosneft = 65% of crude supply, 15-day buffer)
   Urgency: 1.5 (weeks away)
   Mitigation: 1.2 (ADNOC exists but only 35% capacity)
   Risk Score: (0.56 × 8.1 × 1.5) / 1.2 = 5.67 → HIGH band

4. PROPAGATION (Module 2c)
   NetworkX graph: Rosneft → Nayara Energy (weight=0.65)
   Propagated score to Nayara: 5.67 × 0.65 × 0.9 = 3.31
   Also propagates to downstream product lines (Product-A, Product-B)
   Critical path identified: Rosneft → Nayara is single-source for 65% of crude

5. ALERT CREATED (Module 2 → Alert Agent)
   Severity: HIGH | Score: 5.67
   Title: "Geopolitical: US Sanctions Threat on Russian Crude Oil Imports"
   XADD "new_alerts" → triggers Recommendation Agent

6. RECOMMENDATION (Module 3)
   Material: crude oil | Volume needed: 65% of current Rosneft supply
   MongoDB query: find alternate crude oil suppliers
   Top 3 ranked:
   ① ADNOC (UAE)        — Score 8.4 — 2 weeks — pre-qualified ✓
   ② Saudi Aramco (KSA) — Score 7.9 — 3 weeks — approved vendor ✓
   ③ ONGC (India)       — Score 6.2 — 1 week  — domestic, no sanctions risk ✓
   Alert document updated with recommendations

7. NOTIFICATIONS
   Email → Supply Chain Manager, VP Operations
   Slack → #supply-chain-alerts channel
   WebSocket → Dashboard shows alert toast in real-time

8. AGENT RESPONSE (if queried)
   User: "What should we do about the Russian oil sanctions threat?"

   LangGraph Orchestrator → calls query_risk_events("Rosneft", 7)
                          → calls find_alternate_suppliers("crude oil", "Rosneft")
                          → calls get_supply_chain_summary()

   Gemini 1.5 Pro synthesizes:
   "A HIGH risk geopolitical event has been detected: Trump's threat to sanction India
   over Russian crude oil imports poses a significant supply risk to your operations.
   Rosneft currently supplies 65% of your crude oil, and you have approximately 15 days
   of inventory buffer. Immediate recommendation: issue a purchase order to ADNOC (UAE)
   to cover at least 30% of your crude oil needs as a contingency — they are pre-qualified
   and can deliver within 2 weeks. Also begin qualification of Saudi Aramco as a second
   alternate. Monitor this situation daily; if sanctions are confirmed, execute the ADNOC
   order immediately."
```

---

## Quick Start: Minimal Viable System

Build this in 2 weeks to have a working demo:

```
✅ Python FastAPI backend
✅ MongoDB (local Docker or free MongoDB Atlas M0 cluster)
✅ Redis (local Docker) — for Celery + dedup + streams
✅ NewsAPI (free tier — 100 req/day)
✅ Gemini API (free tier — 15 req/min on Flash)
✅ NetworkX (in-memory graph, seeded from MongoDB)
✅ React frontend (basic dashboard + alerts table)
✅ Celery Beat (fetch news every 15 min)
```

**Seed 5–10 suppliers manually in MongoDB, run the pipeline, and watch risks flow through.**
Then add: graph propagation → recommendation engine → LangGraph agent → full dashboard.

---

*Architecture v2.0 — Stack: MongoDB · Redis Streams · Gemini · LangGraph · FastAPI · React*
