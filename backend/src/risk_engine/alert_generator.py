"""
Alert Generation System
Creates actionable alerts from risk events and triggers notifications
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pymongo.database import Database

from ..utils.config import settings
from ..recommender.supplier_finder import find_alternates
from ..recommender.recommendation_text import (
    generate_recommendation_text,
    generate_alert_title,
    generate_alert_description
)

logger = logging.getLogger(__name__)


def should_create_alert(risk_event: Dict[str, Any]) -> bool:
    """
    Determine if a risk event should generate an alert
    
    Args:
        risk_event: Risk event document
    
    Returns:
        True if alert should be created
    """
    risk_score = risk_event.get("risk_score", 0.0)
    threshold = settings.alert_threshold_score
    
    # Only create alerts for risks above threshold
    if risk_score < threshold:
        logger.debug(
            f"Risk score {risk_score:.2f} below threshold {threshold}, "
            f"skipping alert"
        )
        return False
    
    # Check if risk actually affects supply chain nodes
    affected_nodes = risk_event.get("affected_supply_chain_nodes", [])
    if not affected_nodes:
        logger.debug("No supply chain nodes affected, skipping alert")
        return False
    
    return True


def create_alert(
    risk_event: Dict[str, Any],
    db: Database,
    gemini_client: Optional[Any] = None
) -> Optional[str]:
    """
    Create an alert from a risk event
    
    Args:
        risk_event: Risk event document
        db: MongoDB database instance
        gemini_client: Gemini client for generating recommendations (optional)
    
    Returns:
        Alert ID if created, None otherwise
    """
    if not should_create_alert(risk_event):
        return None
    
    try:
        # Get company profile
        company_id = risk_event.get("company_id", settings.company_id)
        company = db.companies.find_one({"_id": company_id})
        if not company:
            logger.error(f"Company {company_id} not found")
            return None
        
        # Extract primary affected supplier
        affected_nodes = risk_event.get("affected_supply_chain_nodes", [])
        primary_supplier_name = affected_nodes[0] if affected_nodes else "Unknown"
        
        # Find supplier document
        supplier = db.suppliers.find_one({
            "name": primary_supplier_name,
            "company_id": company_id
        })
        
        if not supplier:
            logger.warning(f"Supplier '{primary_supplier_name}' not found in database")
            affected_material = "unknown"
        else:
            affected_material = supplier.get("supplies", ["unknown"])[0]
        
        # Generate alert content
        title = generate_alert_title(risk_event)
        description = generate_alert_description(risk_event)
        
        # Find alternate suppliers if supplier was found
        alternates = []
        recommendation_text = None
        
        if supplier:
            logger.info(f"Finding alternates for supplier: {supplier['name']}")
            alternates_raw = find_alternates(str(supplier["_id"]), db, max_results=5)
            
            # Convert to alert format
            for alt in alternates_raw:
                alternates.append({
                    "supplier_id": alt["supplier_id"],
                    "name": alt["name"],
                    "score": alt["score"],
                    "lead_time_weeks": alt["lead_time_weeks"],
                    "approved_vendor": alt["approved_vendor"],
                    "country": alt["country"],
                    "score_breakdown": alt["score_breakdown"]
                })
            
            # Generate recommendation text
            if gemini_client and alternates:
                alert_data = {
                    "_id": "temp",
                    "title": title,
                    "risk_score": risk_event["risk_score"],
                    "severity_band": risk_event["severity_band"],
                    "affected_supplier": primary_supplier_name,
                    "affected_material": affected_material
                }
                recommendation_text = generate_recommendation_text(
                    alert_data,
                    alternates,
                    company,
                    gemini_client
                )
        
        # Create alert document
        alert = {
            "risk_event_id": str(risk_event["_id"]),
            "company_id": company_id,
            "severity_band": risk_event["severity_band"],
            "risk_score": risk_event["risk_score"],
            "title": title,
            "description": description,
            "affected_supplier": primary_supplier_name,
            "affected_material": affected_material,
            "recommendations": alternates,
            "recommendation_text": recommendation_text,
            "is_acknowledged": False,
            "acknowledged_by": None,
            "acknowledged_at": None,
            "resolved_at": None,
            "notification_sent": False,
            "notification_sent_at": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Insert into database
        result = db.alerts.insert_one(alert)
        alert_id = str(result.inserted_id)
        
        logger.info(
            f"✓ Created alert {alert_id}: {title} "
            f"(score={risk_event['risk_score']:.2f}, "
            f"alternates={len(alternates)})"
        )
        
        return alert_id
    
    except Exception as e:
        logger.error(f"Error creating alert: {e}", exc_info=True)
        return None


def batch_create_alerts(
    risk_events: List[Dict[str, Any]],
    db: Database,
    gemini_client: Optional[Any] = None
) -> List[str]:
    """
    Create alerts for multiple risk events
    
    Args:
        risk_events: List of risk event documents
        db: MongoDB database instance
        gemini_client: Gemini client (optional)
    
    Returns:
        List of created alert IDs
    """
    alert_ids = []
    
    for risk_event in risk_events:
        try:
            alert_id = create_alert(risk_event, db, gemini_client)
            if alert_id:
                alert_ids.append(alert_id)
        except Exception as e:
            logger.error(f"Error in batch alert creation: {e}")
            continue
    
    logger.info(f"Created {len(alert_ids)} alerts from {len(risk_events)} risk events")
    
    return alert_ids


def update_alert_with_recommendations(
    alert_id: str,
    recommendation_text: str,
    db: Database
) -> bool:
    """
    Update existing alert with recommendation text
    
    Args:
        alert_id: Alert ID
        recommendation_text: Generated recommendation
        db: MongoDB database instance
    
    Returns:
        True if updated successfully
    """
    try:
        result = db.alerts.update_one(
            {"_id": alert_id},
            {
                "$set": {
                    "recommendation_text": recommendation_text,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"Updated alert {alert_id} with recommendations")
            return True
        
        return False
    
    except Exception as e:
        logger.error(f"Error updating alert {alert_id}: {e}")
        return False


def get_unacknowledged_alerts(
    db: Database,
    company_id: Optional[str] = None,
    severity: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get unacknowledged alerts
    
    Args:
        db: MongoDB database instance
        company_id: Filter by company ID (optional)
        severity: Filter by severity band (optional)
    
    Returns:
        List of alert documents
    """
    query = {"is_acknowledged": False}
    
    if company_id:
        query["company_id"] = company_id
    
    if severity:
        query["severity_band"] = severity
    
    alerts = list(
        db.alerts.find(query)
        .sort("risk_score", -1)
        .limit(100)
    )
    
    return alerts
