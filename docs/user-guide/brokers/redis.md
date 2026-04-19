# Redis Broker

The Redis broker uses [Redis Streams](https://redis.io/docs/data-types/streams/) for task distribution.
It's lightweight, easy to set up, and provides excellent performance for most use cases.

## Installation

Install Chicory with Redis support:

```bash
pip install chicory[redis]
```

## Quick Start

### Basic Setup

```python
from chicory import Chicory, BrokerType

app = Chicory(broker=BrokerType.REDIS)

@app.task()
async def my_task(x: int) -> int:
    return x * 2

# Start worker
# chicory worker tasks:app
```

### Configuration

Configure via environment variables:

```bash
export CHICORY_BROKER_REDIS_HOST=localhost
export CHICORY_BROKER_REDIS_PORT=6379
export CHICORY_BROKER_REDIS_DB=0
```

Or programmatically:

```python
from chicory.config import ChicoryConfig, RedisBrokerConfig

config = ChicoryConfig(
    broker=BrokerConfig(
        redis=RedisBrokerConfig(
            host="localhost",
            port=6379,
            db=0,
        )
    )
)

app = Chicory(broker=BrokerType.REDIS, config=config)
```

## Configuration Options

### Connection Settings

```python
from chicory.config import RedisBrokerConfig
from pydantic import SecretStr

config = RedisBrokerConfig(
    # Basic connection
    host="localhost",
    port=6379,
    db=0,

    # Authentication
    username="myuser",  # Redis 6+ ACL
    password=SecretStr("mypassword"),

    # Or use full URL (overrides above)
    url="redis://user:pass@localhost:6379/0",
)
```

**Environment variables:**
```bash
CHICORY_BROKER_REDIS_HOST=localhost
CHICORY_BROKER_REDIS_PORT=6379
CHICORY_BROKER_REDIS_DB=0
CHICORY_BROKER_REDIS_USERNAME=myuser
CHICORY_BROKER_REDIS_PASSWORD=mypassword
# Or
CHICORY_BROKER_REDIS_URL=redis://user:pass@localhost:6379/0
```

### Consumer Group Settings

```python
config = RedisBrokerConfig(
    # Consumer group name (shared across all workers)
    consumer_group="chicory-workers",

    # Blocking time for XREADGROUP (milliseconds)
    block_ms=5000,

    # Reclaim messages idle for this long (milliseconds)
    claim_min_idle_ms=30000,  # 30 seconds
)
```

**Environment variables:**
```bash
CHICORY_BROKER_REDIS_CONSUMER_GROUP=chicory-workers
CHICORY_BROKER_REDIS_BLOCK_MS=5000
CHICORY_BROKER_REDIS_CLAIM_MIN_IDLE_MS=30000
```

### Delayed-Task Mover Settings

These settings control the background loop that promotes delayed tasks from the sorted set
to the main stream. See [Delayed Tasks / How It Works](#how-it-works-1) for details.

```python
config = RedisBrokerConfig(
    # Minimum sleep between mover iterations (milliseconds).
    # Used after a batch of tasks is promoted or as the lower
    # bound when the next ETA is very close.
    mover_min_sleep_ms=50,   # default 50 ms

    # Maximum sleep between mover iterations (milliseconds).
    # Used when the delayed set is empty or the next ETA is
    # far in the future.
    mover_max_sleep_ms=1000,  # default 1000 ms (1 second)
)
```

**Environment variables:**
```bash
CHICORY_BROKER_REDIS_MOVER_MIN_SLEEP_MS=50
CHICORY_BROKER_REDIS_MOVER_MAX_SLEEP_MS=1000
```

!!! tip "Tuning guidance"
    - **Lower `mover_min_sleep_ms`** (e.g. 10) for sub-100ms ETA precision at the cost of slightly more Redis traffic.
    - **Raise `mover_max_sleep_ms`** (e.g. 5000) to reduce idle polling when delayed tasks are infrequent.

### Stream Management

```python
config = RedisBrokerConfig(
    # Maximum stream length (None = unlimited)
    max_stream_length=100000,

    # Maximum DLQ length
    dlq_max_length=10000,

    # Key prefix for Redis keys
    key_prefix="chicory",
)
```

**Environment variables:**
```bash
CHICORY_BROKER_REDIS_MAX_STREAM_LENGTH=100000
CHICORY_BROKER_REDIS_DLQ_MAX_LENGTH=10000
CHICORY_BROKER_REDIS_KEY_PREFIX=chicory
```

## How It Works

### Redis Streams Overview

Redis Streams provide an append-only log structure perfect for task queues:

```
Stream: chicory:stream:default
├─ 1234567890-0: {data: {...}, task_id: "abc"}
├─ 1234567891-0: {data: {...}, task_id: "def"}
└─ 1234567892-0: {data: {...}, task_id: "ghi"}
```

### Consumer Groups

Workers form a consumer group to distribute tasks:

```
Consumer Group: chicory-workers
├─ worker-1: processing task abc
├─ worker-2: processing task def
└─ worker-3: waiting for tasks
```

Each task is delivered to exactly one consumer in the group.

### Key Structure

Chicory uses these Redis keys:

```
chicory:stream:{queue}         # Main task stream
chicory:delayed:{queue}        # Sorted set for delayed tasks
chicory:dlq:{queue}            # Dead-letter queue stream
```

## Delivery Modes

### At-Least-Once Delivery

Messages are acknowledged after successful processing:

```python
from chicory.types import DeliveryMode

app = Chicory(
    broker=BrokerType.REDIS,
    delivery_mode=DeliveryMode.AT_LEAST_ONCE,
)
```

**Flow:**
1. Worker reads message via `XREADGROUP`
2. Message enters Pending Entries List (PEL)
3. Worker processes task
4. Worker calls `XACK` to acknowledge
5. Message removed from PEL

**If worker crashes:**
- Message remains in PEL
- Other workers can claim it via `XAUTOCLAIM`
- Task is reprocessed (ensure idempotency!)

### At-Most-Once Delivery

Messages are acknowledged before processing:

```python
app = Chicory(
    broker=BrokerType.REDIS,
    delivery_mode=DeliveryMode.AT_MOST_ONCE,
)
```

**Flow:**
1. Worker reads message via `XREADGROUP`
2. Worker immediately calls `XACK`
3. Worker processes task
4. If worker crashes, task is lost

**Use for:** Non-critical tasks where occasional loss is acceptable.

## Dead Letter Queue

### Enabling DLQ

```bash
chicory worker tasks:app --dlq
```

Or programmatically:

```python
from chicory.config import WorkerConfig

worker_config = WorkerConfig(use_dead_letter_queue=True)
worker = Worker(app, config=worker_config)
```

### DLQ Structure

Failed tasks are moved to a separate stream:

```
Stream: chicory:dlq:default
├─ Entry 1:
│   ├─ data: {original task data}
│   ├─ failed_at: "2024-01-24T10:30:00Z"
│   ├─ error: "ConnectionError: timeout"
│   ├─ retry_count: "3"
│   ├─ task_id: "abc123"
│   └─ task_name: "myapp.tasks.fetch_data"
```

### Working with DLQ

```python
# Get failed messages
dlq_messages = await app.broker.get_dlq_messages("default", count=100)

for msg in dlq_messages:
    print(f"Task: {msg.original_message.name}")
    print(f"Failed at: {msg.failed_at}")
    print(f"Error: {msg.error}")
    print(f"Retries: {msg.retry_count}")

# Replay a message (retry it)
success = await app.broker.replay_from_dlq(
    message_id="abc123",
    queue="default",
    reset_retries=True,  # Reset retry counter
)

# Delete a message permanently
success = await app.broker.delete_from_dlq("abc123", queue="default")

# Purge entire DLQ
count = await app.broker.purge_dlq("default")
print(f"Deleted {count} messages from DLQ")
```

## Delayed Tasks

### Scheduling Tasks

```python
from datetime import datetime, timedelta, UTC

# Schedule for specific time
eta = datetime(2024, 12, 25, 9, 0, 0, tzinfo=UTC)
message = TaskMessage(
    id=str(uuid.uuid4()),
    name="send_greeting",
    args=["user@example.com"],
    kwargs={},
    retries=0,
    eta=eta,
)
await app.broker.publish(message)

# Schedule with delay
eta = datetime.now(UTC) + timedelta(hours=1)
```

### How It Works

Delayed tasks use a Redis sorted set with the ETA timestamp as the score and the
pickle-serialized task bytes as the value:

```
Sorted Set: chicory:delayed:default
Score (timestamp) | Value (binary task data)
1640433600.0      | <pickle bytes for task "abc">
1640437200.0      | <pickle bytes for task "def">
```

A **background mover loop** runs inside each worker and periodically promotes
ready tasks to the main stream. Promotion is **atomic**: a server-side Lua
script executes `ZRANGEBYSCORE`, `XADD`, and `ZREM` in a single `EVAL` call,
so no two workers can promote the same task:

```
EVAL lua_move_delayed 2 chicory:delayed:default chicory:stream:default <now>
```

The mover loop uses **adaptive polling** to balance responsiveness and
efficiency:

1. **Tasks just moved**: re-check quickly (`mover_min_sleep_ms`) in case
   more messages are ready in a burst.
2. **Delayed tasks pending**: sleep until the earliest one matures, clamped
   to `[mover_min_sleep_ms, mover_max_sleep_ms]`.
3. **No delayed tasks**: sleep for `mover_max_sleep_ms` to minimize idle
   Redis traffic.

All exceptions except `CancelledError` are caught, so transient Redis errors
(pool exhaustion, network blips) cannot kill the loop; it logs the error and
retries after `mover_max_sleep_ms`.

See [Delayed-Task Mover Settings](#delayed-task-mover-settings) for tuning.

## Comparison with Celery

| Feature             | Chicory      | Celery     |
|---------------------|--------------|------------|
| **Stream API**      | XREADGROUP   | Custom Lua |
| **Consumer Groups** | Native       | Custom     |
| **Delayed Tasks**   | Sorted Set   | Sorted Set |
| **DLQ**             | Stream-based | Custom     |

Chicory uses native Redis Streams features for simpler, more maintainable code.

## Next Steps

- Configure [Redis Backend](../backends/redis.md) for result storage
- Configure [Retry Policies](../../tutorial/retry-policies.md) for error handling
