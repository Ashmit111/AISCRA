"""
LangGraph Agent Tools
Provides tools for AI agent to query supply chain risk data
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from langchain.tools import tool
from src.models.db import db_manager
from src.recommender.supplier_finder import find_alternates
import logging

logger = logging.getLogger(__name__)


@tool
def query_risk_events(
    risk_type: Optional[str] = None,
    severity: Optional[str] = None,
    days_back: int = 7,
    limit: int = 10
) -> str:
    """
    Query recent risk events with optional filters.
    
    Args:
        risk_type: Filter by risk type (geopolitical, financial, natural_disaster, regulatory, operational, cybersecurity, esg, other)
        severity: Filter by severity band (critical, high, medium, low)
        days_back: Number of days to look back (default: 7)
        limit: Maximum number of results (default: 10)
    
    Returns:
        JSON string with list of risk events
    """
    try:
        # Build query
        query = {
            "created_at": {"$gte": datetime.utcnow() - timedelta(days=days_back)}
        }
        
        if risk_type:
            query["risk_type"] = risk_type
        
        if severity:
            query["severity_band"] = severity
        
        # Execute query
        risk_events = list(
            db_manager.risk_events
            .find(query)
            .sort("created_at", -1)
            .limit(limit)
        )
        
        # Format results
        results = []
        for event in risk_events:
            results.append({
                "id": str(event["_id"]),
                "title": event.get("title", ""),
                "risk_type": event.get("risk_type", ""),
                "severity": event.get("severity_band", ""),
                "risk_score": event.get("risk_score", 0.0),
                "affected_entities": event.get("affected_entities", []),
                "description": event.get("description", "")[:200],  # Truncate
                "created_at": event.get("created_at", datetime.utcnow()).isoformat()
            })
        
        if not results:
            return "No risk events found matching the criteria."
        
        return str({
            "count": len(results),
            "risk_events": results
        })
    
    except Exception as e:
        logger.error(f"Error querying risk events: {e}")
        return f"Error: {str(e)}"


@tool
def get_active_alerts(severity: Optional[str] = None, limit: int = 10) -> str:
    """
    Get currently active (unacknowledged) alerts.
    
    Args:
        severity: Filter by severity (critical, high, medium, low)
        limit: Maximum number of results (default: 10)
    
    Returns:
        JSON string with list of active alerts
    """
    try:
        # Build query
        query = {
            "acknowledged": False
        }
        
        if severity:
            query["severity"] = severity
        
        # Execute query
        alerts = list(
            db_manager.alerts
            .find(query)
            .sort([("risk_score", -1), ("created_at", -1)])
            .limit(limit)
        )
        
        # Format results
        results = []
        for alert in alerts:
            results.append({
                "id": str(alert["_id"]),
                "title": alert.get("title", ""),
                "severity": alert.get("severity", ""),
                "risk_score": alert.get("risk_score", 0.0),
                "affected_suppliers": alert.get("affected_suppliers", []),
                "affected_materials": alert.get("affected_materials", []),
                "recommendation": alert.get("ai_recommendation", ""),
                "alternate_suppliers": [
                    {
                        "name": alt.get("name", ""),
                        "score": alt.get("score", 0.0),
                        "reason": alt.get("reason", "")
                    }
                    for alt in alert.get("alternate_suppliers", [])[:3]  # Top 3
                ],
                "created_at": alert.get("created_at", datetime.utcnow()).isoformat()
            })
        
        if not results:
            return "No active alerts found."
        
        return str({
            "count": len(results),
            "alerts": results
        })
    
    except Exception as e:
        logger.error(f"Error getting active alerts: {e}")
        return f"Error: {str(e)}"


@tool
def find_alternate_suppliers_tool(
    supplier_name: str,
    material: Optional[str] = None
) -> str:
    """
    Find alternate suppliers for a given supplier and material.
    
    Args:
        supplier_name: Name of the current supplier
        material: Specific material to find alternates for (optional)
    
    Returns:
        JSON string with ranked list of alternate suppliers
    """
    try:
        # Get company profile
        company = db_manager.companies.find_one({})
        if not company:
            return "Error: Company profile not found"
        
        # Get current supplier
        current_supplier = db_manager.suppliers.find_one({
            "name": supplier_name
        })
        
        if not current_supplier:
            return f"Error: Supplier '{supplier_name}' not found"
        
        # Use material from supplier if not specified
        if not material:
            materials = current_supplier.get("supplies", [])
            material = materials[0] if materials else None
        
        if not material:
            return "Error: Material not specified and supplier has no materials"
        
        # Find alternates
        alternates = find_alternates(
            company_profile=company,
            current_supplier=current_supplier,
            material=material
        )
        
        # Format results
        results = []
        for alt in alternates:
            results.append({
                "name": alt.get("name", ""),
                "country": alt.get("country", ""),
                "score": alt.get("score", 0.0),
                "capacity": alt.get("max_capacity", 0),
                "lead_time_weeks": alt.get("lead_time_weeks", 0),
                "esg_score": alt.get("esg_score", 0),
                "status": alt.get("status", ""),
                "reason": alt.get("reason", "")
            })
        
        if not results:
            return f"No alternate suppliers found for {material}"
        
        return str({
            "supplier": supplier_name,
            "material": material,
            "alternates_count": len(results),
            "alternates": results
        })
    
    except Exception as e:
        logger.error(f"Error finding alternate suppliers: {e}")
        return f"Error: {str(e)}"


@tool
def get_supply_chain_summary() -> str:
    """
    Get high-level summary of supply chain status.
    
    Returns:
        JSON string with supply chain summary statistics
    """
    try:
        # Get company profile
        company = db_manager.companies.find_one({})
        if not company:
            return "Error: Company profile not found"
        
        # Supplier statistics
        total_suppliers = db_manager.suppliers.count_documents({})
        active_suppliers = db_manager.suppliers.count_documents({"status": "active"})
        at_risk_suppliers = db_manager.suppliers.count_documents({
            "risk_score_current": {"$gte": 3.0}
        })
        
        # Alert statistics
        total_alerts = db_manager.alerts.count_documents({})
        active_alerts = db_manager.alerts.count_documents({
            "status": "active",
            "acknowledged_at": {"$exists": False}
        })
        critical_alerts = db_manager.alerts.count_documents({
            "severity": "critical",
            "status": "active"
        })
        high_alerts = db_manager.alerts.count_documents({
            "severity": "high",
            "status": "active"
        })
        
        # Risk event statistics
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_risks = db_manager.risk_events.count_documents({
            "created_at": {"$gte": week_ago}
        })
        
        # Top risk types
        risk_type_pipeline = [
            {"$match": {"created_at": {"$gte": week_ago}}},
            {"$group": {"_id": "$risk_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 3}
        ]
        top_risk_types = list(db_manager.risk_events.aggregate(risk_type_pipeline))
        
        # Build summary
        summary = {
            "company_name": company.get("company_name", ""),
            "industry": company.get("industry", ""),
            "suppliers": {
                "total": total_suppliers,
                "active": active_suppliers,
                "at_risk": at_risk_suppliers
            },
            "alerts": {
                "total": total_alerts,
                "active": active_alerts,
                "critical": critical_alerts,
                "high": high_alerts
            },
            "risk_events_last_7_days": recent_risks,
            "top_risk_types": [
                {"type": item["_id"], "count": item["count"]}
                for item in top_risk_types
            ],
            "materials": company.get("raw_materials", []),
            "key_geographies": company.get("key_geographies", [])
        }
        
        return str(summary)
    
    except Exception as e:
        logger.error(f"Error getting supply chain summary: {e}")
        return f"Error: {str(e)}"


@tool
def get_risk_trend(
    supplier_name: Optional[str] = None,
    risk_type: Optional[str] = None,
    days_back: int = 30
) -> str:
    """
    Get risk trend over time, optionally filtered by supplier or risk type.
    
    Args:
        supplier_name: Filter by specific supplier (optional)
        risk_type: Filter by risk type (optional)
        days_back: Number of days to analyze (default: 30)
    
    Returns:
        JSON string with risk trend data
    """
    try:
        # Build query
        start_date = datetime.utcnow() - timedelta(days=days_back)
        match_query = {"created_at": {"$gte": start_date}}
        
        if risk_type:
            match_query["risk_type"] = risk_type
        
        if supplier_name:
            match_query["affected_entities"] = supplier_name
        
        # Aggregate by day
        pipeline = [
            {"$match": match_query},
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$created_at"
                        }
                    },
                    "count": {"$sum": 1},
                    "avg_score": {"$avg": "$risk_score"},
                    "max_score": {"$max": "$risk_score"}
                }
            },
            {"$sort": {"_id": 1}}
        ]
        
        trend_data = list(db_manager.risk_events.aggregate(pipeline))
        
        # Calculate statistics
        total_events = sum(item["count"] for item in trend_data)
        avg_daily = total_events / days_back if days_back > 0 else 0
        
        # Find change trend
        if len(trend_data) >= 2:
            recent_avg = sum(item["count"] for item in trend_data[-7:]) / 7
            older_avg = sum(item["count"] for item in trend_data[:-7]) / max(len(trend_data) - 7, 1)
            trend_direction = "increasing" if recent_avg > older_avg else "decreasing"
        else:
            trend_direction = "stable"
        
        result = {
            "period_days": days_back,
            "total_events": total_events,
            "avg_events_per_day": round(avg_daily, 2),
            "trend_direction": trend_direction,
            "daily_breakdown": [
                {
                    "date": item["_id"],
                    "count": item["count"],
                    "avg_score": round(item.get("avg_score", 0.0), 2),
                    "max_score": round(item.get("max_score", 0.0), 2)
                }
                for item in trend_data
            ]
        }
        
        if supplier_name:
            result["supplier"] = supplier_name
        if risk_type:
            result["risk_type"] = risk_type
        
        return str(result)
    
    except Exception as e:
        logger.error(f"Error getting risk trend: {e}")
        return f"Error: {str(e)}"


# Export all tools
AGENT_TOOLS = [
    query_risk_events,
    get_active_alerts,
    find_alternate_suppliers_tool,
    get_supply_chain_summary,
    get_risk_trend
]
