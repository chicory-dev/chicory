# Task Context

The `TaskContext` provides runtime metadata and advanced control over task execution. It gives you access to information about the current task and allows manual control over retries, failures, and execution flow.

## Overview

When you need more control over your task's behavior, inject `TaskContext` as the first parameter of your task function. This special parameter is automatically provided by Chicory and gives you access to:

- Task metadata (ID, name, retry count)
- Manual retry triggering
- Explicit failure handling
- Retry state information

## Basic Task Context Usage

To use task context, add it as the first parameter with type hint `TaskContext`:

```python
from chicory import TaskContext

@app.task(
    name="tasks.context_aware",
    retry_policy=RetryPolicy(max_retries=3, retry_delay=1.0),
)
async def context_aware_task(ctx: TaskContext, value: int) -> dict[str, Any]:
    """
    Task that uses context for runtime information.

    Args:
        ctx: Automatically injected by Chicory
        value: Your regular task parameter
    """
    # Access task metadata
    print(f"Task ID: {ctx.task_id}")
    print(f"Task Name: {ctx.task_name}")
    print(f"Current attempt: {ctx.retries + 1}")
    print(f"Max retries: {ctx.max_retries}")

    return {
        "value": value,
        "task_id": ctx.task_id,
        "attempts": ctx.retries + 1,
    }
```

**When calling the task, don't pass the context:**

```python
# ✅ Correct - context is injected automatically
result = await context_aware_task.delay(value=42)

# ❌ Wrong - don't pass context manually
# result = await context_aware_task.delay(ctx, value=42)
```

!!! note "Automatic Injection"
    The `TaskContext` parameter is automatically injected by Chicory. You never pass it when calling `.delay()` or `.send()`.

## Task Metadata

The context provides access to task identification and retry state:

```python
@app.task(
    name="tasks.retry_info",
    retry_policy=RetryPolicy(max_retries=5, retry_delay=1.0),
)
async def retry_info_task(ctx: TaskContext, value: int) -> dict:
    print(f"Task ID: {ctx.task_id}")           # Unique execution ID
    print(f"Task Name: {ctx.task_name}")       # Registered name
    print(f"Attempt: {ctx.retries + 1}")       # Current retry count (0-based)
    print(f"Max retries: {ctx.max_retries}")
    print(f"Remaining: {ctx.remaining_retries}")

    if ctx.is_last_retry:
        print("This is the final attempt!")

    return {"attempt": ctx.retries + 1}
```

## Manual Retry Control

Use `ctx.retry()` to manually trigger a retry:

### Basic Manual Retry

```python
@app.task(
    name="tasks.manual_retry",
    retry_policy=RetryPolicy(max_retries=3, retry_delay=1.0),
)
async def manual_retry_task(ctx: TaskContext, value: int) -> dict[str, Any]:
    """Task with manual retry logic."""

    print(f"Processing value: {value}")

    # Conditional retry logic
    if value < 0:
        print("Negative value detected, retrying...")
        ctx.retry()  # Manually trigger retry

    # Check if this is the last retry
    if ctx.is_last_retry and value < 0:
        print("Last attempt with negative value - will fail")
        # Don't retry on last attempt, let it fail naturally

    return {
        "value": value,
        "attempts": ctx.retries + 1,
        "status": "success",
    }
```

**Usage:**

```python
# Positive value - succeeds immediately
result = await manual_retry_task.delay(value=10)
data = await result.get(timeout=10.0)
print(f"Attempts: {data['attempts']}")  # Output: 1

# Negative value - will retry
result = await manual_retry_task.delay(value=-5)
try:
    data = await result.get(timeout=15.0)
    print(f"Eventually succeeded after {data['attempts']} attempts")
except Exception as e:
    print(f"Failed after {ctx.max_retries + 1} attempts")
```

### Retry with Custom Delay

Override the default retry delay for specific situations:

```python
@app.task(
    name="tasks.custom_delay_retry",
    retry_policy=RetryPolicy(max_retries=5, retry_delay=2.0),
)
async def custom_delay_retry(ctx: TaskContext, data: dict) -> dict:
    """Task with conditional custom retry delays."""

    # Check for required field
    if "required_field" not in data:
        if ctx.retries < 2:
            print("Missing required_field, retrying in 5 seconds...")
            ctx.retry(countdown=5.0)  # Wait 5 seconds before retry
        else:
            print("Still missing required_field after retries")
            # After 2 retries, fail explicitly
            ctx.fail(ValueError("required_field is mandatory"))

    return {
        "data": data,
        "processed_at": datetime.now(UTC).isoformat(),
    }
```

**Example scenarios:**

```python
# Missing required field - will retry with 5s delay
incomplete_data = {"user_id": 123}
result = await custom_delay_retry.delay(data=incomplete_data)
# Retries after 5s, 5s, then fails

# Complete data - succeeds immediately
complete_data = {"user_id": 123, "required_field": "present"}
result = await custom_delay_retry.delay(data=complete_data)
data = await result.get(timeout=10.0)  # Success on first attempt
```

!!! tip "Custom Countdown"
    Use `ctx.retry(countdown=N)` to override the retry policy's delay for specific situations, such as:

    - Waiting for eventual consistency
    - Rate limit cooldowns
    - Service-specific backoff requirements

## Explicit Failure

Use `ctx.fail()` to explicitly fail a task without retrying:

```python
@app.task(
    name="tasks.explicit_failure",
    retry_policy=RetryPolicy(max_retries=3, retry_delay=1.0),
)
async def validate_and_process(ctx: TaskContext, user_input: str) -> dict:
    """Task that can fail explicitly on validation errors."""

    # Validation that should NOT be retried
    if len(user_input) < 3:
        # Explicitly fail without retry
        ctx.fail(ValueError("Input must be at least 3 characters"))

    # Transient error that SHOULD be retried
    try:
        result = await external_api_call(user_input)
    except ConnectionError as e:
        # Let retry policy handle this
        raise e

    return {"result": result, "input": user_input}
```

**Example usage:**

```python
# Validation error - fails immediately without retry
result = await validate_and_process.delay("ab")  # Too short
try:
    await result.get(timeout=10.0)
except Exception as e:
    print(f"Failed immediately: {e}")
    # No retries happened

# Valid input but API fails - will retry
result = await validate_and_process.delay("valid_input")
data = await result.get(timeout=30.0)  # May retry on network errors
```

!!! warning "When to Use ctx.fail()"
    Use `ctx.fail()` for **permanent errors** that won't be fixed by retrying:

    - Validation errors
    - Authentication failures
    - Malformed input data
    - Business logic violations

    Don't use it for **transient errors** that might succeed on retry:

    - Network failures
    - Temporary service outages
    - Rate limiting

## Next Steps

Now that you understand task context, explore:

- [**Delivery Modes**](delivery-modes.md) - Delivery guarantees and acknowledgment
