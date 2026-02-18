#!/usr/bin/env python3
"""
Create sample risk events and alerts for demonstration
"""
import sys
sys.path.insert(0, '.')

from src.models.db import db_manager, get_company_profile
from datetime import datetime, timedelta
from bson import ObjectId
import random

print("=" * 70)
print("CREATING SAMPLE RISK EVENTS & ALERTS")
print("=" * 70)

db = db_manager.db

# Get company profile
company_profile = get_company_profile()
if not company_profile:
    print("ERROR: No company profile found!")
    sys.exit(1)

company_id = str(company_profile["_id"])
print(f"✓ Company: {company_profile['company_name']}")

# Get some suppliers
suppliers = list(db.suppliers.find({}).limit(4))
print(f"✓ Found {len(suppliers)} suppliers")

# Sample risk events
risk_templates = [
    {
        "risk_type": "geopolitical",
        "severity": "high",
        "headline": "Russia announces new oil export restrictions affecting Asian markets",
        "description": "Russian government announces temporary restrictions on crude oil exports to Asia-Pacific region due to domestic supply concerns, potentially impacting refinery operations.",
        "source": "Reuters",
        "reasoning": "Direct impact on crude oil supply chain from Russian suppliers",
        "recommended_action": "Activate alternate supplier agreements with Middle Eastern producers. Increase strategic reserves by 15%.",
        "affected_entities": ["Rosneft", "Russia", "crude oil"],
        "risk_score": 8.5
    },
    {
        "risk_type": "price_volatility",
        "severity": "medium",
        "headline": "Crude oil prices surge 12% on Middle East tensions",
        "description": "Oil prices jumped to $92 per barrel amid escalating tensions in the Persian Gulf, raising concerns about supply disruptions.",
        "source": "Bloomberg",
        "reasoning": "Price volatility affects procurement costs and margin projections for Q2",
        "recommended_action": "Review hedging strategies. Consider locking in prices for next quarter supplies.",
        "affected_entities": ["crude oil", "Saudi Arabia", "Iran"],
        "risk_score": 6.5
    },
    {
        "risk_type": "regulatory",
        "severity": "medium",
        "headline": "New environmental regulations impact Indian refinery operations",
        "description": "Government announces stricter emission standards for refineries, requiring significant equipment upgrades by year-end.",
        "source": "Economic Times",
        "reasoning": "Compliance requirements may impact production capacity and costs",
        "recommended_action": "Initiate compliance assessment. Budget $50M for equipment upgrades. Timeline: 9 months.",
        "affected_entities": ["India", "Nayara Energy"],
        "risk_score": 5.0
    },
    {
        "risk_type": "supply_disruption",
        "severity": "critical",
        "headline": "Major pipeline disruption halts LPG shipments from key supplier",
        "description": "Technical failure in main pipeline infrastructure causes temporary halt in LPG supply from primary source.",
        "source": "Industry News",
        "reasoning": "Critical supply chain disruption affecting LPG procurement",
        "recommended_action": "IMMEDIATE: Activate emergency supply protocol. Contact alternate LPG suppliers in UAE and Qatar.",
        "affected_entities": ["LPG", "pipeline", "transportation"],
        "risk_score": 9.2
    },
    {
        "risk_type": "financial",
        "severity": "low",
        "headline": "Currency fluctuations impact Russian crude oil contracts",
        "description": "Ruble volatility creates pricing uncertainties in existing supply contracts denominated in Russian currency.",
        "source": "Financial Times",
        "reasoning": "Currency risk affects contract valuations but manageable through existing hedges",
        "recommended_action": "Monitor currency trends. Review currency hedging positions monthly.",
        "affected_entities": ["Russia", "Rosneft", "currency"],
        "risk_score": 3.5
    }
]

print(f"\nCreating {len(risk_templates)} risk events...")

created_risks = []
for i, template in enumerate(risk_templates):
    # Add supplier IDs to affected nodes
    affected_nodes = []
    if i < len(suppliers):
        affected_nodes.append(str(suppliers[i]["_id"]))
    
    risk_event = {
        "company_id": company_id,
        "timestamp": datetime.utcnow() - timedelta(hours=random.randint(1, 24)),
        "risk_type": template["risk_type"],
        "severity": template["severity"],
        "headline": template["headline"],
        "description": template["description"],
        "source": template["source"],
        "url": f"https://news.example.com/article-{i+1}",
        "affected_entities": template["affected_entities"],
        "affected_supply_chain_nodes": affected_nodes,
        "reasoning": template["reasoning"],
        "recommended_action": template["recommended_action"],
        "risk_score": template["risk_score"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = db.risk_events.insert_one(risk_event)
    created_risks.append(result.inserted_id)
    print(f"  ✓ [{i+1}] {template['severity'].upper()}: {template['headline'][:60]}...")

# Create alerts for high severity risks
print(f"\nCreating alerts for high-severity risks...")
alerts_created = 0

for risk_id in created_risks:
    risk = db.risk_events.find_one({"_id": risk_id})
    if risk["risk_score"] >= 6.0:  # High or critical
        alert = {
            "company_id": company_id,
            "risk_event_id": str(risk_id),
            "severity": risk["severity"],
            "title": risk["headline"],
            "message": risk["description"],
            "risk_score": risk["risk_score"],
            "affected_suppliers": risk["affected_supply_chain_nodes"],
            "affected_materials": [e for e in risk["affected_entities"] if e in ["crude oil", "LPG", "naphtha"]],
            "ai_recommendation": risk["recommended_action"],
            "alternate_suppliers": [],
            "acknowledged": False,
            "acknowledged_at": None,
            "acknowledged_by": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        db.alerts.insert_one(alert)
        alerts_created += 1
        print(f"  ✓ Alert: {risk['headline'][:60]}...")

print("\n" + "=" * 70)
print(f"RESULTS:")
print(f"  Risk Events Created: {len(created_risks)}")
print(f"  Alerts Created: {alerts_created}")
print("=" * 70)

print(f"\n✅ SUCCESS! Database populated with sample data")
print(f"\n📊 REFRESH YOUR BROWSER: http://localhost:3000")
print(f"   You should now see:")
print(f"   - {alerts_created} active alerts")
print(f"   - {len(created_risks)} risk events")
print(f"   - Data in the dashboard\n")
