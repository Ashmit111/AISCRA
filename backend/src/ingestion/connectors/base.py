"""
Base Connector Class
Abstract base class for all data source connectors
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class Connector(ABC):
    """Abstract base class for data source connectors"""
    
    def __init__(self, source_name: str):
        """
        Initialize connector
        
        Args:
            source_name: Name of the data source
        """
        self.source_name = source_name
        logger.info(f"Initialized {source_name} connector")
    
    @abstractmethod
    def fetch(self) -> List[Dict[str, Any]]:
        """
        Fetch data from the source
        
        Returns:
            List of raw articles/events
        """
        pass
    
    def validate_config(self) -> bool:
        """
        Validate connector configuration
        
        Returns:
            True if configuration is valid
        """
        return True
    
    def test_connection(self) -> bool:
        """
        Test connection to data source
        
        Returns:
            True if connection successful
        """
        try:
            # Try fetching a small amount of data
            self.fetch()
            return True
        except Exception as e:
            logger.error(f"Connection test failed for {self.source_name}: {e}")
            return False
