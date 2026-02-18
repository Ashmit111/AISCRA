"""
AI Agent Orchestrator
Uses Gemini Pro with tools for natural language supply chain queries
"""

from typing import Dict, Any, List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from src.agent.tools import (
    query_risk_events,
    get_active_alerts,
    find_alternate_suppliers_tool,
    get_supply_chain_summary,
    get_risk_trend
)
from src.utils.config import settings
from src.models.db import db_manager
import logging
import json

logger = logging.getLogger(__name__)


def format_tool_response(tool_name: str, raw_result: str) -> str:
    """
    Format raw tool results into human-readable text
    
    Args:
        tool_name: Name of the tool that was called
        raw_result: Raw string result from the tool
    
    Returns:
        Formatted human-readable text
    """
    try:
        # Try to parse as Python dict/list literal
        import ast
        data = ast.literal_eval(raw_result)
        
        if tool_name == "get_active_alerts":
            if isinstance(data, dict) and "alerts" in data:
                alerts = data["alerts"]
                count = data.get("count", len(alerts))
                
                if count == 0:
                    return "✅ No active alerts at this time."
                
                formatted = f"🔔 **{count} Active Alert{'s' if count != 1 else ''}:**\n\n"
                
                for i, alert in enumerate(alerts, 1):
                    severity = alert.get("severity", "unknown").upper()
                    severity_icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(severity, "⚪")
                    
                    formatted += f"{i}. {severity_icon} **{severity}** (Risk Score: {alert.get('risk_score', 0)}/10)\n"
                    formatted += f"   📋 {alert.get('title', 'No title')}\n"
                    
                    if alert.get('affected_suppliers'):
                        formatted += f"   🏢 Suppliers: {', '.join(alert.get('affected_suppliers', []))}\n"
                    if alert.get('affected_materials'):
                        formatted += f"   📦 Materials: {', '.join(alert.get('affected_materials', []))}\n"
                    if alert.get('recommendation'):
                        formatted += f"   💡 Recommendation: {alert.get('recommendation')}\n"
                    formatted += "\n"
                
                return formatted
        
        elif tool_name == "query_risk_events":
            if isinstance(data, dict) and "risk_events" in data:
                events = data["risk_events"]
                count = data.get("count", len(events))
                
                if count == 0:
                    return "✅ No recent risk events found."
                
                formatted = f"📊 **{count} Recent Risk Event{'s' if count != 1 else ''}:**\n\n"
                
                for i, event in enumerate(events, 1):
                    risk_type = event.get("risk_type", "unknown").replace("_", " ").title()
                    severity = event.get("severity", "").upper()
                    
                    formatted += f"{i}. **{risk_type}** - {severity}\n"
                    formatted += f"   Risk Score: {event.get('risk_score', 0)}/10\n"
                    formatted += f"   📝 {event.get('description', 'No description')}\n"
                    
                    if event.get('affected_entities'):
                        formatted += f"   🎯 Affected: {', '.join(event.get('affected_entities', []))}\n"
                    formatted += "\n"
                
                return formatted
        
        elif tool_name == "get_supply_chain_summary":
            if isinstance(data, dict):
                formatted = "📈 **Supply Chain Overview:**\n\n"
                
                if "company_name" in data:
                    formatted += f"🏭 Company: {data['company_name']}\n"
                if "industry" in data:
                    formatted += f"🏗️ Industry: {data['industry']}\n\n"
                
                if "suppliers" in data:
                    s = data["suppliers"]
                    formatted += f"**Suppliers:**\n"
                    formatted += f"   • Total: {s.get('total', 0)}\n"
                    formatted += f"   • Active: {s.get('active', 0)}\n"
                    formatted += f"   • At Risk: {s.get('at_risk', 0)}\n\n"
                
                if "alerts" in data:
                    a = data["alerts"]
                    total = a.get('total', 0)
                    formatted += f"**Alerts:**\n"
                    formatted += f"   • Total Open: {total}\n"
                    if total > 0:
                        formatted += f"   • 🔴 Critical: {a.get('critical', 0)}\n"
                        formatted += f"   • 🟠 High: {a.get('high', 0)}\n"
                        formatted += f"   • 🟡 Medium: {a.get('medium', 0)}\n"
                        formatted += f"   • 🟢 Low: {a.get('low', 0)}\n\n"
                
                if "risk_events_last_7_days" in data:
                    formatted += f"**Recent Activity (7 days):**\n"
                    formatted += f"   • Risk Events: {data['risk_events_last_7_days']}\n"
                
                if "top_risk_types" in data:
                    types = data["top_risk_types"]
                    if types:
                        formatted += f"\n**Top Risk Types:**\n"
                        for risk in types:
                            formatted += f"   • {risk.get('type', '').replace('_', ' ').title()}: {risk.get('count', 0)}\n"
                
                if "materials" in data:
                    formatted += f"\n**Key Materials:** {', '.join(data['materials'])}\n"
                
                if "key_geographies" in data:
                    formatted += f"**Key Geographies:** {', '.join(data['key_geographies'])}\n"
                
                return formatted
        
        elif tool_name == "get_risk_trend":
            if isinstance(data, dict):
                formatted = "📉 **Risk Trend Analysis:**\n\n"
                
                if "period_days" in data:
                    formatted += f"Period: Last {data['period_days']} days\n\n"
                
                if "total_events" in data:
                    formatted += f"**Total Events:** {data['total_events']}\n"
                
                if "by_severity" in data:
                    formatted += f"\n**By Severity:**\n"
                    for sev in data["by_severity"]:
                        formatted += f"   • {sev.get('severity', '').title()}: {sev.get('count', 0)}\n"
                
                if "by_type" in data:
                    formatted += f"\n**By Type:**\n"
                    for typ in data["by_type"]:
                        type_name = typ.get('type', '').replace('_', ' ').title()
                        formatted += f"   • {type_name}: {typ.get('count', 0)}\n"
                
                if "trend" in data:
                    trend = data["trend"]
                    if trend == "increasing":
                        formatted += f"\n📈 **Trend:** ⚠️ INCREASING - Risk activity is rising\n"
                    elif trend == "decreasing":
                        formatted += f"\n📉 **Trend:** ✅ DECREASING - Risk activity is declining\n"
                    else:
                        formatted += f"\n📊 **Trend:** ➡️ STABLE - Risk activity is steady\n"
                
                return formatted
        
        elif tool_name == "find_alternate_suppliers":
            if isinstance(data, dict) and "alternates" in data:
                alternates = data["alternates"]
                count = len(alternates)
                
                if count == 0:
                    return "❌ No alternate suppliers found."
                
                formatted = f"🔄 **{count} Alternate Supplier{'s' if count != 1 else ''} Found:**\n\n"
                
                for i, alt in enumerate(alternates, 1):
                    formatted += f"{i}. **{alt.get('name', 'Unknown')}**\n"
                    formatted += f"   📍 Country: {alt.get('country', 'Unknown')}\n"
                    formatted += f"   ⭐ Match Score: {alt.get('score', 0)}/10\n"
                    
                    if alt.get('supplies'):
                        formatted += f"   📦 Supplies: {', '.join(alt.get('supplies', []))}\n"
                    if alt.get('esg_score'):
                        formatted += f"   🌱 ESG Score: {alt.get('esg_score')}/100\n"
                    if alt.get('reason'):
                        formatted += f"   💭 {alt.get('reason')}\n"
                    formatted += "\n"
                
                return formatted
        
        # If we couldn't format nicely, return the raw result
        return raw_result
    
    except Exception as e:
        # If parsing fails, return raw result
        logger.debug(f"Could not format tool response: {e}")
        return raw_result


# System prompt for supply chain risk agent
SYSTEM_PROMPT = """You are an AI assistant specialized in supply chain risk analysis for {company_name}.

Your role is to help analyze supply chain risks, recommend alternate suppliers, and provide insights on potential disruptions. You have access to tools that can:
1. Query recent risk events by type, severity, or timeframe
2. Get active alerts that require attention
3. Find alternate suppliers for any material or supplier
4. Get a high-level summary of supply chain status
5. Analyze risk trends over time

When answering questions:
- Always provide specific data and numbers when available
- Prioritize critical and high severity risks
- Recommend actionable steps when appropriate
- Consider geographic diversification and ESG factors
- Be concise but thorough

Current company context:
- Industry: {industry}
- Key Materials: {materials}
- Key Geographies: {geographies}

Answer user questions using the tools available to you."""


class SupplyChainAgent:
    """
    AI Agent for natural language supply chain risk queries
    """
    
    def __init__(self):
        """Initialize agent with Gemini Pro"""
        
        # Initialize LLM (Gemini Flash for reasoning)
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=settings.gemini_api_key,
            temperature=0.3,  # Lower for more factual responses
            max_output_tokens=2048
        )
        
        # Get company context
        self.company_profile = self._get_company_profile()
        
        # Build system prompt with company context
        self.system_message = SYSTEM_PROMPT.format(
            company_name=self.company_profile.get("company_name", "Unknown"),
            industry=self.company_profile.get("industry", "Unknown"),
            materials=", ".join(self.company_profile.get("raw_materials", [])),
            geographies=", ".join(self.company_profile.get("key_geographies", []))
        )
        
        # Store tool functions
        self.tools = {
            "query_risk_events": query_risk_events,
            "get_active_alerts": get_active_alerts,
            "find_alternate_suppliers": find_alternate_suppliers_tool,
            "get_supply_chain_summary": get_supply_chain_summary,
            "get_risk_trend": get_risk_trend
        }
        
        logger.info(f"Initialized Supply Chain Agent with {len(self.tools)} tools")
    
    
    def _get_company_profile(self) -> Dict[str, Any]:
        """Get company profile from database"""
        try:
            company = db_manager.companies.find_one({})
            if company:
                return company
            else:
                logger.warning("No company profile found in database")
                return {
                    "company_name": "Unknown Company",
                    "industry": "Unknown",
                    "raw_materials": [],
                    "key_geographies": []
                }
        except Exception as e:
            logger.error(f"Error loading company profile: {e}")
            return {
                "company_name": "Unknown Company",
                "industry": "Unknown",
                "raw_materials": [],
                "key_geographies": []
            }
    
    
    def query(
        self,
        user_query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Process auser query using the agent
        
        Args:
            user_query: Natural language question from user
            conversation_history: Previous messages in conversation (optional)
        
       Returns:
            Dict with response and metadata
        """
        try:
            # Determine which tools to call based on query keywords
            tool_calls = []
            raw_results = []
            
            query_lower = user_query.lower()
            
            # Check for alerts-related queries
            if any(word in query_lower for word in ['alert', 'critical', 'urgent', 'warning']):
                try:
                    result = get_active_alerts.invoke({})
                    raw_results.append(("get_active_alerts", result))
                    tool_calls.append({"tool": "get_active_alerts", "args": {}})
                except Exception as e:
                    logger.error(f"Error calling get_active_alerts: {e}")
            
            # Check for risk/event queries
            if any(word in query_lower for word in ['risk', 'event', 'disruption', 'issue', 'high risk']):
                try:
                    result = query_risk_events.invoke({"days_back": 30})
                    raw_results.append(("query_risk_events", result))
                    tool_calls.append({"tool": "query_risk_events", "args": {"days_back": 30}})
                except Exception as e:
                    logger.error(f"Error calling query_risk_events: {e}")
            
            # Check for supplier queries (not alternate)
            if any(word in query_lower for word in ['supplier', 'vendor']) and not any(word in query_lower for word in ['alternate', 'alternative']):
                try:
                    result = get_supply_chain_summary.invoke({})
                    raw_results.append(("get_supply_chain_summary", result))
                    tool_calls.append({"tool": "get_supply_chain_summary", "args": {}})
                except Exception as e:
                    logger.error(f"Error calling get_supply_chain_summary: {e}")
            
            # Check for alternate supplier queries
            if any(word in query_lower for word in ['alternate', 'alternative', 'replacement', 'backup']):
                try:
                    result = find_alternate_suppliers_tool.invoke({})
                    raw_results.append(("find_alternate_suppliers", result))
                    tool_calls.append({"tool": "find_alternate_suppliers", "args": {}})
                except Exception as e:
                    logger.error(f"Error calling find_alternate_suppliers: {e}")
            
            # Check for summary/status queries
            if any(word in query_lower for word in ['summary', 'status', 'overview', 'how many', 'what', 'whats', "what's"]):
                try:
                    result = get_supply_chain_summary.invoke({})
                    raw_results.append(("get_supply_chain_summary", result))
                    tool_calls.append({"tool": "get_supply_chain_summary", "args": {}})
                except Exception as e:
                    logger.error(f"Error calling get_supply_chain_summary: {e}")
            
            # Check for trend queries
            if any(word in query_lower for word in ['trend', 'pattern', 'over time', 'history']):
                try:
                    result = get_risk_trend.invoke({"days_back": 30})
                    raw_results.append(("get_risk_trend", result))
                    tool_calls.append({"tool": "get_risk_trend", "args": {"days_back": 30}})
                except Exception as e:
                    logger.error(f"Error calling get_risk_trend: {e}")
            
            # If no specific tool was called, call summary as default
            if not raw_results:
                try:
                    result = get_supply_chain_summary.invoke({})
                    raw_results.append(("get_supply_chain_summary", result))
                    tool_calls.append({"tool": "get_supply_chain_summary", "args": {}})
                except Exception as e:
                    logger.error(f"Error calling get_supply_chain_summary: {e}")
            
            # Format all tool results
            formatted_results = []
            for tool_name, raw_result in raw_results:
                formatted = format_tool_response(tool_name, raw_result)
                formatted_results.append(formatted)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_results = []
            for result in formatted_results:
                if result not in seen:
                    seen.add(result)
                    unique_results.append(result)
            
            # Build final response
            if unique_results:
                response_text = "\n\n".join(unique_results)
            else:
                response_text = "I couldn't find any relevant information for your query."
            
            return {
                "success": True,
                "response": response_text,
                "tool_calls": tool_calls,
                "query": user_query
            }
        
        except Exception as e:
            logger.error(f"Error processing agent query: {e}", exc_info=True)
            return {
                "success": False,
                "response": f"I encountered an error processing your request: {str(e)}",
                "error": str(e),
                "query": user_query
            }
    
    
    def get_conversation_starters(self) -> List[str]:
        """
        Get suggested conversation starter questions
        
        Returns:
            List of example questions
        """
        return [
            "What are the current critical alerts?",
            "Show me risk trends for the past 30 days",
            "What alternate suppliers are available for crude oil?",
            "Give me a summary of our supply chain status",
            "What are the top geopolitical risks this week?",
            "Which suppliers are currently at high risk?",
            "How many alerts do we have for financial risks?",
            "What's the risk trend for Rosneft?"
        ]


# Global agent instance (singleton)
_agent_instance: Optional[SupplyChainAgent] = None


def get_agent() -> SupplyChainAgent:
    """
    Get or create the global agent instance
    
    Returns:
        SupplyChainAgent instance
    """
    global _agent_instance
    
    if _agent_instance is None:
        # Connect to database if not connected
        db_manager.connect()
        _agent_instance = SupplyChainAgent()
    
    return _agent_instance


def reset_agent():
    """Reset the global agent instance (useful for testing)"""
    global _agent_instance
    _agent_instance = None
