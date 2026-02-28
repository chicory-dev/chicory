# Configuration

Chicory provides a flexible configuration system using Pydantic Settings with support for environment variables, .env files, and programmatic configuration.

## Configuration Priority

Configuration is loaded in this order (highest to lowest priority):

1. **Explicit parameters** passed to `Chicory()` or `Worker()`
2. **Programmatic config** via `ChicoryConfig` object
3. **Environment variables** with `CHICORY_` prefix
4. **.env file** in current directory
5. **Default values**

## Quick Start

### Environment Variables

```bash
# .env file
CHICORY_BROKER_REDIS_HOST=localhost
CHICORY_BROKER_REDIS_PORT=6379
CHICORY_BACKEND_REDIS_HOST=localhost
CHICORY_WORKER_CONCURRENCY=32
CHICORY_VALIDATION_MODE=strict
```

```python
# Automatic loading from .env
from chicory import Chicory, BrokerType, BackendType

app = Chicory(
    broker=BrokerType.REDIS,
    backend=BackendType.REDIS,
)
```

### Programmatic Configuration

```python
from chicory import Chicory, ChicoryConfig
from chicory.config import (
    BrokerConfig,
    BackendConfig,
    WorkerConfig,
    RedisBrokerConfig,
    RedisBackendConfig,
)
from chicory.types import ValidationMode, DeliveryMode
from pydantic import SecretStr

config = ChicoryConfig(
    # App-level settings
    validation_mode=ValidationMode.STRICT,
    delivery_mode=DeliveryMode.AT_LEAST_ONCE,

    # Broker configuration
    broker=BrokerConfig(
        redis=RedisBrokerConfig(
            host="redis.example.com",
            port=6379,
            db=0,
            password=SecretStr("broker-password"),
        )
    ),

    # Backend configuration
    backend=BackendConfig(
        redis=RedisBackendConfig(
            host="redis.example.com",
            port=6379,
            db=1,
            password=SecretStr("backend-password"),
            result_ttl=3600,
        )
    ),

    # Worker configuration
    worker=WorkerConfig(
        concurrency=32,
        queue="default",
        use_dead_letter_queue=True,
        heartbeat_interval=10.0,
        heartbeat_ttl=30,
        shutdown_timeout=30.0,
        log_level="INFO",
    ),
)

app = Chicory(
    broker=BrokerType.REDIS,
    backend=BackendType.REDIS,
    config=config,
)
```

## App Configuration

### Validation Mode

```python
from chicory.types import ValidationMode

# Validate inputs only (default)
app = Chicory(validation_mode=ValidationMode.INPUTS)

# Validate outputs only
app = Chicory(validation_mode=ValidationMode.OUTPUTS)

# Validate both
app = Chicory(validation_mode=ValidationMode.STRICT)

# No validation
app = Chicory(validation_mode=ValidationMode.NONE)
```

**Environment variable:**
```bash
CHICORY_VALIDATION_MODE=strict  # none, inputs, outputs, strict
```

### Delivery Mode

```python
from chicory.types import DeliveryMode

# At-least-once (default)
app = Chicory(delivery_mode=DeliveryMode.AT_LEAST_ONCE)

# At-most-once
app = Chicory(delivery_mode=DeliveryMode.AT_MOST_ONCE)
```

**Environment variable:**
```bash
CHICORY_DELIVERY_MODE=at_least_once  # or at_most_once
```

### Result Polling

```python
config = ChicoryConfig(
    result_poll_interval=0.1,  # Poll every 100ms
    result_default_timeout=None,  # No timeout by default
)
```

**Environment variables:**
```bash
CHICORY_RESULT_POLL_INTERVAL=0.1
CHICORY_RESULT_DEFAULT_TIMEOUT=30.0
```

## Broker Configuration

### Redis Broker

```python
from chicory.config import RedisBrokerConfig
from pydantic import SecretStr

config = RedisBrokerConfig(
    # Connection
    host="localhost",
    port=6379,
    db=0,
    username=None,
    password=SecretStr("secret"),
    url=None,  # Overrides above if set

    # Consumer group
    consumer_group="chicory-workers",
    block_ms=5000,
    claim_min_idle_ms=30000,

    # Stream management
    max_stream_length=100000,
    dlq_max_length=10000,
    key_prefix="chicory",
)
```

**Environment variables:**
```bash
CHICORY_BROKER_REDIS_HOST=localhost
CHICORY_BROKER_REDIS_PORT=6379
CHICORY_BROKER_REDIS_DB=0
CHICORY_BROKER_REDIS_PASSWORD=secret
CHICORY_BROKER_REDIS_CONSUMER_GROUP=chicory-workers
CHICORY_BROKER_REDIS_BLOCK_MS=5000
CHICORY_BROKER_REDIS_CLAIM_MIN_IDLE_MS=30000
CHICORY_BROKER_REDIS_MAX_STREAM_LENGTH=100000
CHICORY_BROKER_REDIS_DLQ_MAX_LENGTH=10000
CHICORY_BROKER_REDIS_KEY_PREFIX=chicory
```

### RabbitMQ Broker

```python
from chicory.config import RabbitMQBrokerConfig
from pydantic import SecretStr

config = RabbitMQBrokerConfig(
    # Connection
    host="localhost",
    port=5672,
    username="guest",
    password=SecretStr("guest"),
    vhost=None,
    url=None,  # Overrides above if set

    # Pooling
    connection_pool_size=1,
    channel_pool_size=10,
    prefetch_count=1,

    # Queue settings
    queue_max_length=None,
    queue_max_length_bytes=None,
    dlq_max_length=10000,
    message_ttl=None,
    dlq_message_ttl=None,
    durable_queues=True,
    queue_mode=None,  # or "lazy"
    max_priority=None,  # or 10 for priority queues

    # Timeouts
    channel_acquire_timeout=10.0,
    reconnect_delay_base=1.0,
    reconnect_delay_max=60.0,
    max_dlq_scan_limit=10000,
)
```

**Environment variables:**
```bash
CHICORY_BROKER_RABBITMQ_HOST=localhost
CHICORY_BROKER_RABBITMQ_PORT=5672
CHICORY_BROKER_RABBITMQ_USERNAME=guest
CHICORY_BROKER_RABBITMQ_PASSWORD=guest
CHICORY_BROKER_RABBITMQ_VHOST=/
CHICORY_BROKER_RABBITMQ_CONNECTION_POOL_SIZE=1
CHICORY_BROKER_RABBITMQ_CHANNEL_POOL_SIZE=10
CHICORY_BROKER_RABBITMQ_PREFETCH_COUNT=1
CHICORY_BROKER_RABBITMQ_QUEUE_MAX_LENGTH=100000
CHICORY_BROKER_RABBITMQ_DLQ_MAX_LENGTH=10000
CHICORY_BROKER_RABBITMQ_DURABLE_QUEUES=true
CHICORY_BROKER_RABBITMQ_QUEUE_MODE=lazy
CHICORY_BROKER_RABBITMQ_MAX_PRIORITY=10
```

## Backend Configuration

### Redis Backend

```python
from chicory.config import RedisBackendConfig
from pydantic import SecretStr

config = RedisBackendConfig(
    # Connection
    host="localhost",
    port=6379,
    db=1,
    username=None,
    password=SecretStr("secret"),
    url=None,  # Overrides above if set

    # TTL
    result_ttl=3600,  # Results expire after 1 hour

    # Key prefix
    key_prefix="chicory",
)
```

**Environment variables:**
```bash
CHICORY_BACKEND_REDIS_HOST=localhost
CHICORY_BACKEND_REDIS_PORT=6379
CHICORY_BACKEND_REDIS_DB=1
CHICORY_BACKEND_REDIS_PASSWORD=secret
CHICORY_BACKEND_REDIS_RESULT_TTL=3600
CHICORY_BACKEND_REDIS_KEY_PREFIX=chicory
```

### PostgreSQL Backend

```python
from chicory.config import PostgresBackendConfig
from pydantic import SecretStr

config = PostgresBackendConfig(
    # Connection
    host="localhost",
    port=5432,
    database="chicory",
    username="chicory",
    password=SecretStr("secret"),
    url=None,  # Overrides above if set

    # Connection pool
    echo=False,  # SQL logging
    pool_size=5,
    max_overflow=5,
    pool_recycle=1800,
    pool_timeout=30,
)
```

**Environment variables:**
```bash
CHICORY_BACKEND_POSTGRES_HOST=localhost
CHICORY_BACKEND_POSTGRES_PORT=5432
CHICORY_BACKEND_POSTGRES_DATABASE=chicory
CHICORY_BACKEND_POSTGRES_USERNAME=chicory
CHICORY_BACKEND_POSTGRES_PASSWORD=secret
CHICORY_BACKEND_POSTGRES_ECHO=false
CHICORY_BACKEND_POSTGRES_POOL_SIZE=5
CHICORY_BACKEND_POSTGRES_MAX_OVERFLOW=5
CHICORY_BACKEND_POSTGRES_POOL_RECYCLE=1800
CHICORY_BACKEND_POSTGRES_POOL_TIMEOUT=30
```

### Other Backends

!!! warning "Experimental"
    MySQL, SQLite, and MSSQL backends are **experimental and not tested**. They may work but are not guaranteed to be stable.

MySQL, SQLite, and MSSQL backends have similar configuration options to PostgreSQL.

## Worker Configuration

```python
from chicory.config import WorkerConfig

config = WorkerConfig(
    concurrency=32,  # Concurrent tasks
    queue="default",
    use_dead_letter_queue=False,
    heartbeat_interval=10.0,
    heartbeat_ttl=30,
    cleanup_interval=900.0,
    stale_workers_timeout=300.0,
    shutdown_timeout=30.0,
    log_level="INFO",  # DEBUG, INFO, WARNING, ERROR, CRITICAL
)
```

**Environment variables:**
```bash
CHICORY_WORKER_CONCURRENCY=32
CHICORY_WORKER_QUEUE=default
CHICORY_WORKER_USE_DEAD_LETTER_QUEUE=false
CHICORY_WORKER_HEARTBEAT_INTERVAL=10.0
CHICORY_WORKER_HEARTBEAT_TTL=30
CHICORY_WORKER_CLEANUP_INTERVAL=900.0
CHICORY_WORKER_STALE_WORKERS_TIMEOUT=300.0
CHICORY_WORKER_SHUTDOWN_TIMEOUT=30.0
CHICORY_WORKER_LOG_LEVEL=INFO
```

## Environment-Specific Configuration

### Development

```bash
# .env.development
CHICORY_BROKER_REDIS_HOST=localhost
CHICORY_BACKEND_REDIS_HOST=localhost
CHICORY_WORKER_CONCURRENCY=4
CHICORY_WORKER_LOG_LEVEL=DEBUG
CHICORY_BACKEND_POSTGRES_ECHO=true
```

### Production

```bash
# .env.production
CHICORY_BROKER_REDIS_HOST=redis.prod.example.com
CHICORY_BROKER_REDIS_PASSWORD=${REDIS_PASSWORD}
CHICORY_BACKEND_POSTGRES_HOST=postgres.prod.example.com
CHICORY_BACKEND_POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
CHICORY_WORKER_CONCURRENCY=32
CHICORY_WORKER_LOG_LEVEL=WARNING
CHICORY_WORKER_USE_DEAD_LETTER_QUEUE=true
```

### Docker

```yaml
# docker-compose.yml
services:
  worker:
    image: myapp:latest
    environment:
      CHICORY_BROKER_REDIS_HOST: redis
      CHICORY_BACKEND_POSTGRES_HOST: postgres
      CHICORY_WORKER_CONCURRENCY: 32
    env_file:
      - .env.production
```

## Best Practices

### 1. Use Environment Variables in Production

```bash
# Never hardcode secrets
export CHICORY_BROKER_REDIS_PASSWORD=${REDIS_PASSWORD}
export CHICORY_BACKEND_POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
```

### 2. Separate Broker and Backend

```bash
# Different Redis databases
CHICORY_BROKER_REDIS_DB=0
CHICORY_BACKEND_REDIS_DB=1

# Or different instances
CHICORY_BROKER_REDIS_HOST=broker-redis.example.com
CHICORY_BACKEND_REDIS_HOST=backend-redis.example.com
```

### 3. Set Appropriate Timeouts

```bash
# Worker shutdown
CHICORY_WORKER_SHUTDOWN_TIMEOUT=60.0  # Allow long tasks to finish

# Database pool
CHICORY_BACKEND_POSTGRES_POOL_TIMEOUT=30
```

### 4. Enable DLQ in Production

```bash
CHICORY_WORKER_USE_DEAD_LETTER_QUEUE=true
```

### 5. Monitor Resource Usage

```bash
# Conservative concurrency
CHICORY_WORKER_CONCURRENCY=16

# Increase based on monitoring
# Watch CPU, memory, database connections
```

## Complete Example

```python
# config.py
from chicory import ChicoryConfig
from chicory.config import (
    BrokerConfig,
    BackendConfig,
    WorkerConfig,
    RedisBrokerConfig,
    PostgresBackendConfig,
)
from chicory.types import ValidationMode, DeliveryMode
from pydantic import SecretStr
import os

def get_config() -> ChicoryConfig:
    env = os.getenv("ENV", "development")

    if env == "production":
        return ChicoryConfig(
            validation_mode=ValidationMode.STRICT,
            delivery_mode=DeliveryMode.AT_LEAST_ONCE,
            broker=BrokerConfig(
                redis=RedisBrokerConfig(
                    host="redis.prod.example.com",
                    password=SecretStr(os.getenv("REDIS_PASSWORD")),
                    max_stream_length=100000,
                )
            ),
            backend=BackendConfig(
                postgres=PostgresBackendConfig(
                    host="postgres.prod.example.com",
                    database="chicory",
                    username="chicory",
                    password=SecretStr(os.getenv("POSTGRES_PASSWORD")),
                    pool_size=20,
                    max_overflow=10,
                )
            ),
            worker=WorkerConfig(
                concurrency=32,
                use_dead_letter_queue=True,
                log_level="WARNING",
            ),
        )
    else:
        return ChicoryConfig(
            validation_mode=ValidationMode.INPUTS,
            delivery_mode=DeliveryMode.AT_MOST_ONCE,
            broker=BrokerConfig(
                redis=RedisBrokerConfig(host="localhost", db=0)
            ),
            backend=BackendConfig(
                redis=RedisBackendConfig(host="localhost", db=1, result_ttl=3600)
            ),
            worker=WorkerConfig(
                concurrency=4,
                log_level="DEBUG",
            ),
        )

# tasks.py
from chicory import Chicory, BrokerType, BackendType
from config import get_config

app = Chicory(
    broker=BrokerType.REDIS,
    backend=BackendType.POSTGRES if os.getenv("ENV") == "production" else BackendType.REDIS,
    config=get_config(),
)
```

## Next Steps

- Configure [Retry Policies](../tutorial/retry-policies.md) for error handling
- Review broker guides: [Redis](brokers/redis.md) or [RabbitMQ](brokers/rabbitmq.md)
- Review backend guides: [Redis](backends/redis.md) or [PostgreSQL](backends/postgres.md)
