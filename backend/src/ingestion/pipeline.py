"""
Pipeline Orchestrator
Manages the end-to-end automated news ingestion ➜ risk analysis pipeline.

Pipeline stages:
  1. FETCH    – Pull articles from NewsAPI + GDELT
  2. NORMALIZE – Convert to standard format, deduplicate
  3. EXTRACT  – Relevance filter + Gemini risk extraction
  4. SCORE    – Calculate risk score per event
  5. ALERT    – Generate alerts & send notifications

Each stage is a Celery task. The orchestrator chains them so one
complete run = fetch → extract → score → alert, all automatic.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from ..utils.config import settings
from ..models.db import db_manager, get_company_profile
from ..ingestion.redis_streams import (
    RedisStreamManager, stream_manager, push_to_stream
)

logger = logging.getLogger(__name__)

# ─── Pipeline tracking key in Redis ─────────────────────────────────────
PIPELINE_STATUS_KEY = "pipeline:status"
PIPELINE_HISTORY_KEY = "pipeline:history"


def _set_pipeline_status(status: str, detail: str = "", run_id: str = ""):
    """Persist current pipeline status to Redis so the API can expose it."""
    try:
        client = stream_manager.client
        data = {
            "status": status,
            "detail": detail,
            "run_id": run_id,
            "updated_at": datetime.utcnow().isoformat(),
        }
        client.set(PIPELINE_STATUS_KEY, json.dumps(data))
    except Exception as e:
        logger.warning(f"Could not set pipeline status: {e}")


def _push_pipeline_history(entry: dict):
    """Push a completed run summary to a capped Redis list."""
    try:
        client = stream_manager.client
        client.lpush(PIPELINE_HISTORY_KEY, json.dumps(entry))
        client.ltrim(PIPELINE_HISTORY_KEY, 0, 49)   # keep last 50 runs
    except Exception as e:
        logger.warning(f"Could not push pipeline history: {e}")


def get_pipeline_status() -> dict:
    """Read current pipeline status from Redis."""
    try:
        client = stream_manager.client
        raw = client.get(PIPELINE_STATUS_KEY)
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return {"status": "idle", "detail": "", "run_id": "", "updated_at": ""}


def get_pipeline_history(limit: int = 20) -> list:
    """Read recent pipeline run history from Redis."""
    try:
        client = stream_manager.client
        items = client.lrange(PIPELINE_HISTORY_KEY, 0, limit - 1)
        return [json.loads(i) for i in items]
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════════════
# Stage 1 — FETCH + NORMALIZE + DEDUPLICATE
# ═══════════════════════════════════════════════════════════════════════

def stage_fetch(run_id: str) -> Dict[str, Any]:
    """
    Fetch articles from all sources, normalize, deduplicate, push to
    the ``normalized_events`` Redis stream.

    Returns summary dict with counts.
    """
    from ..ingestion.connectors.newsapi import NewsAPIConnector
    from ..ingestion.connectors.gdelt import GDELTConnector
    from ..ingestion.normalizer import (
        normalize_newsapi_article,
        normalize_gdelt_article,
        validate_article,
    )
    from ..ingestion.deduplicator import is_duplicate

    _set_pipeline_status("fetching", "Pulling articles from sources", run_id)

    stats = {
        "newsapi_fetched": 0, "gdelt_fetched": 0,
        "normalized": 0, "duplicates": 0, "invalid": 0, "pushed": 0,
    }

    # --- NewsAPI ---
    try:
        newsapi = NewsAPIConnector()
        raw_articles = newsapi.fetch(max_articles=100)
        stats["newsapi_fetched"] = len(raw_articles)

        for raw in raw_articles:
            try:
                normalized = normalize_newsapi_article(raw)
                if not validate_article(normalized):
                    stats["invalid"] += 1
                    continue
                if is_duplicate(normalized):
                    stats["duplicates"] += 1
                    continue
                push_to_stream(RedisStreamManager.STREAM_NORMALIZED_EVENTS, normalized)
                stats["normalized"] += 1
                stats["pushed"] += 1
            except Exception as e:
                logger.error(f"NewsAPI article processing error: {e}")
    except Exception as e:
        logger.error(f"NewsAPI fetch error: {e}", exc_info=True)

    # --- GDELT ---
    try:
        gdelt = GDELTConnector()
        raw_gdelt = gdelt.fetch(max_articles=50)
        stats["gdelt_fetched"] = len(raw_gdelt)

        for raw in raw_gdelt:
            try:
                normalized = normalize_gdelt_article(raw)
                if not validate_article(normalized):
                    stats["invalid"] += 1
                    continue
                if is_duplicate(normalized):
                    stats["duplicates"] += 1
                    continue
                push_to_stream(RedisStreamManager.STREAM_NORMALIZED_EVENTS, normalized)
                stats["normalized"] += 1
                stats["pushed"] += 1
            except Exception as e:
                logger.error(f"GDELT article processing error: {e}")
    except Exception as e:
        logger.error(f"GDELT fetch error: {e}", exc_info=True)

    logger.info(
        f"[{run_id}] Fetch complete — "
        f"NewsAPI={stats['newsapi_fetched']}, GDELT={stats['gdelt_fetched']}, "
        f"pushed={stats['pushed']}, dupes={stats['duplicates']}, invalid={stats['invalid']}"
    )
    return stats


# ═══════════════════════════════════════════════════════════════════════
# Stage 2 — RISK EXTRACTION (batch, non-blocking)
# ═══════════════════════════════════════════════════════════════════════

def stage_extract_risks(run_id: str, batch_size: int = 20) -> Dict[str, Any]:
    """
    Read up to *batch_size* articles from ``normalized_events`` stream,
    run relevance filter + Gemini extraction, push risk entities to
    ``risk_entities`` stream, and save articles & risk events to Mongo.
    """
    from ..risk_engine.groq_client import get_groq_client
    from ..risk_engine.relevance_filter import is_relevant, build_company_keywords

    _set_pipeline_status("extracting", "Filtering & extracting risks via AI", run_id)

    db = db_manager.db
    company_profile = get_company_profile()
    if not company_profile:
        logger.error("Company profile not found")
        return {"error": "no_company_profile"}

    groq_client = get_groq_client()
    keywords = build_company_keywords(company_profile)

    stats = {"read": 0, "relevant": 0, "risks_found": 0, "not_relevant": 0, "errors": 0}

    # Read batch from stream (no consumer group needed; use XRANGE + trim)
    try:
        entries = stream_manager.client.xrange(
            RedisStreamManager.STREAM_NORMALIZED_EVENTS,
            min="-", max="+", count=batch_size,
        )
    except Exception as e:
        logger.error(f"Cannot read from normalized_events stream: {e}")
        return {"error": str(e)}

    if not entries:
        logger.info(f"[{run_id}] No new articles in normalized_events stream")
        return stats

    entry_ids = []
    for entry_id, raw_data in entries:
        entry_ids.append(entry_id)
        stats["read"] += 1

        # Deserialize
        article_data = {}
        for k, v in raw_data.items():
            try:
                article_data[k] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                article_data[k] = v

        try:
            relevant, score = is_relevant(article_data, keywords)
            if not relevant:
                stats["not_relevant"] += 1
                continue

            stats["relevant"] += 1
            risk_data = groq_client.extract_risk(article_data, company_profile)

            if not risk_data or not risk_data.get("is_risk"):
                # Save article as processed, no risk
                article_data["processed"] = True
                article_data["risk_extracted"] = False
                article_data["raw_relevance_score"] = score
                try:
                    db.articles.update_one(
                        {"event_id": article_data.get("event_id")},
                        {"$set": article_data},
                        upsert=True,
                    )
                except Exception:
                    pass
                continue

            # Save article to Mongo
            article_data["raw_relevance_score"] = score
            article_data["processed"] = True
            article_data["risk_extracted"] = True
            try:
                result = db.articles.update_one(
                    {"event_id": article_data.get("event_id")},
                    {"$set": article_data},
                    upsert=True,
                )
                article_id = str(result.upserted_id) if result.upserted_id else article_data.get("event_id")
            except Exception:
                article_id = article_data.get("event_id")

            # Create risk event
            risk_event = {
                "article_id": article_id,
                "company_id": company_profile["_id"],
                "timestamp": article_data.get("timestamp", datetime.utcnow().isoformat()),
                "risk_type": risk_data["risk_type"],
                "affected_entities": risk_data.get("affected_entities", []),
                "affected_supply_chain_nodes": risk_data.get("affected_supply_chain_nodes", []),
                "severity": risk_data["severity"],
                "is_confirmed": risk_data.get("is_confirmed", "uncertain"),
                "time_horizon": risk_data["time_horizon"],
                "reasoning": risk_data.get("reasoning", ""),
                "recommended_action": risk_data.get("recommended_action"),
                "risk_score_components": {
                    "probability": 0.0,
                    "impact": 0.0,
                    "urgency": 0.0,
                    "mitigation": 0.0,
                },
                "risk_score": 0.0,
                "severity_band": "low",
                "propagation": {},
                "created_at": datetime.utcnow(),
            }
            re_result = db.risk_events.insert_one(risk_event)
            risk_event_id = str(re_result.inserted_id)

            # Push for scoring stage
            push_to_stream(RedisStreamManager.STREAM_RISK_ENTITIES, {
                "risk_event_id": risk_event_id,
                "risk_type": risk_data["risk_type"],
                "severity": risk_data["severity"],
                "affected_nodes": risk_data.get("affected_supply_chain_nodes", []),
            })
            stats["risks_found"] += 1

        except Exception as e:
            logger.error(f"Error extracting risk: {e}", exc_info=True)
            stats["errors"] += 1

    # Remove processed entries from stream
    if entry_ids:
        try:
            stream_manager.client.xdel(
                RedisStreamManager.STREAM_NORMALIZED_EVENTS, *entry_ids
            )
        except Exception as e:
            logger.warning(f"Could not trim processed entries: {e}")

    logger.info(
        f"[{run_id}] Extract complete — read={stats['read']}, "
        f"relevant={stats['relevant']}, risks={stats['risks_found']}"
    )
    return stats


# ═══════════════════════════════════════════════════════════════════════
# Stage 3 — RISK SCORING (batch)
# ═══════════════════════════════════════════════════════════════════════

def stage_score_risks(run_id: str, batch_size: int = 20) -> Dict[str, Any]:
    """
    Read risk entities from ``risk_entities`` stream, calculate scores,
    update Mongo, push to ``risk_scores`` for alerting.
    """
    from ..risk_engine.scoring import calculate_risk_score
    from bson import ObjectId

    _set_pipeline_status("scoring", "Calculating risk scores", run_id)

    db = db_manager.db
    company_profile = get_company_profile()
    if not company_profile:
        return {"error": "no_company_profile"}

    # Build supplier map
    suppliers = list(db.suppliers.find({"company_id": company_profile["_id"]}))
    supplier_map = {s["name"]: s for s in suppliers}

    stats = {"read": 0, "scored": 0, "errors": 0}

    entries = stream_manager.client.xrange(
        RedisStreamManager.STREAM_RISK_ENTITIES,
        min="-", max="+", count=batch_size,
    )
    if not entries:
        logger.info(f"[{run_id}] No risk entities to score")
        return stats

    entry_ids = []
    for entry_id, raw_data in entries:
        entry_ids.append(entry_id)
        stats["read"] += 1

        data = {}
        for k, v in raw_data.items():
            try:
                data[k] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                data[k] = v

        try:
            risk_event_id = data.get("risk_event_id")
            # Try ObjectId first, fall back to string
            try:
                risk_event = db.risk_events.find_one({"_id": ObjectId(risk_event_id)})
            except Exception:
                risk_event = db.risk_events.find_one({"_id": risk_event_id})

            if not risk_event:
                logger.warning(f"Risk event {risk_event_id} not found in DB")
                continue

            affected_nodes = risk_event.get("affected_supply_chain_nodes", [])
            if not affected_nodes:
                continue

            supplier_name = affected_nodes[0]
            supplier = supplier_map.get(supplier_name)
            if not supplier:
                supplier = db.suppliers.find_one({
                    "name": supplier_name,
                    "company_id": company_profile["_id"],
                })
            if not supplier:
                logger.warning(f"Supplier '{supplier_name}' not found, using defaults")
                supplier = {
                    "name": supplier_name,
                    "supply_volume_pct": 50,
                    "supplies": ["unknown"],
                    "is_single_source": False,
                }

            score_result = calculate_risk_score(risk_event, supplier, company_profile)

            db.risk_events.update_one(
                {"_id": risk_event["_id"]},
                {"$set": {
                    "risk_score": score_result["risk_score"],
                    "severity_band": score_result["severity_band"],
                    "risk_score_components": score_result["components"],
                }},
            )

            # Also update supplier's current risk score
            if isinstance(supplier.get("_id"), str) or isinstance(supplier.get("_id"), ObjectId):
                db.suppliers.update_one(
                    {"_id": supplier["_id"]},
                    {"$set": {
                        "risk_score_current": score_result["risk_score"],
                        "updated_at": datetime.utcnow(),
                    }},
                )

            push_to_stream(RedisStreamManager.STREAM_RISK_SCORES, {
                "risk_event_id": str(risk_event["_id"]),
                "risk_score": score_result["risk_score"],
                "severity_band": score_result["severity_band"],
                "affected_supplier": supplier_name,
            })
            stats["scored"] += 1

        except Exception as e:
            logger.error(f"Scoring error: {e}", exc_info=True)
            stats["errors"] += 1

    if entry_ids:
        try:
            stream_manager.client.xdel(RedisStreamManager.STREAM_RISK_ENTITIES, *entry_ids)
        except Exception:
            pass

    logger.info(f"[{run_id}] Score complete — scored={stats['scored']}")
    return stats


# ═══════════════════════════════════════════════════════════════════════
# Stage 4 — ALERT GENERATION (batch)
# ═══════════════════════════════════════════════════════════════════════

def stage_generate_alerts(run_id: str, batch_size: int = 20) -> Dict[str, Any]:
    """
    Read scored risks from ``risk_scores`` stream, propagate through the
    supply-chain graph, create alerts, send notifications.
    """
    from ..risk_engine.alert_generator import create_alert
    from ..risk_engine.graph_propagation import build_supply_graph, propagate_risk
    from ..risk_engine.gemini_client import get_gemini_client
    from ..utils.notifications import send_alert_notifications
    from bson import ObjectId

    _set_pipeline_status("alerting", "Generating alerts & notifications", run_id)

    db = db_manager.db
    company_profile = get_company_profile()
    gemini_client = get_gemini_client()
    if not company_profile:
        return {"error": "no_company_profile"}

    graph = build_supply_graph(db, company_profile["_id"])

    stats = {"read": 0, "alerts_created": 0, "below_threshold": 0, "errors": 0}

    entries = stream_manager.client.xrange(
        RedisStreamManager.STREAM_RISK_SCORES,
        min="-", max="+", count=batch_size,
    )
    if not entries:
        logger.info(f"[{run_id}] No scored risks to alert on")
        return stats

    entry_ids = []
    for entry_id, raw_data in entries:
        entry_ids.append(entry_id)
        stats["read"] += 1

        data = {}
        for k, v in raw_data.items():
            try:
                data[k] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                data[k] = v

        try:
            risk_event_id = data.get("risk_event_id")
            try:
                risk_event = db.risk_events.find_one({"_id": ObjectId(risk_event_id)})
            except Exception:
                risk_event = db.risk_events.find_one({"_id": risk_event_id})

            if not risk_event:
                continue

            # Graph propagation
            supplier_name = data.get("affected_supplier")
            if supplier_name and graph.number_of_nodes() > 0:
                supplier_node = None
                for node, ndata in graph.nodes(data=True):
                    if ndata.get("name") == supplier_name:
                        supplier_node = node
                        break
                if supplier_node:
                    propagated = propagate_risk(
                        graph, supplier_node,
                        risk_event.get("risk_score", 0), threshold=1.0,
                    )
                    db.risk_events.update_one(
                        {"_id": risk_event["_id"]},
                        {"$set": {"propagation": propagated}},
                    )

            # Create alert
            alert_id = create_alert(risk_event, db, gemini_client)
            if alert_id:
                stats["alerts_created"] += 1
                alert = db.alerts.find_one({"_id": alert_id})
                if alert and not alert.get("notification_sent"):
                    try:
                        send_alert_notifications(alert, db)
                    except Exception as e:
                        logger.warning(f"Notification error: {e}")

                push_to_stream(RedisStreamManager.STREAM_NEW_ALERTS, {
                    "alert_id": str(alert_id),
                    "severity_band": risk_event.get("severity_band", "low"),
                    "risk_score": risk_event.get("risk_score", 0),
                    "title": alert.get("title", "") if alert else "",
                })
            else:
                stats["below_threshold"] += 1

        except Exception as e:
            logger.error(f"Alert generation error: {e}", exc_info=True)
            stats["errors"] += 1

    if entry_ids:
        try:
            stream_manager.client.xdel(RedisStreamManager.STREAM_RISK_SCORES, *entry_ids)
        except Exception:
            pass

    logger.info(f"[{run_id}] Alerts complete — created={stats['alerts_created']}")
    return stats


# ═══════════════════════════════════════════════════════════════════════
# Full pipeline run (called by Celery)
# ═══════════════════════════════════════════════════════════════════════

def run_full_pipeline() -> Dict[str, Any]:
    """
    Execute the full pipeline synchronously:
      fetch ➜ extract ➜ score ➜ alert
    Returns a combined summary of all stages.
    """
    import uuid as _uuid
    run_id = _uuid.uuid4().hex[:8]
    started = datetime.utcnow()

    logger.info("=" * 60)
    logger.info(f"PIPELINE RUN [{run_id}] STARTED at {started.isoformat()}")
    logger.info("=" * 60)

    _set_pipeline_status("running", "Full pipeline started", run_id)

    result = {"run_id": run_id, "started_at": started.isoformat()}

    try:
        # Stage 1
        result["fetch"] = stage_fetch(run_id)

        # Stage 2 — may need multiple batches
        extract_total = {"read": 0, "relevant": 0, "risks_found": 0, "errors": 0}
        for _ in range(10):  # max 10 batches × 20 = 200 articles
            batch = stage_extract_risks(run_id, batch_size=20)
            if batch.get("error") or batch.get("read", 0) == 0:
                break
            for k in extract_total:
                extract_total[k] += batch.get(k, 0)
        result["extract"] = extract_total

        # Stage 3
        score_total = {"read": 0, "scored": 0, "errors": 0}
        for _ in range(10):
            batch = stage_score_risks(run_id, batch_size=20)
            if batch.get("error") or batch.get("read", 0) == 0:
                break
            for k in score_total:
                score_total[k] += batch.get(k, 0)
        result["score"] = score_total

        # Stage 4
        alert_total = {"read": 0, "alerts_created": 0, "below_threshold": 0, "errors": 0}
        for _ in range(10):
            batch = stage_generate_alerts(run_id, batch_size=20)
            if batch.get("error") or batch.get("read", 0) == 0:
                break
            for k in alert_total:
                alert_total[k] += batch.get(k, 0)
        result["alert"] = alert_total

        finished = datetime.utcnow()
        result["finished_at"] = finished.isoformat()
        result["duration_seconds"] = (finished - started).total_seconds()
        result["status"] = "completed"

        _set_pipeline_status("idle", f"Last run {run_id} completed", run_id)
        _push_pipeline_history(result)

        logger.info("=" * 60)
        logger.info(f"PIPELINE RUN [{run_id}] COMPLETED in {result['duration_seconds']:.1f}s")
        logger.info(f"  Fetched: {result['fetch'].get('pushed', 0)} articles")
        logger.info(f"  Risks found: {result['extract'].get('risks_found', 0)}")
        logger.info(f"  Scored: {result['score'].get('scored', 0)}")
        logger.info(f"  Alerts: {result['alert'].get('alerts_created', 0)}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Pipeline run [{run_id}] FAILED: {e}", exc_info=True)
        result["status"] = "failed"
        result["error"] = str(e)
        _set_pipeline_status("failed", str(e), run_id)
        _push_pipeline_history(result)

    return result
