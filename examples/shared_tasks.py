"""
Shared Task Definitions for Chicory Examples
==============================================

This module contains all task definitions used across the example scripts.
All tasks are registered with the app instance in this file.

Run a worker that imports these tasks:
    chicory worker examples.shared_tasks:app
"""

import asyncio
import logging
import random
from datetime import UTC, datetime
from typing import Any

from chicory import (
    BackendType,
    BrokerType,
    Chicory,
    DeliveryMode,
    RetryBackoff,
    RetryPolicy,
    TaskContext,
    ValidationMode,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = Chicory(
    broker=BrokerType.REDIS,
    backend=BackendType.REDIS,
    validation_mode=ValidationMode.INPUTS,
)


@app.task(name="tasks.add")
async def add(x: int, y: int) -> int:
    """
    Simple addition task.

    Demonstrates: Basic async task execution with type hints.
    """
    logger.info(f"Computing {x} + {y}")
    await asyncio.sleep(0.1)  # Simulate some work
    return x + y


@app.task(name="tasks.multiply")
async def multiply(x: int, y: int) -> int:
    """
    Simple multiplication task.

    Demonstrates: Basic math operation.
    """
    logger.info(f"Computing {x} * {y}")
    return x * y


@app.task(name="tasks.greet")
async def greet(name: str) -> str:
    """
    Greet someone by name.

    Demonstrates: String operations.
    """
    greeting = f"Hello, {name}!"
    logger.info(greeting)
    return greeting


@app.task(name="tasks.process_data")
async def process_data(data: dict[str, Any]) -> dict[str, Any]:
    """
    Process a dictionary of data.

    Demonstrates: Complex data type handling.
    """
    logger.info(f"Processing data: {data}")
    await asyncio.sleep(0.5)  # Simulate processing time

    return {
        "original": data,
        "processed_at": datetime.now(UTC).isoformat(),
        "item_count": len(data),
    }


@app.task(name="tasks.long_running")
async def long_running_task(duration: int) -> dict[str, Any]:
    """
    Simulate a long-running task.

    Demonstrates: Tasks that take significant time to complete.
    """
    logger.info(f"Starting long task ({duration} seconds)")
    await asyncio.sleep(duration)
    logger.info(f"Completed long task ({duration} seconds)")

    return {
        "duration": duration,
        "completed_at": datetime.now(UTC).isoformat(),
    }


@app.task(
    name="tasks.validate_email",
    validation_mode=ValidationMode.STRICT,
)
async def validate_email(email: str, user_id: int) -> dict[str, Any]:
    """
    Validate an email address.

    Demonstrates: Strict input validation.
    """
    logger.info(f"Validating email for user {user_id}: {email}")

    # Simple validation
    is_valid = "@" in email and "." in email.split("@")[1]

    return {
        "email": email,
        "user_id": user_id,
        "is_valid": is_valid,
        "validated_at": datetime.now(UTC).isoformat(),
    }


@app.task(
    name="tasks.process_order",
    validation_mode=ValidationMode.INPUTS,
)
async def process_order(
    order_id: str,
    items: list[str],
    total: float,
    customer_email: str | None = None,
) -> dict[str, Any]:
    """
    Process an order.

    Demonstrates: Input validation with optional parameters.
    """
    logger.info(f"Processing order {order_id}")

    return {
        "order_id": order_id,
        "item_count": len(items),
        "total": total,
        "customer_email": customer_email,
        "status": "processed",
        "processed_at": datetime.now(UTC).isoformat(),
    }


@app.task(
    name="tasks.flaky_api_call",
    retry_policy=RetryPolicy(
        max_retries=5,
        retry_delay=1.0,
        backoff=RetryBackoff.EXPONENTIAL,
        max_delay=30.0,
        jitter=True,
    ),
)
async def flaky_api_call(url: str, fail_rate: float = 0.7) -> dict[str, Any]:
    """
    Simulate a flaky API call that might fail.

    Demonstrates: Automatic retry with exponential backoff.
    """
    logger.info(f"Calling API: {url}")

    # Simulate random failures
    if random.random() < fail_rate:
        logger.warning("API call failed (simulated)")
        raise Exception(f"API call to {url} failed")

    logger.info("API call succeeded")
    return {
        "url": url,
        "status": "success",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.task(
    name="tasks.fixed_backoff_task",
    retry_policy=RetryPolicy(
        max_retries=3,
        retry_delay=2.0,
        backoff=RetryBackoff.FIXED,
    ),
)
async def fixed_backoff_task(task_id: str) -> dict[str, Any]:
    """
    Task with fixed retry backoff.

    Demonstrates: Fixed delay between retries (2s, 2s, 2s).
    """
    logger.info(f"Executing task {task_id}")

    # Fail 50% of the time
    if random.random() < 0.5:
        raise Exception("Random failure")

    return {"task_id": task_id, "status": "success"}


@app.task(
    name="tasks.selective_retry",
    retry_policy=RetryPolicy(
        max_retries=3,
        retry_delay=1.0,
        backoff=RetryBackoff.LINEAR,
        retry_on=["ConnectionError", "TimeoutError"],
        ignore_on=["ValueError", "KeyError"],
    ),
)
async def selective_retry(operation: str) -> dict[str, Any]:
    """
    Task that only retries specific exceptions.

    Demonstrates: Selective retry based on exception type.
    """
    logger.info(f"Executing operation: {operation}")

    if operation == "connection_error":
        raise ConnectionError("Connection failed")  # Will retry
    if operation == "value_error":
        raise ValueError("Invalid value")  # Will NOT retry, goes to DLQ
    if operation == "timeout":
        raise TimeoutError("Operation timed out")  # Will retry

    return {"operation": operation, "status": "success"}


@app.task(
    name="tasks.context_aware",
    retry_policy=RetryPolicy(max_retries=3, retry_delay=1.0),
)
async def context_aware_task(ctx: TaskContext, value: int) -> dict[str, Any]:
    """
    Task that uses TaskContext for control flow.

    Demonstrates: Using context to make retry decisions.
    """
    logger.info(f"Task {ctx.task_id} - Attempt {ctx.retries + 1}/{ctx.max_retries + 1}")

    # Simulate occasional failures
    if value < 0:
        logger.warning(f"Negative value {value}, retrying...")
        ctx.retry()  # Explicit retry

    # Check if this is the last retry attempt
    if ctx.is_last_retry:
        logger.info("This is the last retry attempt!")

    logger.info(f"Remaining retries: {ctx.remaining_retries}")

    return {
        "value": value,
        "task_id": ctx.task_id,
        "attempts": ctx.retries + 1,
        "status": "success",
    }


@app.task(
    name="tasks.conditional_retry",
    retry_policy=RetryPolicy(max_retries=5, retry_delay=2.0),
)
async def conditional_retry_task(
    ctx: TaskContext,
    data: dict[str, Any],
) -> dict[str, Any]:
    """
    Task with conditional retry logic.

    Demonstrates: Using context to conditionally retry or fail.
    """
    logger.info(f"Processing data (attempt {ctx.retries + 1})")

    # Simulate a condition that requires retry
    if "required_field" not in data:
        if ctx.retries < 2:
            logger.warning("Missing required_field, retrying with delay...")
            ctx.retry(countdown=5.0)  # Retry with custom delay
        else:
            logger.error("Still missing required_field after retries")
            ctx.fail(ValueError("required_field is mandatory"))

    return {
        "data": data,
        "processed_at": datetime.now(UTC).isoformat(),
    }


@app.task(
    name="tasks.at_most_once",
    delivery_mode=DeliveryMode.AT_MOST_ONCE,
)
async def at_most_once_task(event: str) -> None:
    """
    Fire-and-forget task.

    Demonstrates: AT_MOST_ONCE delivery (acknowledged before execution).
    May be lost if worker crashes, but never duplicated.
    """
    logger.info(f"Processing event (at-most-once): {event}")
    await asyncio.sleep(0.5)
    logger.info(f"Event processed: {event}")


@app.task(
    name="tasks.at_least_once",
    delivery_mode=DeliveryMode.AT_LEAST_ONCE,
)
async def at_least_once_task(transaction_id: str, amount: float) -> dict[str, Any]:
    """
    Guaranteed delivery task.

    Demonstrates: AT_LEAST_ONCE delivery (acknowledged after execution).
    Guaranteed to be executed, but may be executed multiple times.
    Make this task idempotent!
    """
    logger.info(f"Processing transaction {transaction_id}: ${amount}")

    # Simulate idempotent operation (check if already processed)
    # In real world, check database for transaction_id

    await asyncio.sleep(1.0)

    return {
        "transaction_id": transaction_id,
        "amount": amount,
        "status": "completed",
        "processed_at": datetime.now(UTC).isoformat(),
    }


@app.task(
    name="tasks.fire_and_forget",
    delivery_mode=DeliveryMode.AT_MOST_ONCE,
    ignore_result=True,
)
async def fire_and_forget_task(log_message: str) -> None:
    """
    Log task that doesn't return results.

    Demonstrates: Fire-and-forget with no result storage.
    """
    logger.info(f"LOG: {log_message}")
    await asyncio.sleep(0.1)


@app.task(name="tasks.process_batch_item")
async def process_batch_item(item_id: int, data: str) -> dict[str, Any]:
    """
    Process a single item from a batch.

    Demonstrates: Individual item processing in batch operations.
    """
    logger.info(f"Processing item {item_id}")
    await asyncio.sleep(random.uniform(0.1, 0.5))  # Variable processing time

    return {
        "item_id": item_id,
        "data": data.upper(),
        "processed_at": datetime.now(UTC).isoformat(),
    }


@app.task(name="tasks.aggregate_results")
async def aggregate_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Aggregate results from batch processing.

    Demonstrates: Aggregation/reduction task.
    """
    logger.info(f"Aggregating {len(results)} results")

    return {
        "total_items": len(results),
        "aggregated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "processed": len([r for r in results if "processed_at" in r]),
        },
    }


@app.task(name="tasks.chain_step_one")
async def chain_step_one(value: int) -> int:
    """
    First step in a task chain.

    Demonstrates: Task chaining - step 1.
    """
    logger.info(f"Chain step 1: Processing {value}")
    await asyncio.sleep(0.5)
    result = value * 2
    logger.info(f"Chain step 1: Result = {result}")
    return result


@app.task(name="tasks.chain_step_two")
async def chain_step_two(value: int) -> int:
    """
    Second step in a task chain.

    Demonstrates: Task chaining - step 2.
    """
    logger.info(f"Chain step 2: Processing {value}")
    await asyncio.sleep(0.5)
    result = value + 10
    logger.info(f"Chain step 2: Result = {result}")
    return result


@app.task(name="tasks.chain_step_three")
async def chain_step_three(value: int) -> dict[str, Any]:
    """
    Final step in a task chain.

    Demonstrates: Task chaining - step 3 (final).
    """
    logger.info(f"Chain step 3: Processing {value}")
    await asyncio.sleep(0.5)
    result = value**2
    logger.info(f"Chain step 3: Result = {result}")

    return {
        "final_result": result,
        "completed_at": datetime.now(UTC).isoformat(),
    }


@app.task(
    name="tasks.cpu_intensive",
    retry_policy=RetryPolicy(max_retries=2, retry_delay=1.0),
)
def cpu_intensive_task(n: int) -> int:
    """
    CPU-intensive synchronous task.

    Demonstrates: Non-async task execution (runs in thread pool).
    Calculate Fibonacci number recursively (inefficient on purpose).
    """
    logger.info(f"Computing Fibonacci({n})")

    def fib(x: int) -> int:
        if x <= 1:
            return x
        return fib(x - 1) + fib(x - 2)

    result = fib(n)
    logger.info(f"Fibonacci({n}) = {result}")
    return result


@app.task(name="tasks.notification")
async def send_notification(
    user_id: int,
    message: str,
    notification_type: str = "email",
) -> dict[str, Any]:
    """
    Send a notification to a user.

    Demonstrates: Real-world notification task.
    """
    logger.info(
        f"Sending {notification_type} notification to user {user_id}: {message}"
    )

    # Simulate sending notification
    await asyncio.sleep(0.3)

    return {
        "user_id": user_id,
        "notification_type": notification_type,
        "message": message,
        "sent_at": datetime.now(UTC).isoformat(),
        "status": "sent",
    }


@app.task(name="tasks.cleanup")
async def cleanup_task(resource_id: str, older_than_days: int) -> dict[str, Any]:
    """
    Cleanup old resources.

    Demonstrates: Maintenance/cleanup task.
    """
    logger.info(f"Cleaning up resource {resource_id} older than {older_than_days} days")

    await asyncio.sleep(1.0)

    return {
        "resource_id": resource_id,
        "items_deleted": random.randint(0, 100),
        "cleaned_at": datetime.now(UTC).isoformat(),
    }


@app.task(
    name="tasks.always_fails",
    retry_policy=RetryPolicy(max_retries=2, retry_delay=1.0),
)
async def always_fails_task(reason: str) -> None:
    """
    Task that always fails (for testing error handling).

    Demonstrates: Task failure and DLQ behavior.
    """
    logger.error(f"Task failing: {reason}")
    raise Exception(f"Task failed: {reason}")


@app.task(name="tasks.sometimes_fails")
async def sometimes_fails_task(success_rate: float = 0.5) -> dict[str, Any]:
    """
    Task that fails randomly.

    Demonstrates: Probabilistic failures without retry policy.
    """
    logger.info(f"Attempting task (success_rate={success_rate})")

    if random.random() > success_rate:
        raise Exception("Random failure occurred")

    return {
        "status": "success",
        "timestamp": datetime.now(UTC).isoformat(),
    }
