"""
Recommendation Text Generator
Uses Gemini to generate natural language recommendations
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def generate_recommendation_text(
    alert: Dict[str, Any],
    alternates: List[Dict[str, Any]],
    company_profile: Dict[str, Any],
    gemini_client
) -> str:
    """
    Generate natural language recommendation using Gemini
    
    Args:
        alert: Alert document
        alternates: List of alternate suppliers
        company_profile: Company profile
        gemini_client: Gemini client instance
    
    Returns:
        Recommendation text (3-4 sentences)
    """
    # Format alternates for prompt
    alternates_text = "\n".join([
        f"  {i+1}. {alt['name']} ({alt['country']}) - Score: {alt['score']}/10, "
        f"Lead time: {alt['lead_time_weeks']} weeks, "
        f"Approved: {'Yes' if alt.get('approved_vendor') else 'No'}"
        for i, alt in enumerate(alternates[:3])
    ])
    
    prompt = f"""You are a supply chain advisor for {company_profile['company_name']}.

ALERT DETAILS:
- Title: {alert['title']}
- Risk Score: {alert['risk_score']} ({alert['severity_band'].upper()})
- Affected Supplier: {alert['affected_supplier']}
- Affected Material: {alert['affected_material']}

TOP ALTERNATE SUPPLIERS:
{alternates_text}

Write a concise (3-4 sentences) recommendation for the supply chain manager.
Include:
1. Urgency level and immediate action needed
2. Top recommended supplier and why
3. Risk mitigation strategy

Use professional but direct language. No bullet points - write flowing sentences."""
    
    try:
        recommendation = gemini_client.generate_text(
            prompt,
            use_pro=False,  # Flash is sufficient
            temperature=0.5
        )
        
        logger.info(f"Generated recommendation for alert {alert.get('_id', 'unknown')}")
        return recommendation.strip()
    
    except Exception as e:
        logger.error(f"Error generating recommendation text: {e}")
        # Fallback to template
        if alternates:
            top = alternates[0]
            return (
                f"This {alert['severity_band']} priority risk requires immediate attention. "
                f"We recommend engaging {top['name']} as an alternate supplier, "
                f"with a score of {top['score']}/10 and {top['lead_time_weeks']}-week lead time. "
                f"Begin qualification process immediately to mitigate supply disruption risk."
            )
        else:
            return (
                f"This {alert['severity_band']} priority risk requires immediate attention. "
                f"No pre-qualified alternates are available. "
                f"Recommend emergency supplier sourcing and increasing inventory buffer."
            )


def generate_alert_title(risk_event: Dict[str, Any]) -> str:
    """
    Generate concise alert title from risk event
    
    Args:
        risk_event: Risk event document
    
    Returns:
        Alert title string
    """
    risk_type = risk_event.get("risk_type", "unknown").replace("_", " ").title()
    affected = risk_event.get("affected_supply_chain_nodes", ["Unknown"])
    affected_str = affected[0] if affected else "Supply Chain"
    
    return f"{risk_type} Risk: {affected_str}"


def generate_alert_description(risk_event: Dict[str, Any]) -> str:
    """
    Generate alert description from risk event
    
    Args:
        risk_event: Risk event document
    
    Returns:
        Alert description
    """
    reasoning = risk_event.get("reasoning", "Supply chain disruption detected")
    entities = risk_event.get("affected_entities", [])
    
    description = reasoning
    
    if entities:
        description += f" Affected entities: {', '.join(entities[:5])}."
    
    return description
