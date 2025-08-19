"""
Tests for Service Bus implementation including in-memory queue and message serialization.
"""
import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from domain.models import ServiceBusMessage, QueueConfig
from services.service_bus import (
    ServiceBusProducer, 
    ServiceBusConsumer, 
    InMemoryQueue,
    get_queue_statistics,
    retry
)
from services.consumers import BaseConsumer, IngestConsumer, MinutesConsumer, ScoreConsumer


class TestServiceBusMessage:
    """Test ServiceBusMessage model serialization and validation"""
    
    def test_message_creation(self):
        """Test creating a Service Bus message"""
        payload = {"test": "data", "value": 123}
        message = ServiceBusMessage(
            type="test_message",
            payload=payload,
            engagement_id="eng-123",
            user_email="test@example.com"
        )
        
        assert message.type == "test_message"
        assert message.payload == payload
        assert message.engagement_id == "eng-123"
        assert message.user_email == "test@example.com"
        assert message.retry_count == 0
        assert message.max_retries == 3
        assert not message.is_dead_lettered
        assert message.dead_letter_reason is None
    
    def test_message_serialization(self):
        """Test message serialization to/from dict"""
        message = ServiceBusMessage(
            type="ingest",
            payload={"document_id": "doc-123"},
            engagement_id="eng-456"
        )
        
        # Test serialization
        data = message.model_dump()
        assert data["type"] == "ingest"
        assert data["payload"]["document_id"] == "doc-123"
        assert data["engagement_id"] == "eng-456"
        
        # Test deserialization
        new_message = ServiceBusMessage.model_validate(data)
        assert new_message.type == message.type
        assert new_message.payload == message.payload
        assert new_message.engagement_id == message.engagement_id


class TestInMemoryQueue:
    """Test in-memory queue implementation"""
    
    @pytest.fixture
    def queue(self):
        return InMemoryQueue()
    
    @pytest.fixture
    def test_message(self):
        return ServiceBusMessage(
            type="test",
            payload={"data": "test"},
            engagement_id="eng-123"
        )
    
    @pytest.mark.asyncio
    async def test_send_message(self, queue, test_message):
        """Test sending message to queue"""
        result = await queue.send_message("test-topic", test_message)
        assert result is True
        
        stats = queue.get_queue_stats("test-topic")
        assert stats["active_messages"] == 1
        assert stats["dead_letter_messages"] == 0
    
    @pytest.mark.asyncio
    async def test_receive_messages(self, queue, test_message):
        """Test receiving messages from queue"""
        # Send a message first
        await queue.send_message("test-topic", test_message)
        
        # Receive messages
        messages = await queue.receive_messages("test-topic", max_count=10)
        assert len(messages) == 1
        assert messages[0].id == test_message.id
        
        # Queue should be empty now
        stats = queue.get_queue_stats("test-topic")
        assert stats["active_messages"] == 0
    
    @pytest.mark.asyncio
    async def test_dead_letter_message(self, queue, test_message):
        """Test dead lettering a message"""
        await queue.dead_letter_message("test-topic", test_message, "Test error")
        
        # Check message was moved to DLQ
        assert test_message.is_dead_lettered is True
        assert test_message.dead_letter_reason == "Test error"
        
        stats = queue.get_queue_stats("test-topic")
        assert stats["dead_letter_messages"] == 1
    
    @pytest.mark.asyncio
    async def test_queue_stats_empty_topic(self, queue):
        """Test getting stats for non-existent topic"""
        stats = queue.get_queue_stats("non-existent")
        assert stats["active_messages"] == 0
        assert stats["dead_letter_messages"] == 0


class TestServiceBusProducer:
    """Test Service Bus producer"""
    
    @pytest.fixture
    def producer(self):
        return ServiceBusProducer()
    
    @pytest.mark.asyncio
    async def test_send_message_in_memory(self, producer):
        """Test sending message using in-memory queue"""
        # Patch config to use in-memory mode
        with patch('services.service_bus.config.service_bus.is_configured', return_value=False):
            result = await producer.send_message(
                topic="test-topic",
                message_type="test",
                payload={"test": "data"},
                engagement_id="eng-123",
                user_email="test@example.com"
            )
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_send_message_with_idempotency_key(self, producer):
        """Test sending message with idempotency key"""
        with patch('services.service_bus.config.service_bus.is_configured', return_value=False):
            result = await producer.send_message(
                topic="test-topic",
                message_type="test",
                payload={"test": "data"},
                idempotency_key="unique-key-123"
            )
            
            assert result is True


class TestRetryDecorator:
    """Test retry decorator implementation"""
    
    @pytest.mark.asyncio
    async def test_retry_success_first_attempt(self):
        """Test successful function on first attempt"""
        call_count = 0
        
        @retry(max_attempts=3, delay_seconds=0.1)
        async def test_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await test_func()
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_success_after_failures(self):
        """Test successful function after initial failures"""
        call_count = 0
        
        @retry(max_attempts=3, delay_seconds=0.01)  # Very short delay for testing
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception(f"Attempt {call_count} failed")
            return "success"
        
        result = await test_func()
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_exhausted_attempts(self):
        """Test function that fails all retry attempts"""
        call_count = 0
        
        @retry(max_attempts=2, delay_seconds=0.01)
        async def test_func():
            nonlocal call_count
            call_count += 1
            raise Exception(f"Attempt {call_count} failed")
        
        with pytest.raises(Exception) as exc_info:
            await test_func()
        
        assert "Attempt 2 failed" in str(exc_info.value)
        assert call_count == 2


class TestConsumers:
    """Test consumer implementations"""
    
    @pytest.mark.asyncio
    async def test_ingest_consumer_valid_message(self):
        """Test ingest consumer with valid message"""
        consumer = IngestConsumer()
        message = ServiceBusMessage(
            type="ingest",
            payload={
                "document_id": "doc-123",
                "engagement_id": "eng-456",
                "action": "embed"
            }
        )
        
        result = await consumer.process_message(message)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_ingest_consumer_missing_document_id(self):
        """Test ingest consumer with missing document_id"""
        consumer = IngestConsumer()
        message = ServiceBusMessage(
            type="ingest",
            payload={"engagement_id": "eng-456"}
        )
        
        result = await consumer.process_message(message)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_minutes_consumer_valid_message(self):
        """Test minutes consumer with valid message"""
        consumer = MinutesConsumer()
        message = ServiceBusMessage(
            type="minutes",
            payload={
                "engagement_id": "eng-456",
                "assessment_id": "assess-789",
                "template": "executive"
            }
        )
        
        result = await consumer.process_message(message)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_score_consumer_valid_message(self):
        """Test score consumer with valid message"""
        consumer = ScoreConsumer()
        message = ServiceBusMessage(
            type="score",
            payload={
                "assessment_id": "assess-789",
                "engagement_id": "eng-456",
                "scoring_mode": "detailed"
            }
        )
        
        result = await consumer.process_message(message)
        assert result is True
    
    def test_consumer_statistics(self):
        """Test consumer statistics collection"""
        consumer = IngestConsumer()
        stats = consumer.get_statistics()
        
        assert stats["topic"] == "ingest"
        assert stats["consumer_class"] == "IngestConsumer"
        assert "statistics" in stats
        assert stats["statistics"]["messages_processed"] == 0
        assert stats["statistics"]["messages_failed"] == 0


class TestQueueStatistics:
    """Test queue statistics functionality"""
    
    def test_queue_statistics_in_memory_mode(self):
        """Test getting queue statistics in in-memory mode"""
        with patch('services.service_bus.config.service_bus.is_configured', return_value=False):
            stats = get_queue_statistics()
            
            assert stats["mode"] == "in_memory"
            assert "ingest" in stats
            assert "minutes" in stats
            assert "score" in stats
            
            # Each topic should have active and dead letter message counts
            for topic in ["ingest", "minutes", "score"]:
                assert "active_messages" in stats[topic]
                assert "dead_letter_messages" in stats[topic]
    
    def test_queue_statistics_azure_mode(self):
        """Test getting queue statistics in Azure Service Bus mode"""
        with patch('services.service_bus.config.service_bus.is_configured', return_value=True):
            stats = get_queue_statistics()
            
            assert stats["mode"] == "azure_service_bus"
            assert stats["status"] == "not_implemented"