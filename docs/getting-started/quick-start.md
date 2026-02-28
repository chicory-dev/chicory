# Quick Start

Get Chicory up and running in under 5 minutes!

## Prerequisites

- Python 3.11 or higher
- Redis server (we'll use Docker)

## Step 1: Install Chicory

```bash
pip install chicory[redis,cli]
```

This installs Chicory with Redis support and the CLI tools.

## Step 2: Start Redis

Using Docker (easiest):

```bash
docker run -d -p 6379:6379 redis:latest
```

!!! tip
    Already have Redis? Skip this step and make sure it's running on `localhost:6379`

## Step 3: Create Your Tasks

Create a file called `tasks.py`:

```python title="tasks.py"
import asyncio
from chicory import Chicory, BrokerType, BackendType

# Initialize Chicory
app = Chicory(
    broker=BrokerType.REDIS,
    backend=BackendType.REDIS,
)

@app.task()
async def add(x: int, y: int) -> int:
    """Add two numbers."""
    await asyncio.sleep(1)  # Simulate work
    return x + y

@app.task()
async def greet(name: str) -> str:
    """Generate a greeting."""
    return f"Hello, {name}!"
```

## Step 4: Start a Worker

Open a new terminal and run:

```bash
chicory worker tasks:app
```

## Step 5: Dispatch Tasks

Create another file called `client.py`:

```python title="client.py"
import asyncio
from tasks import app, add, greet

async def main():
    # Connect to broker and backend
    await app.connect()

    try:
        # Dispatch a task
        print("Dispatching add(10, 32)...")
        result = await add.delay(10, 32)

        # Wait for the result
        print(f"Task ID: {result.task_id}")
        answer = await result.get(timeout=10.0)
        print(f"Result: {answer}")

        # Dispatch another task
        print("\nDispatching greet('World')...")
        result = await greet.delay("World")
        greeting = await result.get(timeout=10.0)
        print(f"Result: {greeting}")

    finally:
        await app.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:

```bash
python client.py
```

## What Just Happened?

1. **Created Tasks**: Defined async functions with `@app.task()`
2. **Started Worker**: Worker connected to Redis and waits for tasks
3. **Dispatched Tasks**: Used `.delay()` to send tasks to the queue
4. **Got Results**: Used `.get()` to wait for and retrieve results

## Next Steps

Congratulations! You now have a working distributed task queue.

### Learn More

- **[Tutorial](../tutorial/basic-usage.md)** - Understand core concepts
- **[Tutorial](../tutorial/index.md)** - In-depth guide with examples
- **[User Guide](../user-guide/index.md)** - Complete documentation

### Try More Features

Add retry policies:

```python
from chicory import RetryPolicy, RetryBackoff

@app.task(
    retry_policy=RetryPolicy(
        max_retries=3,
        backoff=RetryBackoff.EXPONENTIAL,
    )
)
async def flaky_task() -> str:
    # Will retry up to 3 times if it fails
    ...
```

Add input validation:

```python
from pydantic import BaseModel, EmailStr

class EmailData(BaseModel):
    to: EmailStr
    subject: str
    body: str

@app.task()
async def send_email(data: EmailData) -> dict:
    # Input is automatically validated
    ...
```

Use task context:

```python
from chicory import TaskContext

@app.task()
async def advanced_task(context: TaskContext, value: int) -> int:
    # Access task metadata
    print(f"Task ID: {context.task_id}")
    print(f"Attempt: {context.retries + 1}")
    return value * 2
```

---

That's it! You're now ready to build distributed applications with Chicory.
