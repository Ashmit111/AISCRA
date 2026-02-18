"""
FastAPI Main Application
REST API for Supply Chain Risk Analysis System
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import logging
from datetime import datetime, timedelta
from bson import ObjectId

from ..models.db import db_manager, get_company_profile
from ..utils.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Supply Chain Risk Analysis API",
    description="AI-powered real-time supply chain risk monitoring system using Multi-Agent AI",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Startup/Shutdown Events ====================

@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    logger.info("=" * 60)
    logger.info("Starting Supply Chain Risk Analysis API")
    logger.info("=" * 60)
    
    # Connect to MongoDB
    db_manager.connect()
    logger.info("✓ MongoDB connected")
    
    # Test company profile
    company = get_company_profile()
    if company:
        logger.info(f"✓ Company profile loaded: {company['company_name']}")
    else:
        logger.warning("⚠ No company profile found - run seed script")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down API...")
    db_manager.disconnect()


# ==================== Health Check ====================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Supply Chain Risk Analysis API",
        "status": "operational",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test MongoDB
        db_manager.db.command("ping")
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected",
            "company": settings.company_id
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


# ==================== Dashboard Endpoints ====================

@app.get("/api/dashboard/summary")
async def get_dashboard_summary():
    """
    Get dashboard summary statistics
    """
    try:
        company_id = settings.company_id
        db = db_manager.db
        
        # Aggregate alerts by severity
        pipeline = [
            {"$match": {"company_id": company_id, "acknowledged": False}},
            {"$group": {
                "_id": "$severity",
                "count": {"$sum": 1},
                "avg_score": {"$avg": "$risk_score"}
            }}
        ]
        
        severity_counts = {}
        for doc in db.alerts.aggregate(pipeline):
            severity_counts[doc["_id"]] = {
                "count": doc["count"],
                "avg_score": round(doc["avg_score"], 2)
            }
        
        # Count suppliers
        total_suppliers = db.suppliers.count_documents({"company_id": company_id})
        active_suppliers = db.suppliers.count_documents({
            "company_id": company_id,
            "status": "active"
        })
        
        # Count at-risk suppliers (risk_score_current >= 3.0)
        at_risk_suppliers = db.suppliers.count_documents({
            "company_id": company_id,
            "risk_score_current": {"$gte": 3.0}
        })
        
        # Count recent articles
        since_24h = datetime.utcnow() - timedelta(hours=24)
        recent_articles = db.articles.count_documents({
            "timestamp": {"$gte": since_24h}
        })
        
        # Count risk events
        recent_risks = db.risk_events.count_documents({
            "company_id": company_id,
            "timestamp": {"$gte": since_24h}
        })
        
        # Return in format expected by frontend
        return {
            "summary": {
                "active_alerts": sum(s.get("count", 0) for s in severity_counts.values()),
                "critical_alerts": severity_counts.get("critical", {}).get("count", 0),
                "high_alerts": severity_counts.get("high", {}).get("count", 0),
                "medium_alerts": severity_counts.get("medium", {}).get("count", 0),
                "low_alerts": severity_counts.get("low", {}).get("count", 0),
                "total_suppliers": total_suppliers,
                "active_suppliers": active_suppliers,
                "at_risk_suppliers": at_risk_suppliers
            }
        }
    
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Alert Endpoints ====================

@app.get("/api/alerts")
async def get_alerts(
    severity: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    limit: int = 50
):
    """
    Get alerts with optional filters
    """
    try:
        query = {"company_id": settings.company_id}
        
        if severity:
            query["severity_band"] = severity
        
        if acknowledged is not None:
            query["acknowledged"] = acknowledged
        
        alerts = list(
            db_manager.alerts.find(query)
            .sort("created_at", -1)
            .limit(limit)
        )
        
        # Convert ObjectId to string
        for alert in alerts:
            alert["_id"] = str(alert["_id"])
            if "risk_event_id" in alert:
                alert["risk_event_id"] = str(alert["risk_event_id"])
        
        return {"alerts": alerts, "count": len(alerts)}
    
    except Exception as e:
        logger.error(f"Error getting alerts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/alerts/{alert_id}")
async def get_alert(alert_id: str):
    """Get single alert by ID"""
    try:
        alert = db_manager.alerts.find_one({"_id": alert_id})
        
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        alert["_id"] = str(alert["_id"])
        if "risk_event_id" in alert:
            alert["risk_event_id"] = str(alert["risk_event_id"])
        
        return alert
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting alert {alert_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, acknowledged_by: str = "user"):
    """Acknowledge an alert"""
    try:
        # Convert string ID to ObjectId
        try:
            obj_id = ObjectId(alert_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid alert ID format")
        
        result = db_manager.alerts.update_one(
            {"_id": obj_id},
            {
                "$set": {
                    "acknowledged": True,
                    "acknowledged_by": acknowledged_by,
                    "acknowledged_at": datetime.utcnow()
                }
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return {"status": "acknowledged", "alert_id": alert_id}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging alert {alert_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Supplier Endpoints ====================

@app.get("/api/suppliers")
async def get_suppliers(
    status: Optional[str] = None,
    tier: Optional[int] = None
):
    """Get suppliers with optional filters"""
    try:
        query = {"company_id": settings.company_id}
        
        if status:
            query["status"] = status
        
        if tier:
            query["tier"] = tier
        
        suppliers = list(db_manager.suppliers.find(query).sort("name", 1))
        
        # Convert ObjectId to string
        for supplier in suppliers:
            supplier["_id"] = str(supplier["_id"])
        
        return {"suppliers": suppliers, "count": len(suppliers)}
    
    except Exception as e:
        logger.error(f"Error getting suppliers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/suppliers/{supplier_id}")
async def get_supplier(supplier_id: str):
    """Get single supplier by ID"""
    try:
        supplier = db_manager.suppliers.find_one({"_id": supplier_id})
        
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")
        
        supplier["_id"] = str(supplier["_id"])
        
        return supplier
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting supplier {supplier_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Risk Event Endpoints ====================

@app.get("/api/risks")
async def get_risk_events(
    risk_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 50
):
    """Get risk events with optional filters"""
    try:
        query = {"company_id": settings.company_id}
        
        if risk_type:
            query["risk_type"] = risk_type
        
        if severity:
            query["severity_band"] = severity
        
        risks = list(
            db_manager.risk_events.find(query)
            .sort("timestamp", -1)
            .limit(limit)
        )
        
        # Convert ObjectId to string
        for risk in risks:
            risk["_id"] = str(risk["_id"])
            if "article_id" in risk:
                risk["article_id"] = str(risk["article_id"])
        
        return {"risk_events": risks, "count": len(risks)}
    
    except Exception as e:
        logger.error(f"Error getting risk events: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== AI Agent Endpoints ====================

@app.post("/api/agent/query")
async def agent_query(request: dict):
    """
    Query the AI agent with natural language
    
    Request body:
    {
        "query": "What are the current critical alerts?",
        "conversation_history": [...]  // Optional
    }
    """
    try:
        from src.agent.agent import get_agent
        
        query = request.get("query")
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        conversation_history = request.get("conversation_history", [])
        
        # Get agent and process query
        agent = get_agent()
        result = agent.query(query, conversation_history)
        
        logger.info(f"Agent query processed: {query[:50]}...")
        
        return result
    
    except Exception as e:
        logger.error(f"Error processing agent query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agent/starters")
async def get_conversation_starters():
    """Get suggested conversation starter questions"""
    try:
        from src.agent.agent import get_agent
        
        agent = get_agent()
        starters = agent.get_conversation_starters()
        
        return {"starters": starters}
    
    except Exception as e:
        logger.error(f"Error getting conversation starters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Report Endpoints ====================

@app.get("/api/reports")
async def get_reports(report_type: Optional[str] = None, limit: int = 10):
    """
    Get recent reports
    
    Query params:
    - report_type: Filter by type (daily, weekly, custom)
    - limit: Max number of reports (default: 10)
    """
    try:
        from src.agent.report_generator import ReportGenerator
        
        generator = ReportGenerator()
        reports = generator.get_recent_reports(report_type, limit)
        
        # Convert ObjectId to string
        for report in reports:
            report["_id"] = str(report["_id"])
            if "generated_at" in report:
                report["generated_at"] = report["generated_at"].isoformat()
            if "period_start" in report:
                report["period_start"] = report["period_start"].isoformat()
            if "period_end" in report:
                report["period_end"] = report["period_end"].isoformat()
        
        logger.info(f"Retrieved {len(reports)} reports")
        return {"reports": reports}
    
    except Exception as e:
        logger.error(f"Error fetching reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reports/{report_id}")
async def get_report(report_id: str):
    """Get specific report by ID"""
    try:
        from bson import ObjectId
        
        report = db_manager.reports.find_one({"_id": ObjectId(report_id)})
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Convert ObjectId to string
        report["_id"] = str(report["_id"])
        if "generated_at" in report:
            report["generated_at"] = report["generated_at"].isoformat()
        if "period_start" in report:
            report["period_start"] = report["period_start"].isoformat()
        if "period_end" in report:
            report["period_end"] = report["period_end"].isoformat()
        
        return {"report": report}
    
    except Exception as e:
        logger.error(f"Error fetching report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reports/generate")
async def generate_report(request: dict):
    """
    Generate a new report
    
    Request body:
    {
        "type": "daily" | "weekly" | "custom",
        "queries": [...]  // Required for custom reports
    }
    """
    try:
        from src.agent.report_generator import ReportGenerator
        
        report_type = request.get("type", "daily")
        
        generator = ReportGenerator()
        
        if report_type == "daily":
            report = generator.generate_daily_report()
        elif report_type == "weekly":
            report = generator.generate_weekly_report()
        elif report_type == "custom":
            queries = request.get("queries", [])
            if not queries:
                raise HTTPException(status_code=400, detail="Queries required for custom report")
            report = generator.generate_custom_report(queries)
        else:
            raise HTTPException(status_code=400, detail="Invalid report type")
        
        # Convert ObjectId to string
        report["_id"] = str(report["_id"])
        if "generated_at" in report:
            report["generated_at"] = report["generated_at"].isoformat()
        if "period_start" in report:
            report["period_start"] = report["period_start"].isoformat()
        if "period_end" in report:
            report["period_end"] = report["period_end"].isoformat()
        
        logger.info(f"Generated {report_type} report: {report['_id']}")
        
        return {
            "success": True,
            "report_id": report["_id"],
            "report": report
        }
    
    except Exception as e:
        logger.error(f"Error generating report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== WebSocket for Real-time Alerts ====================

class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")


manager = ConnectionManager()


@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """WebSocket endpoint for real-time alert updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Echo back for heartbeat
            await websocket.send_json({"type": "heartbeat", "status": "ok"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload
    )
