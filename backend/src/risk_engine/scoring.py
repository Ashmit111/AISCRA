"""
Risk Scoring Engine
Calculates risk scores using formula: (Probability × Impact × Urgency) / Mitigation
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def calculate_risk_score(
    risk_data: Dict[str, Any],
    supplier: Dict[str, Any],
    company_profile: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate risk score for an extracted risk event
    
    Args:
        risk_data: Extracted risk data from Gemini
        supplier: Affected supplier document
        company_profile: Company profile document
    
    Returns:
        Dictionary with score and component breakdown
    """
    # ============== PROBABILITY (0.0 - 1.0) ==============
    prob_map = {
        "critical": 0.95,
        "high": 0.80,
        "medium": 0.55,
        "low": 0.25
    }
    probability = prob_map.get(risk_data.get("severity", "medium"), 0.55)
    
    # Adjust for confirmation status
    is_confirmed = risk_data.get("is_confirmed", "uncertain")
    if is_confirmed == "uncertain":
        probability *= 0.7
    elif is_confirmed == "false" or is_confirmed == False:
        probability *= 0.3
    
    logger.debug(f"Probability: {probability:.3f}")
    
    # ============== IMPACT (1 - 10) ==============
    
    # 1. Dependency ratio (how much of material comes from this supplier)
    dependency_ratio = supplier.get("supply_volume_pct", 50) / 100.0
    
    # 2. Material criticality (from company profile)
    material = supplier.get("supplies", ["unknown"])[0]
    material_criticality = company_profile.get("material_criticality", {}).get(
        material, 5
    )
    
    # 3. Inventory buffer (how long can we survive without this supplier)
    inventory_days = company_profile.get("inventory_days", {}).get(material, 0)
    buffer_score = 1.0 / (1.0 + inventory_days / 30.0)  # Normalize to 0-1
    
    # Calculate impact (1-10 scale)
    impact = dependency_ratio * (material_criticality / 10.0) * buffer_score * 10
    impact = max(1.0, min(10.0, impact))  # Clamp to 1-10
    
    logger.debug(
        f"Impact: {impact:.2f} (dep={dependency_ratio:.2f}, "
        f"crit={material_criticality}, buffer={buffer_score:.2f})"
    )
    
    # ============== URGENCY (0.5 - 2.0) ==============
    urgency_map = {
        "immediate": 2.0,
        "days": 1.5,
        "weeks": 1.0,
        "months": 0.5
    }
    urgency = urgency_map.get(risk_data.get("time_horizon", "weeks"), 1.0)
    
    logger.debug(f"Urgency: {urgency}")
    
    # ============== MITIGATION (0.5 - 2.0) ==============
    
    # Count available alternate suppliers for this material
    num_alternates = count_alternate_suppliers(material, company_profile)
    
    # More alternates = better mitigation = higher divisor (lower final score)
    mitigation = 1.0 + min(num_alternates * 0.2, 1.0)  # Max 2.0
    
    # Adjust for single-source dependency
    if supplier.get("is_single_source", False):
        mitigation = 0.5  # Worst case - no alternatives
    
    logger.debug(f"Mitigation: {mitigation} (alternates={num_alternates})")
    
    # ============== FINAL SCORE ==============
    score = (probability * impact * urgency) / mitigation
    
    # Map score to severity band
    severity_band = score_to_band(score)
    
    logger.info(
        f"Risk score calculated: {score:.2f} ({severity_band}) - "
        f"P={probability:.2f}, I={impact:.2f}, U={urgency}, M={mitigation}"
    )
    
    return {
        "risk_score": round(score, 2),
        "severity_band": severity_band,
        "components": {
            "probability": round(probability, 3),
            "impact": round(impact, 2),
            "urgency": urgency,
            "mitigation": mitigation
        }
    }


def score_to_band(score: float) -> str:
    """
    Map numerical score to severity band
    
    Args:
        score: Risk score
    
    Returns:
        Severity band string
    """
    if score >= 10.0:
        return "critical"
    elif score >= 6.0:
        return "high"
    elif score >= 3.0:
        return "medium"
    else:
        return "low"


def count_alternate_suppliers(material: str, company_profile: Dict) -> int:
    """
    Count available alternate suppliers for a material
    
    Args:
        material: Material name
        company_profile: Company profile with suppliers
    
    Returns:
        Number of alternate suppliers
    """
    if "suppliers" not in company_profile:
        return 0
    
    count = 0
    for supplier in company_profile["suppliers"]:
        # Check if supplier provides this material and is available
        supplies = supplier.get("supplies", [])
        status = supplier.get("status", "active")
        
        if material.lower() in [s.lower() for s in supplies]:
            if status in ["active", "alternate", "pre_qualified"]:
                count += 1
    
    # Subtract 1 for the currently affected supplier
    return max(0, count - 1)


def calculate_batch_scores(
    risk_events: List[Dict[str, Any]],
    suppliers_map: Dict[str, Dict],
    company_profile: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Calculate scores for multiple risk events in batch
    
    Args:
        risk_events: List of risk event dictionaries
        suppliers_map: Map of supplier_name -> supplier document
        company_profile: Company profile
    
    Returns:
        List of risk events with calculated scores
    """
    scored_events = []
    
    for risk_event in risk_events:
        try:
            # Find affected supplier
            affected_nodes = risk_event.get("affected_supply_chain_nodes", [])
            if not affected_nodes:
                logger.warning(f"Risk event has no affected suppliers, skipping scoring")
                continue
            
            # Use first affected supplier for scoring
            supplier_name = affected_nodes[0]
            supplier = suppliers_map.get(supplier_name)
            
            if not supplier:
                logger.warning(f"Supplier '{supplier_name}' not found in map, skipping")
                continue
            
            # Calculate score
            score_result = calculate_risk_score(risk_event, supplier, company_profile)
            
            # Add score to risk event
            risk_event.update({
                "risk_score": score_result["risk_score"],
                "severity_band": score_result["severity_band"],
                "risk_score_components": score_result["components"]
            })
            
            scored_events.append(risk_event)
        
        except Exception as e:
            logger.error(f"Error scoring risk event: {e}", exc_info=True)
            continue
    
    return scored_events
