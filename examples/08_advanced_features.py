"""
Example 8: Advanced Features
=============================

This example demonstrates advanced Chicory features:
- Task chaining (workflows)
- Synchronous vs asynchronous tasks
- CPU-intensive tasks
- Custom task names
- Task result inspection
- Worker health checks
- Dead Letter Queue (DLQ) management

Prerequisites:
--------------
1. Redis server running on localhost:6379
2. Worker running with DLQ: chicory worker examples.shared_tasks:app --dlq

Usage:
------
    python examples/08_advanced_features.py
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from examples.shared_tasks import (
    app,
    chain_step_one,
    chain_step_three,
    chain_step_two,
    cleanup_task,
    cpu_intensive_task,
    send_notification,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Demonstrate advanced Chicory features."""

    logger.info("=" * 70)
    logger.info("CHICORY EXAMPLE 8: Advanced Features")
    logger.info("=" * 70)

    await app.connect()

    try:
        # ====================================================================
        # 1. Task Chaining (Manual Workflow)
        # ====================================================================
        logger.info("1. Task chaining - building a workflow...")
        logger.info("   Chain: (value * 2) -> (+ 10) -> (^ 2)")

        initial_value = 5
        logger.info(f"   Initial value: {initial_value}")

        # Step 1: Multiply by 2
        result1 = await chain_step_one.delay(initial_value)
        step1_result = await result1.get(timeout=10.0)
        logger.info(f"   Step 1 (x2): {step1_result}")

        # Step 2: Add 10
        result2 = await chain_step_two.delay(step1_result)
        step2_result = await result2.get(timeout=10.0)
        logger.info(f"   Step 2 (+10): {step2_result}")

        # Step 3: Square
        result3 = await chain_step_three.delay(step2_result)
        step3_result = await result3.get(timeout=10.0)
        if step3_result is None:
            raise Exception("Task returned None unexpectedly")

        logger.info(f"   Step 3 (^2): {step3_result['final_result']}")
        logger.info(f"   Completed at: {step3_result['completed_at']}")

        # ====================================================================
        # 2. Parallel chains
        # ====================================================================
        logger.info("2. Multiple parallel workflow chains...")

        input_values = [3, 5, 7, 9]
        logger.info(f"   Processing {len(input_values)} parallel chains")
        logger.info(f"   Input values: {input_values}")

        # Start all chains in parallel
        chain_results = []
        for val in input_values:
            # Step 1
            r1 = await chain_step_one.delay(val)
            chain_results.append((val, r1))

        logger.info("   Step 1 dispatched for all chains...")

        # Wait for step 1 and dispatch step 2
        step2_results = []
        for val, r1 in chain_results:
            s1 = await r1.get(timeout=10.0)
            r2 = await chain_step_two.delay(s1)
            step2_results.append((val, r2))

        logger.info("   Step 2 dispatched for all chains...")

        # Wait for step 2 and dispatch step 3
        step3_results = []
        for val, r2 in step2_results:
            s2 = await r2.get(timeout=10.0)
            r3 = await chain_step_three.delay(s2)
            step3_results.append((val, r3))

        logger.info("   Step 3 dispatched for all chains...")

        # Collect final results
        final_results = []
        for val, r3 in step3_results:
            s3 = await r3.get(timeout=10.0)
            final_results.append((val, s3["final_result"]))

        logger.info("   Final results:")
        for input_val, output_val in final_results:
            logger.info(f"     {input_val} -> {output_val}")

        # ====================================================================
        # 3. Synchronous (CPU-intensive) tasks
        # ====================================================================
        logger.info("3. Synchronous CPU-intensive tasks...")
        logger.info("   (These run in a thread pool, not async)")

        # Calculate Fibonacci numbers
        fib_inputs = [10, 15, 20, 25]

        logger.info(f"   Computing Fibonacci for: {fib_inputs}")

        # Dispatch all
        fib_results = [await cpu_intensive_task.delay(n) for n in fib_inputs]

        logger.info("   Tasks dispatched, waiting for completion...")

        # Wait for all
        fib_values = await asyncio.gather(*[r.get(timeout=30.0) for r in fib_results])

        logger.info("   Results:")
        for n, fib_n in zip(fib_inputs, fib_values):
            logger.info(f"     Fibonacci({n}) = {fib_n}")

        logger.info("   Note: These tasks run in ThreadPoolExecutor")
        logger.info("   Use for CPU-bound work (parsing, computation, etc.)")

        # ====================================================================
        # 4. Task state inspection
        # ====================================================================
        logger.info("4. Task state inspection...")

        from examples.shared_tasks import long_running_task

        # Start a long task
        result = await long_running_task.delay(duration=3)
        logger.info(f"   Started long task: {result.task_id}")

        # Check state progression
        await asyncio.sleep(0.5)
        state = await result.state()
        logger.info(f"   State after 0.5s: {state}")

        await asyncio.sleep(1.0)
        state = await result.state()
        logger.info(f"   State after 1.5s: {state}")

        # Wait for completion
        task_result = await result.get(timeout=5.0)
        if task_result is None:
            raise Exception("Task returned None unexpectedly")

        state = await result.state()
        logger.info(f"   State after completion: {state}")
        logger.info(f"   Task completed at: {task_result['completed_at']}")

        # ====================================================================
        # 5. Real-world notification system
        # ====================================================================
        logger.info("5. Real-world notification system...")

        # Send multiple notifications
        notifications = [
            (101, "Your order has been shipped!", "email"),
            (102, "Payment received", "sms"),
            (103, "Welcome to our service!", "push"),
            (104, "Your subscription is expiring soon", "email"),
        ]

        logger.info(f"   Sending {len(notifications)} notifications...")

        notification_results = []
        for user_id, message, notif_type in notifications:
            result = await send_notification.delay(
                user_id=user_id,
                message=message,
                notification_type=notif_type,
            )
            notification_results.append((user_id, notif_type, result))
            logger.info(f"     • User {user_id} ({notif_type}): {message[:30]}...")

        logger.info("   Waiting for notifications to be sent...")

        # Wait for all
        sent_notifications = await asyncio.gather(
            *[r.get(timeout=10.0) for _, _, r in notification_results],
            return_exceptions=True,
        )

        successes = sum(1 for n in sent_notifications if not isinstance(n, Exception))
        logger.info(f"   ✓ Sent {successes}/{len(notifications)} notifications")

        # ====================================================================
        # 6. Scheduled maintenance tasks
        # ====================================================================
        logger.info("6. Scheduled maintenance/cleanup tasks...")

        resources_to_cleanup = [
            ("temp_files", 7),
            ("old_logs", 30),
            ("cache_entries", 1),
        ]

        logger.info(
            f"   Scheduling cleanup for {len(resources_to_cleanup)} resources..."
        )

        cleanup_results = []
        for resource_id, days in resources_to_cleanup:
            result = await cleanup_task.delay(
                resource_id=resource_id,
                older_than_days=days,
            )
            cleanup_results.append((resource_id, result))
            logger.info(f"     • {resource_id} (older than {days} days)")

        logger.info("   Waiting for cleanup to complete...")

        # Wait for all
        cleanup_completed = await asyncio.gather(
            *[r.get(timeout=15.0) for _, r in cleanup_results]
        )

        logger.info("   ✓ Cleanup completed:")
        for cleanup_result in cleanup_completed:
            logger.info(
                f"     • {cleanup_result['resource_id']}: "
                f"{cleanup_result['items_deleted']} items deleted"
            )

        # ====================================================================
        # 7. Task result metadata
        # ====================================================================
        logger.info("7. Inspecting task result metadata...")

        from examples.shared_tasks import add

        result = await add.delay(100, 200)
        logger.info(f"   Task dispatched: {result.task_id}")

        # Get result
        answer = await result.get(timeout=10.0)

        # Check various attributes
        logger.info(f"   Result value: {answer}")
        logger.info(f"   Task ID: {result.task_id}")
        logger.info(f"   State: {await result.state()}")
        logger.info(f"   Is ready: {await result.ready()}")
        logger.info(f"   Has failed: {await result.failed()}")

        # ====================================================================
        # 8. Custom task names
        # ====================================================================
        logger.info("8. Tasks with custom names...")

        # All our tasks have custom names (e.g., "tasks.add", "tasks.multiply")
        # This is useful for:
        # - Organizing tasks in a namespace
        # - Making logs more readable
        # - Avoiding naming conflicts

        logger.info("   Task names in our app:")
        task_names = list(app._tasks.keys())
        for name in sorted(task_names)[:10]:  # Show first 10
            logger.info(f"     • {name}")

        logger.info(f"   ... and {len(task_names) - 10} more")

        logger.info("   Custom names help with:")
        logger.info("     - Organization and namespacing")
        logger.info("     - Log filtering and monitoring")
        logger.info("     - Task discovery and documentation")

        # ====================================================================
        # 9. Demonstrating DLQ behavior
        # ====================================================================
        logger.info("9. Dead Letter Queue (DLQ) behavior...")

        from examples.shared_tasks import always_fails_task

        # This task will always fail and end up in DLQ
        result = await always_fails_task.delay(reason="Demonstrating DLQ")

        logger.info(f"   Dispatched failing task: {result.task_id}")
        logger.info("   This task will fail and be moved to DLQ")
        logger.info("   Worker must be started with --dlq flag")

        try:
            await result.get(timeout=15.0)
        except Exception as e:
            logger.info("   ✓ Task failed as expected (moved to DLQ)")
            logger.info(f"   Error: {str(e)[:60]}")

        logger.info(f"  DLQ Message count {await app.broker.get_dlq_count()}")
        logger.info(f"  DLQ Messages: {await app.broker.get_dlq_messages()}")

        logger.info("   DLQ tasks can be:")
        logger.info("     • Inspected for debugging")
        logger.info("     • Requeued for retry")
        logger.info("     • Deleted if truly failed")
        logger.info("     • Monitored for alerting")

        # ====================================================================
        # 10. Performance monitoring
        # ====================================================================
        logger.info("10. Task performance patterns...")

        import time

        # Measure task dispatch speed
        logger.info("   Measuring task dispatch performance...")
        start = time.time()

        dispatch_count = 100
        results = []
        for i in range(dispatch_count):
            result = await add.delay(i, i)
            results.append(result)

        dispatch_time = time.time() - start

        logger.info(f"   ✓ Dispatched {dispatch_count} tasks in {dispatch_time:.3f}s")
        logger.info(f"   Rate: {dispatch_count / dispatch_time:.0f} tasks/second")

        # Don't wait for all tasks to complete (would take too long)
        logger.info("   (Not waiting for all tasks to complete)")

        logger.info("=" * 70)
        logger.info("All advanced features demonstrated!")
        logger.info("=" * 70)

        logger.info("Key takeaways:")

        logger.info("Task Chaining:")
        logger.info("  • Chain tasks by passing results as inputs")
        logger.info("  • Useful for multi-step workflows")
        logger.info("  • Can parallelize independent chains")

        logger.info("Synchronous Tasks:")
        logger.info("  • Use regular functions (not async) for CPU-bound work")
        logger.info("  • Automatically run in ThreadPoolExecutor")
        logger.info("  • Avoid blocking the event loop")

        logger.info("Task States:")
        logger.info("  • PENDING: Not yet started")
        logger.info("  • STARTED: Currently executing")
        logger.info("  • SUCCESS: Completed successfully")
        logger.info("  • FAILURE: Failed")
        logger.info("  • RETRY: Scheduled for retry")
        logger.info("  • DEAD_LETTERED: Moved to DLQ")

        logger.info("Best Practices:")
        logger.info("  • Use custom task names for organization")
        logger.info("  • Monitor DLQ for failed tasks")
        logger.info("  • Chain tasks for complex workflows")
        logger.info("  • Use sync tasks for CPU-intensive work")
        logger.info("  • Track task states for monitoring")

    finally:
        await app.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
