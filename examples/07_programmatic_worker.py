"""
Example 7: Programmatic Worker
===============================

This example demonstrates running a worker programmatically within your application,
rather than using the CLI. This is useful for:
- Testing
- Embedding workers in your application
- Custom worker lifecycle management
- Integration with your existing async application

This is the ONLY example that doesn't require a separate worker process.

Prerequisites:
--------------
1. Redis server running on localhost:6379

Usage:
------
    python examples/07_programmatic_worker.py
"""

import asyncio
import logging
from datetime import UTC, datetime

from chicory import (
    BackendType,
    BrokerType,
    Chicory,
    ValidationMode,
    Worker,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ============================================================================
# Define tasks inline (normally would import from shared module)
# ============================================================================

app = Chicory(
    broker=BrokerType.REDIS,
    backend=BackendType.REDIS,
    validation_mode=ValidationMode.INPUTS,
)


@app.task(name="inline.add")
async def add(x: int, y: int) -> int:
    """Simple addition task."""
    logger.info(f"[Worker] Computing {x} + {y}")
    await asyncio.sleep(0.5)  # Simulate work
    return x + y


@app.task(name="inline.process")
async def process_item(item_id: int, data: str) -> dict:
    """Process an item."""
    logger.info(f"[Worker] Processing item {item_id}: {data}")
    await asyncio.sleep(1.0)  # Simulate work

    return {
        "item_id": item_id,
        "data": data.upper(),
        "processed_at": datetime.now(UTC).isoformat(),
    }


@app.task(name="inline.greet")
async def greet(name: str) -> str:
    """Greet someone."""
    greeting = f"Hello, {name}!"
    logger.info(f"[Worker] {greeting}")
    return greeting


# ============================================================================
# Worker functions
# ============================================================================


async def run_worker_for_duration(duration: int = 10):
    """
    Run a worker for a specific duration, then stop.

    This pattern is useful for testing or temporary workers.
    """
    logger.info("=" * 70)
    logger.info("CHICORY EXAMPLE 7: Programmatic Worker")
    logger.info("=" * 70)

    logger.info("This example runs a worker programmatically (no CLI needed)")

    # Connect to broker and backend
    await app.connect()

    try:
        # Create worker instance
        worker = Worker(app)

        logger.info(f"Worker ID: {worker.worker_id}")
        logger.info(f"Concurrency: {worker.concurrency}")
        logger.info(f"Queue: {worker.queue}")

        # Start worker (non-blocking)
        logger.info(f"Starting worker for {duration} seconds...")
        await worker.start()

        logger.info("✓ Worker started")

        # Dispatch some tasks while worker is running
        logger.info("Dispatching tasks...")

        # Task 1: Simple addition
        result1 = await add.delay(10, 20)
        logger.info(f"  • Task 1 (add): {result1.task_id}")

        # Task 2: Process items
        result2 = await process_item.delay(item_id=1, data="important data")
        logger.info(f"  • Task 2 (process): {result2.task_id}")

        # Task 3: Greet
        result3 = await greet.delay(name="Alice")
        logger.info(f"  • Task 3 (greet): {result3.task_id}")

        logger.info("Tasks dispatched. Worker is processing them...")

        # Wait a bit for tasks to be processed
        await asyncio.sleep(3)

        # Check results
        logger.info("Checking results...")
        try:
            res1 = await result1.get(timeout=2.0)
            logger.info(f"  ✓ Task 1 result: {res1}")
        except TimeoutError:
            logger.info("  ⏳ Task 1 still processing...")

        try:
            res2 = await result2.get(timeout=2.0)
            logger.info(f"  ✓ Task 2 result: {res2}")
        except TimeoutError:
            logger.info("  ⏳ Task 2 still processing...")

        try:
            res3 = await result3.get(timeout=2.0)
            logger.info(f"  ✓ Task 3 result: {res3}")
        except TimeoutError:
            logger.info("  ⏳ Task 3 still processing...")

        # Get worker stats
        stats = worker.get_stats()
        logger.info("Worker statistics:")
        logger.info(f"  • Tasks processed: {stats.tasks_processed}")
        logger.info(f"  • Tasks failed: {stats.tasks_failed}")
        logger.info(f"  • Active tasks: {stats.active_tasks}")
        logger.info(f"  • Uptime: {stats.uptime_seconds:.1f}s")

        # Wait for remaining duration
        remaining = duration - 3
        if remaining > 0:
            logger.info(f"Worker will run for {remaining} more seconds...")
            await asyncio.sleep(remaining)

        # Stop worker gracefully
        logger.info("Stopping worker...")
        await worker.stop(timeout=5.0)
        logger.info("✓ Worker stopped")

    finally:
        await app.disconnect()


async def run_worker_with_signal_handling():
    """
    Run a worker with proper signal handling.

    This pattern is useful for production deployments where you want
    graceful shutdown on SIGINT/SIGTERM.
    """
    logger.info("=" * 70)
    logger.info("Running worker with signal handling (Press Ctrl+C to stop)")
    logger.info("=" * 70)

    # Connect to broker and backend
    await app.connect()

    try:
        # Create worker instance
        worker = Worker(app)

        logger.info(f"Worker ID: {worker.worker_id}")
        logger.info(f"Concurrency: {worker.concurrency}")

        # Dispatch some tasks before starting worker
        logger.info("Pre-dispatching tasks for the worker...")
        results = []
        for i in range(5):
            result = await add.delay(i, i * 2)
            results.append(result)
            logger.info(f"  • Task {i + 1}: {result.task_id}")

        logger.info("Starting worker (will process tasks)...")
        logger.info("Press Ctrl+C to stop gracefully")

        # Run worker (blocking, with signal handling)
        # This will handle SIGINT (Ctrl+C) and SIGTERM automatically
        try:
            await worker.run()
        except KeyboardInterrupt:
            logger.info("\nKeyboard interrupt received")

        logger.info("Worker stopped")

        # Check if our tasks completed
        logger.info("Checking task results...")
        for i, result in enumerate(results):
            try:
                if await result.ready():
                    res = await result.get(timeout=1.0)
                    logger.info(f"  ✓ Task {i + 1}: {res}")
                else:
                    logger.info(f"  ⏳ Task {i + 1}: Not completed")
            except Exception as e:
                logger.info(f"  ✗ Task {i + 1}: {e}")

    finally:
        await app.disconnect()


async def run_worker_in_background():
    """
    Run a worker in the background while doing other work.

    This pattern is useful when you want to embed a worker in your
    application alongside other async operations.
    """
    logger.info("=" * 70)
    logger.info("Running worker in background")
    logger.info("=" * 70)

    # Connect to broker and backend
    await app.connect()

    try:
        # Create and start worker
        worker = Worker(app)
        await worker.start()

        logger.info("✓ Worker started in background")
        logger.info(f"  Worker ID: {worker.worker_id}")

        # Simulate application doing other work while worker runs
        logger.info("Application is running, dispatching tasks periodically...")

        try:
            for round_num in range(1, 4):
                logger.info(f"Round {round_num}: Dispatching tasks")

                # Dispatch some tasks
                results = []
                for i in range(3):
                    result = await add.delay(round_num * 10 + i, i)
                    results.append(result)

                logger.info(f"  Dispatched {len(results)} tasks")

                # Do other work while tasks are being processed
                logger.info("  Doing other application work...")
                await asyncio.sleep(2)

                # Check results
                ready_states = await asyncio.gather(*[r.ready() for r in results])
                completed = sum(1 for ready in ready_states if ready)
                logger.info(f"  ✓ {completed}/{len(results)} tasks completed")

                # Get worker stats
                stats = worker.get_stats()
                logger.info(
                    f"  Worker: {stats.tasks_processed} processed, "
                    f"{stats.active_tasks} active"
                )

                await asyncio.sleep(1)

        finally:
            # Clean shutdown
            logger.info("Shutting down worker...")
            await worker.stop(timeout=5.0)
            logger.info("✓ Worker stopped")

    finally:
        await app.disconnect()


async def main():
    """Main entry point - choose which pattern to demonstrate."""

    # You can run any of these patterns:

    # Pattern 1: Worker runs for fixed duration
    await run_worker_for_duration(duration=15)

    # Pattern 2: Worker with signal handling (uncomment to try)
    # await run_worker_with_signal_handling()

    # Pattern 3: Worker in background (uncomment to try)
    # await run_worker_in_background()

    logger.info("=" * 70)
    logger.info("Programmatic worker example completed!")
    logger.info("=" * 70)

    logger.info("Key takeaways:")
    logger.info("  • Create Worker instance: worker = Worker(app)")
    logger.info("  • Start worker: await worker.start()")
    logger.info("  • Stop worker: await worker.stop()")
    logger.info("  • Run with signals: await worker.run()  # Blocking")
    logger.info("  • Get stats: worker.get_stats()")

    logger.info("Use cases:")
    logger.info("  • Testing: Run worker in test fixtures")
    logger.info("  • Embedded: Run worker within your application")
    logger.info("  • Custom lifecycle: Full control over start/stop")
    logger.info("  • Development: Quick testing without CLI")

    logger.info("For production, prefer the CLI:")
    logger.info("  chicory worker examples.shared_tasks:app --concurrency 8")


if __name__ == "__main__":
    asyncio.run(main())
