"""
Celery Application Configuration
Task queue for background processing and scheduled jobs.

The main periodic task is ``run_pipeline`` which executes the full
automated pipeline:  fetch -> extract -> score -> alert.
"""

from celery import Celery
from celery.schedules import crontab
import logging

from ..utils.config import settings

logger = logging.getLogger(__name__)


# --- Celery app ---
celery_app = Celery(
    "supply_risk_ingestion",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,       # 30 min hard limit
    task_soft_time_limit=25 * 60,  # 25 min soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)


# =====================================================================
# Celery Beat schedule -- everything is automatic
# =====================================================================
celery_app.conf.beat_schedule = {
    # Core pipeline: fetch + risk analysis, every N minutes
    "run-pipeline-periodic": {
        "task": "src.ingestion.celery_app.run_pipeline",
        "schedule": crontab(minute=f"*/{settings.news_fetch_interval_minutes}"),
    },

    # Daily AI report (8 AM UTC)
    "generate-daily-report": {
        "task": "src.ingestion.celery_app.generate_daily_report_task",
        "schedule": crontab(hour=8, minute=0),
    },

    # Weekly AI report (Monday 9 AM UTC)
    "generate-weekly-report": {
        "task": "src.ingestion.celery_app.generate_weekly_report_task",
        "schedule": crontab(hour=9, minute=0, day_of_week=1),
    },
}


# =====================================================================
# Tasks
# =====================================================================

@celery_app.task(bind=True, name="src.ingestion.celery_app.run_pipeline")
def run_pipeline(self):
    """
    Master pipeline task -- runs the full automated pipeline:
      1. Fetch articles (NewsAPI + GDELT)
      2. Filter & extract risks (Gemini AI)
      3. Calculate risk scores
      4. Generate alerts & notifications

    Triggered automatically by Celery Beat every N minutes,
    or manually via the /api/pipeline/trigger endpoint.
    """
    from .pipeline import run_full_pipeline

    logger.info("=" * 60)
    logger.info("CELERY: Triggering full pipeline run")
    logger.info("=" * 60)

    return run_full_pipeline()


# Legacy alias so old beat entries / manual calls still work
@celery_app.task(bind=True, name="src.ingestion.celery_app.fetch_all_sources")
def fetch_all_sources(self):
    """Backward-compatible task name.  Now delegates to the full pipeline."""
    from .pipeline import run_full_pipeline
    return run_full_pipeline()


@celery_app.task(bind=True, name="src.ingestion.celery_app.test_task")
def test_task(self):
    """Simple test task to verify Celery is working"""
    logger.info("Test task executed successfully!")
    return {"status": "success", "message": "Celery is working"}


@celery_app.task(bind=True, name="src.ingestion.celery_app.generate_daily_report_task")
def generate_daily_report_task(self):
    """Generate daily supply chain risk report using AI agent"""
    from src.agent.report_generator import generate_scheduled_daily_report

    logger.info("Generating daily supply chain risk report")
    try:
        report_id = generate_scheduled_daily_report()
        logger.info(f"Daily report generated: {report_id}")
        return {"status": "success", "report_id": report_id}
    except Exception as e:
        logger.error(f"Error generating daily report: {e}", exc_info=True)
        raise


@celery_app.task(bind=True, name="src.ingestion.celery_app.generate_weekly_report_task")
def generate_weekly_report_task(self):
    """Generate weekly supply chain risk report using AI agent"""
    from src.agent.report_generator import generate_scheduled_weekly_report

    logger.info("Generating weekly supply chain risk report")
    try:
        report_id = generate_scheduled_weekly_report()
        logger.info(f"Weekly report generated: {report_id}")
        return {"status": "success", "report_id": report_id}
    except Exception as e:
        logger.error(f"Error generating weekly report: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    celery_app.start()

# Import workers to register their tasks with this celery app
from ..risk_engine import workers  # noqa: F401, E402
