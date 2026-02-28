# Delivery Modes

Delivery modes define the guarantees Chicory provides about task execution. Understanding these modes is crucial for building reliable distributed systems with the right trade-offs between performance and reliability.

## Overview

Chicory supports two delivery modes that determine when a task is acknowledged:

| Mode | Acknowledgment | Execution Guarantee | Can Be Lost | Can Be Duplicated |
|------|---------------|---------------------|-------------|-------------------|
| `AT_MOST_ONCE` | Before execution | Best effort | ✅ Yes | ❌ No |
| `AT_LEAST_ONCE` | After execution | Guaranteed | ❌ No | ✅ Yes |

The choice between these modes represents a fundamental trade-off in distributed systems: **reliability vs. performance**.

## AT_MOST_ONCE Delivery

Tasks are acknowledged **before** execution. This is the fastest mode but provides the weakest guarantees.

### How It Works

1. Task is dispatched to the queue
2. Worker receives the task
3. **Task is immediately acknowledged** ✅
4. Worker executes the task

If the worker crashes during step 4, the task is lost.

### Configuration

```python
from chicory import DeliveryMode

@app.task(
    name="tasks.at_most_once",
    delivery_mode=DeliveryMode.AT_MOST_ONCE,
)
async def log_event(event: str) -> None:
    """Fire-and-forget logging task."""
    print(f"Processing event: {event}")
    await asyncio.sleep(0.5)
    print(f"Event processed: {event}")
```

### When to Use AT_MOST_ONCE

Perfect for tasks where:

- ✅ Occasional loss is acceptable
- ✅ Performance is critical
- ✅ Tasks are not critical to business logic
- ✅ Duplication would be worse than loss

**Ideal use cases:**

- Logging and metrics collection
- Analytics events
- Cache warming
- Non-critical notifications
- Activity tracking
- Performance monitoring

!!! warning "Risk of Loss"
    If the worker crashes after acknowledging but before execution:
    ```python
    await log_event.delay("important_event")
    # Worker acknowledges immediately
    # Worker crashes before execution
    # ⚠️  Event is lost - never executed
    ```

## AT_LEAST_ONCE Delivery

Tasks are acknowledged **after** successful execution. This guarantees execution but may result in duplicates.

### How It Works

1. Task is dispatched to the queue
2. Worker receives the task
3. Worker executes the task
4. **Task is acknowledged after completion** ✅

If the worker crashes during step 3, the task remains in the queue and will be retried.

### Configuration

```python
@app.task(
    name="tasks.at_least_once",
    delivery_mode=DeliveryMode.AT_LEAST_ONCE,
)
async def process_payment(
    transaction_id: str,
    amount: float,
) -> dict[str, Any]:
    """Critical payment processing - must not be lost."""
    print(f"Processing payment {transaction_id}: ${amount}")

    # Idempotent operation: check if already processed
    if await already_processed(transaction_id):
        print(f"Transaction {transaction_id} already processed")
        return {"status": "already_processed"}

    # Process payment
    await payment_gateway.charge(transaction_id, amount)

    return {
        "transaction_id": transaction_id,
        "amount": amount,
        "status": "completed",
        "processed_at": datetime.now(UTC).isoformat(),
    }
```

### When to Use AT_LEAST_ONCE

Essential for tasks where:

- ✅ Execution must be guaranteed
- ✅ Data loss is unacceptable
- ✅ Operations can be made idempotent
- ✅ Business logic is critical

**Ideal use cases:**

- Financial transactions
- Payment processing
- Order fulfillment
- Email notifications (with deduplication)
- Database updates
- Critical business operations

!!! danger "Must Be Idempotent"
    AT_LEAST_ONCE tasks **must** be idempotent because they may execute multiple times:
    ```python
    # ❌ BAD: Not idempotent
    async def charge_customer(customer_id: int, amount: float):
        await payment.charge(customer_id, amount)
        # If executed twice, customer is charged twice!

    # ✅ GOOD: Idempotent
    async def charge_customer(transaction_id: str, customer_id: int, amount: float):
        if await payment.already_charged(transaction_id):
            return {"status": "already_charged"}
        await payment.charge(transaction_id, customer_id, amount)
        # transaction_id ensures idempotency
    ```

## Next Steps

Now that you understand delivery modes:

- [**Retry Policies**](retry-policies.md) - Combine with retry strategies
