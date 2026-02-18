"""
Redis Streams Pipeline Utilities
Provides functions for pushing/consuming messages via Redis Streams
"""

import redis
import json
import logging
from typing import Callable, Optional, Dict, Any, List
from ..utils.config import settings

logger = logging.getLogger(__name__)


class RedisStreamManager:
    """Manages Redis Streams for event processing pipeline"""
    
    # Stream names used in the system
    STREAM_RAW_EVENTS = "raw_events"
    STREAM_NORMALIZED_EVENTS = "normalized_events"
    STREAM_RISK_ENTITIES = "risk_entities"
    STREAM_RISK_SCORES = "risk_scores"
    STREAM_NEW_ALERTS = "new_alerts"
    
    def __init__(self):
        self._redis_client: Optional[redis.Redis] = None
    
    @property
    def client(self) -> redis.Redis:
        """Get Redis client instance"""
        if self._redis_client is None:
            logger.info(f"Connecting to Redis at {settings.redis_url}")
            self._redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True
            )
            # Test connection
            self._redis_client.ping()
            logger.info("Redis connection successful")
        return self._redis_client
    
    def push_to_stream(self, stream_name: str, data: Dict[str, Any]) -> str:
        """
        Push data to a Redis Stream
        
        Args:
            stream_name: Name of the stream
            data: Dictionary of data to push (will be JSON serialized)
        
        Returns:
            Entry ID from Redis
        """
        # Convert complex objects to JSON strings
        serialized_data = {}
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                serialized_data[key] = json.dumps(value)
            else:
                serialized_data[key] = str(value)
        
        entry_id = self.client.xadd(stream_name, serialized_data)
        logger.debug(f"Pushed to stream {stream_name}: {entry_id}")
        return entry_id
    
    def create_consumer_group(self, stream_name: str, group_name: str):
        """
        Create a consumer group for a stream
        
        Args:
            stream_name: Name of the stream
            group_name: Name of the consumer group
        """
        try:
            self.client.xgroup_create(
                name=stream_name,
                groupname=group_name,
                id='$',
                mkstream=True
            )
            logger.info(f"Created consumer group '{group_name}' for stream '{stream_name}'")
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.debug(f"Consumer group '{group_name}' already exists for '{stream_name}'")
            else:
                raise
    
    def consume_stream(
        self,
        stream_name: str,
        group_name: str,
        consumer_name: str,
        handler: Callable[[Dict[str, Any]], None],
        block_ms: int = 5000,
        count: int = 10
    ):
        """
        Consume messages from a Redis Stream with consumer group
        
        Args:
            stream_name: Name of the stream to consume from
            group_name: Consumer group name
            consumer_name: This consumer's unique name
            handler: Function to process each message
            block_ms: Milliseconds to block waiting for messages
            count: Number of messages to fetch at once
        """
        # Ensure consumer group exists
        self.create_consumer_group(stream_name, group_name)
        
        logger.info(f"Consumer '{consumer_name}' started on stream '{stream_name}' (group: {group_name})")
        last_id = '>'
        
        while True:
            try:
                # Read from stream
                messages = self.client.xreadgroup(
                    groupname=group_name,
                    consumername=consumer_name,
                    streams={stream_name: last_id},
                    count=count,
                    block=block_ms
                )
                
                if not messages:
                    continue
                
                for stream, entries in messages:
                    for entry_id, data in entries:
                        try:
                            # Deserialize JSON fields
                            deserialized_data = {}
                            for key, value in data.items():
                                try:
                                    deserialized_data[key] = json.loads(value)
                                except (json.JSONDecodeError, TypeError):
                                    deserialized_data[key] = value
                            
                            # Process message
                            handler(deserialized_data)
                            
                            # Acknowledge message
                            self.client.xack(stream_name, group_name, entry_id)
                            logger.debug(f"Processed and ACKed message {entry_id} from {stream_name}")
                            
                        except Exception as e:
                            logger.error(f"Error processing message {entry_id}: {e}", exc_info=True)
                            # Don't ACK failed messages - they'll be redelivered
                
            except KeyboardInterrupt:
                logger.info(f"Consumer '{consumer_name}' stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in consumer loop: {e}", exc_info=True)
                continue
    
    def read_stream_range(
        self,
        stream_name: str,
        start: str = '-',
        end: str = '+',
        count: Optional[int] = None
    ) -> List[tuple]:
        """
        Read a range of messages from a stream (without consumer group)
        
        Args:
            stream_name: Name of the stream
            start: Start ID ('-' for beginning)
            end: End ID ('+' for end)
            count: Maximum number of messages to return
        
        Returns:
            List of (entry_id, data) tuples
        """
        return self.client.xrange(stream_name, min=start, max=end, count=count)
    
    def get_stream_length(self, stream_name: str) -> int:
        """Get the number of messages in a stream"""
        return self.client.xlen(stream_name)
    
    def trim_stream(self, stream_name: str, max_len: int = 10000):
        """
        Trim stream to maximum length (remove old messages)
        
        Args:
            stream_name: Name of the stream
            max_len: Maximum number of messages to keep
        """
        self.client.xtrim(stream_name, maxlen=max_len, approximate=True)
        logger.info(f"Trimmed stream '{stream_name}' to ~{max_len} messages")


# Global Redis Stream manager instance
stream_manager = RedisStreamManager()


def get_redis_client() -> redis.Redis:
    """Get Redis client instance"""
    return stream_manager.client


def push_to_stream(stream_name: str, data: Dict[str, Any]) -> str:
    """Push data to a Redis Stream"""
    return stream_manager.push_to_stream(stream_name, data)


def consume_stream(
    stream_name: str,
    group_name: str,
    consumer_name: str,
    handler: Callable[[Dict[str, Any]], None],
    block_ms: int = 5000,
    count: int = 10
):
    """Consume messages from a Redis Stream"""
    stream_manager.consume_stream(
        stream_name, group_name, consumer_name, handler, block_ms, count
    )
