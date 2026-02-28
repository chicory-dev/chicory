# Basic Usage

This guide covers the fundamental concepts of Chicory and shows you how to dispatch tasks, retrieve results, and handle common task execution patterns.

## Overview

Chicory provides a simple and intuitive API for distributing work across multiple processes or machines. At its core, you define tasks as Python functions and execute them asynchronously using the task queue system.

## Your First Task

Let's start with the simplest possible task - an addition function:

```python
from chicory import Chicory, BrokerType, BackendType

app = Chicory(
    broker=BrokerType.REDIS,
    backend=BackendType.REDIS,
)

@app.task(name="tasks.add")
async def add(x: int, y: int) -> int:
    """Add two numbers together."""
    return x + y
```

**Key Concepts:**

- The `@app.task` decorator registers your function as a task
- The `name` parameter gives your task a unique identifier
- Tasks can be either `async` functions or regular synchronous functions
- Type hints are optional but highly recommended for validation

## Connecting to Broker and Backend

Before dispatching tasks, you need to connect to your broker and backend:

```python
import asyncio

async def main():
    # Connect to broker and backend
    await app.connect()

    try:
        # Your task dispatching code here
        pass
    finally:
        # Always disconnect when done
        await app.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

!!! tip "Connection Management"
    Always use a try/finally block to ensure proper cleanup of connections, even if your code encounters an error.

## Dispatching Tasks

There are two primary ways to dispatch tasks in Chicory:

### 1. Using `.delay()` - With Result Retrieval

The `.delay()` method dispatches a task and returns an `AsyncResult` object that you can use to retrieve the result:

```python
# Dispatch the task
result = await add.delay(10, 32)

# Get the task ID
print(f"Task ID: {result.task_id}")

# Wait for and retrieve the result
answer = await result.get(timeout=10.0)
print(f"Result: {answer}")  # Output: Result: 42
```

**When to use `.delay()`:**

- You need to retrieve the task result
- You want to check the task status
- You need to wait for task completion
- You're building workflows that depend on task outputs

### 2. Using `.send()` - Fire and Forget

The `.send()` method dispatches a task without expecting to retrieve the result:

```python
# Dispatch and forget
task_id = await multiply.send(5, 8)
print(f"Task sent with ID: {task_id}")
# Continue without waiting for completion
```

**When to use `.send()`:**

- You don't need the result
- You're logging events or metrics
- Performance is critical (no result storage overhead)
- You're dispatching many non-critical tasks

!!! warning "Result Storage"
    When using `.send()`, results are still stored in the backend by default. Use `ignore_result=True` in the task decorator to prevent result storage entirely.

## Working with Results

The `AsyncResult` object provides several methods for working with task execution:

### Getting the Result

```python
result = await add.delay(100, 200)

# Wait for result with timeout
try:
    answer = await result.get(timeout=10.0)
    print(f"Result: {answer}")
except TimeoutError:
    print("Task didn't complete in time")
```

### Checking Task State

```python
result = await add.delay(100, 200)

# Check if task is ready
is_ready = await result.ready()
print(f"Is ready: {is_ready}")

# Get current state
state = await result.state()
print(f"State: {state}")  # PENDING, STARTED, SUCCESS, FAILURE, etc.

# Check if task failed
has_failed = await result.failed()
print(f"Has failed: {has_failed}")
```

**Available Task States:**

- `PENDING` - Task has been dispatched but not yet started
- `STARTED` - Task is currently executing
- `SUCCESS` - Task completed successfully
- `FAILURE` - Task failed with an error
- `RETRY` - Task is scheduled for retry
- `DEAD_LETTERED` - Task moved to Dead Letter Queue after max retries

## Concurrent Task Execution

One of Chicory's main benefits is executing multiple tasks concurrently:

```python
# Dispatch multiple tasks
tasks = [
    await add.delay(i, i * 2)
    for i in range(1, 6)
]

print(f"Dispatched {len(tasks)} tasks")
print(f"Task IDs: {[t.task_id for t in tasks]}")

# Wait for all results
results = await asyncio.gather(
    *[t.get(timeout=10.0) for t in tasks]
)

print(f"Results: {results}")
# Output: Results: [3, 6, 9, 12, 15]
```

!!! tip "Parallel Execution"
    Tasks are executed in parallel by the worker pool. The concurrency level is controlled by the worker's `--concurrency` flag (default: number of CPU cores).

## Handling Timeouts

Tasks that take a long time to execute require proper timeout handling:

```python
@app.task(name="tasks.long_running")
async def long_running_task(duration: int) -> dict[str, Any]:
    await asyncio.sleep(duration)
    return {
        "duration": duration,
        "completed_at": datetime.now(UTC).isoformat(),
    }

# Dispatch a 3-second task
result = await long_running_task.delay(3)

try:
    # Try with short timeout (will fail)
    answer = await result.get(timeout=1.0)
except TimeoutError:
    print("Timeout after 1 second (expected)")
    print("Task is still running...")

    # Wait with longer timeout
    answer = await result.get(timeout=5.0)
    print(f"Task completed: {answer}")
```

!!! note "Timeout Behavior"
    The `timeout` parameter in `.get()` controls how long to wait for the result. It does **not** cancel the task - the task continues executing in the worker.

## Complete Example

Here's a complete example putting it all together:

```python
import asyncio
from datetime import datetime, UTC
from typing import Any
from chicory import Chicory, BrokerType, BackendType

app = Chicory(
    broker=BrokerType.REDIS,
    backend=BackendType.REDIS,
)

@app.task(name="tasks.add")
async def add(x: int, y: int) -> int:
    await asyncio.sleep(0.1)  # Simulate work
    return x + y

@app.task(name="tasks.process_data")
async def process_data(data: dict[str, Any]) -> dict[str, Any]:
    await asyncio.sleep(0.5)
    return {
        "original": data,
        "processed_at": datetime.now(UTC).isoformat(),
        "item_count": len(data),
    }

async def main():
    # Connect
    await app.connect()

    try:
        # Simple task
        result = await add.delay(10, 32)
        print(f"10 + 32 = {await result.get(timeout=10.0)}")

        # Multiple concurrent tasks
        tasks = [await add.delay(i, i * 2) for i in range(1, 6)]
        results = await asyncio.gather(
            *[t.get(timeout=10.0) for t in tasks]
        )
        print(f"Batch results: {results}")

        # Complex data
        data = {"user_id": 42, "items": ["book", "pen"]}
        result = await process_data.delay(data)
        processed = await result.get(timeout=10.0)
        print(f"Processed {processed['item_count']} items")

    finally:
        await app.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

## Best Practices

!!! success "Do's"
    - Always use try/finally blocks for connection management
    - Set appropriate timeouts based on expected task duration
    - Use type hints for better validation and IDE support
    - Give tasks descriptive names for easier debugging
    - Use `.send()` for fire-and-forget tasks to improve performance

!!! failure "Don'ts"
    - Don't forget to connect before dispatching tasks
    - Don't use very short timeouts for long-running tasks
    - Don't dispatch tasks in a tight loop without throttling
    - Don't ignore connection errors

## Next Steps

Now that you understand the basics, explore these advanced topics:

- [**Validation**](validation.md) - Learn how to validate task inputs and outputs
- [**Retry Policies**](retry-policies.md) - Configure automatic retries for failed tasks
- [**Task Context**](task-context.md) - Access task metadata and control execution flow
- [**Delivery Modes**](delivery-modes.md) - Choose the right delivery guarantee for your use case
