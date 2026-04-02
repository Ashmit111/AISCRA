"""
Relevance Filter
Pre-filters articles using keyword matching to avoid expensive LLM calls on irrelevant content
"""

import logging
from typing import Dict, Any, List
import re

from ..utils.config import settings

logger = logging.getLogger(__name__)


def keyword_match_score(text: str, keywords: List[str]) -> float:
    """
    Calculate relevance score based on keyword matching (partial match)
    
    Args:
        text: Text to search in
        keywords: List of keywords to look for
    
    Returns:
        Score between 0.0 and 1.0
    """
    if not text or not keywords:
        return 0.5  # Default to moderate relevance if no data
    
    text_lower = text.lower()
    matched = 0
    
    for kw in keywords:
        kw_lower = kw.lower()
        # Partial match - check if keyword stem appears
        if len(kw_lower) > 3:
            # For longer keywords, check if first 4 chars match
            if kw_lower[:4] in text_lower:
                matched += 1
        else:
            if kw_lower in text_lower:
                matched += 1
    
    # Return ratio of matched keywords
    return matched / len(keywords) if keywords else 0.0


def calculate_relevance_score(
    article: Dict[str, Any],
    company_keywords: List[str]
) -> float:
    """
    Calculate relevance score for an article using keyword matching
    
    Args:
        article: Article dictionary with headline and body
        company_keywords: List of keywords from company profile
    
    Returns:
        Relevance score (0.0-1.0)
    """
    # Combine article text
    article_text = f"{article.get('headline', '')} {article.get('body', '')}"
    
    try:
        score = keyword_match_score(article_text, company_keywords)
        
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
    
    # Raw materials
    if "raw_materials" in company_profile:
        keywords.extend(company_profile["raw_materials"])
    
    # Key geographies (top 3)
    if "key_geographies" in company_profile:
        keywords.extend(company_profile["key_geographies"][:3])
    
    # Add supply chain risk terms (always relevant)
    risk_terms = [
        "supply chain", "shortage", "disruption", "sanctions",
        "tariff", "port", "shipping", "logistics", "factory",
        "oil", "crude", "refinery", "energy", "fuel",
        "Russia", "Ukraine", "embargo", "export ban"
    ]
    keywords.extend(risk_terms)
