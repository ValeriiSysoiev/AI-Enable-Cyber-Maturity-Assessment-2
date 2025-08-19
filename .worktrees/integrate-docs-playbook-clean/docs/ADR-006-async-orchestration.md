# ADR-006: Async Orchestration with Azure Service Bus

**Status:** ✅ Accepted  
**Date:** 2025-08-18  
**Sprint:** S4  

## Context

Sprint S4 requires implementing asynchronous orchestration capabilities to handle chat commands that generate RunCards for long-running AI operations. The system needs to:

- Decouple command processing from execution to improve user experience
- Support fan-out/fan-in patterns for parallel AI agent coordination
- Provide reliable message delivery with retry and dead letter queue (DLQ) capabilities
- Enable horizontal scaling of consumer services
- Maintain exactly-once processing semantics with idempotency
- Support both local development and production Azure environments

The synchronous approach creates bottlenecks when users initiate complex operations like generating comprehensive cybersecurity assessments that require multiple AI agents to coordinate work.

## Decision

We have implemented a dual-mode asynchronous orchestration system using **Azure Service Bus** for production with **in-memory queue fallback** for local development.

### Architecture Overview

```
Chat Commands → RunCards → Service Bus → Consumers → AI Agents
                    ↓           ↓           ↓          ↓
              [Idempotency] [Retries]  [DLQ]    [Results]
                    ↓           ↓           ↓          ↓
              Correlation IDs  Metrics  Monitoring  Storage
```

### Core Components

#### 1. **Message Queue Infrastructure**
- **Production:** Azure Service Bus with managed identities
- **Development:** In-memory queue with identical interface
- **Topics:** `ingest`, `minutes`, `score` for different workflow stages
- **Subscriptions:** Auto-scaling consumer groups per topic

#### 2. **Fan-Out/Fan-In Pattern**
```
Orchestration Request
        ↓
    Service Bus
   ↙     ↓     ↘
Ingest  Minutes Score  (Fan-Out)
   ↓     ↓     ↓
Consumer Consumer Consumer
   ↓     ↓     ↓
Results Aggregation     (Fan-In)
        ↓
   Final Response
```

#### 3. **Message Structure**
- **ID:** UUID for tracking and deduplication
- **Type:** Routing key (`ingest`, `minutes`, `score`)
- **Payload:** JSON data with engagement context
- **Correlation ID:** Request tracing across service boundaries
- **Retry Logic:** Exponential backoff with max 5 attempts
- **Idempotency Key:** Prevents duplicate processing

#### 4. **Consumer Architecture**
```python
class BaseConsumer(ABC):
    async def process_message(self, message: ServiceBusMessage) -> bool
    async def handle_retry(self, message: ServiceBusMessage, error: str)
    async def dead_letter(self, message: ServiceBusMessage, reason: str)
```

## Implementation Details

### Retry Policy & Error Handling

**Exponential Backoff Strategy:**
- Initial delay: 1 second
- Backoff multiplier: 2.0
- Maximum retries: 5 attempts
- Total retry window: ~31 seconds

```python
retry_delay = base_delay * (2 ** (retry_count - 1))
# Sequence: 1s, 2s, 4s, 8s, 16s → DLQ
```

**Dead Letter Queue (DLQ) Strategy:**
- Messages exceeding max retries → automatic DLQ transfer
- Poison message detection and isolation
- Manual DLQ inspection and reprocessing capabilities
- Alerting on DLQ threshold breaches

### Idempotency Implementation

**Message Deduplication:**
- Idempotency keys in message payload: `_idempotency_key`
- Consumer-side duplicate detection and skip logic
- Exactly-once processing semantics
- Result caching for duplicate requests

**Correlation ID Propagation:**
```python
message.correlation_id = request_correlation_id
logger = get_correlated_logger("consumer", correlation_id)
# Enables distributed tracing across service boundaries
```

### Topic/Subscription Model

| Topic | Purpose | Consumers | Scaling |
|-------|---------|-----------|---------|
| `ingest` | Document processing | IngestConsumer | Auto-scale 1-10 |
| `minutes` | Meeting analysis | MinutesConsumer | Auto-scale 1-5 |
| `score` | Assessment scoring | ScoreConsumer | Auto-scale 1-15 |

### Local Development Support

**In-Memory Queue Features:**
- Thread-safe deque implementation
- Identical producer/consumer interfaces
- DLQ simulation with separate queues
- Statistics and monitoring endpoints
- No external dependencies required

### Migration Path

**Phase 1:** In-memory development (✅ Complete)
**Phase 2:** Azure Service Bus integration (🔄 In Progress)
**Phase 3:** Consumer auto-scaling (📋 Planned)
**Phase 4:** Advanced monitoring (📋 Planned)

## Configuration

```python
class ServiceBusConfig:
    namespace: str = "cyber-assessment-sb"
    connection_string: str = env("SERVICE_BUS_CONN_STRING")
    max_retries: int = 5
    retry_delay_seconds: int = 1
    message_ttl_seconds: int = 3600
    
    def is_configured(self) -> bool:
        return bool(self.namespace and self.connection_string)
```

**Environment Variables:**
- `SERVICE_BUS_NAMESPACE`: Azure Service Bus namespace
- `SERVICE_BUS_CONN_STRING`: Connection string with managed identity
- `SERVICE_BUS_MAX_RETRIES`: Maximum retry attempts (default: 5)
- `SERVICE_BUS_RETRY_DELAY`: Base retry delay in seconds (default: 1)

## Monitoring & Observability

**Structured Logging:**
```json
{
  "timestamp": "2025-08-18T10:30:00Z",
  "level": "INFO",
  "correlation_id": "req-12345",
  "component": "service_bus.producer",
  "topic": "score",
  "message_id": "msg-67890",
  "engagement_id": "eng-abc123",
  "retry_count": 0,
  "message": "Message sent successfully"
}
```

**Key Metrics:**
- Message throughput per topic
- Processing latency percentiles (P50, P95, P99)
- Retry rates and DLQ volume
- Consumer scaling events
- Error rates by consumer type

**Alerting Thresholds:**
- DLQ messages > 10 per hour
- Processing latency > 30 seconds
- Error rate > 5%
- Consumer failures > 3 per minute

## Consequences

### Positive

✅ **Improved User Experience:** Non-blocking operations with progress tracking  
✅ **Horizontal Scalability:** Consumer auto-scaling based on queue depth  
✅ **Reliability:** Retry logic and DLQ handling prevent message loss  
✅ **Decoupling:** Services can evolve independently  
✅ **Development Velocity:** In-memory fallback enables offline development  
✅ **Observability:** Correlation IDs enable distributed tracing  
✅ **Cost Efficiency:** Pay-per-use Azure Service Bus pricing model  

### Negative

⚠️ **Complexity:** Additional infrastructure and error handling  
⚠️ **Eventual Consistency:** Async operations require status polling  
⚠️ **Operational Overhead:** Monitoring queues and consumer health  
⚠️ **Message Ordering:** Limited ordering guarantees across partitions  

### Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| **Message Loss** | Retry logic, DLQ, and Azure Service Bus durability |
| **Poison Messages** | Circuit breakers and automatic DLQ transfer |
| **Consumer Failures** | Health checks, auto-restart, and scaling policies |
| **Queue Backpressure** | Auto-scaling, alerting, and manual intervention |
| **Azure Outages** | Graceful degradation to synchronous processing |

## Alternatives Considered

1. **Synchronous Processing:** Rejected due to user experience and scalability concerns
2. **Azure Storage Queues:** Rejected due to limited message size and features  
3. **Redis Pub/Sub:** Rejected due to message persistence requirements
4. **Event Grid:** Rejected due to complexity for simple fan-out patterns
5. **Custom Queue System:** Rejected due to operational overhead and reliability

## Status

**Current Implementation:**
- ✅ Service Bus producer/consumer interfaces
- ✅ In-memory queue fallback for development
- ✅ Retry logic with exponential backoff
- ✅ Dead letter queue handling
- ✅ Idempotency key support
- ✅ Correlation ID propagation
- ✅ Comprehensive test coverage

**Next Phase (S5):**
- 🔄 Azure Service Bus SDK integration
- 🔄 Consumer auto-scaling policies
- 🔄 Advanced monitoring and alerting
- 🔄 Performance optimization and tuning

## References

- [Sprint S4 Requirements](../README.md#async-orchestration-sprint-s4)
- [Service Bus Implementation](/app/services/service_bus.py)
- [Consumer Base Classes](/app/services/consumers/)
- [Message Models](/app/domain/models.py#ServiceBusMessage)
- [Configuration](/app/config.py#ServiceBusConfig)
- [Test Coverage](/app/tests/test_service_bus.py)