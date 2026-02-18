"""
MongoDB Schema Definitions using Pydantic
Defines all document models for supply chain risk analysis
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# ==================== Enums ====================

class RiskType(str, Enum):
    """Risk classification categories"""
    GEOPOLITICAL = "geopolitical"
    NATURAL_DISASTER = "natural_disaster"
    FINANCIAL = "financial"
    REGULATORY = "regulatory"
    OPERATIONAL = "operational"
    CYBERSECURITY = "cybersecurity"
    ESG = "esg"
    OTHER = "other"


class SeverityLevel(str, Enum):
    """Severity classification"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TimeHorizon(str, Enum):
    """Time horizon for risk materialization"""
    IMMEDIATE = "immediate"
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"


class SupplierStatus(str, Enum):
    """Supplier operational status"""
    ACTIVE = "active"
    ALTERNATE = "alternate"
    PRE_QUALIFIED = "pre_qualified"
    INACTIVE = "inactive"
    AT_RISK = "at_risk"


# ==================== Company Schema ====================

class Company(BaseModel):
    """Company profile - drives all risk analysis"""
    id: Optional[str] = Field(None, alias="_id")
    company_name: str
    industry: str
    raw_materials: List[str]
    key_geographies: List[str]
    inventory_days: Dict[str, int]  # material -> days
    material_criticality: Dict[str, int]  # material -> score (1-10)
    alert_contacts: List[Dict[str, str]]  # name, email, role
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


# ==================== Supplier Schema ====================

class UpstreamSupplier(BaseModel):
    """Upstream (Tier-2+) supplier reference"""
    name: str
    country: str
    supply_volume_pct: float


class Supplier(BaseModel):
    """Supplier document - Tier-1, Tier-2, and alternates"""
    id: Optional[str] = Field(None, alias="_id")
    company_id: str
    name: str
    country: str
    region: str
    tier: int  # 1, 2, 3...
    supplies: List[str]  # materials
    supply_volume_pct: float  # % of material this supplier provides
    status: SupplierStatus
    approved_vendor: bool = False
    pre_qualified: bool = False
    is_single_source: bool = False
    
    # Financial & ESG
    esg_score: Optional[int] = None  # 0-100
    credit_rating: Optional[str] = None
    financial_health_score: Optional[float] = None  # 0-10
    
    # Capacity & Logistics
    max_capacity: Optional[float] = None
    lead_time_weeks: int = 4
    switching_cost_estimate: Optional[float] = None  # 0-10 scale
    
    # Relationships
    contract_end: Optional[datetime] = None
    upstream_suppliers: List[UpstreamSupplier] = []
    
    # Risk
    risk_score_current: float = 0.0
    description: Optional[str] = None
    description_embedding: Optional[List[float]] = None  # For vector search
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


# ==================== Article Schema ====================

class Article(BaseModel):
    """Raw news article"""
    id: Optional[str] = Field(None, alias="_id")
    event_id: str
    timestamp: datetime
    source: str  # NewsAPI, GDELT, etc.
    headline: str
    body: str
    url: str
    entities_mentioned: List[str] = []
    raw_relevance_score: float = 0.0
    processed: bool = False
    risk_extracted: bool = False
    risk_event_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


# ==================== Risk Event Schema ====================

class RiskScoreComponents(BaseModel):
    """Breakdown of risk score calculation"""
    probability: float
    impact: float
    urgency: float
    mitigation: float


class RiskEvent(BaseModel):
    """Extracted and scored risk event"""
    id: Optional[str] = Field(None, alias="_id")
    article_id: str
    company_id: str
    timestamp: datetime
    
    # Classification
    risk_type: RiskType
    affected_entities: List[str]  # companies, countries, materials
    affected_supply_chain_nodes: List[str]  # supplier names
    
    # Severity & Confirmation
    severity: SeverityLevel
    is_confirmed: Optional[str] = "uncertain"  # true, false, uncertain
    time_horizon: TimeHorizon
    
    # Analysis
    reasoning: str
    recommended_action: Optional[str] = None
    
    # Scoring
    risk_score_components: RiskScoreComponents
    risk_score: float
    severity_band: SeverityLevel
    
    # Propagation results
    propagation: Dict[str, float] = {}  # node_id -> propagated_score
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


# ==================== Alert Schema ====================

class AlternateSupplierRecommendation(BaseModel):
    """Alternate supplier recommendation"""
    supplier_id: str
    name: str
    score: float
    lead_time_weeks: int
    approved_vendor: bool
    country: str
    score_breakdown: Dict[str, float]


class Alert(BaseModel):
    """Generated alert for decision makers"""
    id: Optional[str] = Field(None, alias="_id")
    risk_event_id: str
    company_id: str
    
    # Alert Info
    severity_band: SeverityLevel
    risk_score: float
    title: str
    description: str
    
    # Supply Chain Impact
    affected_supplier: str
    affected_material: str
    
    # Recommendations
    recommendations: List[AlternateSupplierRecommendation] = []
    recommendation_text: Optional[str] = None
    
    # Status
    is_acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    # Notifications
    notification_sent: bool = False
    notification_sent_at: Optional[datetime] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


# ==================== Report Schema ====================

class ReportType(str, Enum):
    """Type of report"""
    DAILY = "daily"
    WEEKLY = "weekly"
    ON_DEMAND = "on_demand"


class Report(BaseModel):
    """AI-generated report"""
    id: Optional[str] = Field(None, alias="_id")
    type: ReportType
    content: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    alert_count: int = 0
    critical_count: int = 0

    class Config:
        populate_by_name = True
        use_enum_values = True
