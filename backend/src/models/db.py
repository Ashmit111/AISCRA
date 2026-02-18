"""
MongoDB Database Connection and Management
Provides database client, collection access, and helper functions
"""

from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.database import Database
from pymongo.collection import Collection
from typing import Optional, Dict
import logging

from ..utils.config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages MongoDB connection and provides collection access"""
    
    def __init__(self):
        self._client: Optional[MongoClient] = None
        self._db: Optional[Database] = None
    
    def connect(self) -> Database:
        """Initialize MongoDB connection"""
        if self._client is None:
            logger.info(f"Connecting to MongoDB at {settings.mongo_uri}")
            self._client = MongoClient(settings.mongo_uri)
            self._db = self._client[settings.mongo_db_name]
            logger.info(f"Connected to database: {settings.mongo_db_name}")
            
            # Test connection
            self._client.admin.command('ping')
            logger.info("MongoDB connection successful")
            
            # Create indexes
            self.create_indexes()
        
        return self._db
    
    def disconnect(self):
        """Close MongoDB connection"""
        if self._client:
            self._client.close()
            logger.info("MongoDB connection closed")
            self._client = None
            self._db = None
    
    @property
    def db(self) -> Database:
        """Get database instance"""
        if self._db is None:
            self.connect()
        return self._db
    
    # Collection accessors
    @property
    def companies(self) -> Collection:
        """Companies collection"""
        return self.db["companies"]
    
    @property
    def suppliers(self) -> Collection:
        """Suppliers collection"""
        return self.db["suppliers"]
    
    @property
    def articles(self) -> Collection:
        """Articles collection"""
        return self.db["articles"]
    
    @property
    def risk_events(self) -> Collection:
        """Risk events collection"""
        return self.db["risk_events"]
    
    @property
    def alerts(self) -> Collection:
        """Alerts collection"""
        return self.db["alerts"]
    
    @property
    def reports(self) -> Collection:
        """Reports collection"""
        return self.db["reports"]
    
    def create_indexes(self):
        """Create all necessary indexes for optimal query performance"""
        logger.info("Creating MongoDB indexes...")
        
        # Articles indexes
        self.articles.create_index([("processed", ASCENDING), ("timestamp", DESCENDING)])
        self.articles.create_index([("event_id", ASCENDING)], unique=True)
        
        # Risk events indexes
        self.risk_events.create_index([("affected_supply_chain_nodes", ASCENDING), ("timestamp", DESCENDING)])
        self.risk_events.create_index([("risk_type", ASCENDING), ("severity_band", ASCENDING)])
        self.risk_events.create_index([("company_id", ASCENDING), ("timestamp", DESCENDING)])
        
        # Alerts indexes
        self.alerts.create_index([("is_acknowledged", ASCENDING), ("severity_band", ASCENDING), ("created_at", DESCENDING)])
        self.alerts.create_index([("company_id", ASCENDING), ("created_at", DESCENDING)])
        self.alerts.create_index([("affected_supplier", ASCENDING)])
        
        # Suppliers indexes
        self.suppliers.create_index([("supplies", ASCENDING), ("status", ASCENDING)])
        self.suppliers.create_index([("company_id", ASCENDING), ("tier", ASCENDING)])
        self.suppliers.create_index([("name", ASCENDING)])
        
        # Reports indexes
        self.reports.create_index([("type", ASCENDING), ("generated_at", DESCENDING)])
        
        # Companies index
        self.companies.create_index([("company_name", ASCENDING)])
        
        logger.info("MongoDB indexes created successfully")
    
    def get_company_profile(self, company_id: Optional[str] = None) -> Optional[Dict]:
        """
        Load company profile from MongoDB
        
        Args:
            company_id: Company ID to load (defaults to settings.company_id)
        
        Returns:
            Company profile document or None
        """
        if company_id is None:
            company_id = settings.company_id
        
        company = self.companies.find_one({"_id": company_id})
        return company
    
    def get_suppliers_for_company(self, company_id: Optional[str] = None) -> list:
        """
        Get all suppliers for a company
        
        Args:
            company_id: Company ID (defaults to settings.company_id)
        
        Returns:
            List of supplier documents
        """
        if company_id is None:
            company_id = settings.company_id
        
        suppliers = list(self.suppliers.find({"company_id": company_id}))
        return suppliers


# Global database manager instance
db_manager = DatabaseManager()


def get_db() -> Database:
    """Get MongoDB database instance"""
    return db_manager.db


def get_company_profile(company_id: Optional[str] = None) -> Optional[Dict]:
    """Get company profile"""
    return db_manager.get_company_profile(company_id)


def get_suppliers_for_company(company_id: Optional[str] = None) -> list:
    """Get suppliers for company"""
    return db_manager.get_suppliers_for_company(company_id)
