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
            "status": "active",
            "approved_vendor": True,
            "pre_qualified": True,
            "is_single_source": False,
            "esg_score": 42,
            "credit_rating": "BB+",
            "financial_health_score": 5.8,
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
            "risk_score_current": 0.0,
            "description": "Major Russian oil company providing crude oil",
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
            "status": "active",
            "approved_vendor": True,
            "pre_qualified": True,
            "is_single_source": False,
            "esg_score": 68,
            "credit_rating": "AA-",
            "financial_health_score": 8.2,
            "max_capacity": 30000,
            "lead_time_weeks": 2,
            "switching_cost_estimate": 4.0,
            "contract_end": datetime.utcnow() + timedelta(days=365*3),
            "upstream_suppliers": [],
            "risk_score_current": 0.0,
            "description": "Abu Dhabi National Oil Company, reliable UAE supplier",
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
        
        logger.info("=" * 60)
        logger.info("✓ Database seeding complete!")
        logger.info("=" * 60)
        
        # Print summary
        company_count = db_manager.companies.count_documents({})
        supplier_count = db_manager.suppliers.count_documents({})
        
        logger.info(f"Companies: {company_count}")
        logger.info(f"Suppliers: {supplier_count}")
        
    except Exception as e:
        logger.error(f"Error seeding database: {e}", exc_info=True)
        raise
    finally:
        db_manager.disconnect()


if __name__ == "__main__":
    seed_all()
