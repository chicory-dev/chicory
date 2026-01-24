"""
Example 5: Delivery Modes
==========================

This example demonstrates Chicory's delivery guarantee modes:
- AT_MOST_ONCE: Fire-and-forget, acknowledged before execution
- AT_LEAST_ONCE: Guaranteed delivery, acknowledged after execution
- Idempotency considerations
- Result storage options

Prerequisites:
--------------
1. Redis server running on localhost:6379
2. Worker running: chicory worker examples.shared_tasks:app

Usage:
------
    python examples/05_delivery_modes.py
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from examples.shared_tasks import (
    app,
    at_least_once_task,
    at_most_once_task,
    fire_and_forget_task,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Demonstrate delivery mode features."""

    logger.info("=" * 70)
    logger.info("CHICORY EXAMPLE 5: Delivery Modes")
    logger.info("=" * 70)

    await app.connect()

    try:
        # ====================================================================
        # 1. AT_MOST_ONCE delivery mode
        # ====================================================================
        logger.info("1. AT_MOST_ONCE delivery mode...")
        logger.info("   • Acknowledged BEFORE execution")
        logger.info("   • May be lost if worker crashes")
        logger.info("   • Never duplicated")
        logger.info("   • Best for: Logging, analytics, non-critical events")

        # Send multiple events
        events = [
            "user_login",
            "page_view",
            "button_click",
            "api_call",
            "cache_miss",
        ]

        logger.info(f"   Sending {len(events)} events...")
        results = []
        for event in events:
            result = await at_most_once_task.delay(event=event)
            results.append(result)
            logger.info(f"     • {event}: {result.task_id}")

        logger.info("   Events dispatched (fire-and-forget)")
        logger.info("   No result retrieval needed")

        # Note: We can try to get results, but it's not the primary use case
        await asyncio.sleep(2)  # Give tasks time to complete
        logger.info("   All events should be processed (check worker logs)")

        # ====================================================================
        # 2. AT_LEAST_ONCE delivery mode
        # ====================================================================
        logger.info("2. AT_LEAST_ONCE delivery mode...")
        logger.info("   • Acknowledged AFTER successful execution")
        logger.info("   • Guaranteed to execute")
        logger.info("   • May be duplicated if worker crashes after execution")
        logger.info("   • Best for: Financial transactions, critical operations")
        logger.info("   • IMPORTANT: Make your tasks idempotent!")

        # Send a critical transaction
        result = await at_least_once_task.delay(
            transaction_id="TXN-001",
            amount=99.99,
        )

        logger.info(f"   Transaction dispatched: {result.task_id}")
        logger.info("   Waiting for confirmation...")

        transaction_result = await result.get(timeout=10.0)
        if transaction_result is None:
            raise Exception("Task returned None unexpectedly")

        logger.info("   ✓ Transaction completed:")
        logger.info(f"     Transaction ID: {transaction_result['transaction_id']}")
        logger.info(f"     Amount: ${transaction_result['amount']:.2f}")
        logger.info(f"     Status: {transaction_result['status']}")
        logger.info(f"     Processed at: {transaction_result['processed_at']}")

        # ====================================================================
        # 3. Multiple critical transactions
        # ====================================================================
        logger.info("3. Multiple AT_LEAST_ONCE transactions...")

        transactions = [
            ("TXN-100", 29.99),
            ("TXN-101", 149.50),
            ("TXN-102", 5.00),
            ("TXN-103", 1299.99),
        ]

        logger.info(f"   Dispatching {len(transactions)} transactions...")
        results = []
        for txn_id, amount in transactions:
            result = await at_least_once_task.delay(
                transaction_id=txn_id,
                amount=amount,
            )
            results.append((result, txn_id, amount))
            logger.info(f"     • {txn_id}: ${amount:.2f}")

        logger.info("   Waiting for all transactions to complete...")

        completed = []
        for result, txn_id, amount in results:
            try:
                txn_result = await result.get(timeout=15.0)
                completed.append(txn_result)
                logger.info(f"     ✓ {txn_id}: {txn_result['status']}")
            except Exception as e:
                logger.info(f"     ✗ {txn_id}: Failed - {e}")

        total_amount = sum(c["amount"] for c in completed)

        logger.info(f"   Processed {len(completed)} transactions")
        logger.info(f"   Total amount: ${total_amount:.2f}")

        # ====================================================================
        # 4. Fire-and-forget with no result storage
        # ====================================================================
        logger.info("4. Fire-and-forget with ignore_result=True...")
        logger.info("   • AT_MOST_ONCE + no result storage")
        logger.info("   • Minimal overhead")
        logger.info("   • Best for: High-volume logging, metrics")

        log_messages = [
            "Application started",
            "User authentication successful",
            "Database connection established",
            "Cache warmed up",
            "Ready to serve requests",
        ]

        logger.info(f"   Sending {len(log_messages)} log messages...")
        for msg in log_messages:
            task_id = await fire_and_forget_task.send(log_message=msg)
            logger.info(f"     • {msg[:40]:40s} [ID: {task_id[:8]}...]")

        logger.info("   Logs dispatched (no result tracking)")

        # ====================================================================
        # 5. Comparing delivery modes
        # ====================================================================
        logger.info("5. Performance comparison...")

        import time

        # AT_MOST_ONCE (faster dispatch, no waiting)
        logger.info("   Dispatching 10 AT_MOST_ONCE tasks...")
        start = time.time()
        at_most_results = []
        for i in range(10):
            result = await at_most_once_task.delay(event=f"event_{i}")
            at_most_results.append(result)
        at_most_elapsed = time.time() - start
        logger.info(f"   Dispatch time: {at_most_elapsed:.3f}s")

        # AT_LEAST_ONCE (guaranteed, but wait for completion)
        logger.info("   Dispatching 10 AT_LEAST_ONCE tasks...")
        start = time.time()
        at_least_results = []
        for i in range(10):
            result = await at_least_once_task.delay(
                transaction_id=f"TXN-{i}",
                amount=10.0 + i,
            )
            at_least_results.append(result)

        # Wait for all to complete
        await asyncio.gather(
            *[r.get(timeout=15.0) for r in at_least_results],
            return_exceptions=True,
        )
        at_least_elapsed = time.time() - start
        logger.info(f"   Total time (dispatch + execution): {at_least_elapsed:.3f}s")

        logger.info(
            f"   Dispatch time ratio: {at_least_elapsed / at_most_elapsed:.1f}x"
        )
        logger.info("   (AT_LEAST_ONCE includes waiting for results)")

        # ====================================================================
        # 6. Idempotency demonstration
        # ====================================================================
        logger.info("6. Idempotency best practices...")

        logger.info("   For AT_LEAST_ONCE tasks, make them idempotent:")
        logger.info("     ✓ Use unique transaction IDs")
        logger.info("     ✓ Check if already processed (database lookup)")
        logger.info("     ✓ Use database constraints (unique keys)")
        logger.info("     ✓ Design operations that are naturally idempotent")

        logger.info("   Example idempotent operations:")
        logger.info("     • SET operations (not INCREMENT)")
        logger.info("     • Upsert (INSERT OR UPDATE)")
        logger.info("     • Absolute state changes (not relative)")

        # Simulate sending the same transaction twice
        txn_id = "TXN-IDEMPOTENT-001"
        amount = 50.0

        logger.info(f"   Sending same transaction twice: {txn_id}")
        result1 = await at_least_once_task.delay(
            transaction_id=txn_id,
            amount=amount,
        )
        result2 = await at_least_once_task.delay(
            transaction_id=txn_id,
            amount=amount,
        )

        txn1 = await result1.get(timeout=10.0)
        if txn1 is None:
            raise Exception("Task returned None unexpectedly")

        txn2 = await result2.get(timeout=10.0)
        if txn2 is None:
            raise Exception("Task returned None unexpectedly")

        logger.info(f"     First execution: {txn1['status']}")
        logger.info(f"     Second execution: {txn2['status']}")
        logger.info(
            "     In production: Check transaction_id to prevent duplicate processing"
        )

        logger.info("=" * 70)
        logger.info("All delivery mode examples completed!")
        logger.info("=" * 70)

        logger.info("Key takeaways:")

        logger.info("AT_MOST_ONCE:")
        logger.info("  • Fast, low overhead")
        logger.info("  • May be lost on worker failure")
        logger.info("  • Never duplicated")
        logger.info("  • Use for: Logs, metrics, non-critical events")

        logger.info("AT_LEAST_ONCE:")
        logger.info("  • Guaranteed execution")
        logger.info("  • May be duplicated on worker failure")
        logger.info("  • Higher overhead (waits for ACK)")
        logger.info("  • Use for: Financial transactions, critical operations")
        logger.info("  • MUST be idempotent!")

        logger.info("ignore_result=True:")
        logger.info("  • Doesn't store results in backend")
        logger.info("  • Saves memory and storage")
        logger.info("  • Use for fire-and-forget tasks")

    finally:
        await app.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
