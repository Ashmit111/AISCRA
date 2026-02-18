"""
Report Generator
Uses AI agent to generate comprehensive supply chain risk reports
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from src.agent.agent import get_agent
from src.models.db import db_manager
from src.utils.config import settings
import logging

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Generates automated supply chain risk reports using AI agent
    """
    
    def __init__(self):
        """Initialize report generator"""
        self.agent = get_agent()
    
    
    def generate_daily_report(self) -> Dict[str, Any]:
        """
        Generate daily supply chain risk report
        
        Returns:
            Dict with report data
        """
        try:
            logger.info("Generating daily supply chain risk report...")
            
            # Report sections - each uses agent to query data
            sections = []
            
            # 1. Executive Summary
            summary_query = "Give me a high-level summary of our supply chain status"
            summary_response = self.agent.query(summary_query)
            sections.append({
                "title": "Executive Summary",
                "content": summary_response["response"]
            })
            
            # 2. Critical Alerts
            alerts_query = "What are the current critical and high severity alerts? Be specific."
            alerts_response = self.agent.query(alerts_query)
            sections.append({
                "title": "Critical Alerts",
                "content": alerts_response["response"]
            })
            
            # 3. Risk Events (Last 24 Hours)
            risks_query = "Show me risk events from the last 24 hours"
            risks_response = self.agent.query(risks_query)
            sections.append({
                "title": "New Risk Events (24 Hours)",
                "content": risks_response["response"]
            })
            
            # 4. Top Risk Types
            types_query = "What are the top 3 risk types this week?"
            types_response = self.agent.query(types_query)
            sections.append({
                "title": "Top Risk Types",
                "content": types_response["response"]
            })
            
            # 5. Supplier Risk Status
            suppliers_query = "Which suppliers are currently at elevated risk?"
            suppliers_response = self.agent.query(suppliers_query)
            sections.append({
                "title": "Supplier Risk Status",
                "content": suppliers_response["response"]
            })
            
            # 6. Recommendations
            recommendations_query = "Based on current risks, what are the top 3 recommendations for supply chain resilience?"
            recommendations_response = self.agent.query(recommendations_query)
            sections.append({
                "title": "Recommendations",
                "content": recommendations_response["response"]
            })
            
            # Build full report
            report_date = datetime.utcnow()
            report = {
                "report_type": "daily",
                "title": f"Daily Supply Chain Risk Report - {report_date.strftime('%B %d, %Y')}",
                "generated_at": report_date,
                "sections": sections,
                "metadata": {
                    "tool_calls": sum(
                        len(resp.get("tool_calls", [])) 
                        for resp in [
                            summary_response, alerts_response, risks_response,
                            types_response, suppliers_response, recommendations_response
                        ]
                    )
                }
            }
            
            # Save to database
            report_id = self._save_report(report)
            report["_id"] = report_id
            
            logger.info(f"Daily report generated: {report_id}")
            
            return report
        
        except Exception as e:
            logger.error(f"Error generating daily report: {e}", exc_info=True)
            raise
    
    
    def generate_weekly_report(self) -> Dict[str, Any]:
        """
        Generate weekly supply chain risk report (more comprehensive)
        
        Returns:
            Dict with report data
        """
        try:
            logger.info("Generating weekly supply chain risk report...")
            
            sections = []
            
            # 1. Executive Summary
            summary_query = "Give me a comprehensive summary of our supply chain status"
            summary_response = self.agent.query(summary_query)
            sections.append({
                "title": "Executive Summary",
                "content": summary_response["response"]
            })
            
            # 2. Week in Review
            review_query = "Show me risk events from the past 7 days, grouped by severity"
            review_response = self.agent.query(review_query)
            sections.append({
                "title": "Week in Review",
                "content": review_response["response"]
            })
            
            # 3. Risk Trend Analysis
            trend_query = "What is the risk trend over the past 30 days? Is supply chain risk increasing or decreasing?"
            trend_response = self.agent.query(trend_query)
            sections.append({
                "title": "Risk Trend Analysis",
                "content": trend_response["response"]
            })
            
            # 4. Supplier Performance
            performance_query = "Which suppliers had the most risk events this week?"
            performance_response = self.agent.query(performance_query)
            sections.append({
                "title": "Supplier Risk Performance",
                "content": performance_response["response"]
            })
            
            # 5. Geographic Risk Distribution
            geo_query = "What are the key geographic risks affecting our supply chain this week?"
            geo_response = self.agent.query(geo_query)
            sections.append({
                "title": "Geographic Risk Distribution",
                "content": geo_response["response"]
            })
            
            # 6. Material Risk Analysis
            material_query = "Which of our key materials (crude oil, naphtha, LPG) have the highest supply risk?"
            material_response = self.agent.query(material_query)
            sections.append({
                "title": "Material Risk Analysis",
                "content": material_response["response"]
            })
            
            # 7. Alternate Supplier Recommendations
            alternates_query = "For our top 2 at-risk suppliers, what are the best alternate supplier options?"
            alternates_response = self.agent.query(alternates_query)
            sections.append({
                "title": "Alternate Supplier Recommendations",
                "content": alternates_response["response"]
            })
            
            # 8. Strategic Recommendations
            strategy_query = "Based on this week's data, what are the top 5 strategic recommendations for improving supply chain resilience?"
            strategy_response = self.agent.query(strategy_query)
            sections.append({
                "title": "Strategic Recommendations",
                "content": strategy_response["response"]
            })
            
            # Build full report
            report_date = datetime.utcnow()
            week_start = report_date - timedelta(days=7)
            report = {
                "report_type": "weekly",
                "title": f"Weekly Supply Chain Risk Report - Week of {week_start.strftime('%B %d, %Y')}",
                "generated_at": report_date,
                "period_start": week_start,
                "period_end": report_date,
                "sections": sections,
                "metadata": {
                    "tool_calls": sum(
                        len(resp.get("tool_calls", [])) 
                        for resp in [
                            summary_response, review_response, trend_response,
                            performance_response, geo_response, material_response,
                            alternates_response, strategy_response
                        ]
                    )
                }
            }
            
            # Save to database
            report_id = self._save_report(report)
            report["_id"] = report_id
            
            logger.info(f"Weekly report generated: {report_id}")
            
            return report
        
        except Exception as e:
            logger.error(f"Error generating weekly report: {e}", exc_info=True)
            raise
    
    
    def generate_custom_report(self, queries: list[str]) -> Dict[str, Any]:
        """
        Generate custom report from list of queries
        
        Args:
            queries: List of natural language queries to include
        
        Returns:
            Dict with report data
        """
        try:
            logger.info(f"Generating custom report with {len(queries)} queries...")
            
            sections = []
            for i, query in enumerate(queries, 1):
                response = self.agent.query(query)
                sections.append({
                    "title": f"Section {i}",
                    "query": query,
                    "content": response["response"]
                })
            
            report_date = datetime.utcnow()
            report = {
                "report_type": "custom",
                "title": f"Custom Supply Chain Report - {report_date.strftime('%B %d, %Y at %H:%M UTC')}",
                "generated_at": report_date,
                "sections": sections,
                "metadata": {
                    "query_count": len(queries)
                }
            }
            
            # Save to database
            report_id = self._save_report(report)
            report["_id"] = report_id
            
            logger.info(f"Custom report generated: {report_id}")
            
            return report
        
        except Exception as e:
            logger.error(f"Error generating custom report: {e}", exc_info=True)
            raise
    
    
    def _save_report(self, report: Dict[str, Any]) -> str:
        """
        Save report to database
        
        Args:
            report: Report document
        
        Returns:
            Report ID
        """
        try:
            result = db_manager.reports.insert_one(report)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error saving report: {e}")
            raise
    
    
    def get_recent_reports(
        self,
        report_type: Optional[str] = None,
        limit: int = 10
    ) -> list[Dict[str, Any]]:
        """
        Get recent reports from database
        
        Args:
            report_type: Filter by report type (daily, weekly, custom)
            limit: Maximum number of reports
        
        Returns:
            List of reports
        """
        try:
            query = {}
            if report_type:
                query["report_type"] = report_type
            
            reports = list(
                db_manager.reports
                .find(query)
                .sort("generated_at", -1)
                .limit(limit)
            )
            
            return reports
        
        except Exception as e:
            logger.error(f"Error getting recent reports: {e}")
            return []


# Celery task for scheduled report generation
def generate_scheduled_daily_report():
    """
    Celery task to generate daily report (scheduled via Beat)
    """
    try:
        generator = ReportGenerator()
        report = generator.generate_daily_report()
        logger.info(f"Scheduled daily report generated: {report['_id']}")
        return report["_id"]
    except Exception as e:
        logger.error(f"Error in scheduled daily report: {e}")
        raise


def generate_scheduled_weekly_report():
    """
    Celery task to generate weekly report (scheduled via Beat)
    """
    try:
        generator = ReportGenerator()
        report = generator.generate_weekly_report()
        logger.info(f"Scheduled weekly report generated: {report['_id']}")
        return report["_id"]
    except Exception as e:
        logger.error(f"Error in scheduled weekly report: {e}")
        raise
