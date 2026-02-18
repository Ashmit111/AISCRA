"""
Celery Application Configuration
Task queue for background processing and scheduled jobs
"""

from celery import Celery
from celery.schedules import crontab
import logging

from ..utils.config import settings

logger = logging.getLogger(__name__)


# Initialize Celery app
celery_app = Celery(
    "supply_risk_ingestion",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Celery Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    'fetch-news-every-15-minutes': {
        'task': 'src.ingestion.celery_app.fetch_all_sources',
        'schedule': crontab(minute=f'*/{settings.news_fetch_interval_minutes}'),
    },
    'generate-daily-report': {
        'task': 'src.ingestion.celery_app.generate_daily_report_task',
        'schedule': crontab(hour=8, minute=0),  # Daily at 8:00 AM UTC
    },
    'generate-weekly-report': {
        'task': 'src.ingestion.celery_app.generate_weekly_report_task',
        'schedule': crontab(hour=9, minute=0, day_of_week=1),  # Mondays at 9:00 AM UTC
    },
}


@celery_app.task(bind=True, name='src.ingestion.celery_app.fetch_all_sources')
def fetch_all_sources(self):
    """
    Celery task: Fetch articles from all configured sources
    """
    from .connectors.newsapi import NewsAPIConnector
    from .normalizer import normalize_newsapi_article, validate_article
    from .deduplicator import is_duplicate
    from .redis_streams import push_to_stream, RedisStreamManager
    
    logger.info("=" * 60)
    logger.info("Starting scheduled news fetch from all sources")
    logger.info("=" * 60)
    
    total_fetched = 0
    total_new = 0
    total_duplicates = 0
    total_invalid = 0
    
    try:
        # NewsAPI Connector
        logger.info("Fetching from NewsAPI...")
        newsapi = NewsAPIConnector()
        articles = newsapi.fetch(max_articles=100)
        total_fetched += len(articles)
        
        for raw_article in articles:
            try:
                # Normalize
                normalized = normalize_newsapi_article(raw_article)
                
                # Validate
                if not validate_article(normalized):
                    total_invalid += 1
                    continue
                
                # Check for duplicates
                if is_duplicate(normalized):
                    total_duplicates += 1
                    continue
                
                # Push to normalized_events stream
                push_to_stream(RedisStreamManager.STREAM_NORMALIZED_EVENTS, normalized)
                total_new += 1
                
            except Exception as e:
                logger.error(f"Error processing article: {e}", exc_info=True)
                continue
        
        logger.info("=" * 60)
        logger.info(f"Fetch complete:")
        logger.info(f"  Total fetched: {total_fetched}")
        logger.info(f"  New articles: {total_new}")
        logger.info(f"  Duplicates: {total_duplicates}")
        logger.info(f"  Invalid: {total_invalid}")
        logger.info("=" * 60)
        
        return {
            "total_fetched": total_fetched,
            "total_new": total_new,
            "total_duplicates": total_duplicates,
            "total_invalid": total_invalid
        }
    
    except Exception as e:
        logger.error(f"Error in fetch_all_sources task: {e}", exc_info=True)
        raise


@celery_app.task(bind=True, name='src.ingestion.celery_app.test_task')
def test_task(self):
    """Simple test task to verify Celery is working"""
    logger.info("Test task executed successfully!")
    return {"status": "success", "message": "Celery is working"}


@celery_app.task(bind=True, name='src.ingestion.celery_app.generate_daily_report_task')
def generate_daily_report_task(self):
    """
    Celery task: Generate daily supply chain risk report using AI agent
    """
    from src.agent.report_generator import generate_scheduled_daily_report
    
    logger.info("=" * 60)
    logger.info("Generating daily supply chain risk report")
    logger.info("=" * 60)
    
    try:
        report_id = generate_scheduled_daily_report()
        logger.info(f"Daily report generated successfully: {report_id}")
        return {"status": "success", "report_id": report_id}
    except Exception as e:
        logger.error(f"Error generating daily report: {e}", exc_info=True)
        raise


@celery_app.task(bind=True, name='src.ingestion.celery_app.generate_weekly_report_task')
def generate_weekly_report_task(self):
    """
    Celery task: Generate weekly supply chain risk report using AI agent
    """
    from src.agent.report_generator import generate_scheduled_weekly_report
    
    logger.info("=" * 60)
    logger.info("Generating weekly supply chain risk report")
    logger.info("=" * 60)
    
    try:
        report_id = generate_scheduled_weekly_report()
        logger.info(f"Weekly report generated successfully: {report_id}")
        return {"status": "success", "report_id": report_id}
    except Exception as e:
        logger.error(f"Error generating weekly report: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    # For testing
    celery_app.start()

# Import workers to register tasks
from ..risk_engine import workers
