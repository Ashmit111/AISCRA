"""
Configuration management for Supply Chain Risk Analysis System
Loads environment variables and provides centralized config access
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # API Keys
    gemini_api_key: str
    newsapi_key: str
    sendgrid_api_key: Optional[str] = None
    
    # Database
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "supply_risk_db"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    
    # News Ingestion
    news_fetch_interval_minutes: int = 15
    news_relevance_threshold: float = 0.3
    
    # Risk Scoring Thresholds
    alert_threshold_score: float = 3.0
    critical_threshold_score: float = 10.0
    high_threshold_score: float = 6.0
    medium_threshold_score: float = 3.0
    
    # Notifications
    slack_webhook_url: Optional[str] = None
    notification_email_from: str = "alerts@company.com"
    notification_email_to: str = "supplychain@company.com"
    
    # Company Configuration
    company_id: str = "company_nayara_energy"
    
    # Environment
    environment: str = "development"
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings
