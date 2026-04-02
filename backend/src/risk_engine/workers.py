"""
Risk Processing Workers
Celery tasks that process risk pipeline stages in batch mode.

These tasks are NOT scheduled on a timer any more -- they are called
as part of the pipeline orchestrator (see ingestion/pipeline.py).
They are still registered as Celery tasks so they can also be invoked
independently via the API or CLI when needed.
"""

import logging
from datetime import datetime

from ..utils.config import settings
from ..models.db import db_manager, get_company_profile
from ..ingestion.redis_streams import RedisStreamManager

logger = logging.getLogger(__name__)

# Get Celery app from ingestion module
from ..ingestion.celery_app import celery_app


@celery_app.task(bind=True, name="src.risk_engine.workers.process_risk_extraction_batch")
def process_risk_extraction_batch(self, batch_size: int = 20):
    """
    Celery task: Process a batch of articles from normalized_events stream.
    Non-blocking -- reads up to batch_size, processes, returns.
    """
    from ..ingestion.pipeline import stage_extract_risks
    import uuid

    run_id = uuid.uuid4().hex[:8]
    logger.info(f"Risk extraction batch task started (run_id={run_id})")
    return stage_extract_risks(run_id, batch_size)


@celery_app.task(bind=True, name="src.risk_engine.workers.process_risk_scoring_batch")
def process_risk_scoring_batch(self, batch_size: int = 20):
    """
    Celery task: Score a batch of risk events from risk_entities stream.
    Non-blocking -- reads up to batch_size, processes, returns.
    """
    from ..ingestion.pipeline import stage_score_risks
    import uuid

    run_id = uuid.uuid4().hex[:8]
    logger.info(f"Risk scoring batch task started (run_id={run_id})")
    return stage_score_risks(run_id, batch_size)


@celery_app.task(bind=True, name="src.risk_engine.workers.process_alerts_batch")
def process_alerts_batch(self, batch_size: int = 20):
    """
    Celery task: Generate alerts from a batch of scored risks.
    Non-blocking -- reads up to batch_size, processes, returns.
    """
    from ..ingestion.pipeline import stage_generate_alerts
    import uuid

    run_id = uuid.uuid4().hex[:8]
    logger.info(f"Alert generation batch task started (run_id={run_id})")
    return stage_generate_alerts(run_id, batch_size)


# ---------------------------------------------------------------
# Legacy task names (kept for backward compat, delegate to batch)
# ---------------------------------------------------------------

@celery_app.task(bind=True, name="src.risk_engine.workers.process_risk_extraction")
def process_risk_extraction_task(self):
    """Legacy: delegates to batch extraction."""
    return process_risk_extraction_batch(batch_size=50)


@celery_app.task(bind=True, name="src.risk_engine.workers.process_risk_scoring")
def process_risk_scoring_task(self):
    """Legacy: delegates to batch scoring."""
    return process_risk_scoring_batch(batch_size=50)


@celery_app.task(bind=True, name="src.risk_engine.workers.process_alerts")
def process_alerts_task(self):
    """Legacy: delegates to batch alerts."""
    return process_alerts_batch(batch_size=50)
