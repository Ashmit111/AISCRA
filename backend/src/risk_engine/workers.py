"""
Risk Processing Workers
Celery workers that consume from Redis streams and process the full risk pipeline
"""

from celery import Celery
import logging
from datetime import datetime

from ..utils.config import settings
from ..models.db import db_manager, get_company_profile
from ..ingestion.redis_streams import RedisStreamManager, consume_stream
from ..risk_engine.gemini_client import get_gemini_client
from ..risk_engine.relevance_filter import is_relevant, build_company_keywords
from ..risk_engine.scoring import calculate_risk_score
from ..risk_engine.graph_propagation import build_supply_graph, propagate_risk
from ..risk_engine.alert_generator import create_alert
from ..utils.notifications import send_alert_notifications

logger = logging.getLogger(__name__)

# Get Celery app from ingestion module
from ..ingestion.celery_app import celery_app


@celery_app.task(bind=True, name='src.risk_engine.workers.process_risk_extraction')
def process_risk_extraction_task(self):
    """
    Celery task: Process articles from normalized_events stream
    Consumes: normalized_events
    Produces: risk_entities (for scoring)
    """
    logger.info("Starting risk extraction worker...")
    
    db = db_manager.db
    gemini_client = get_gemini_client()
    company_profile = get_company_profile()
    
    if not company_profile:
        logger.error("Company profile not found, cannot process")
        return
    
    # Build relevance keywords
    keywords = build_company_keywords(company_profile)
    
    def handler(article_data):
        """Process each article"""
        try:
            logger.info(f"Processing article: {article_data.get('headline', '')[:80]}...")
            
            # Check relevance first (to save Gemini API calls)
            relevant, relevance_score = is_relevant(article_data, keywords)
            
            if not relevant:
                logger.info(f"Article not relevant (score: {relevance_score:.3f}), skipping")
                return
            
            logger.info(f"Article relevant (score: {relevance_score:.3f}), extracting risk...")
            
            # Extract risk using Gemini
            risk_data = gemini_client.extract_risk(article_data, company_profile)
            
            if not risk_data:
                logger.warning("Risk extraction failed")
                return
            
            # Check if it's actually a risk
            if not risk_data.get("is_risk"):
                logger.info("Not identified as a risk, skipping")
                # Update article as processed
                db.articles.update_one(
                    {"event_id": article_data.get("event_id")},
                    {"$set": {"processed": True, "risk_extracted": False}}
                )
                return
            
            # Save article to MongoDB
            article_doc = article_data.copy()
            article_doc["raw_relevance_score"] = relevance_score
            article_doc["processed"] = True
            article_doc["risk_extracted"] = True
            
            result = db.articles.insert_one(article_doc)
            article_id = str(result.inserted_id)
            
            # Create risk event document
            risk_event = {
                "article_id": article_id,
                "company_id": company_profile["_id"],
                "timestamp": article_data.get("timestamp", datetime.utcnow()),
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
                    "mitigation": 0.0
                },
                "risk_score": 0.0,  # Will be calculated by scoring worker
                "severity_band": "low",  # Will be updated by scoring worker
                "propagation": {},
                "created_at": datetime.utcnow()
            }
            
            # Save risk event
            result = db.risk_events.insert_one(risk_event)
            risk_event_id = str(result.inserted_id)
            
            logger.info(
                f"✓ Created risk event {risk_event_id}: "
                f"{risk_data['risk_type']} affecting {risk_data.get('affected_supply_chain_nodes')}"
            )
            
            # Push to risk_entities stream for scoring
            from ..ingestion.redis_streams import push_to_stream
            push_to_stream(RedisStreamManager.STREAM_RISK_ENTITIES, {
                "risk_event_id": risk_event_id,
                "risk_type": risk_data["risk_type"],
                "severity": risk_data["severity"],
                "affected_nodes": risk_data.get("affected_supply_chain_nodes", [])
            })
            
        except Exception as e:
            logger.error(f"Error processing article: {e}", exc_info=True)
    
    # Consume from normalized_events stream
    consume_stream(
        RedisStreamManager.STREAM_NORMALIZED_EVENTS,
        "risk_extraction_group",
        "extraction_worker_1",
        handler,
        block_ms=5000,
        count=5
    )


@celery_app.task(bind=True, name='src.risk_engine.workers.process_risk_scoring')
def process_risk_scoring_task(self):
    """
    Celery task: Score risk events from risk_entities stream
    Consumes: risk_entities
    Produces: risk_scores (for alert generation)
    """
    logger.info("Starting risk scoring worker...")
    
    db = db_manager.db
    company_profile = get_company_profile()
    
    if not company_profile:
        logger.error("Company profile not found, cannot process")
        return
    
    # Build supplier map for quick lookup
    suppliers = db.suppliers.find({"company_id": company_profile["_id"]})
    supplier_map = {s["name"]: s for s in suppliers}
    
    def handler(risk_entity_data):
        """Process each risk entity"""
        try:
            risk_event_id = risk_entity_data.get("risk_event_id")
            logger.info(f"Scoring risk event: {risk_event_id}")
            
            # Load risk event from MongoDB
            risk_event = db.risk_events.find_one({"_id": risk_event_id})
            if not risk_event:
                logger.error(f"Risk event {risk_event_id} not found")
                return
            
            # Get affected supplier
            affected_nodes = risk_event.get("affected_supply_chain_nodes", [])
            if not affected_nodes:
                logger.warning("No affected suppliers, cannot score")
                return
            
            supplier_name = affected_nodes[0]
            supplier = supplier_map.get(supplier_name)
            
            if not supplier:
                logger.warning(f"Supplier '{supplier_name}' not found in map")
                # Try database lookup
                supplier = db.suppliers.find_one({
                    "name": supplier_name,
                    "company_id": company_profile["_id"]
                })
                
                if not supplier:
                    logger.error(f"Supplier '{supplier_name}' not in database, skipping")
                    return
            
            # Calculate risk score
            score_result = calculate_risk_score(risk_event, supplier, company_profile)
            
            # Update risk event with score
            db.risk_events.update_one(
                {"_id": risk_event_id},
                {
                    "$set": {
                        "risk_score": score_result["risk_score"],
                        "severity_band": score_result["severity_band"],
                        "risk_score_components": score_result["components"]
                    }
                }
            )
            
            logger.info(
                f"✓ Scored risk event {risk_event_id}: "
                f"{score_result['risk_score']:.2f} ({score_result['severity_band']})"
            )
            
            # Push to risk_scores stream for propagation/alerts
            from ..ingestion.redis_streams import push_to_stream
            push_to_stream(RedisStreamManager.STREAM_RISK_SCORES, {
                "risk_event_id": risk_event_id,
                "risk_score": score_result["risk_score"],
                "severity_band": score_result["severity_band"],
                "affected_supplier": supplier_name
            })
            
        except Exception as e:
            logger.error(f"Error scoring risk: {e}", exc_info=True)
    
    # Consume from risk_entities stream
    consume_stream(
        RedisStreamManager.STREAM_RISK_ENTITIES,
        "risk_scoring_group",
        "scoring_worker_1",
        handler,
        block_ms=5000,
        count=5
    )


@celery_app.task(bind=True, name='src.risk_engine.workers.process_alerts')
def process_alerts_task(self):
    """
    Celery task: Generate alerts from scored risks
    Consumes: risk_scores
    Produces: new_alerts + notifications
    """
    logger.info("Starting alert generation worker...")
    
    db = db_manager.db
    company_profile = get_company_profile()
    gemini_client = get_gemini_client()
    
    if not company_profile:
        logger.error("Company profile not found, cannot process")
        return
    
    # Build supply graph once for propagation
    graph = build_supply_graph(db, company_profile["_id"])
    logger.info(f"Built supply graph with {graph.number_of_nodes()} nodes")
    
    def handler(risk_score_data):
        """Process each scored risk"""
        try:
            risk_event_id = risk_score_data.get("risk_event_id")
            logger.info(f"Processing alert for risk event: {risk_event_id}")
            
            # Load risk event
            risk_event = db.risk_events.find_one({"_id": risk_event_id})
            if not risk_event:
                logger.error(f"Risk event {risk_event_id} not found")
                return
            
            # Propagate risk through graph
            supplier_name = risk_score_data.get("affected_supplier")
            if supplier_name:
                # Find supplier node in graph
                supplier_node = None
                for node, data in graph.nodes(data=True):
                    if data.get("name") == supplier_name:
                        supplier_node = node
                        break
                
                if supplier_node:
                    logger.info(f"Propagating risk from {supplier_name}...")
                    propagated = propagate_risk(
                        graph,
                        supplier_node,
                        risk_event["risk_score"],
                        threshold=1.0
                    )
                    
                    # Update risk event with propagation
                    db.risk_events.update_one(
                        {"_id": risk_event_id},
                        {"$set": {"propagation": propagated}}
                    )
                    
                    logger.info(f"✓ Propagated to {len(propagated)} nodes")
            
            # Create alert
            alert_id = create_alert(risk_event, db, gemini_client)
            
            if alert_id:
                logger.info(f"✓ Created alert: {alert_id}")
                
                # Load alert for notification
                alert = db.alerts.find_one({"_id": alert_id})
                
                # Send notifications
                if alert and not alert.get("notification_sent"):
                    logger.info("Sending notifications...")
                    send_alert_notifications(alert, db)
                
                # Push to new_alerts stream (for real-time dashboard updates)
                from ..ingestion.redis_streams import push_to_stream
                push_to_stream(RedisStreamManager.STREAM_NEW_ALERTS, {
                    "alert_id": alert_id,
                    "severity_band": risk_event["severity_band"],
                    "risk_score": risk_event["risk_score"],
                    "title": alert.get("title", "") if alert else ""
                })
            else:
                logger.info("Alert not created (below threshold or no affected nodes)")
            
        except Exception as e:
            logger.error(f"Error generating alert: {e}", exc_info=True)
    
    # Consume from risk_scores stream
    consume_stream(
        RedisStreamManager.STREAM_RISK_SCORES,
        "alert_generation_group",
        "alert_worker_1",
        handler,
        block_ms=5000,
        count=5
    )


# Register worker tasks with Celery Beat (optional long-running workers)
celery_app.conf.beat_schedule.update({
    'risk-extraction-worker': {
        'task': 'src.risk_engine.workers.process_risk_extraction',
        'schedule': 60.0,  # Run every 60 seconds
    },
    'risk-scoring-worker': {
        'task': 'src.risk_engine.workers.process_risk_scoring',
        'schedule': 60.0,
    },
    'alert-generation-worker': {
        'task': 'src.risk_engine.workers.process_alerts',
        'schedule': 60.0,
    },
})
