# Retry Policies

Distributed systems are inherently unreliable - network failures, temporary service outages, and transient errors are inevitable. Chicory's powerful retry mechanisms help you build resilient task queues that automatically recover from failures.

## Overview

Retry policies define how Chicory should handle task failures. Instead of immediately failing when an error occurs, tasks can be automatically retried with configurable delays and backoff strategies.

## Basic Retry Configuration

Define a retry policy using the `RetryPolicy` class:

```python
from chicory import RetryPolicy, RetryBackoff

@app.task(
    name="tasks.flaky_api_call",
    retry_policy=RetryPolicy(
        max_retries=5,              # Retry up to 5 times
        retry_delay=1.0,            # Initial delay: 1 second
        backoff=RetryBackoff.EXPONENTIAL,  # Exponential backoff
        max_delay=30.0,             # Cap delay at 30 seconds
        jitter=True,                # Add random jitter
    ),
)
async def flaky_api_call(url: str) -> dict[str, Any]:
    """Call an API that might fail temporarily."""
    response = await http_client.get(url)
    return response.json()
```

**Retry Policy Parameters:**

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `max_retries` | int | Maximum number of retry attempts | 3 |
| `retry_delay` | float | Initial delay in seconds | 1.0 |
| `backoff` | RetryBackoff | Backoff strategy (FIXED, LINEAR, EXPONENTIAL) | EXPONENTIAL |
| `max_delay` | float | Maximum delay between retries | 300.0 |
| `jitter` | bool | Add randomness to prevent thundering herd | False |
| `retry_on` | list[str] | Only retry these exception types | None (retry all) |
| `ignore_on` | list[str] | Never retry these exception types | None |

## Backoff Strategies

Chicory supports three backoff strategies for controlling retry timing:

### Exponential Backoff (Recommended)

Doubles the delay with each retry. Best for external APIs, database connections, and network errors.

```python
@app.task(
    name="tasks.api_with_exponential_backoff",
    retry_policy=RetryPolicy(
        max_retries=5,
        retry_delay=1.0,
        backoff=RetryBackoff.EXPONENTIAL,
        jitter=True,  # Prevents "thundering herd" when many tasks retry simultaneously
    ),
)
async def call_external_api(url: str) -> dict:
    # Retry schedule: ~1s, ~2s, ~4s, ~8s, ~16s
    response = await fetch(url)
    return response
```

### Fixed Backoff

Uses the same delay for every retry. Good for quick retries on transient errors.

```python
@app.task(
    name="tasks.fixed_backoff_task",
    retry_policy=RetryPolicy(
        max_retries=3,
        retry_delay=2.0,
        backoff=RetryBackoff.FIXED,
    ),
)
async def process_with_fixed_delay(task_id: str) -> dict:
    # Retry schedule: 2s, 2s, 2s
    return await process(task_id)
```

### Linear Backoff

Increases the delay by a constant amount. A middle ground between exponential and fixed.

```python
@app.task(
    name="tasks.linear_backoff_task",
    retry_policy=RetryPolicy(
        max_retries=4,
        retry_delay=2.0,
        backoff=RetryBackoff.LINEAR,
    ),
)
async def process_with_linear_backoff(data: str) -> dict:
    # Retry schedule: 2s, 4s, 6s, 8s
    return await process(data)
```

## Selective Retry

Control which exceptions trigger retries and which should fail immediately:

```python
@app.task(
    name="tasks.selective_retry",
    retry_policy=RetryPolicy(
        max_retries=3,
        retry_delay=1.0,
        backoff=RetryBackoff.LINEAR,
        retry_on=["ConnectionError", "TimeoutError"],  # Only retry these
        ignore_on=["ValueError", "KeyError"],          # Never retry these
    ),
)
async def selective_retry_task(operation: str) -> dict:
    """Only retries network-related errors."""
    if operation == "connection_error":
        raise ConnectionError("Network failed")  # ✅ Will retry

    if operation == "value_error":
        raise ValueError("Invalid data")  # ❌ Won't retry, goes to DLQ

    return {"status": "success"}
```

**Example execution:**

```python
# This will retry up to 3 times
result1 = await selective_retry_task.delay("connection_error")
# Retry attempts: 1s, 2s, 3s delays

try:
    data = await result1.get(timeout=15.0)
except Exception as e:
    print(f"Failed after retries: {e}")

# This will fail immediately (no retries)
result2 = await selective_retry_task.delay("value_error")

try:
    data = await result2.get(timeout=10.0)
except Exception as e:
    print(f"Failed immediately: {e}")
    # Task moved to Dead Letter Queue
```

!!! warning "Exception Name Matching"
    The `retry_on` and `ignore_on` parameters use exception class names as strings. Make sure to use the exact exception name (e.g., "ConnectionError", not "connection_error").

## Maximum Delay Cap

Prevent exponential backoff from creating extremely long delays:

```python
@app.task(
    name="tasks.capped_backoff",
    retry_policy=RetryPolicy(
        max_retries=10,
        retry_delay=1.0,
        backoff=RetryBackoff.EXPONENTIAL,
        max_delay=60.0,  # Never wait more than 60 seconds
    ),
)
async def task_with_cap(data: str) -> dict:
    """
    Retry schedule (exponential with cap):
    - Attempt 1: Immediate
    - Attempt 2: ~1s
    - Attempt 3: ~2s
    - Attempt 4: ~4s
    - Attempt 5: ~8s
    - Attempt 6: ~16s
    - Attempt 7: ~32s
    - Attempt 8: ~60s (capped)
    - Attempt 9: ~60s (capped)
    - Attempt 10: ~60s (capped)
    """
    return await process(data)
```

!!! tip "Reasonable Caps"
    Set `max_delay` to prevent tasks from being delayed for hours. A cap of 60-300 seconds is reasonable for most use cases.

## Dead Letter Queue (DLQ)

When a task exhausts all retry attempts, it's moved to the Dead Letter Queue:

```python
@app.task(
    name="tasks.always_fails",
    retry_policy=RetryPolicy(
        max_retries=2,
        retry_delay=1.0,
    ),
)
async def always_fails_task(reason: str) -> None:
    """Task that always fails - demonstrates DLQ."""
    raise Exception(f"Task failed: {reason}")

# Usage
result = await always_fails_task.delay("Testing DLQ")

try:
    await result.get(timeout=15.0)
except Exception as e:
    print(f"Task failed after retries: {e}")
    # Task is now in the Dead Letter Queue

# Check DLQ
dlq_count = await app.broker.get_dlq_count()
print(f"DLQ has {dlq_count} messages")

dlq_messages = await app.broker.get_dlq_messages()
for msg in dlq_messages:
    print(f"Failed task: {msg['task_name']}")
```

**Start worker with DLQ enabled:**

```bash
chicory worker examples.shared_tasks:app --dlq
```

!!! note "DLQ Management"
    DLQ tasks can be:

    - Inspected for debugging
    - Manually requeued for retry
    - Deleted if truly failed
    - Monitored for alerting

## Next Steps

Now that you understand retry policies, explore:

- [**Task Context**](task-context.md) - Manual retry control with `ctx.retry()`
- [**Delivery Modes**](delivery-modes.md) - Combine retries with delivery guarantees
