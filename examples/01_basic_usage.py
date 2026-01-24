"""
Example 1: Basic Task Execution
================================

This example demonstrates the fundamental usage of Chicory:
- Importing and using tasks
- Dispatching tasks asynchronously with .delay()
- Fire-and-forget with .send()
- Waiting for task results with .get()
- Checking task status

Prerequisites:
--------------
1. Redis server running on localhost:6379
2. Worker running: chicory worker examples.shared_tasks:app

Usage:
------
    python examples/01_basic_usage.py
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from examples.shared_tasks import add, app, greet, multiply, process_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Demonstrate basic task execution patterns."""

    logger.info("=" * 70)
    logger.info("CHICORY EXAMPLE 1: Basic Task Execution")
    logger.info("=" * 70)

    # Connect to broker and backend
    await app.connect()

    try:
        # ====================================================================
        # 1. Simple task with result retrieval
        # ====================================================================
        logger.info("1. Dispatching a simple addition task...")
        result = await add.delay(10, 32)
        logger.info(f"   Task ID: {result.task_id}")
        logger.info("   Waiting for result...")

        answer = await result.get(timeout=10.0)
        logger.info(f"   Result: 10 + 32 = {answer}")

        # ====================================================================
        # 2. Fire-and-forget (no result retrieval)
        # ====================================================================
        logger.info("2. Fire-and-forget task...")
        task_id = await multiply.send(5, 8)
        logger.info(f"   Task sent with ID: {task_id}")
        logger.info("   Not waiting for result (fire-and-forget)")

        # ====================================================================
        # 3. Multiple concurrent tasks
        # ====================================================================
        logger.info("3. Dispatching multiple tasks concurrently...")
        tasks = [await add.delay(i, i * 2) for i in range(1, 6)]

        logger.info(f"   Dispatched {len(tasks)} tasks")
        logger.info(f"   Task IDs: {[t.task_id for t in tasks]}")
        logger.info("   Waiting for all results...")

        results = await asyncio.gather(*[t.get(timeout=10.0) for t in tasks])
        logger.info(f"   Results: {results}")

        # ====================================================================
        # 4. Checking task state
        # ====================================================================
        logger.info("4. Checking task state...")
        result = await add.delay(100, 200)

        logger.info(f"   Task ID: {result.task_id}")

        # Check state before completion
        state = await result.state()
        logger.info(f"   Initial state: {state}")

        # Wait for completion
        answer = await result.get(timeout=10.0)

        # Check state after completion
        state = await result.state()
        logger.info(f"   Final state: {state}")
        logger.info(f"   Result: {answer}")

        # Check if ready and if failed
        is_ready = await result.ready()
        has_failed = await result.failed()
        logger.info(f"   Is ready: {is_ready}")
        logger.info(f"   Has failed: {has_failed}")

        # ====================================================================
        # 5. Working with strings
        # ====================================================================
        logger.info("5. String processing task...")
        result = await greet.delay("Alice")
        greeting = await result.get(timeout=10.0)
        logger.info(f"   {greeting}")

        # ====================================================================
        # 6. Working with complex data types
        # ====================================================================
        logger.info("6. Complex data type handling...")
        data = {
            "user_id": 42,
            "action": "purchase",
            "items": ["book", "pen", "notebook"],
            "total": 29.99,
        }

        result = await process_data.delay(data)
        processed = await result.get(timeout=10.0)
        logger.info(f"   Original data: {data}")
        logger.info("   Processed result:")
        for key, value in processed.items():
            logger.info(f"     - {key}: {value}")

        # ====================================================================
        # 7. Task timeout handling
        # ====================================================================
        logger.info("7. Task timeout handling...")
        from examples.shared_tasks import long_running_task

        result = await long_running_task.delay(3)
        logger.info("   Started long-running task (3 seconds)")
        logger.info(f"   Task ID: {result.task_id}")

        try:
            # Try to get result with short timeout
            answer = await result.get(timeout=1.0)
            logger.info(f"   Result: {answer}")
        except TimeoutError:
            logger.info("   ⚠️  Timeout after 1 second (expected)")
            logger.info("   Task is still running...")

            # Now wait with longer timeout
            logger.info("   Waiting with longer timeout (5 seconds)...")
            answer = await result.get(timeout=5.0)
            logger.info(f"   ✓ Task completed: {answer}")

        logger.info("=" * 70)
        logger.info("All examples completed successfully!")
        logger.info("=" * 70)

    finally:
        # Always disconnect
        await app.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
