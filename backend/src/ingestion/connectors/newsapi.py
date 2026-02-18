"""
NewsAPI Connector
Fetches news articles from NewsAPI.org based on company profile keywords
"""

import requests
from typing import List, Dict, Any
import logging

from .base import Connector
from ...utils.config import settings
from ...models.db import get_company_profile

logger = logging.getLogger(__name__)


class NewsAPIConnector(Connector):
    """Connector for NewsAPI.org"""
    
    def __init__(self, api_key: str = None, company_profile: Dict = None):
        """
        Initialize NewsAPI connector
        
        Args:
            api_key: NewsAPI API key (defaults to settings.newsapi_key)
            company_profile: Company profile dict (loaded from DB if not provided)
        """
        super().__init__("NewsAPI")
        self.api_key = api_key or settings.newsapi_key
        self.base_url = "https://newsapi.org/v2/everything"
        
        # Load company profile if not provided
        if company_profile is None:
            company_profile = get_company_profile()
            if company_profile is None:
                raise ValueError("Company profile not found in database")
        
        self.company_profile = company_profile
        self.keywords = self._build_keywords(company_profile)
        logger.info(f"Built {len(self.keywords)} keywords from company profile")
    
    def _build_keywords(self, profile: Dict) -> List[str]:
        """
        Build search keywords from company profile
        
        Args:
            profile: Company profile dictionary
        
        Returns:
            List of keywords for news search
        """
        keywords = []
        
        # Company name
        keywords.append(profile["company_name"])
        
        # Supplier names (Tier-1 priority)
        if "suppliers" in profile:
            for supplier in profile["suppliers"]:
                keywords.append(supplier["name"])
        
        # Raw materials
        if "raw_materials" in profile:
            keywords.extend(profile["raw_materials"])
        
        # Key geographies
        if "key_geographies" in profile:
            keywords.extend(profile["key_geographies"])
        
        return keywords
    
    def validate_config(self) -> bool:
        """Validate API key is present"""
        if not self.api_key:
            logger.error("NewsAPI API key not configured")
            return False
        return True
    
    def fetch(self, max_articles: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch recent news articles from NewsAPI
        
        Args:
            max_articles: Maximum number of articles to fetch
        
        Returns:
            List of raw articles
        """
        if not self.validate_config():
            logger.error("NewsAPI configuration invalid, skipping fetch")
            return []
        
        all_articles = []
        
        # NewsAPI query string limit is ~500 chars, so we batch keywords
        # Use top priority keywords (company + top suppliers + critical materials)
        priority_keywords = self.keywords[:5]  # Top 5 most important
        
        query = " OR ".join(f'"{kw}"' for kw in priority_keywords)
        
        logger.info(f"Fetching news with query: {query[:100]}...")
        
        try:
            params = {
                "q": query,
                "sortBy": "publishedAt",
                "language": "en",
                "pageSize": min(max_articles, 100),  # NewsAPI max is 100
                "apiKey": self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("status") == "ok":
                articles = data.get("articles", [])
                logger.info(f"Fetched {len(articles)} articles from NewsAPI")
                return articles
            else:
                logger.error(f"NewsAPI error: {data.get('message', 'Unknown error')}")
                return []
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching from NewsAPI: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in NewsAPI fetch: {e}", exc_info=True)
            return []
    
    def fetch_by_keyword(self, keyword: str, max_articles: int = 20) -> List[Dict[str, Any]]:
        """
        Fetch articles for a specific keyword
        
        Args:
            keyword: Specific keyword to search
            max_articles: Maximum articles to fetch
        
        Returns:
            List of raw articles
        """
        try:
            params = {
                "q": f'"{keyword}"',
                "sortBy": "publishedAt",
                "language": "en",
                "pageSize": min(max_articles, 100),
                "apiKey": self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "ok":
                articles = data.get("articles", [])
                logger.info(f"Fetched {len(articles)} articles for keyword '{keyword}'")
                return articles
            
            return []
        
        except Exception as e:
            logger.error(f"Error fetching articles for keyword '{keyword}': {e}")
            return []
