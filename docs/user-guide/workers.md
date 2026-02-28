# Workers

Workers are the processes that consume tasks from the message broker and execute them. Chicory provides flexible worker management with both CLI and programmatic options.

## Starting Workers

### CLI Worker

The simplest way to run workers is using the CLI:

```bash
chicory worker tasks:app
```

This starts a single worker process that:
- Imports your Chicory app from `tasks.py`
- Connects to the configured broker and backend
- Begins consuming and executing tasks
- Handles signals for graceful shutdown

#### CLI Options

```bash
chicory worker tasks:app \
    --workers 4 \              # Number of worker processes
    --concurrency 16 \         # Tasks per worker process
    --queue default \          # Queue to consume from
    --dlq \                    # Enable dead-letter queue
    --heartbeat-interval 10.0 \  # Heartbeat frequency (seconds)
    --heartbeat-ttl 30 \       # Heartbeat expiration (seconds)
    --log-level INFO \         # Logging level
    --shutdown-timeout 30.0    # Graceful shutdown timeout
```

!!! example "Production Worker Command"
    ```bash
    chicory worker myapp.tasks:app \
        --workers 4 \
        --concurrency 32 \
        --queue high-priority \
        --dlq \
        --log-level WARNING
    ```

### Programmatic Worker

For more control, create workers programmatically:

```python
import asyncio
from chicory import Worker

async def main():
    # Create worker instance
    worker = Worker(app)

    # Start worker (blocking)
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
```

#### Custom Configuration

```python
from chicory.config import WorkerConfig

# Create custom configuration
worker_config = WorkerConfig(
    concurrency=16,
    queue="default",
    use_dead_letter_queue=True,
    heartbeat_interval=10.0,
    heartbeat_ttl=30,
    shutdown_timeout=30.0,
    log_level="INFO",
)

# Create worker with config
worker = Worker(app, config=worker_config)
await worker.run()
```

#### Non-Blocking Worker

Run worker in the background:

```python
async def main():
    worker = Worker(app)

    # Start worker (non-blocking)
    await worker.start()

    # Worker runs in background
    # Do other work...
    await asyncio.sleep(60)

    # Stop worker gracefully
    await worker.stop(timeout=30.0)
```

## Worker Lifecycle

### Startup Sequence

1. **Initialization**
   - Generate unique worker ID
   - Create connection pools
   - Initialize semaphore for concurrency control

2. **Connection**
   - Connect to message broker
   - Connect to result backend (if configured)
   - Declare queues and consumer groups

3. **Consumption**
   - Start heartbeat loop (if backend configured)
   - Start cleanup loop for stale workers
   - Begin consuming messages from queue

```python
@app.task()
async def my_task():
    # This executes on a worker
    return "result"
```

### Graceful Shutdown

Workers handle shutdown signals (`SIGTERM`, `SIGINT`) gracefully:

1. **Stop Accepting New Tasks**
   - Worker stops consuming from queue
   - Existing tasks continue executing

2. **Drain Active Tasks**
   - Wait for in-flight tasks to complete
   - Respect shutdown timeout

3. **Cleanup**
   - Send final heartbeat (status: stopped)
   - Close broker and backend connections
   - Shutdown thread pool

```python
# Shutdown with custom timeout
await worker.stop(timeout=60.0)
```

!!! tip "Shutdown Timeout"
    Set a generous shutdown timeout in production to allow long-running tasks to complete. Tasks that don't finish within the timeout are forcefully cancelled.

## Concurrency

### Concurrency Levels

Chicory uses asyncio for concurrency with a semaphore to limit parallel execution:

```python
worker_config = WorkerConfig(
    concurrency=32,  # Maximum 32 tasks executing simultaneously
)
```

**How it works:**
- Worker maintains a semaphore with `concurrency` permits
- Each task acquires a permit before execution
- Permits are released when tasks complete
- Tasks wait if all permits are in use

### Choosing Concurrency

```python
import os

# Auto-detect based on CPU cores
default_concurrency = min(32, (os.cpu_count() or 1) + 4)

# For I/O-bound tasks (API calls, database queries)
concurrency = 64  # Higher concurrency

# For CPU-bound tasks (image processing, data transformation)
concurrency = os.cpu_count()  # Match CPU cores
```

!!! warning "Database Connections"
    Ensure your database connection pool can handle `workers * concurrency` connections. For example, 4 workers with concurrency 32 requires 128 database connections.

### Async vs Sync Tasks

Chicory handles both async and sync tasks efficiently:

```python
# Async task: Runs on event loop
@app.task()
async def fetch_data(url: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()

# Sync task: Runs in thread pool
@app.task()
def process_image(path: str):
    img = Image.open(path)
    img.resize((800, 600))
    img.save(f"{path}_resized.jpg")
```

Sync tasks execute in a thread pool to avoid blocking the event loop.

## Multiple Workers

### Process-Based Scaling

Run multiple worker processes for better CPU utilization:

```bash
# CLI: 4 worker processes, each with 16 concurrent tasks
chicory worker tasks:app --workers 4 --concurrency 16
```

Each worker process:
- Has its own event loop
- Manages its own connection pools
- Competes for tasks from the shared queue
- Runs independently (crash isolation)

### Container Scaling

Scale horizontally by running workers in multiple containers:

```yaml
# docker-compose.yml
services:
  worker:
    image: myapp:latest
    command: chicory worker myapp.tasks:app --concurrency 32
    deploy:
      replicas: 4  # 4 worker containers
    environment:
      CHICORY_BROKER_REDIS_HOST: redis
      CHICORY_BACKEND_REDIS_HOST: redis
```

```bash
# Scale up
docker-compose up --scale worker=8

# Kubernetes
kubectl scale deployment chicory-worker --replicas=10
```

### Queue-Based Routing

Route tasks to specific workers using multiple queues:

```python
# Define queue-specific tasks
@app.task()
async def high_priority_task():
    pass  # Dispatch to "high-priority" queue

@app.task()
async def low_priority_task():
    pass  # Dispatch to "low-priority" queue

# Dispatch to specific queue
await app.broker.publish(message, queue="high-priority")
```

```bash
# Start workers for different queues
chicory worker tasks:app --queue high-priority --concurrency 32
chicory worker tasks:app --queue low-priority --concurrency 8
```

## Worker Configuration

### Environment Variables

Configure workers via environment variables:

```bash
# Worker settings
export CHICORY_WORKER_CONCURRENCY=32
export CHICORY_WORKER_QUEUE=default
export CHICORY_WORKER_USE_DEAD_LETTER_QUEUE=true
export CHICORY_WORKER_HEARTBEAT_INTERVAL=10.0
export CHICORY_WORKER_HEARTBEAT_TTL=30
export CHICORY_WORKER_SHUTDOWN_TIMEOUT=30.0
export CHICORY_WORKER_LOG_LEVEL=INFO

# Broker settings
export CHICORY_BROKER_REDIS_HOST=redis.example.com
export CHICORY_BROKER_REDIS_PORT=6379

# Backend settings
export CHICORY_BACKEND_REDIS_HOST=redis.example.com
```

### Configuration File

Use a `.env` file for local development:

```bash
# .env
CHICORY_WORKER_CONCURRENCY=16
CHICORY_WORKER_QUEUE=default
CHICORY_BROKER_REDIS_HOST=localhost
CHICORY_BACKEND_REDIS_HOST=localhost
```

Chicory automatically loads `.env` files using `pydantic-settings`.

### Programmatic Configuration

```python
from chicory import ChicoryConfig
from chicory.config import WorkerConfig, RedisBrokerConfig, RedisBackendConfig

config = ChicoryConfig(
    broker=BrokerConfig(
        redis=RedisBrokerConfig(
            host="redis.example.com",
            port=6379,
            db=0,
        )
    ),
    backend=BackendConfig(
        redis=RedisBackendConfig(
            host="redis.example.com",
            port=6379,
            db=1,
        )
    ),
    worker=WorkerConfig(
        concurrency=32,
        queue="default",
        use_dead_letter_queue=True,
    ),
)

app = Chicory(broker=BrokerType.REDIS, backend=BackendType.REDIS, config=config)
```

## Worker Monitoring

### Heartbeats

Workers send periodic heartbeats to the backend:

```python
worker_config = WorkerConfig(
    heartbeat_interval=10.0,  # Send heartbeat every 10 seconds
    heartbeat_ttl=30,  # Heartbeat expires after 30 seconds
)
```

Heartbeats include:
- Worker ID and hostname
- Process ID
- Tasks processed/failed counts
- Active task count
- Uptime

### Listing Active Workers

```bash
# CLI command
chicory workers tasks:app
```

```python
# Programmatic
async def list_workers():
    await app.connect()
    workers = await app.backend.get_active_workers()

    for worker in workers:
        print(f"Worker: {worker.worker_id}")
        print(f"  Hostname: {worker.hostname}")
        print(f"  PID: {worker.pid}")
        print(f"  Tasks Processed: {worker.tasks_processed}")
        print(f"  Active Tasks: {worker.active_tasks}")
```

### Worker Statistics

Get detailed stats from a running worker:

```python
worker = Worker(app)
await worker.start()

# Get current stats
stats = worker.get_stats()
print(f"Processed: {stats.tasks_processed}")
print(f"Failed: {stats.tasks_failed}")
print(f"Active: {stats.active_tasks}")
print(f"Uptime: {stats.uptime_seconds}s")

# Healthcheck (includes broker/backend status)
health = await worker.healthcheck()
print(f"Broker connected: {health.broker.connected}")
print(f"Backend connected: {health.backend.connected}")
```

### Cleanup Stale Workers

Remove workers that haven't sent heartbeats:

```bash
# CLI: Remove workers idle for 60+ seconds
chicory cleanup tasks:app --stale-seconds 60
```

```python
# Programmatic cleanup
removed_backends = await app.backend.cleanup_stale_clients(stale_seconds=60.0)
removed_brokers = await app.broker.cleanup_stale_clients(queue="default", stale_seconds=60.0)
print(f"Removed {removed_backends} stale backends, {removed_brokers} stale brokers")
```

## Next Steps

- Configure [Retry Policies](../tutorial/retry-policies.md) for error handling and DLQ
- Review [Configuration](configuration.md) for advanced settings
- Explore [Brokers](brokers/index.md) and [Backends](backends/index.md) for infrastructure options
