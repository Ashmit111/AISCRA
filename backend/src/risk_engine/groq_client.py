"""
Groq AI Client
Handles LLM-based risk extraction using Groq API (fast inference)
"""

import json
import logging
import os
from typing import Dict, Any, Optional, List
import requests

from ..utils.config import settings

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqClient:
    """Client for Groq API operations - fast LLM inference"""
    
    def __init__(self, api_key: str = None):
        """
        Initialize Groq client
        
        Args:
            api_key: Groq API key
        """
        self.api_key = api_key or settings.groq_api_key or os.environ.get("GROQ_API_KEY", "")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not configured")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Use llama-3.3-70b for best quality, mixtral for speed
        self.model = "llama-3.3-70b-versatile"
        self.fast_model = "llama-3.1-8b-instant"
        
        logger.info(f"Groq client initialized with model: {self.model}")
    
    def extract_risk(
        self,
        article: Dict[str, Any],
        company_profile: Dict,
        use_fast: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Extract structured risk data from an article
        
        Args:
            article: Normalized article dictionary
            company_profile: Company profile for context
            use_fast: Use faster model for quick processing
        
        Returns:
            Extracted risk dictionary or None if extraction fails
        """
        # Build context from company profile
        supplier_list = ", ".join(
            s["name"] for s in company_profile.get("suppliers", [])
        ) if company_profile.get("suppliers") else "Not specified"
        materials_list = ", ".join(company_profile.get("raw_materials", [])) or "Not specified"
        geographies = ", ".join(company_profile.get("key_geographies", [])) or "Not specified"
        
        # Build prompt
        prompt = self._build_extraction_prompt(
            company_name=company_profile.get("company_name", "Unknown"),
            supplier_list=supplier_list,
            materials_list=materials_list,
            geographies=geographies,
            article_text=f"{article.get('headline', '')}\n\n{article.get('body', article.get('headline', ''))}"
        )
        
        model = self.fast_model if use_fast else self.model
        
        try:
            logger.debug(f"Extracting risk using Groq {model}")
            
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a supply chain risk analyst. Always respond with valid JSON only, no markdown or explanation."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 1024,
                "response_format": {"type": "json_object"}
            }
            
            response = requests.post(
                GROQ_API_URL,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Groq API error: {response.status_code} - {response.text[:200]}")
                return None
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # Parse JSON response
            risk_data = json.loads(content)
            
            logger.info(
                f"Risk extracted - Type: {risk_data.get('risk_type', 'unknown')}, "
                f"Is Risk: {risk_data.get('is_risk', False)}, "
                f"Severity: {risk_data.get('severity', 'unknown')}"
            )
            
            return risk_data
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Groq JSON response: {e}")
            return None
        except requests.exceptions.Timeout:
            logger.error("Groq API request timed out")
            return None
        except Exception as e:
            logger.error(f"Error in Groq risk extraction: {e}", exc_info=True)
            return None
    
    def _build_extraction_prompt(
        self,
        company_name: str,
        supplier_list: str,
        materials_list: str,
        geographies: str,
        article_text: str
    ) -> str:
        """Build the structured extraction prompt"""
        
        prompt = f"""You are a supply chain risk analyst for {company_name}, an oil refining company in India.

Company's key suppliers: {supplier_list}
Company's raw materials: {materials_list}
Key geographies: {geographies}

Analyze the following news article for POTENTIAL supply chain risks.

Article:
{article_text[:2000]}

Return a JSON object:
{{
  "is_risk": true or false,
  "risk_type": "geopolitical | natural_disaster | financial | regulatory | operational | cybersecurity | esg | other",
  "affected_entities": ["companies, countries, or commodities mentioned"],
  "affected_supply_chain_nodes": ["any matching suppliers, materials, or regions"],
  "severity": "critical | high | medium | low",
  "is_confirmed": true or false,
  "time_horizon": "immediate | days | weeks | months",
  "reasoning": "brief explanation of potential impact",
  "recommended_action": "suggested response"
}}

IMPORTANT - Set is_risk=true if the article:
- Mentions Russia, Ukraine, Middle East, or oil-producing regions
- Discusses oil, crude, energy, or fuel supply/prices
- Reports sanctions, trade restrictions, or geopolitical tensions
- Covers shipping, logistics, or port disruptions
- Mentions any of our suppliers or materials
- Could indirectly impact oil supply chains
- Be conservative: if connection is weak, set is_risk=false
- severity should reflect potential operational impact"""
        return prompt
    
    def batch_extract_risks(
        self,
        articles: List[Dict[str, Any]],
        company_profile: Dict
    ) -> List[Optional[Dict[str, Any]]]:
        """
        Extract risks from multiple articles
        
        Args:
            articles: List of article dictionaries
            company_profile: Company profile for context
        
        Returns:
            List of extracted risk data (None for failed extractions)
        """
        results = []
        for article in articles:
            result = self.extract_risk(article, company_profile, use_fast=True)
            results.append(result)
        return results


# Singleton instance
_client: Optional[GroqClient] = None


def get_groq_client(api_key: str = None) -> GroqClient:
    """Get or create Groq client singleton"""
    global _client
    if _client is None:
        _client = GroqClient(api_key=api_key)
    return _client
