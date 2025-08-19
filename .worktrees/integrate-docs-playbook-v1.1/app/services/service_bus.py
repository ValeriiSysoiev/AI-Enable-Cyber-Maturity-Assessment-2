"""
Azure Service Bus integration for message queuing with in-memory fallback.
Provides producer and consumer interfaces with retry logic and correlation ID propagation.
"""
import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Any, Callable, TypeVar
from datetime import datetime, timezone
from collections import deque
import uuid

from ..domain.models import ServiceBusMessage, QueueConfig
from ..config import config
from ..util.logging import get_correlated_logger

T = TypeVar('T')

# In-memory queue implementation for local development
class InMemoryQueue:
    """Thread-safe in-memory queue implementation"""
    def __init__(self):
        self._queues: Dict[str, deque] = {}
        self._dlq: Dict[str, deque] = {}
        
    async def send_message(self, topic: str, message: ServiceBusMessage) -> bool:
        """Send message to queue"""
        if topic not in self._queues:
            self._queues[topic] = deque()
        self._queues[topic].append(message)
        return True
    
    async def receive_messages(self, topic: str, max_count: int = 10) -> List[ServiceBusMessage]:
        """Receive messages from queue"""
        if topic not in self._queues:
            return []
        
        messages = []
        for _ in range(min(max_count, len(self._queues[topic]))):
            if self._queues[topic]:
                messages.append(self._queues[topic].popleft())
        return messages
    
    async def dead_letter_message(self, topic: str, message: ServiceBusMessage, reason: str):
        """Move message to dead letter queue"""
        dlq_topic = f"{topic}-dlq"
        if dlq_topic not in self._dlq:
            self._dlq[dlq_topic] = deque()
        
        message.is_dead_lettered = True
        message.dead_letter_reason = reason
        self._dlq[dlq_topic].append(message)
    
    def get_queue_stats(self, topic: str) -> Dict[str, int]:
        """Get queue statistics"""
        return {
            "active_messages": len(self._queues.get(topic, [])),
            "dead_letter_messages": len(self._dlq.get(f"{topic}-dlq", []))
        }


# Global in-memory queue instance
_in_memory_queue = InMemoryQueue()


def retry(max_attempts: int = 3, delay_seconds: int = 1, backoff_multiplier: float = 2.0):
    """
    Retry decorator with exponential backoff.
    Implements the bounded wait pattern similar to scripts/lib/safe.sh::retry
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        async def async_wrapper(*args, **kwargs) -> T:
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait_time = delay_seconds * (backoff_multiplier ** attempt)
                        await asyncio.sleep(wait_time)
                    continue
            raise last_exception
        
        def sync_wrapper(*args, **kwargs) -> T:
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait_time = delay_seconds * (backoff_multiplier ** attempt)
                        time.sleep(wait_time)
                    continue
            raise last_exception
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class ServiceBusProducer:
    """Service Bus producer for sending messages"""
    
    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.logger = get_correlated_logger("service_bus.producer", self.correlation_id)
        self._use_cloud = config.service_bus.is_configured()
        
        if self._use_cloud:
            self.logger.info("Initializing Azure Service Bus producer")
        else:
            self.logger.info("Using in-memory queue fallback for producer")
    
    @retry(max_attempts=3, delay_seconds=1)
    async def send_message(
        self, 
        topic: str, 
        message_type: str, 
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        engagement_id: Optional[str] = None,
        user_email: Optional[str] = None
    ) -> bool:
        """
        Send message to Service Bus topic with idempotency key support.
        Uses Azure Service Bus if configured, otherwise falls back to in-memory queue.
        """
        message = ServiceBusMessage(
            type=message_type,
            payload=payload,
            correlation_id=self.correlation_id,
            max_retries=config.service_bus.max_retries,
            engagement_id=engagement_id,
            user_email=user_email
        )
        
        # Add idempotency key to payload if provided
        if idempotency_key:
            message.payload["_idempotency_key"] = idempotency_key
        
        try:
            if self._use_cloud:
                success = await self._send_to_azure_service_bus(topic, message)
            else:
                success = await _in_memory_queue.send_message(topic, message)
            
            if success:
                self.logger.info(
                    f"Message sent successfully",
                    topic=topic,
                    message_type=message_type,
                    message_id=message.id,
                    idempotency_key=idempotency_key,
                    engagement_id=engagement_id
                )
            return success
            
        except Exception as e:
            self.logger.error(
                f"Failed to send message",
                topic=topic,
                message_type=message_type,
                error=str(e),
                engagement_id=engagement_id
            )
            raise
    
    async def _send_to_azure_service_bus(self, topic: str, message: ServiceBusMessage) -> bool:
        """Send message to Azure Service Bus (placeholder for Azure SDK integration)"""
        # TODO: Implement Azure Service Bus SDK integration
        # from azure.servicebus.aio import ServiceBusClient
        # async with ServiceBusClient.from_connection_string(config.service_bus.connection_string) as client:
        #     sender = client.get_topic_sender(topic)
        #     await sender.send_messages(message.model_dump_json())
        
        self.logger.warning("Azure Service Bus integration not implemented - using in-memory fallback")
        return await _in_memory_queue.send_message(topic, message)


class ServiceBusConsumer:
    """Service Bus consumer for receiving and processing messages"""
    
    def __init__(self, topic: str, correlation_id: Optional[str] = None):
        self.topic = topic
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.logger = get_correlated_logger(f"service_bus.consumer.{topic}", self.correlation_id)
        self._use_cloud = config.service_bus.is_configured()
        self._running = False
        
        if self._use_cloud:
            self.logger.info(f"Initializing Azure Service Bus consumer for topic: {topic}")
        else:
            self.logger.info(f"Using in-memory queue fallback for consumer on topic: {topic}")
    
    async def start_listening(
        self, 
        message_handler: Callable[[ServiceBusMessage], bool],
        max_concurrent_calls: int = 1
    ):
        """Start listening for messages and processing them"""
        self._running = True
        self.logger.info(f"Starting message consumer for topic: {self.topic}")
        
        while self._running:
            try:
                messages = await self._receive_messages()
                
                for message in messages:
                    await self._process_message(message, message_handler)
                
                # Polling delay to prevent tight loop
                if not messages:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                self.logger.error(f"Error in message consumer loop: {str(e)}")
                await asyncio.sleep(5)  # Back off on errors
    
    async def _receive_messages(self) -> List[ServiceBusMessage]:
        """Receive messages from queue"""
        if self._use_cloud:
            return await self._receive_from_azure_service_bus()
        else:
            return await _in_memory_queue.receive_messages(self.topic, max_count=10)
    
    async def _receive_from_azure_service_bus(self) -> List[ServiceBusMessage]:
        """Receive messages from Azure Service Bus (placeholder)"""
        # TODO: Implement Azure Service Bus SDK integration
        self.logger.warning("Azure Service Bus integration not implemented - using in-memory fallback")
        return await _in_memory_queue.receive_messages(self.topic, max_count=10)
    
    async def _process_message(self, message: ServiceBusMessage, handler: Callable[[ServiceBusMessage], bool]):
        """Process individual message with retry logic"""
        try:
            success = handler(message)
            
            if success:
                message.processed_at = datetime.now(timezone.utc)
                message.processed_by = self.topic
                self.logger.info(
                    f"Message processed successfully",
                    message_id=message.id,
                    message_type=message.type,
                    retry_count=message.retry_count
                )
            else:
                await self._handle_message_failure(message, "Handler returned False")
                
        except Exception as e:
            self.logger.error(
                f"Error processing message",
                message_id=message.id,
                error=str(e),
                retry_count=message.retry_count
            )
            await self._handle_message_failure(message, str(e))
    
    async def _handle_message_failure(self, message: ServiceBusMessage, error_reason: str):
        """Handle message processing failure with retry logic"""
        message.retry_count += 1
        
        if message.retry_count >= message.max_retries:
            # Move to dead letter queue
            await self._dead_letter_message(message, error_reason)
        else:
            # Requeue for retry
            delay = config.service_bus.retry_delay_seconds * (2 ** (message.retry_count - 1))
            await asyncio.sleep(delay)
            
            if self._use_cloud:
                # Would requeue in Azure Service Bus
                pass
            else:
                await _in_memory_queue.send_message(self.topic, message)
    
    async def _dead_letter_message(self, message: ServiceBusMessage, reason: str):
        """Move message to dead letter queue"""
        if self._use_cloud:
            # Would use Azure Service Bus DLQ
            pass
        else:
            await _in_memory_queue.dead_letter_message(self.topic, message, reason)
        
        self.logger.warning(
            f"Message moved to dead letter queue",
            message_id=message.id,
            reason=reason,
            retry_count=message.retry_count
        )
    
    def stop(self):
        """Stop the consumer"""
        self._running = False
        self.logger.info(f"Stopping consumer for topic: {self.topic}")


def get_queue_statistics() -> Dict[str, Any]:
    """Get queue statistics for monitoring"""
    if config.service_bus.is_configured():
        # TODO: Implement Azure Service Bus statistics
        return {"mode": "azure_service_bus", "status": "not_implemented"}
    else:
        topics = ["ingest", "minutes", "score"]
        stats = {"mode": "in_memory"}
        
        for topic in topics:
            stats[topic] = _in_memory_queue.get_queue_stats(topic)
        
        return stats