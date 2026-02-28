# Input Validation

Chicory provides powerful built-in validation capabilities using Pydantic to ensure your tasks receive the correct data types and structure. This prevents runtime errors and makes your task queue more reliable.

## Overview

Validation in Chicory happens automatically based on your function's type hints. You can control the validation behavior using validation modes to catch errors early and ensure data integrity.

## Validation Modes

Chicory supports three validation modes:

| Mode | Input Validation | Output Validation | Use Case |
|------|-----------------|-------------------|----------|
| `NONE` | ❌ No | ❌ No | Maximum performance, trusted inputs |
| `INPUTS` | ✅ Yes | ❌ No | Validate caller inputs (recommended) |
| `OUTPUTS` | ❌ No | ✅ Yes | Validate caller outputs |
| `STRICT` | ✅ Yes | ✅ Yes | Full validation for critical tasks |

### Setting Validation Mode

You can set validation mode globally or per-task:

```python
from chicory import Chicory, ValidationMode

# Global validation mode
app = Chicory(
    broker=BrokerType.REDIS,
    backend=BackendType.REDIS,
    validation_mode=ValidationMode.INPUTS,  # Default for all tasks
)

# Per-task override
@app.task(
    name="tasks.critical_operation",
    validation_mode=ValidationMode.STRICT,  # Override global setting
)
async def critical_operation(data: dict) -> dict:
    return {"status": "processed"}
```

!!! tip "Recommended Default"
    Use `ValidationMode.INPUTS` as your default. It catches input errors without the overhead of validating outputs (which you control).

## Type Validation

Chicory validates arguments based on your type hints:

### Basic Types

```python
@app.task(
    name="tasks.validate_email",
    validation_mode=ValidationMode.STRICT,
)
async def validate_email(email: str, user_id: int) -> dict[str, Any]:
    """Validate email and user ID types."""
    is_valid = "@" in email and "." in email.split("@")[1]

    return {
        "email": email,
        "user_id": user_id,
        "is_valid": is_valid,
    }
```

**Valid usage:**

```python
# Correct types - will succeed
result = await validate_email.delay(
    email="alice@example.com",
    user_id=123,
)
validation_result = await result.get(timeout=10.0)
```

**Invalid usage:**

```python
from chicory import ValidationError

try:
    # Wrong type: user_id should be int, not string
    result = await validate_email.delay(
        email="bob@example.com",
        user_id="not_an_integer",  # ❌ Wrong type!
    )
    await result.get(timeout=10.0)
except ValidationError as e:
    print(f"Validation error: {e}")
    # Output: Validation error: Field 'user_id' expected int, got str
```

!!! note "Validation Timing"
    Validation errors are raised **immediately** when you call `.delay()` or `.send()`, before the task is dispatched. This provides fast feedback and prevents invalid tasks from entering the queue.

### Complex Types

Chicory validates complex types including lists, dictionaries, and nested structures:

```python
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
    """Process an order with validation."""
    return {
        "order_id": order_id,
        "item_count": len(items),
        "total": total,
        "customer_email": customer_email,
        "status": "processed",
    }
```

**Valid examples:**

```python
# All parameters with correct types
result = await process_order.delay(
    order_id="ORD-001",
    items=["laptop", "mouse", "keyboard"],
    total=1299.99,
    customer_email="customer@example.com",
)

# Optional parameter omitted (None is allowed)
result = await process_order.delay(
    order_id="ORD-002",
    items=["book"],
    total=25.50,
    # customer_email is optional
)

# Empty list is valid
result = await process_order.delay(
    order_id="ORD-003",
    items=[],  # ✅ Valid
    total=0.0,
)
```

**Invalid examples:**

```python
# Wrong type for items (string instead of list)
try:
    result = await process_order.delay(
        order_id="ORD-004",
        items="this should be a list",  # ❌ Wrong type!
        total=99.99,
    )
except ValidationError as e:
    print("Items must be a list")

# Wrong type for total (string instead of float)
try:
    result = await process_order.delay(
        order_id="ORD-005",
        items=["item1"],
        total="not_a_number",  # ❌ Wrong type!
    )
except ValidationError as e:
    print("Total must be a number")
```

## STRICT Mode: Output Validation

!!! warning "Not Yet Implemented"
    Output validation (`OUTPUTS` and `STRICT` modes) is planned but **not yet implemented**. Currently, only input validation (`INPUTS` mode) is functional. Setting `STRICT` mode will validate inputs but not outputs.

When using `ValidationMode.STRICT`, Chicory also validates the task's return value:

```python
@app.task(
    name="tasks.strict_validation",
    validation_mode=ValidationMode.STRICT,
)
async def strict_task(value: int) -> dict[str, int]:
    """Task with both input and output validation."""
    # Return value must match the type hint: dict[str, int]
    return {"result": value * 2, "status": 200}
```

**Correct return value:**

```python
result = await strict_task.delay(10)
data = await result.get(timeout=10.0)  # ✅ Valid: returns dict[str, int]
```

**Incorrect return value:**

```python
@app.task(
    name="tasks.bad_output",
    validation_mode=ValidationMode.STRICT,
)
async def bad_output(value: int) -> dict[str, int]:
    # ❌ This will fail: values should be int, not str
    return {"result": str(value), "status": "ok"}
```

!!! danger "Output Validation Overhead"
    STRICT mode adds overhead to validate return values. Use it only for critical tasks where you need guarantees about output structure. For most tasks, INPUTS mode is sufficient.

## Next Steps

Now that you understand validation, explore these related topics:

- [**Retry Policies**](retry-policies.md) - Handle validation failures with automatic retries
- [**Task Context**](task-context.md) - Access validation information in your tasks
