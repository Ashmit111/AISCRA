"""
Seed Database with Example Data
Populates MongoDB with Nayara Energy company profile and suppliers
"""

import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.db import db_manager
from src.utils.config import settings

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_company():
    """Seed company profile (Nayara Energy)"""
    company_data = {
        "_id": "company_nayara_energy",
        "company_name": "Nayara Energy",
        "industry": "Oil Refining",
        "raw_materials": ["crude oil", "naphtha", "LPG"],
        "key_geographies": ["Russia", "UAE", "India", "USA"],
        "inventory_days": {
            "crude oil": 15,
            "naphtha": 7,
            "LPG": 10
        },
        "material_criticality": {
            "crude oil": 10,
            "naphtha": 6,
            "LPG": 5
        },
        "alert_contacts": [
            {
                "name": "Rajesh Kumar",
                "email": "rajesh.kumar@nayaraenergy.com",
                "role": "Supply Chain Manager"
            },
            {
                "name": "Priya Sharma",
                "email": "priya.sharma@nayaraenergy.com",
                "role": "VP Operations"
            }
        ],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    # Remove existing
    db_manager.companies.delete_many({"_id": "company_nayara_energy"})
    
    # Insert
    db_manager.companies.insert_one(company_data)
    logger.info("✓ Seeded company: Nayara Energy")


def seed_suppliers():
    """Seed suppliers (Tier-1, Tier-2, and alternates)"""
    
    suppliers = [
        # ========== TIER-1 SUPPLIERS ==========
        {
            "_id": "supplier_rosneft",
            "company_id": "company_nayara_energy",
            "name": "Rosneft",
            "country": "Russia",
            "region": "Eastern Europe",
            "tier": 1,
            "supplies": ["crude oil"],
            "supply_volume_pct": 65.0,
            "status": "at_risk",
            "approved_vendor": True,
            "pre_qualified": True,
            "is_single_source": False,
            "esg_score": 42,
            "credit_rating": "CCC",
            "financial_health_score": 3.2,
            "max_capacity": 50000,
            "lead_time_weeks": 3,
            "switching_cost_estimate": 7.5,
            "contract_end": datetime.utcnow() + timedelta(days=365*2),
            "upstream_suppliers": [
                {
                    "name": "Siberian Oil Fields",
                    "country": "Russia",
                    "supply_volume_pct": 100
                }
            ],
            "risk_score_current": 9.2,
            "description": "Major Russian oil company providing crude oil — currently under critical export restriction risk due to Western sanctions.",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "_id": "supplier_adnoc",
            "company_id": "company_nayara_energy",
            "name": "ADNOC",
            "country": "UAE",
            "region": "Middle East",
            "tier": 1,
            "supplies": ["crude oil"],
            "supply_volume_pct": 35.0,
            "status": "at_risk",
            "approved_vendor": True,
            "pre_qualified": True,
            "is_single_source": False,
            "esg_score": 68,
            "credit_rating": "AA-",
            "financial_health_score": 8.2,
            "max_capacity": 30000,
            "lead_time_weeks": 5,
            "switching_cost_estimate": 4.0,
            "contract_end": datetime.utcnow() + timedelta(days=365*3),
            "upstream_suppliers": [],
            "risk_score_current": 7.1,
            "description": "Abu Dhabi National Oil Company — currently experiencing port congestion at Ruwais/Jebel Ali causing 2-3 week shipment delays.",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        
        # ========== ALTERNATE SUPPLIERS ==========
        {
            "_id": "supplier_saudi_aramco",
            "company_id": "company_nayara_energy",
            "name": "Saudi Aramco",
            "country": "Saudi Arabia",
            "region": "Middle East",
            "tier": 1,
            "supplies": ["crude oil"],
            "supply_volume_pct": 0.0,
            "status": "alternate",
            "approved_vendor": True,
            "pre_qualified": False,
            "is_single_source": False,
            "esg_score": 65,
            "credit_rating": "A+",
            "financial_health_score": 8.9,
            "max_capacity": 60000,
            "lead_time_weeks": 3,
            "switching_cost_estimate": 5.5,
            "contract_end": None,
            "upstream_suppliers": [],
            "risk_score_current": 0.0,
            "description": "World's largest oil company, Saudi Arabia",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "_id": "supplier_ongc",
            "company_id": "company_nayara_energy",
            "name": "ONGC",
            "country": "India",
            "region": "South Asia",
            "tier": 1,
            "supplies": ["crude oil"],
            "supply_volume_pct": 0.0,
            "status": "alternate",
            "approved_vendor": True,
            "pre_qualified": True,
            "is_single_source": False,
            "esg_score": 72,
            "credit_rating": "BBB+",
            "financial_health_score": 7.1,
            "max_capacity": 20000,
            "lead_time_weeks": 1,
            "switching_cost_estimate": 3.0,
            "contract_end": None,
            "upstream_suppliers": [],
            "risk_score_current": 0.0,
            "description": "Oil and Natural Gas Corporation, domestic Indian supplier",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "_id": "supplier_bp",
            "company_id": "company_nayara_energy",
            "name": "BP",
            "country": "United Kingdom",
            "region": "Western Europe",
            "tier": 1,
            "supplies": ["crude oil", "naphtha"],
            "supply_volume_pct": 0.0,
            "status": "pre_qualified",
            "approved_vendor": False,
            "pre_qualified": True,
            "is_single_source": False,
            "esg_score": 78,
            "credit_rating": "A",
            "financial_health_score": 7.8,
            "max_capacity": 40000,
            "lead_time_weeks": 4,
            "switching_cost_estimate": 6.0,
            "contract_end": None,
            "upstream_suppliers": [],
            "risk_score_current": 0.0,
            "description": "British Petroleum, diversified energy company",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "_id": "supplier_shell",
            "company_id": "company_nayara_energy",
            "name": "Shell",
            "country": "Netherlands",
            "region": "Western Europe",
            "tier": 1,
            "supplies": ["crude oil", "LPG"],
            "supply_volume_pct": 0.0,
            "status": "pre_qualified",
            "approved_vendor": False,
            "pre_qualified": True,
            "is_single_source": False,
            "esg_score": 76,
            "credit_rating": "AA-",
            "financial_health_score": 8.3,
            "max_capacity": 45000,
            "lead_time_weeks": 4,
            "switching_cost_estimate": 5.8,
            "contract_end": None,
            "upstream_suppliers": [],
            "risk_score_current": 0.0,
            "description": "Royal Dutch Shell, global energy giant",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    # Remove existing
    db_manager.suppliers.delete_many({"company_id": "company_nayara_energy"})
    
    # Insert
    db_manager.suppliers.insert_many(suppliers)
    logger.info(f"✓ Seeded {len(suppliers)} suppliers")


def seed_alerts():
    """Seed 4 realistic alerts for Nayara Energy"""
    now = datetime.utcnow()
    alerts = [
        {
            "risk_event_id": "seed_risk_event_001",
            "company_id": "company_nayara_energy",
            "severity_band": "critical",
            "severity": "critical",
            "risk_score": 9.2,
            "title": "Russia Imposes Crude Oil Export Restrictions",
            "description": (
                "The Russian government has announced emergency export restrictions on crude oil "
                "following new Western sanctions, effective immediately. Rosneft has halted "
                "shipments to non-CIS buyers. Nayara Energy sources 65% of crude oil from Rosneft, "
                "creating a critical supply gap with only 15 days of inventory remaining."
            ),
            "affected_supplier": "Rosneft",
            "affected_suppliers": ["Rosneft"],
            "affected_material": "crude oil",
            "affected_materials": ["crude oil"],
            "recommendation": "Immediately activate alternate supplier ADNOC for emergency spot procurement. Contact Saudi Aramco for spot cargo. Reduce refinery run rates by 20% to extend inventory buffer.",
            "recommendations": [
                {
                    "supplier_id": "supplier_adnoc",
                    "name": "ADNOC",
                    "score": 8.2,
                    "lead_time_weeks": 2,
                    "approved_vendor": True,
                    "country": "UAE",
                    "score_breakdown": {"esg": 8.5, "financial": 8.2, "logistics": 8.0}
                },
                {
                    "supplier_id": "supplier_saudi_aramco",
                    "name": "Saudi Aramco",
                    "score": 8.9,
                    "lead_time_weeks": 3,
                    "approved_vendor": True,
                    "country": "Saudi Arabia",
                    "score_breakdown": {"esg": 8.0, "financial": 9.1, "logistics": 8.5}
                }
            ],
            "alternate_suppliers": [
                {
                    "supplier_id": "supplier_adnoc",
                    "name": "ADNOC",
                    "score": 8.2,
                    "lead_time_weeks": 2,
                    "approved_vendor": True,
                    "country": "UAE",
                    "score_breakdown": {"esg": 8.5, "financial": 8.2, "logistics": 8.0}
                },
                {
                    "supplier_id": "supplier_saudi_aramco",
                    "name": "Saudi Aramco",
                    "score": 8.9,
                    "lead_time_weeks": 3,
                    "approved_vendor": True,
                    "country": "Saudi Arabia",
                    "score_breakdown": {"esg": 8.0, "financial": 9.1, "logistics": 8.5}
                }
            ],
            "is_acknowledged": False,
            "acknowledged_by": None,
            "acknowledged_at": None,
            "resolved_at": None,
            "notification_sent": True,
            "created_at": now - timedelta(hours=2),
            "updated_at": now - timedelta(hours=2)
        },
        {
            "risk_event_id": "seed_risk_event_002",
            "company_id": "company_nayara_energy",
            "severity_band": "high",
            "severity": "high",
            "risk_score": 7.1,
            "title": "UAE Port Congestion Disrupts ADNOC Shipments",
            "description": (
                "Severe congestion at Ruwais and Jebel Ali ports in UAE is causing "
                "2-3 week delays on crude oil shipments from ADNOC. A collision incident "
                "in the Strait of Hormuz involving two tankers has reduced throughput capacity "
                "by 40%. Nayara Energy's next scheduled cargo is at risk of a 3-week delay."
            ),
            "affected_supplier": "ADNOC",
            "affected_suppliers": ["ADNOC"],
            "affected_material": "crude oil",
            "affected_materials": ["crude oil"],
            "recommendation": "Negotiate with ADNOC for alternative loading port (Fujairah). Pre-book spot cargo from BP or Shell to cover the delay window. Monitor Strait of Hormuz situation daily.",
            "recommendations": [
                {
                    "supplier_id": "supplier_bp",
                    "name": "BP",
                    "score": 7.8,
                    "lead_time_weeks": 4,
                    "approved_vendor": False,
                    "country": "United Kingdom",
                    "score_breakdown": {"esg": 8.5, "financial": 7.8, "logistics": 7.2}
                },
                {
                    "supplier_id": "supplier_shell",
                    "name": "Shell",
                    "score": 8.3,
                    "lead_time_weeks": 4,
                    "approved_vendor": False,
                    "country": "Netherlands",
                    "score_breakdown": {"esg": 8.0, "financial": 8.3, "logistics": 8.5}
                }
            ],
            "alternate_suppliers": [
                {
                    "supplier_id": "supplier_bp",
                    "name": "BP",
                    "score": 7.8,
                    "lead_time_weeks": 4,
                    "approved_vendor": False,
                    "country": "United Kingdom",
                    "score_breakdown": {"esg": 8.5, "financial": 7.8, "logistics": 7.2}
                },
                {
                    "supplier_id": "supplier_shell",
                    "name": "Shell",
                    "score": 8.3,
                    "lead_time_weeks": 4,
                    "approved_vendor": False,
                    "country": "Netherlands",
                    "score_breakdown": {"esg": 8.0, "financial": 8.3, "logistics": 8.5}
                }
            ],
            "is_acknowledged": False,
            "acknowledged_by": None,
            "acknowledged_at": None,
            "resolved_at": None,
            "notification_sent": True,
            "created_at": now - timedelta(hours=6),
            "updated_at": now - timedelta(hours=6)
        },
        {
            "risk_event_id": "seed_risk_event_003",
            "company_id": "company_nayara_energy",
            "severity_band": "medium",
            "severity": "medium",
            "risk_score": 5.4,
            "title": "Rosneft Credit Rating Downgraded to CCC",
            "description": (
                "Moody's downgraded Rosneft from BB+ to CCC following escalating US Treasury "
                "sanctions and restricted access to international capital markets. The downgrade "
                "raises concerns about Rosneft's ability to sustain long-term production capacity "
                "and honor existing supply contracts. Contract renegotiation risk has increased significantly."
            ),
            "affected_supplier": "Rosneft",
            "affected_suppliers": ["Rosneft"],
            "affected_material": "crude oil",
            "affected_materials": ["crude oil"],
            "recommendation": "Review and stress-test Rosneft contract terms. Begin qualification process for ONGC as a domestic backup supplier. Diversify crude oil sourcing to reduce Russia dependency below 50%.",
            "recommendations": [
                {
                    "supplier_id": "supplier_ongc",
                    "name": "ONGC",
                    "score": 7.1,
                    "lead_time_weeks": 1,
                    "approved_vendor": True,
                    "country": "India",
                    "score_breakdown": {"esg": 7.5, "financial": 7.1, "logistics": 6.8}
                }
            ],
            "alternate_suppliers": [
                {
                    "supplier_id": "supplier_ongc",
                    "name": "ONGC",
                    "score": 7.1,
                    "lead_time_weeks": 1,
                    "approved_vendor": True,
                    "country": "India",
                    "score_breakdown": {"esg": 7.5, "financial": 7.1, "logistics": 6.8}
                }
            ],
            "is_acknowledged": False,
            "acknowledged_by": None,
            "acknowledged_at": None,
            "resolved_at": None,
            "notification_sent": False,
            "created_at": now - timedelta(days=1),
            "updated_at": now - timedelta(days=1)
        },
        {
            "risk_event_id": "seed_risk_event_004",
            "company_id": "company_nayara_energy",
            "severity_band": "low",
            "severity": "low",
            "risk_score": 3.0,
            "title": "Geopolitical Risk: Russia",
            "description": (
                "Ongoing geopolitical tensions between Russia and Western nations continue to create "
                "low-level uncertainty for crude oil supply chains. While current shipment schedules "
                "are unaffected, OFAC has issued advisory notices regarding secondary sanctions risk "
                "for entities transacting with sanctioned Russian state-owned enterprises."
            ),
            "affected_supplier": "Rosneft",
            "affected_suppliers": ["Rosneft"],
            "affected_material": "crude oil",
            "affected_materials": ["crude oil"],
            "recommendation": "Monitor OFAC sanctions list weekly. Maintain legal review of all Rosneft transaction documentation. Ensure compliance team is briefed on secondary sanctions exposure.",
            "recommendations": [],
            "alternate_suppliers": [],
            "is_acknowledged": False,
            "acknowledged_by": None,
            "acknowledged_at": None,
            "resolved_at": None,
            "notification_sent": False,
            "created_at": now - timedelta(days=2),
            "updated_at": now - timedelta(days=2)
        }
    ]

    # Remove existing seeded alerts
    db_manager.alerts.delete_many({"company_id": "company_nayara_energy"})

    result = db_manager.alerts.insert_many(alerts)
    logger.info(f"✓ Seeded {len(result.inserted_ids)} alerts")


def seed_all():
    """Seed all data"""
    logger.info("=" * 60)
    logger.info("Starting database seeding...")
    logger.info("=" * 60)

    try:
        # Connect to database
        db_manager.connect()

        # Seed data
        seed_company()
        seed_suppliers()
        seed_alerts()

        logger.info("=" * 60)
        logger.info("✓ Database seeding complete!")
        logger.info("=" * 60)

        # Print summary
        company_count = db_manager.companies.count_documents({})
        supplier_count = db_manager.suppliers.count_documents({})
        alert_count = db_manager.alerts.count_documents({})

        logger.info(f"Companies: {company_count}")
        logger.info(f"Suppliers: {supplier_count}")
        logger.info(f"Alerts:    {alert_count}")

    except Exception as e:
        logger.error(f"Error seeding database: {e}", exc_info=True)
        raise
    finally:
        db_manager.disconnect()


if __name__ == "__main__":
    seed_all()
