"""
Relevance Filter
Pre-filters articles using embeddings to avoid expensive LLM calls on irrelevant content
"""

import logging
from typing import Dict, Any, List
import math

from .gemini_client import get_gemini_client
from ..utils.config import settings

logger = logging.getLogger(__name__)


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors
    
    Args:
        vec1: First embedding vector
        vec2: Second embedding vector
    
    Returns:
        Cosine similarity score (0-1)
    """
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    
    # Dot product
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    
    # Magnitudes
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)


def calculate_relevance_score(
    article: Dict[str, Any],
    company_keywords: List[str]
) -> float:
    """
    Calculate relevance score for an article
    
    Args:
        article: Article dictionary with headline and body
        company_keywords: List of keywords from company profile
    
    Returns:
        Relevance score (0.0-1.0)
    """
    gemini_client = get_gemini_client()
    
    # Combine article text
    article_text = f"{article.get('headline', '')} {article.get('body', '')}"
    
    # Build keyword text
    keyword_text = " ".join(company_keywords)
    
    try:
        # Get embeddings
        article_embedding = gemini_client.get_embedding(article_text[:1000])  # Limit length
        keyword_embedding = gemini_client.get_embedding(keyword_text[:1000])
        
        if not article_embedding or not keyword_embedding:
            logger.warning("Failed to get embeddings, returning default score")
            return 0.5
        
        # Calculate similarity
        score = cosine_similarity(article_embedding, keyword_embedding)
        
        logger.debug(f"Relevance score: {score:.3f} for article: {article.get('headline', '')[:80]}")
        
        return score
    
    except Exception as e:
        logger.error(f"Error calculating relevance score: {e}")
        return 0.5  # Default moderate score on error


def is_relevant(
    article: Dict[str, Any],
    company_keywords: List[str],
    threshold: float = None
) -> tuple[bool, float]:
    """
    Check if article is relevant to company
    
    Args:
        article: Article dictionary
        company_keywords: Company profile keywords
        threshold: Relevance threshold (defaults to settings.news_relevance_threshold)
    
    Returns:
        Tuple of (is_relevant, score)
    """
    if threshold is None:
        threshold = settings.news_relevance_threshold
    
    score = calculate_relevance_score(article, company_keywords)
    relevant = score >= threshold
    
    if not relevant:
        logger.info(
            f"Article filtered as irrelevant (score: {score:.3f}): "
            f"{article.get('headline', '')[:80]}"
        )
    
    return relevant, score


def build_company_keywords(company_profile: Dict) -> List[str]:
    """
    Build list of keywords from company profile for relevance checking
    
    Args:
        company_profile: Company profile dictionary
    
    Returns:
        List of keywords
    """
    keywords = []
    
    # Company name
    keywords.append(company_profile["company_name"])
    
    # Top 5 suppliers (Tier-1)
    if "suppliers" in company_profile:
        tier1_suppliers = [
            s for s in company_profile["suppliers"]
            if s.get("tier", 1) == 1
        ]
        # Sort by supply volume percentage
        tier1_suppliers.sort(
            key=lambda s: s.get("supply_volume_pct", 0),
            reverse=True
        )
        keywords.extend([s["name"] for s in tier1_suppliers[:5]])
    
    # Critical materials (top 3)
    if "material_criticality" in company_profile:
        critical_materials = sorted(
            company_profile["material_criticality"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        keywords.extend([mat for mat, _ in critical_materials])
    
    # Key geographies (top 3)
    if "key_geographies" in company_profile:
        keywords.extend(company_profile["key_geographies"][:3])
    
    logger.debug(f"Built {len(keywords)} keywords for relevance filter: {keywords}")
    
    return keywords
