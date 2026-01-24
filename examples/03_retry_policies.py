"""
Example 3: Retry Policies
==========================

This example demonstrates Chicory's powerful retry mechanisms:
- Exponential backoff
- Fixed backoff
- Linear backoff
- Selective retry based on exception type
- Jitter to prevent thundering herd
- Max retry limits

Prerequisites:
--------------
1. Redis server running on localhost:6379
2. Worker running with DLQ: chicory worker examples.shared_tasks:app --dlq

Usage:
------
    python examples/03_retry_policies.py
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from examples.shared_tasks import (
    always_fails_task,
    app,
    fixed_backoff_task,
    flaky_api_call,
    selective_retry,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Demonstrate retry policy features."""

    logger.info("=" * 70)
    logger.info("CHICORY EXAMPLE 3: Retry Policies")
    logger.info("=" * 70)

    await app.connect()

    try:
        # ====================================================================
        # 1. Exponential backoff with jitter
        # ====================================================================
        logger.info("1. Exponential backoff (may take a few attempts)...")
        logger.info("   Backoff: 1s, 2s, 4s, 8s, 16s (with jitter)")
        logger.info("   Max retries: 5")

        start_time = time.time()
        result = await flaky_api_call.delay(
            url="https://api.example.com/users",
            fail_rate=0.6,  # 60% failure rate
        )

        logger.info(f"   Task dispatched: {result.task_id}")
        logger.info("   Waiting for completion...")

        try:
            api_result = await result.get(timeout=60.0)
            elapsed = time.time() - start_time
            logger.info(f"   ✓ API call succeeded after {elapsed:.1f}s")
            logger.info(f"   Result: {api_result}")
        except Exception as e:
            elapsed = time.time() - start_time
            logger.info(f"   ✗ API call failed after {elapsed:.1f}s: {e}")

        # ====================================================================
        # 2. Fixed backoff retry
        # ====================================================================
        logger.info("2. Fixed backoff (2s delay between each retry)...")
        logger.info("   Backoff: 2s, 2s, 2s")
        logger.info("   Max retries: 3")

        start_time = time.time()
        result = await fixed_backoff_task.delay(task_id="TASK-001")

        logger.info(f"   Task dispatched: {result.task_id}")
        logger.info("   Waiting for completion...")

        try:
            task_result = await result.get(timeout=20.0)
            elapsed = time.time() - start_time
            logger.info(f"   ✓ Task succeeded after {elapsed:.1f}s")
            logger.info(f"   Result: {task_result}")
        except Exception as e:
            elapsed = time.time() - start_time
            logger.info(f"   ✗ Task failed after {elapsed:.1f}s: {e}")

        # ====================================================================
        # 3. Selective retry - retryable exception
        # ====================================================================
        logger.info("3. Selective retry - ConnectionError (will retry)...")
        logger.info("   Only retries: ConnectionError, TimeoutError")
        logger.info("   Ignores: ValueError, KeyError")

        start_time = time.time()
        result = await selective_retry.delay(operation="connection_error")

        logger.info(f"   Task dispatched: {result.task_id}")
        logger.info("   Waiting for completion...")

        try:
            task_result = await result.get(timeout=15.0)
            elapsed = time.time() - start_time
            logger.info(f"   ✓ Task succeeded after {elapsed:.1f}s")
        except Exception as e:
            elapsed = time.time() - start_time
            logger.info(f"   ✗ Task failed after retries ({elapsed:.1f}s)")
            logger.info(f"     Error: {str(e)[:80]}")

        # ====================================================================
        # 4. Selective retry - non-retryable exception
        # ====================================================================
        logger.info("4. Selective retry - ValueError (will NOT retry)...")

        start_time = time.time()
        result = await selective_retry.delay(operation="value_error")

        logger.info(f"   Task dispatched: {result.task_id}")
        logger.info("   Waiting for result (should fail quickly)...")

        try:
            task_result = await result.get(timeout=10.0)
            elapsed = time.time() - start_time
            logger.info(f"   ✗ Unexpected success after {elapsed:.1f}s")
        except Exception as e:
            elapsed = time.time() - start_time
            logger.info(f"   ✓ Task failed immediately ({elapsed:.1f}s, expected)")
            logger.info("     ValueError is not retryable, sent to DLQ")
            logger.info(f"     Error: {str(e)[:80]}")

        # ====================================================================
        # 5. Max retries exceeded - goes to DLQ
        # ====================================================================
        logger.info("5. Task that always fails (goes to Dead Letter Queue)...")
        logger.info("   Max retries: 2")

        start_time = time.time()
        result = await always_fails_task.delay(reason="Testing DLQ behavior")

        logger.info(f"   Task dispatched: {result.task_id}")
        logger.info("   Waiting for result (will fail after retries)...")

        try:
            task_result = await result.get(timeout=15.0)
            elapsed = time.time() - start_time
            logger.info(f"   ✗ Unexpected success: {task_result}")
        except Exception as e:
            elapsed = time.time() - start_time
            logger.info(f"   ✓ Task failed after retries ({elapsed:.1f}s)")
            logger.info("     Task moved to Dead Letter Queue (DLQ)")
            logger.info(f"     Error: {str(e)[:80]}")

        # ====================================================================
        # 6. Multiple concurrent tasks with retries
        # ====================================================================
        logger.info("6. Multiple concurrent tasks with retries...")

        start_time = time.time()

        # Dispatch multiple flaky tasks
        results = [
            await flaky_api_call.delay(
                url=f"https://api.example.com/resource/{i}",
                fail_rate=0.5,  # 50% failure rate
            )
            for i in range(5)
        ]

        logger.info(f"   Dispatched {len(results)} tasks")
        logger.info(f"   Task IDs: {[r.task_id for r in results]}")
        logger.info("   Waiting for all to complete...")

        # Wait for all with timeout
        try:
            gathered_results = await asyncio.gather(
                *[r.get(timeout=60.0) for r in results],
                return_exceptions=True,
            )

            elapsed = time.time() - start_time
            successes = sum(1 for r in gathered_results if not isinstance(r, Exception))
            failures = len(gathered_results) - successes

            logger.info(f"   Completed in {elapsed:.1f}s")
            logger.info(f"   ✓ Successful: {successes}/{len(results)}")
            logger.info(f"   ✗ Failed: {failures}/{len(results)}")
        except Exception as e:
            logger.info(f"   ✗ Error: {e}")

        logger.info("=" * 70)
        logger.info("All retry policy examples completed!")
        logger.info("=" * 70)

        logger.info("Key takeaways:")
        logger.info("  • Exponential backoff prevents overwhelming services")
        logger.info("  • Jitter prevents thundering herd problems")
        logger.info(
            "  • Selective retry policies control which exceptions trigger retries"
        )
        logger.info("  • Failed tasks (after max retries) go to Dead Letter Queue")
        logger.info("  • Different backoff strategies for different use cases")

        logger.info("Note: Check your worker logs to see retry attempts in action!")

    finally:
        await app.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
