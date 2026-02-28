# RabbitMQ Broker

The RabbitMQ broker provides enterprise-grade message queuing with advanced features like priority queues, flexible routing, and native high availability.

## Installation

Install Chicory with RabbitMQ support:

```bash
pip install chicory[rabbitmq]
```

## Quick Start

### Basic Setup

```python
from chicory import Chicory, BrokerType

app = Chicory(broker=BrokerType.RABBITMQ)

@app.task()
async def my_task(x: int) -> int:
    return x * 2

# Start worker
# chicory worker tasks:app
```

### Configuration

Configure via environment variables:

```bash
export CHICORY_BROKER_RABBITMQ_HOST=localhost
export CHICORY_BROKER_RABBITMQ_PORT=5672
export CHICORY_BROKER_RABBITMQ_USERNAME=guest
export CHICORY_BROKER_RABBITMQ_PASSWORD=guest
```

Or programmatically:

```python
from chicory.config import ChicoryConfig, RabbitMQBrokerConfig
from pydantic import SecretStr

config = ChicoryConfig(
    broker=BrokerConfig(
        rabbitmq=RabbitMQBrokerConfig(
            host="localhost",
            port=5672,
            username="guest",
            password=SecretStr("guest"),
        )
    )
)

app = Chicory(broker=BrokerType.RABBITMQ, config=config)
```

## Configuration Options

### Connection Settings

```python
from chicory.config import RabbitMQBrokerConfig
from pydantic import SecretStr

config = RabbitMQBrokerConfig(
    # Basic connection
    host="localhost",
    port=5672,
    username="guest",
    password=SecretStr("guest"),
    vhost="/",  # Virtual host (optional)

    # Or use full AMQP URL (overrides above)
    url="amqp://user:pass@localhost:5672//vhost",

    # Connection pooling
    connection_pool_size=1,
    channel_pool_size=10,
    channel_acquire_timeout=10.0,
)
```

**Environment variables:**
```bash
CHICORY_BROKER_RABBITMQ_HOST=localhost
CHICORY_BROKER_RABBITMQ_PORT=5672
CHICORY_BROKER_RABBITMQ_USERNAME=guest
CHICORY_BROKER_RABBITMQ_PASSWORD=guest
CHICORY_BROKER_RABBITMQ_VHOST=/
# Or
CHICORY_BROKER_RABBITMQ_URL=amqp://guest:guest@localhost:5672/
```

### Queue Settings

```python
config = RabbitMQBrokerConfig(
    # Queue durability
    durable_queues=True,  # Survive broker restarts

    # Queue limits
    queue_max_length=100000,  # Max messages
    queue_max_length_bytes=None,  # Max bytes (optional)

    # Message TTL
    message_ttl=3600000,  # 1 hour in milliseconds

    # Queue mode
    queue_mode="default",  # or "lazy" for disk-first

    # Priority queues
    max_priority=10,  # Enable priority 0-10 (None = disabled)

    # Prefetch count (QoS)
    prefetch_count=1,  # Messages per consumer
)
```

**Environment variables:**
```bash
CHICORY_BROKER_RABBITMQ_DURABLE_QUEUES=true
CHICORY_BROKER_RABBITMQ_QUEUE_MAX_LENGTH=100000
CHICORY_BROKER_RABBITMQ_MESSAGE_TTL=3600000
CHICORY_BROKER_RABBITMQ_QUEUE_MODE=lazy
CHICORY_BROKER_RABBITMQ_MAX_PRIORITY=10
CHICORY_BROKER_RABBITMQ_PREFETCH_COUNT=1
```

### Dead Letter Queue

```python
config = RabbitMQBrokerConfig(
    # DLQ limits
    dlq_max_length=10000,
    dlq_message_ttl=None,  # No expiration

    # DLQ scanning
    max_dlq_scan_limit=10000,  # Max messages to scan
)
```

### Reconnection

```python
config = RabbitMQBrokerConfig(
    # Reconnection backoff
    reconnect_delay_base=1.0,  # Initial delay (seconds)
    reconnect_delay_max=60.0,  # Maximum delay (seconds)
)
```

## How It Works

### Queue Structure

Chicory creates these RabbitMQ queues:

```
chicory.queue.{queue}          # Main task queue
chicory.dlq.{queue}            # Dead-letter queue
chicory.delayed-queue.{queue}  # Delayed task staging
```

### Message Flow

1. **Publishing:**
   ```
   Producer -> Exchange (default) -> chicory.queue.default
   ```

2. **Consuming:**
   ```
   chicory.queue.default -> Worker -> ACK/NACK
   ```

3. **Dead Letter:**
   ```
   Failed Task -> DLX -> chicory.dlq.default
   ```

### Channel Pooling

Chicory maintains connection and channel pools:

```python
# 1 connection pool (for publishing)
# 10 channels (shared across publish operations)
# 1 dedicated connection for consuming
# 1 dedicated channel for consuming
```

This provides better performance and connection efficiency.

## Delivery Modes

### At-Least-Once Delivery

Messages are acknowledged after successful processing:

```python
from chicory.types import DeliveryMode

app = Chicory(
    broker=BrokerType.RABBITMQ,
    delivery_mode=DeliveryMode.AT_LEAST_ONCE,
)
```

**Flow:**
1. Message delivered to worker
2. Worker processes task
3. Worker sends ACK
4. Message removed from queue

**On failure:**
- Worker sends NACK
- Message requeued or moved to DLQ

**Guarantees:** No message loss, possible duplicates

### At-Most-Once Delivery

Messages are acknowledged before processing:

```python
app = Chicory(
    broker=BrokerType.RABBITMQ,
    delivery_mode=DeliveryMode.AT_MOST_ONCE,
)
```

**Flow:**
1. Message delivered to worker
2. Worker sends immediate ACK
3. Worker processes task

**On failure:**
- Task lost (already ACKed)

**Guarantees:** No duplicates, possible message loss

## Priority Queues

Enable priority-based task processing:

### Configuration

```python
config = RabbitMQBrokerConfig(
    max_priority=10,  # Priority range: 0-10
)
```

### Publishing Priority Tasks

```python
from chicory.types import TaskMessage

# High priority task
message = TaskMessage(
    id="task-1",
    name="urgent_task",
    args=[],
    kwargs={},
    retries=0,
    priority=10,  # Highest priority
)
await app.broker.publish(message)

# Normal priority task
message = TaskMessage(..., priority=5)
await app.broker.publish(message)

# Low priority task
message = TaskMessage(..., priority=1)
await app.broker.publish(message)
```

!!! info "Priority Overhead"
    Priority queues have slight performance overhead. Use only when needed.

## Dead Letter Queue

### Native DLX Support

RabbitMQ provides native dead-letter exchange (DLX) support:

```python
# Enable DLQ
chicory worker tasks:app --dlq
```

**How it works:**
1. Task fails after max retries
2. Worker rejects message (`NACK` with `requeue=False`)
3. RabbitMQ routes to DLX automatically
4. Message appears in `chicory.dlq.{queue}`

### DLQ Operations

```python
# List DLQ messages
dlq_messages = await app.broker.get_dlq_messages("default", count=100)

for msg in dlq_messages:
    print(f"Task: {msg.original_message.name}")
    print(f"Error: {msg.error}")
    print(f"Failed at: {msg.failed_at}")

# Replay a message
success = await app.broker.replay_from_dlq(
    message_id="task-123",
    queue="default",
    reset_retries=True,
)

# Delete from DLQ
success = await app.broker.delete_from_dlq("task-123", queue="default")

# Purge DLQ
count = await app.broker.purge_dlq("default")
```

!!! warning "DLQ Scanning"
    `get_dlq_messages()` scans the queue, which can be slow for large DLQs. Consider using the RabbitMQ Management API for better performance.

## Delayed Tasks

Chicory implements delayed tasks using TTL + dead-letter-exchange pattern:

```python
from datetime import datetime, timedelta, UTC

# Schedule task
eta = datetime.now(UTC) + timedelta(hours=1)
message = TaskMessage(..., eta=eta)
await app.broker.publish(message)
```

**How it works:**
1. Message published to `chicory.delayed-queue.{queue}`
2. Message has per-message TTL
3. After TTL expires, RabbitMQ routes to main queue via DLX
4. Worker processes task

**Limitations:**
- Minimum delay: ~1 second
- Maximum delay: Limited by RabbitMQ's 32-bit TTL (24 days)

## Queue Modes

### Default Mode

Messages kept in memory for fast access:

```python
config = RabbitMQBrokerConfig(
    queue_mode="default",
)
```

**Use for:**
- High-throughput, low-latency workloads
- Small message sizes
- Sufficient RAM available

### Lazy Mode

Messages moved to disk as soon as possible:

```python
config = RabbitMQBrokerConfig(
    queue_mode="lazy",
)
```

**Use for:**
- Large queue depths
- Limited RAM
- Large message payloads
- Can tolerate slight latency increase

**Trade-offs:**
- Lower memory usage
- Slightly higher latency (~10-20%)
- Disk I/O becomes bottleneck

## Next Steps

- Configure [Backends](../backends/index.md) for result storage
- Configure [Retry Policies](../../tutorial/retry-policies.md) for error handling
- Review [Configuration](../configuration.md) for advanced tuning
