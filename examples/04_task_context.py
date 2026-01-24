"""
Example 4: Task Context
========================

This example demonstrates using TaskContext for advanced control:
- Accessing task metadata (task_id, task_name, retry count)
- Manual retry triggering with ctx.retry()
- Custom retry delays
- Conditional retry logic
- Checking retry state (is_last_retry, remaining_retries)
- Explicit task failure with ctx.fail()

Prerequisites:
--------------
1. Redis server running on localhost:6379
2. Worker running: chicory worker examples.shared_tasks:app

Usage:
------
    python examples/04_task_context.py
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from examples.shared_tasks import (
    app,
    conditional_retry_task,
    context_aware_task,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Demonstrate TaskContext features."""

    logger.info("=" * 70)
    logger.info("CHICORY EXAMPLE 4: Task Context")
    logger.info("=" * 70)

    await app.connect()

    try:
        # ====================================================================
        # 1. Basic context usage - successful task
        # ====================================================================
        logger.info("1. Context-aware task (successful)...")

        result = await context_aware_task.delay(value=42)
        logger.info(f"   Task ID: {result.task_id}")
        logger.info("   Waiting for result...")

        task_result = await result.get(timeout=10.0)
        if task_result is None:
            raise Exception("Task returned None unexpectedly")

        logger.info("   ✓ Task completed successfully")
        logger.info(f"     Value: {task_result['value']}")
        logger.info(f"     Task ID: {task_result['task_id']}")
        logger.info(f"     Attempts: {task_result['attempts']}")

        # ====================================================================
        # 2. Context-aware task that triggers retry
        # ====================================================================
        logger.info("2. Context-aware task with manual retry...")
        logger.info("   (negative value triggers ctx.retry())")

        result = await context_aware_task.delay(value=-10)
        logger.info(f"   Task ID: {result.task_id}")
        logger.info("   Waiting for result (will retry)...")

        try:
            task_result = await result.get(timeout=15.0)
            if task_result is None:
                raise Exception("Task returned None unexpectedly")

            logger.info("   ✓ Task eventually completed (after retries)")
            logger.info(f"     Attempts: {task_result['attempts']}")
        except Exception as e:
            logger.info(f"   ✗ Task failed after retries: {str(e)[:60]}")

        # ====================================================================
        # 3. Conditional retry with custom delay
        # ====================================================================
        logger.info("3. Conditional retry with custom delay...")
        logger.info("   Task checks for required field and retries if missing")

        # First attempt: missing required_field (will retry)
        data_incomplete = {
            "user_id": 123,
            "action": "login",
        }

        result = await conditional_retry_task.delay(data=data_incomplete)
        logger.info(f"   Task ID: {result.task_id}")
        logger.info("   Sent incomplete data (missing 'required_field')")
        logger.info("   Task will retry with 5s delay...")

        try:
            task_result = await result.get(timeout=20.0)
            logger.info(f"   ✗ Unexpected success: {task_result}")
        except Exception as e:
            logger.info("   ✓ Task failed after retries (expected)")
            logger.info(f"     Error: {str(e)[:60]}")

        # Second attempt: with required field (will succeed)
        data_complete = {
            "user_id": 456,
            "action": "purchase",
            "required_field": "present",
        }

        result = await conditional_retry_task.delay(data=data_complete)
        logger.info(f"   Task ID: {result.task_id}")
        logger.info("   Sent complete data (with 'required_field')")
        logger.info("   Waiting for result...")

        task_result = await result.get(timeout=10.0)
        if task_result is None:
            raise Exception("Task returned None unexpectedly")

        logger.info("   ✓ Task completed successfully")
        logger.info(f"     Data keys: {list(task_result['data'].keys())}")

        # ====================================================================
        # 4. Multiple tasks showing retry progression
        # ====================================================================
        logger.info("4. Multiple tasks with different retry behaviors...")

        tasks_config = [
            (10, "will succeed immediately"),
            (-5, "will retry (negative value)"),
            (25, "will succeed immediately"),
            (-15, "will retry (negative value)"),
        ]

        results = []
        for value, description in tasks_config:
            result = await context_aware_task.delay(value=value)
            results.append((result, value, description))
            logger.info(f"   Dispatched task (value={value}): {description}")

        logger.info("   Waiting for all tasks to complete...")

        for result, value, description in results:
            try:
                task_result = await result.get(timeout=20.0)
                logger.info(
                    f"   ✓ Value {value:3d}: {task_result['attempts']} attempt(s)"
                )
            except Exception as e:
                logger.info(f"   ✗ Value {value:3d}: Failed - {str(e)[:40]}")

        # ====================================================================
        # 5. Demonstrating retry state checks
        # ====================================================================
        logger.info("5. Task with retry state monitoring...")
        logger.info("   (The task logs its retry state internally)")

        result = await context_aware_task.delay(value=99)
        logger.info(f"   Task ID: {result.task_id}")

        task_result = await result.get(timeout=10.0)
        logger.info("   ✓ Task completed")
        logger.info("     Check worker logs to see:")
        logger.info("       - Current attempt number")
        logger.info("       - Remaining retries")
        logger.info("       - Last retry flag")

        # ====================================================================
        # 6. Understanding context metadata
        # ====================================================================
        logger.info("6. Task context metadata...")

        result = await context_aware_task.delay(value=777)
        task_result = await result.get(timeout=10.0)
        if task_result is None:
            raise Exception("Task returned None unexpectedly")

        logger.info("   Context information available in tasks:")
        logger.info("     - task_id: Unique identifier for this execution")
        logger.info("     - task_name: Name of the task function")
        logger.info("     - retries: Current retry count (0 for first attempt)")
        logger.info("     - max_retries: Maximum allowed retries")
        logger.info("     - retry_policy: Full retry policy configuration")

        logger.info("   This task's info:")
        logger.info(f"     - task_id: {task_result['task_id']}")
        logger.info(f"     - attempts: {task_result['attempts']}")

        logger.info("=" * 70)
        logger.info("All task context examples completed!")
        logger.info("=" * 70)

        logger.info("Key takeaways:")
        logger.info("  • TaskContext provides runtime metadata and control")
        logger.info("  • Use ctx.retry() for manual retry triggering")
        logger.info("  • Use ctx.retry(countdown=N) for custom retry delays")
        logger.info("  • Check ctx.is_last_retry to handle final attempts specially")
        logger.info("  • Use ctx.remaining_retries to track retry budget")
        logger.info("  • Use ctx.fail() to explicitly fail without retry")

        logger.info("TaskContext signature:")
        logger.info("  @app.task()")
        logger.info("  async def my_task(ctx: TaskContext, arg1: str) -> Result:")
        logger.info("      # ctx is injected automatically")
        logger.info("      # regular args follow")

    finally:
        await app.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
