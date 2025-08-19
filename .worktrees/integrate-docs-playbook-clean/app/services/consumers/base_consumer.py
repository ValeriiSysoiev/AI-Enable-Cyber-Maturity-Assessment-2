"""
Base consumer class with retry logic and correlation ID propagation.
Provides common functionality for all Service Bus message consumers.
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from ...domain.models import ServiceBusMessage
from ...util.logging import get_correlated_logger
from ..service_bus import ServiceBusConsumer


class BaseConsumer(ABC):
    """Base class for Service Bus message consumers"""
    
    def __init__(self, topic: str, correlation_id: Optional[str] = None):
        self.topic = topic
        self.correlation_id = correlation_id
        self.logger = get_correlated_logger(f"consumer.{topic}", correlation_id)
        self.consumer = ServiceBusConsumer(topic, correlation_id)
        self._stats = {
            "messages_processed": 0,
            "messages_failed": 0,
            "last_processed": None,
            "started_at": datetime.now(timezone.utc)
        }
    
    async def start(self, max_concurrent_calls: int = 1):
        """Start the consumer"""
        self.logger.info(f"Starting {self.__class__.__name__} for topic: {self.topic}")
        await self.consumer.start_listening(self._handle_message, max_concurrent_calls)
    
    def stop(self):
        """Stop the consumer"""
        self.logger.info(f"Stopping {self.__class__.__name__} for topic: {self.topic}")
        self.consumer.stop()
    
    async def _handle_message(self, message: ServiceBusMessage) -> bool:
        """Handle incoming message with correlation ID propagation"""
        # Update logger correlation ID to match message
        self.logger.correlation_id = message.correlation_id
        
        try:
            self.logger.info(
                f"Processing message",
                message_id=message.id,
                message_type=message.type,
                engagement_id=message.engagement_id,
                user_email=message.user_email
            )
            
            # Call the specific consumer implementation
            success = await self.process_message(message)
            
            if success:
                self._stats["messages_processed"] += 1
                self._stats["last_processed"] = datetime.now(timezone.utc)
                self.logger.info(
                    f"Message processed successfully",
                    message_id=message.id,
                    total_processed=self._stats["messages_processed"]
                )
            else:
                self._stats["messages_failed"] += 1
                self.logger.warning(
                    f"Message processing returned false",
                    message_id=message.id,
                    total_failed=self._stats["messages_failed"]
                )
            
            return success
            
        except Exception as e:
            self._stats["messages_failed"] += 1
            self.logger.error(
                f"Error processing message",
                message_id=message.id,
                error=str(e),
                error_type=type(e).__name__,
                total_failed=self._stats["messages_failed"]
            )
            return False
    
    @abstractmethod
    async def process_message(self, message: ServiceBusMessage) -> bool:
        """
        Process a specific message. Must be implemented by subclasses.
        
        Args:
            message: The Service Bus message to process
            
        Returns:
            bool: True if message was processed successfully, False otherwise
        """
        pass
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get consumer statistics"""
        return {
            "topic": self.topic,
            "consumer_class": self.__class__.__name__,
            "statistics": self._stats.copy()
        }