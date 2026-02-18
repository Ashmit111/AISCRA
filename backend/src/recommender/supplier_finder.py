"""
Alternate Supplier Finder
Finds and ranks alternate suppliers when disruptions occur
"""

import logging
from typing import Dict, Any, List, Optional
from pymongo.database import Database

logger = logging.getLogger(__name__)


def score_alternate_supplier(
    candidate: Dict[str, Any],
    disrupted: Dict[str, Any],
    required_volume: float
) -> Dict[str, Any]:
    """
    Score an alternate supplier using weighted multi-factor analysis
    
    Args:
        candidate: Candidate supplier document
        disrupted: Disrupted supplier document
        required_volume: Required supply volume percentage
    
    Returns:
        Scored supplier with breakdown
    """
    # ============== GEOGRAPHIC DIVERSITY (20%) ==============
    # Prefer different country/region from disrupted supplier
    geo_score = 1.0 if candidate.get("country") != disrupted.get("country") else 0.3
    
    # ============== CAPACITY COVERAGE (25%) ==============
    # Can this supplier meet the required volume?
    candidate_capacity = candidate.get("max_capacity", 0)
    if candidate_capacity > 0:
        cap_score = min(candidate_capacity / required_volume, 1.0)
    else:
        cap_score = 0.5  # Unknown capacity
    
    # ============== EXISTING RELATIONSHIP (20%) ==============
    # Prefer suppliers we already work with
    rel_score = 0.4  # Default: new vendor
    if candidate.get("approved_vendor", False):
        rel_score = 1.0  # Approved vendor
    elif candidate.get("pre_qualified", False):
        rel_score = 0.8  # Pre-qualified
    
    # ============== ESG SCORE (10%) ==============
    # Normalize 0-100 rating to 0-1
    esg_score = candidate.get("esg_score", 50) / 100.0
    
    # ============== FINANCIAL STABILITY (10%) ==============
    # Normalize credit rating
    financial_score = candidate.get("financial_health_score", 5.0) / 10.0
    
    # ============== SWITCHING COST (5%) ==============
    # Lower switching cost is better - invert the score
    switching_cost = candidate.get("switching_cost_estimate", 5.0)
    switch_score = 1.0 - (switching_cost / 10.0)
    
    # ============== LEAD TIME (10%) ==============
    # Faster delivery is better - invert
    lead_time_weeks = candidate.get("lead_time_weeks", 8)
    lead_score = 1.0 / (1.0 + lead_time_weeks / 4.0)
    
    # ============== CALCULATE FINAL SCORE (0-10 scale) ==============
    final_score = (
        geo_score   * 0.20 +
        cap_score   * 0.25 +
        rel_score   * 0.20 +
        esg_score   * 0.10 +
        financial_score * 0.10 +
        switch_score * 0.05 +
        lead_score   * 0.10
    ) * 10  # Scale to 0-10
    
    logger.debug(
        f"Scored {candidate['name']}: {final_score:.2f} "
        f"(geo={geo_score:.2f}, cap={cap_score:.2f}, rel={rel_score:.2f})"
    )
    
    return {
        "supplier_id": str(candidate["_id"]),
        "name": candidate["name"],
        "score": round(final_score, 2),
        "lead_time_weeks": lead_time_weeks,
        "approved_vendor": candidate.get("approved_vendor", False),
        "country": candidate["country"],
        "capacity": candidate.get("max_capacity"),
        "esg_score": candidate.get("esg_score"),
        "score_breakdown": {
            "geographic_diversity": round(geo_score, 2),
            "capacity": round(cap_score, 2),
            "relationship": round(rel_score, 2),
            "esg": round(esg_score, 2),
            "financial": round(financial_score, 2),
            "switching_cost": round(switch_score, 2),
            "lead_time": round(lead_score, 2)
        }
    }


def find_alternates(
    disrupted_supplier_id: str,
    db: Database,
    max_results: int = 5
) -> List[Dict[str, Any]]:
    """
    Find and rank alternate suppliers for a disrupted supplier
    
    Args:
        disrupted_supplier_id: ID of disrupted supplier
        db: MongoDB database instance
        max_results: Maximum number of alternates to return
    
    Returns:
        List of scored alternate suppliers (sorted by score descending)
    """
    # Get disrupted supplier
    disrupted = db.suppliers.find_one({"_id": disrupted_supplier_id})
    if not disrupted:
        logger.error(f"Disrupted supplier {disrupted_supplier_id} not found")
        return []
    
    # Extract requirements
    material = disrupted.get("supplies", ["unknown"])[0]
    required_volume = disrupted.get("supply_volume_pct", 50)
    company_id = disrupted.get("company_id")
    
    logger.info(
        f"Finding alternates for {disrupted['name']} "
        f"(material={material}, volume={required_volume}%)"
    )
    
    # Query for candidate suppliers
    # Must: supply same material, not the disrupted supplier, available status
    query = {
        "supplies": material,
        "_id": {"$ne": disrupted_supplier_id},
        "status": {"$in": ["active", "alternate", "pre_qualified"]},
        "company_id": company_id
    }
    
    candidates = list(db.suppliers.find(query))
    logger.info(f"Found {len(candidates)} candidate suppliers")
    
    if not candidates:
        logger.warning(f"No alternate suppliers found for material: {material}")
        return []
    
    # Score each candidate
    scored_alternates = []
    for candidate in candidates:
        try:
            scored = score_alternate_supplier(candidate, disrupted, required_volume)
            scored_alternates.append(scored)
        except Exception as e:
            logger.error(f"Error scoring candidate {candidate.get('name')}: {e}")
            continue
    
    # Sort by score (descending)
    scored_alternates.sort(key=lambda x: x["score"], reverse=True)
    
    # Return top N
    top_alternates = scored_alternates[:max_results]
    
    logger.info(
        f"Top {len(top_alternates)} alternates: "
        f"{', '.join(f'{a['name']} ({a['score']})' for a in top_alternates[:3])}"
    )
    
    return top_alternates


def find_alternates_by_material(
    material: str,
    db: Database,
    company_id: str,
    exclude_supplier_id: Optional[str] = None,
    max_results: int = 5
) -> List[Dict[str, Any]]:
    """
    Find alternate suppliers for a specific material
    
    Args:
        material: Material name
        db: MongoDB database instance
        company_id: Company ID
        exclude_supplier_id: Supplier ID to exclude (optional)
        max_results: Maximum results
    
    Returns:
        List of suppliers supplying this material
    """
    query = {
        "supplies": material,
        "company_id": company_id,
        "status": {"$in": ["active", "alternate", "pre_qualified"]}
    }
    
    if exclude_supplier_id:
        query["_id"] = {"$ne": exclude_supplier_id}
    
    suppliers = list(
        db.suppliers.find(query)
        .sort("risk_score_current", 1)  # Sort by lowest risk
        .limit(max_results)
    )
    
    # Convert to simple format
    results = []
    for supplier in suppliers:
        results.append({
            "supplier_id": str(supplier["_id"]),
            "name": supplier["name"],
            "country": supplier["country"],
            "tier": supplier.get("tier", 1),
            "lead_time_weeks": supplier.get("lead_time_weeks", 4),
            "capacity": supplier.get("max_capacity"),
            "risk_score": supplier.get("risk_score_current", 0.0)
        })
    
    return results
