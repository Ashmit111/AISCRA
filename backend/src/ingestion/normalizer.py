"""
Article Normalizer
Converts articles from different sources into a standard format
"""

import uuid
from datetime import datetime
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def normalize_newsapi_article(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a NewsAPI article to standard format
    
    Args:
        raw: Raw article from NewsAPI
    
    Returns:
        Normalized article dictionary
    """
    return {
        "event_id": str(uuid.uuid4()),
        "timestamp": _parse_timestamp(raw.get("publishedAt")),
        "source": "NewsAPI",
        "headline": raw.get("title", ""),
        "body": raw.get("content") or raw.get("description", ""),
        "url": raw.get("url", ""),
        "entities_mentioned": [],  # Filled by NER in risk extraction
        "raw_relevance_score": 0.0,  # Filled by relevance filter
        "processed": False,
        "risk_extracted": False,
        "risk_event_id": None
    }


def normalize_gdelt_article(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a GDELT article to standard format
    
    Args:
        raw: Raw article from GDELT
    
    Returns:
        Normalized article dictionary
    """
    return {
        "event_id": str(uuid.uuid4()),
        "timestamp": _parse_timestamp(raw.get("seendate")),
        "source": "GDELT",
        "headline": raw.get("title", ""),
        "body": raw.get("sharing_text", ""),
        "url": raw.get("url", ""),
        "entities_mentioned": [],
        "raw_relevance_score": 0.0,
        "processed": False,
        "risk_extracted": False,
        "risk_event_id": None
    }


def normalize_generic_article(
    headline: str,
    body: str,
    url: str,
    source: str,
    published_at: Any = None
) -> Dict[str, Any]:
    """
    Create a normalized article from generic fields
    
    Args:
        headline: Article headline
        body: Article body text
        url: Article URL
        source: Source name
        published_at: Publication timestamp
    
    Returns:
        Normalized article dictionary
    """
    return {
        "event_id": str(uuid.uuid4()),
        "timestamp": _parse_timestamp(published_at),
        "source": source,
        "headline": headline,
        "body": body,
        "url": url,
        "entities_mentioned": [],
        "raw_relevance_score": 0.0,
        "processed": False,
        "risk_extracted": False,
        "risk_event_id": None
    }


def _parse_timestamp(ts: Any) -> datetime:
    """
    Parse various timestamp formats to datetime
    
    Args:
        ts: Timestamp in various formats (str, datetime, None)
    
    Returns:
        datetime object (defaults to utcnow if parsing fails)
    """
    if isinstance(ts, datetime):
        return ts
    
    if isinstance(ts, str):
        # Try parsing ISO format
        try:
            # Handle ISO 8601 format (most common)
            return datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            pass
        
        # Try parsing common formats
        formats = [
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(ts, fmt)
            except ValueError:
                continue
    
    # Default to current time if parsing fails
    logger.warning(f"Could not parse timestamp: {ts}, using current time")
    return datetime.utcnow()


def validate_article(article: Dict[str, Any]) -> bool:
    """
    Validate that an article has required fields
    
    Args:
        article: Normalized article dictionary
    
    Returns:
        True if valid, False otherwise
    """
    required_fields = ["event_id", "timestamp", "source", "headline", "url"]
    
    for field in required_fields:
        if field not in article or not article[field]:
            logger.warning(f"Article missing required field: {field}")
            return False
    
    # Headline should have some minimum length
    if len(article["headline"]) < 10:
        logger.warning("Article headline too short")
        return False
    
    return True
