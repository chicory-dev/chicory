# Chicory

<p align="center">
  <em>Lightweight, async-native job queue for Python</em>
</p>

[![Merge Gate - Full Tests](https://github.com/chicory-dev/chicory/actions/workflows/merge-gate.yml/badge.svg)](https://github.com/chicory-dev/chicory/actions/workflows/merge-gate.yml)

---

**Documentation**: <a href="https://chicory-dev.github.io/chicory" target="_blank">https://chicory-dev.github.io/chicory</a>

**Source Code**: <a href="https://github.com/chicory-dev/chicory" target="_blank">https://github.com/chicory-dev/chicory</a>

---

Chicory is a modern, async-first task queue for Python that makes distributed task execution simple and reliable. Built from the ground up with Python's `async`/`await` syntax, Chicory provides a clean, type-safe API for managing background jobs.

## Key Features

- **Async Native** - Built with Python's asyncio from day one
- **Type Safe** - Full type hints with automatic input/output validation via Pydantic
- **Multiple Brokers** - Support for Redis and RabbitMQ message brokers
- **Multiple Backends** - Store results in Redis, PostgreSQL, MySQL, SQLite, or MS SQL Server
- **Flexible Delivery** - Choose between at-least-once and at-most-once delivery guarantees
- **Smart Retries** - Built-in retry policies with exponential backoff
- **Simple CLI** - Easy worker management with the included CLI tool
- **Production Ready** - Designed for reliability and performance at scale

## Requirements

Python 3.11+

Chicory is built on these excellent libraries:

* <a href="https://docs.pydantic.dev" target="_blank">Pydantic</a> for data validation
* <a href="https://typer.tiangolo.com" target="_blank">Typer</a> for CLI (optional)

## Installation

=== "Basic Installation"

    ```console
    $ pip install chicory
    ```

=== "With Redis"

    ```console
    $ pip install chicory[redis]
    ```

=== "With RabbitMQ"

    ```console
    $ pip install chicory[rabbitmq]
    ```

=== "With PostgreSQL"

    ```console
    $ pip install chicory[postgres]
    ```

=== "With CLI"

    ```console
    $ pip install chicory[cli]
    ```

=== "Everything"

    ```console
    $ pip install chicory[all]
    ```

## Quick Start

### 1. Define Your Tasks

Create a file `tasks.py`:

```python
from chicory import Chicory, BrokerType, BackendType

# Initialize Chicory with Redis broker and backend
app = Chicory(
    broker=BrokerType.REDIS,
    backend=BackendType.REDIS,
)

@app.task()
async def send_email(to: str, subject: str, body: str) -> dict:
    """Send an email asynchronously."""
    # Your email sending logic here
    await asyncio.sleep(1)  # Simulate work
    return {
        "status": "sent",
        "to": to,
        "subject": subject,
    }

@app.task()
async def process_data(data: dict) -> dict:
    """Process some data."""
    # Your data processing logic
    result = {
        "processed": True,
        "items": len(data.get("items", [])),
    }
    return result
```

### 2. Start a Worker

Run workers to process tasks:

```console
$ chicory worker tasks:app
```

Or programmatically:

```python
from chicory import Worker

async def main():
    worker = Worker(app)
    await worker.start()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### 3. Dispatch Tasks

From your application code:

```python
import asyncio
from tasks import app, send_email, process_data

async def main():
    # Connect to broker and backend
    await app.connect()

    try:
        # Dispatch a task and wait for result
        result = await send_email.delay(
            to="user@example.com",
            subject="Welcome!",
            body="Thanks for signing up!",
        )

        # Get the result (waits until task completes)
        email_result = await result.get(timeout=30.0)
        print(f"Email sent: {email_result}")

        # Fire-and-forget (don't wait for result)
        task_id = await process_data.send({"items": [1, 2, 3]})
        print(f"Task dispatched: {task_id}")

    finally:
        await app.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

That's it! You now have a fully functional distributed task queue.

## Why Chicory?

### Designed for Modern Python

Chicory embraces Python's async capabilities from the start. No callbacks, no threading complexity—just clean async code:

```python
@app.task()
async def fetch_user_data(user_id: int) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.example.com/users/{user_id}")
        return response.json()

# Dispatch and await
result = await fetch_user_data.delay(123)
data = await result.get()
```

### Type-Safe by Default

Automatic validation of inputs and outputs using Pydantic:

```python
from pydantic import BaseModel, EmailStr

class EmailData(BaseModel):
    to: EmailStr
    subject: str
    body: str

@app.task()
async def send_email(data: EmailData) -> dict:
    # data is automatically validated
    # Invalid input raises ValidationError before task is queued
    ...

# This validates the input immediately
await send_email.delay(EmailData(
    to="user@example.com",
    subject="Hello",
    body="World"
))
```

### Flexible and Scalable

Choose the right tools for your needs:

- **Brokers**: Redis or RabbitMQ
- **Backends**: Redis, PostgreSQL, MySQL, SQLite, MS SQL Server
- **Delivery Modes**: At-least-once or at-most-once
- **Validation Modes**: Strict, inputs-only, outputs-only, or disabled

Scale from a single process to hundreds of workers across multiple machines.

### Production-Ready Features

Built-in support for:

- **Automatic retries** with exponential backoff
- **Task context** for accessing task metadata
- **Worker lifecycle hooks** for setup/teardown
- **Dead-letter queues** for failed tasks
- **Task timeouts** and cancellation
- **Graceful shutdown** with configurable drain periods

## Comparison with Celery

| Feature | Chicory | Celery |
|---------|---------|--------|
| Async/Await | Native support | No support |
| Type Hints | Full support with validation | Limited |
| Python Version | 3.11+ | 3.8+ |
| Performance | Optimized for async | Thread/process based |

Chicory is not a drop-in replacement for Celery, but if you're starting a new async Python project, Chicory provides a more modern and Pythonic experience.

## Documentation

For detailed documentation, visit <a href="https://chicory-dev.github.io/chicory" target="_blank">https://chicory-dev.github.io/chicory</a>

- **Tutorial**: Step-by-step guides for common use cases
- **User Guide**: In-depth documentation of all features
- **API Reference**: Complete API documentation

## Contributing

Contributions are welcome!

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Credits

Chicory is built and maintained by:

- Davide Di Mauro ([@dadodimauro](https://github.com/dadodimauro))
- Andrea Vouk ([@andreavou](https://github.com/anvouk))

Inspired by the excellent work of the Celery and FastAPI projects.
