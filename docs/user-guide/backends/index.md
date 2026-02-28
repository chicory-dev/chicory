# Result Backends

Result backends store task results and worker metadata. They're essential for retrieving task outcomes and monitoring worker health.

## Overview

Chicory supports multiple backend options:

- **Redis** - Fast, in-memory result storage
- **PostgreSQL** - Persistent, queryable storage
- **MySQL** - Alternative relational database
- **SQLite** - Lightweight, file-based storage
- **MS SQL Server** - Enterprise database support

## Choosing a Backend

### Redis Backend

**Best for:**
- Fast result retrieval
- Temporary results
- High read/write throughput
- Simple setup

**Pros:**
- Extremely fast (in-memory)
- Simple configuration
- Automatic TTL expiration
- Low latency

**Cons:**
- Results lost on restart (unless persistence enabled)
- Limited query capabilities
- Memory-based storage

[:octicons-arrow-right-24: Redis Backend Guide](redis.md)

### PostgreSQL Backend

**Best for:**
- Permanent result storage
- Complex queries
- Compliance requirements
- Long-term analytics

**Pros:**
- Persistent storage
- Rich querying with SQL
- Transactional guarantees
- JSON support for task data

**Cons:**
- Higher latency than Redis
- More complex setup
- Higher resource usage

[:octicons-arrow-right-24: PostgreSQL Backend Guide](postgres.md)

### Other Database Backends

!!! warning "Experimental"
    MySQL, SQLite, and MS SQL Server backends are **experimental and not tested**. They may work but are not guaranteed to be stable. Use at your own risk and please report any issues you encounter.

MySQL, SQLite, and MS SQL Server backends work similarly to PostgreSQL:

- **MySQL**: Alternative to PostgreSQL
- **SQLite**: Single-file database, great for development
- **MS SQL Server**: Enterprise environments


## Basic Usage

### Initialization

```python
from chicory import Chicory, BrokerType, BackendType

# Redis backend
app = Chicory(
    broker=BrokerType.REDIS,
    backend=BackendType.REDIS,
)

# PostgreSQL backend
app = Chicory(
    broker=BrokerType.REDIS,
    backend=BackendType.POSTGRES,
)

# No backend (fire-and-forget only)
app = Chicory(broker=BrokerType.REDIS)
```

### Configuration

Via environment variables:

```bash
# Redis
export CHICORY_BACKEND_REDIS_HOST=localhost
export CHICORY_BACKEND_REDIS_PORT=6379
export CHICORY_BACKEND_REDIS_DB=1

# PostgreSQL
export CHICORY_BACKEND_POSTGRES_HOST=localhost
export CHICORY_BACKEND_POSTGRES_PORT=5432
export CHICORY_BACKEND_POSTGRES_DATABASE=chicory
export CHICORY_BACKEND_POSTGRES_USERNAME=chicory
export CHICORY_BACKEND_POSTGRES_PASSWORD=secret
```

## Result TTL

### Redis (Native TTL)

```python
from chicory.config import RedisBackendConfig

config = RedisBackendConfig(
    result_ttl=3600,  # Results expire after 1 hour
)
```

### Database (Manual Cleanup)

```python
# PostgreSQL/MySQL/SQLite/MSSQL require manual cleanup
from chicory.backend import DatabaseBackend

backend = DatabaseBackend(config)
await backend.connect()

# Clean up results older than 24 hours
deleted = await backend.cleanup_old_results(older_than_seconds=86400)
```

**Recommended:** Run cleanup as a cron job:
```bash
# Cron: Daily at 2 AM
0 2 * * * python -c "import asyncio; from myapp import backend; asyncio.run(backend.cleanup_old_results(86400))"
```

## Without a Backend

You can use Chicory without a backend for fire-and-forget tasks:

```python
app = Chicory(broker=BrokerType.REDIS)  # No backend

@app.task()
async def log_event(message: str):
    await logger.info(message)

# Use send() for fire-and-forget
task_id = await log_event.send("Event occurred")

# delay() and AsyncResult won't work without backend
# result = await log_event.delay("test")  # Raises BackendNotConfiguredError
```

## Mixed Setup

Different brokers and backends can be combined:

```python
# Redis broker + PostgreSQL backend
app = Chicory(
    broker=BrokerType.REDIS,
    backend=BackendType.POSTGRES,
)

# RabbitMQ broker + Redis backend
app = Chicory(
    broker=BrokerType.RABBITMQ,
    backend=BackendType.REDIS,
)
```


## Next Steps

Choose your backend and dive into detailed configuration:

<div class="grid cards" markdown>

-   :simple-redis:{ .lg .middle } **Redis Backend**

    ---

    Fast, in-memory result storage with automatic TTL.

    [:octicons-arrow-right-24: Redis Guide](redis.md)

-   :simple-postgresql:{ .lg .middle } **PostgreSQL Backend**

    ---

    Persistent storage with full SQL query capabilities.

    [:octicons-arrow-right-24: PostgreSQL Guide](postgres.md)

</div>
