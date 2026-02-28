# Message Brokers

Message brokers are the backbone of Chicory's task distribution system. They queue task messages and deliver them to workers for execution.

## Overview

Chicory supports two production-ready message brokers:

- **Redis Streams** - Lightweight, simple setup, great for most use cases
- **RabbitMQ** - Advanced features, high availability, complex routing

## Choosing a Broker

### Redis Streams

**Best for:**
- Getting started quickly
- Simpler infrastructure requirements
- Moderate throughput (< 50k messages/sec)
- Teams already using Redis

**Pros:**
- Simple setup (single Redis instance)
- Low operational overhead
- Lightweight dependencies
- Good performance for most workloads
- Consumer groups for load balancing
- Built-in persistence

**Cons:**
- Fewer advanced features than RabbitMQ
- No native priority queues
- Limited routing capabilities

**Use Redis when:**
- You're already using Redis for caching
- You want minimal infrastructure
- You need simple, reliable task queueing
- Your throughput is < 50k messages/sec

[:octicons-arrow-right-24: Redis Broker Guide](redis.md)

### RabbitMQ

**Best for:**
- High-throughput systems (> 50k messages/sec)
- Complex routing requirements
- Priority queues
- Multi-tenant systems
- Advanced delivery guarantees

**Pros:**
- Battle-tested message broker
- Rich feature set (routing, priorities, federation)
- Excellent management UI
- Built-in clustering and high availability
- Fine-grained control over queues
- Native dead-letter exchange support

**Cons:**
- More complex setup and operation
- Higher resource usage
- Steeper learning curve
- More configuration options

**Use RabbitMQ when:**
- You need priority queues
- You require complex routing
- You need high availability
- You're already using RabbitMQ
- Your throughput exceeds 50k messages/sec

[:octicons-arrow-right-24: RabbitMQ Broker Guide](rabbitmq.md)

## Feature Comparison

| Feature | Redis Streams | RabbitMQ |
|---------|--------------|----------|
| **Setup Complexity** | Simple | Moderate |
| **Priority Queues** | No | Yes |
| **Message Routing** | Basic | Advanced |
| **Dead Letter Queue** | Manual | Native |
| **Delayed Tasks** | Sorted Set | TTL + DLX |
| **Monitoring** | Redis CLI | Management UI |
| **Clustering** | Redis Cluster | Native |
| **Persistence** | RDB/AOF | Built-in |
| **Memory Usage** | Low | Moderate |

## Basic Usage

### Initialization

All brokers use the same Chicory API:

```python
from chicory import Chicory, BrokerType

# Redis
app = Chicory(broker=BrokerType.REDIS)

# RabbitMQ
app = Chicory(broker=BrokerType.RABBITMQ)
```

### Configuration

Configure via environment variables:

```bash
# Redis
export CHICORY_BROKER_REDIS_HOST=localhost
export CHICORY_BROKER_REDIS_PORT=6379

# RabbitMQ
export CHICORY_BROKER_RABBITMQ_HOST=localhost
export CHICORY_BROKER_RABBITMQ_PORT=5672
export CHICORY_BROKER_RABBITMQ_USERNAME=guest
export CHICORY_BROKER_RABBITMQ_PASSWORD=guest
```

Or programmatically:

```python
from chicory.config import ChicoryConfig, RedisBrokerConfig

config = ChicoryConfig(
    broker=BrokerConfig(
        redis=RedisBrokerConfig(
            host="redis.example.com",
            port=6379,
        )
    )
)

app = Chicory(broker=BrokerType.REDIS, config=config)
```

## Delivery Guarantees

### At-Least-Once

Messages are guaranteed to be delivered and processed at least once:

```python
from chicory.types import DeliveryMode

app = Chicory(
    broker=BrokerType.REDIS,
    delivery_mode=DeliveryMode.AT_LEAST_ONCE,
)

@app.task(delivery_mode=DeliveryMode.AT_LEAST_ONCE)
async def critical_task():
    # This may execute multiple times
    # Make it idempotent!
    pass
```

**How it works:**
1. Worker receives message
2. Worker processes task
3. Worker acknowledges message
4. If worker crashes before step 3, message is redelivered

**Use for:** Critical tasks that cannot be lost (payments, data consistency)

### At-Most-Once

Messages are delivered once and may be lost on worker failure:

```python
@app.task(delivery_mode=DeliveryMode.AT_MOST_ONCE)
async def analytics_event():
    # Acknowledged before execution
    # Lost if worker crashes
    pass
```

**How it works:**
1. Worker receives message
2. Worker acknowledges message
3. Worker processes task
4. If worker crashes after step 2, message is lost

**Use for:** Best-effort tasks where occasional loss is acceptable (logging, analytics)

## Delayed/Scheduled Tasks

Both brokers support delayed task execution:

```python
from datetime import datetime, timedelta, UTC

# Schedule for specific time
eta = datetime(2024, 12, 25, 9, 0, 0)
message = TaskMessage(..., eta=eta)
await app.broker.publish(message)

# Schedule with delay
eta = datetime.now(UTC) + timedelta(hours=1)
message = TaskMessage(..., eta=eta)
await app.broker.publish(message)
```

**Implementation:**
- **Redis**: Uses sorted sets, workers periodically move ready tasks to stream
- **RabbitMQ**: Uses per-message TTL + dead-letter-exchange pattern

## Multiple Queues

Route tasks to specific workers using multiple queues:

```python
# Publish to specific queue
await app.broker.publish(message, queue="high-priority")
await app.broker.publish(message, queue="low-priority")
```

```bash
# Start workers for different queues
chicory worker tasks:app --queue high-priority
chicory worker tasks:app --queue low-priority
```

**Use cases:**
- Priority-based processing
- Resource separation (CPU-bound vs I/O-bound)
- Tenant isolation
- Rate limiting

## Next Steps

Choose your broker and dive into the detailed configuration guide:

<div class="grid cards" markdown>

-   :simple-redis:{ .lg .middle } **Redis Streams**

    ---

    Simple, reliable task queueing with Redis Streams.

    [:octicons-arrow-right-24: Redis Guide](redis.md)

-   :simple-rabbitmq:{ .lg .middle } **RabbitMQ**

    ---

    Advanced features and high-throughput messaging.

    [:octicons-arrow-right-24: RabbitMQ Guide](rabbitmq.md)

</div>
