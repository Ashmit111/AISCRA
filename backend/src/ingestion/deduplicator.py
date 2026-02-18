"""
Article Deduplication using Redis
Prevents processing duplicate news articles using content fingerprinting
"""

import hashlib
import logging
from typing import Dict, Any
from .redis_streams import get_redis_client

logger = logging.getLogger(__name__)


def generate_fingerprint(article: Dict[str, Any]) -> str:
    """
    Generate a unique fingerprint for an article
    
    Args:
        article: Article dictionary with headline and optional body
    
    Returns:
        MD5 hash of normalized article content
    """
    # Normalize headline (lowercase, strip whitespace)
    headline = article.get("headline", "").lower().strip()
    
    # Create fingerprint from headline
    # Could also include first 100 chars of body for better accuracy
    content = headline
    if "body" in article and article["body"]:
        content += " " + article["body"][:100].lower().strip()
    
    fingerprint = hashlib.md5(content.encode()).hexdigest()
    return fingerprint


def is_duplicate(article: Dict[str, Any], ttl_seconds: int = 172800) -> bool:
    """
    Check if an article is a duplicate
    
    Args:
        article: Article dictionary
        ttl_seconds: Time to live for dedup key (default: 48 hours)
    
    Returns:
        True if duplicate, False if new
    """
    redis_client = get_redis_client()
    fingerprint = generate_fingerprint(article)
    key = f"dedup:{fingerprint}"
    
    # Try to set the key with NX (only if not exists)
    # Returns True if key was set (not a duplicate)
    # Returns False if key already exists (duplicate)
    was_set = redis_client.set(key, 1, nx=True, ex=ttl_seconds)
    
    if was_set:
        logger.debug(f"New article fingerprint: {fingerprint}")
        return False  # Not a duplicate
    else:
        logger.info(f"Duplicate article detected: {article.get('headline', 'unknown')[:80]}")
        return True  # Is a duplicate


def mark_as_seen(article: Dict[str, Any], ttl_seconds: int = 172800):
    """
    Explicitly mark an article as seen (for manual dedup)
    
    Args:
        article: Article dictionary
        ttl_seconds: Time to live for dedup key (default: 48 hours)
    """
    redis_client = get_redis_client()
    fingerprint = generate_fingerprint(article)
    key = f"dedup:{fingerprint}"
    redis_client.set(key, 1, ex=ttl_seconds)
    logger.debug(f"Marked article as seen: {fingerprint}")


def clear_dedup_cache():
    """Clear all deduplication keys (use with caution)"""
    redis_client = get_redis_client()
    keys = redis_client.keys("dedup:*")
    if keys:
        redis_client.delete(*keys)
        logger.info(f"Cleared {len(keys)} deduplication keys")
    else:
        logger.info("No deduplication keys to clear")
