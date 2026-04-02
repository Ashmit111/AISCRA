"""
GDELT Connector
Fetches news articles from GDELT Project (free, no API key required)
Serves as a secondary/fallback source alongside NewsAPI
"""

import requests
from typing import List, Dict, Any
from datetime import datetime, timedelta
import logging

from .base import Connector
from ...models.db import get_company_profile

logger = logging.getLogger(__name__)

GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"


class GDELTConnector(Connector):
    """Connector for GDELT Project (free, unlimited)"""

    def __init__(self, company_profile: Dict = None):
        super().__init__("GDELT")
        if company_profile is None:
            company_profile = get_company_profile()
            if company_profile is None:
                raise ValueError("Company profile not found in database")
        self.company_profile = company_profile
        self.keywords = self._build_keywords(company_profile)
        logger.info(f"GDELT connector built {len(self.keywords)} keywords")

    def _build_keywords(self, profile: Dict) -> List[str]:
        keywords = []
        keywords.append(profile["company_name"])
        if "suppliers" in profile:
            for supplier in profile["suppliers"]:
                keywords.append(supplier["name"])
        if "raw_materials" in profile:
            keywords.extend(profile["raw_materials"])
        if "key_geographies" in profile:
            keywords.extend(profile["key_geographies"])
        return keywords

    def validate_config(self) -> bool:
        return True  # GDELT is free, no key needed

    def fetch(self, max_articles: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch recent articles from GDELT DOC API.
        GDELT returns articles from the last 24h matching the query.
        """
        if not self.validate_config():
            return []

        all_articles = []
        
        # Simple supply chain focused query (fewer terms = faster response)
        # GDELT requires OR queries to be wrapped in parentheses
        query = '("supply chain" OR "logistics disruption" OR "supplier shortage")'

        logger.info(f"GDELT query: {query}")

        try:
            params = {
                "query": query,
                "mode": "ArtList",
                "maxrecords": str(min(max_articles, 50)),
                "format": "json",
                "sort": "DateDesc",
                "timespan": "7d",
            }
            
            logger.info(f"GDELT request URL: {GDELT_DOC_API}")
            
            response = requests.get(GDELT_DOC_API, params=params, timeout=90)
            
            # Log response for debugging
            logger.info(f"GDELT response status: {response.status_code}")
            logger.info(f"GDELT response length: {len(response.text)} chars")
            
            if response.status_code == 429:
                logger.warning("GDELT rate limited - will retry next pipeline run")
                return []
            
            if response.status_code != 200:
                logger.error(f"GDELT returned status {response.status_code}: {response.text[:200]}")
                return []
            
            # Check if response is empty or not JSON
            response_text = response.text.strip()
            if not response_text:
                logger.warning("GDELT returned empty response")
                return []
            
            # Debug: log first part of response
            logger.info(f"GDELT response preview: {response_text[:200]}")
            
            data = response.json()
            raw_articles = data.get("articles", [])
            logger.info(f"GDELT returned {len(raw_articles)} articles")

            for art in raw_articles:
                all_articles.append({
                    "title": art.get("title", ""),
                    "url": art.get("url", ""),
                    "url_mobile": art.get("url_mobile", ""),
                    "seendate": art.get("seendate", ""),
                    "socialimage": art.get("socialimage", ""),
                    "domain": art.get("domain", ""),
                    "language": art.get("language", "English"),
                    "sourcecountry": art.get("sourcecountry", ""),
                    "sharing_text": art.get("title", ""),  # GDELT doesn't return body in free tier
                    "_source": "GDELT",
                })

            return all_articles[:max_articles]

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching from GDELT: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in GDELT fetch: {e}", exc_info=True)
            return []

    def fetch_by_keyword(self, keyword: str, max_articles: int = 20) -> List[Dict[str, Any]]:
        """Fetch articles for a single keyword from GDELT."""
        try:
            params = {
                "query": f'"{keyword}"',
                "mode": "ArtList",
                "maxrecords": str(min(max_articles, 250)),
                "format": "json",
                "sort": "DateDesc",
                "timespan": "24h",
            }
            response = requests.get(GDELT_DOC_API, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            articles = data.get("articles", [])
            logger.info(f"GDELT: {len(articles)} articles for keyword '{keyword}'")
            return articles
        except Exception as e:
            logger.error(f"GDELT keyword fetch error for '{keyword}': {e}")
            return []
