"""
Google Gemini AI Client
Handles LLM-based risk extraction and classification using Gemini API
"""

import google.generativeai as genai
import json
import logging
from typing import Dict, Any, Optional

from ..utils.config import settings
from ..models.db import get_company_profile

logger = logging.getLogger(__name__)


class GeminiClient:
    """Client for Google Gemini API operations"""
    
    def __init__(self, api_key: str = None):
        """
        Initialize Gemini client
        
        Args:
            api_key: Gemini API key (defaults to settings)
        """
        self.api_key = api_key or settings.gemini_api_key
        genai.configure(api_key=self.api_key)
        
        # Initialize models
        self.model_flash = genai.GenerativeModel("gemini-1.5-flash")
        self.model_pro = genai.GenerativeModel("gemini-1.5-pro")
        
        logger.info("Gemini client initialized with Flash and Pro models")
    
    def extract_risk(
        self,
        article: Dict[str, Any],
        company_profile: Dict,
        use_pro: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Extract structured risk data from an article
        
        Args:
            article: Normalized article dictionary
            company_profile: Company profile for context
            use_pro: Use Pro model instead of Flash (for complex geopolitical analysis)
        
        Returns:
            Extracted risk dictionary or None if extraction fails
        """
        # Build context from company profile
        supplier_list = ", ".join(
            s["name"] for s in company_profile.get("suppliers", [])
        )
        materials_list = ", ".join(company_profile.get("raw_materials", []))
        geographies = ", ".join(company_profile.get("key_geographies", []))
        
        # Build prompt
        prompt = self._build_extraction_prompt(
            company_name=company_profile["company_name"],
            supplier_list=supplier_list,
            materials_list=materials_list,
            geographies=geographies,
            article_text=f"{article['headline']}\n\n{article['body']}"
        )
        
        # Select model
        model = self.model_pro if use_pro else self.model_flash
        model_name = "Pro" if use_pro else "Flash"
        
        try:
            logger.debug(f"Extracting risk using Gemini {model_name}")
            
            # Generate with JSON mode
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.1,  # Low temperature for consistent extraction
                )
            )
            
            # Parse JSON response
            risk_data = json.loads(response.text)
            
            logger.info(
                f"Risk extracted - Type: {risk_data.get('risk_type', 'unknown')}, "
                f"Is Risk: {risk_data.get('is_risk', False)}, "
                f"Severity: {risk_data.get('severity', 'unknown')}"
            )
            
            return risk_data
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {e}")
            logger.error(f"Response text: {response.text if 'response' in locals() else 'N/A'}")
            return None
        except Exception as e:
            logger.error(f"Error in Gemini risk extraction: {e}", exc_info=True)
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
        
        prompt = f"""You are a supply chain risk analyst for {company_name}.

Company's key suppliers: {supplier_list}
Company's raw materials: {materials_list}
Key geographies: {geographies}

Analyze the following news article and return a JSON object ONLY (no explanation):

Article:
{article_text}

JSON schema to follow:
{{
  "is_risk": true or false,
  "risk_type": "geopolitical | natural_disaster | financial | regulatory | operational | cybersecurity | esg | other",
  "affected_entities": ["list of companies, countries, or materials mentioned"],
  "affected_supply_chain_nodes": ["names matching our supplier list or materials exactly"],
  "severity": "critical | high | medium | low",
  "is_confirmed": "true | false | uncertain",
  "time_horizon": "immediate | days | weeks | months",
  "reasoning": "one sentence explaining the link to our supply chain",
  "recommended_action": "one sentence immediate action"
}}

Rules:
- Only set is_risk=true if this directly affects our suppliers, materials, or geographies
- affected_supply_chain_nodes must match names from the supplier list exactly (case-insensitive)
- Be conservative: if connection is weak or speculative, set is_risk=false
- severity should reflect potential operational impact to {company_name}
"""
        return prompt
    
    def get_embedding(self, text: str) -> list:
        """
        Get embedding vector for text using Gemini embedding model
        
        Args:
            text: Text to embed
        
        Returns:
            Embedding vector (list of floats)
        """
        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="SEMANTIC_SIMILARITY"
            )
            return result["embedding"]
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            return []
    
    def generate_text(
        self,
        prompt: str,
        use_pro: bool = False,
        temperature: float = 0.7
    ) -> str:
        """
        Generate text using Gemini
        
        Args:
            prompt: Input prompt
            use_pro: Use Pro model instead of Flash
            temperature: Generation temperature (0.0-1.0)
        
        Returns:
            Generated text
        """
        model = self.model_pro if use_pro else self.model_flash
        
        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature
                )
            )
            return response.text
        except Exception as e:
            logger.error(f"Error generating text: {e}")
            return ""


# Global Gemini client instance
_gemini_client: Optional[GeminiClient] = None


def get_gemini_client() -> GeminiClient:
    """Get global Gemini client instance"""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client
