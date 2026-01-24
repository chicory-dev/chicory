"""
Example 6: Batch Processing
============================

This example demonstrates batch processing patterns with Chicory:
- Dispatching multiple tasks at once
- Processing items in parallel
- Collecting and aggregating results
- Progress tracking
- Fan-out/fan-in pattern

Prerequisites:
--------------
1. Redis server running on localhost:6379
2. Worker running: chicory worker examples.shared_tasks:app --concurrency 8

Usage:
------
    python examples/06_batch_processing.py
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from examples.shared_tasks import (
    add,
    aggregate_results,
    app,
    multiply,
    process_batch_item,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Demonstrate batch processing patterns."""

    logger.info("=" * 70)
    logger.info("CHICORY EXAMPLE 6: Batch Processing")
    logger.info("=" * 70)

    await app.connect()

    try:
        # ====================================================================
        # 1. Simple batch processing
        # ====================================================================
        logger.info("1. Simple batch processing (Fan-out pattern)...")

        # Create a batch of items to process
        batch_size = 20
        items = [(i, f"item_data_{i}") for i in range(batch_size)]

        logger.info(f"   Processing batch of {batch_size} items...")
        start_time = time.time()

        # Dispatch all tasks
        results = []
        for item_id, data in items:
            result = await process_batch_item.delay(item_id=item_id, data=data)
            results.append(result)

        dispatch_time = time.time() - start_time
        logger.info(f"   ✓ Dispatched {len(results)} tasks in {dispatch_time:.3f}s")
        logger.info("   Waiting for completion...")

        # Wait for all results
        completed_results = await asyncio.gather(
            *[r.get(timeout=30.0) for r in results],
            return_exceptions=True,
        )

        total_time = time.time() - start_time
        successes = sum(1 for r in completed_results if not isinstance(r, Exception))

        logger.info(
            f"   ✓ Completed {successes}/{len(results)} tasks in {total_time:.3f}s"
        )
        logger.info(f"   Average time per task: {total_time / len(results):.3f}s")

        # ====================================================================
        # 2. Batch processing with progress tracking
        # ====================================================================
        logger.info("2. Batch processing with progress tracking...")

        batch_size = 30
        items = [(i, f"data_{i}") for i in range(batch_size)]

        logger.info(f"   Processing {batch_size} items with progress updates...")
        start_time = time.time()

        # Dispatch all tasks
        results = [
            await process_batch_item.delay(item_id=i, data=data) for i, data in items
        ]

        logger.info("   Tasks dispatched, monitoring progress...")

        # Poll for completion with progress updates
        completed = 0
        last_progress = 0

        while completed < len(results):
            await asyncio.sleep(0.5)  # Check every 500ms

            # Count completed tasks
            ready_states = await asyncio.gather(*[r.ready() for r in results])
            completed = sum(1 for ready in ready_states if ready)

            # Show progress every 20%
            progress = int((completed / len(results)) * 100)
            if progress >= last_progress + 20:
                elapsed = time.time() - start_time
                logger.info(
                    f"   Progress: {progress}% ({completed}/{len(results)}) "
                    f"- {elapsed:.1f}s"
                )
                last_progress = progress

        total_time = time.time() - start_time

        logger.info(f"   ✓ All tasks completed in {total_time:.2f}s")

        # ====================================================================
        # 3. Fan-out/Fan-in pattern with aggregation
        # ====================================================================
        logger.info("3. Fan-out/Fan-in pattern with result aggregation...")

        batch_size = 15
        items = [(i, f"record_{i}") for i in range(batch_size)]

        logger.info(f"   Step 1: Fan-out - Process {batch_size} items in parallel")
        start_time = time.time()

        # Fan-out: Process items in parallel
        process_results = []
        for item_id, data in items:
            result = await process_batch_item.delay(item_id=item_id, data=data)
            process_results.append(result)

        # Wait for all processing to complete
        processed_items = await asyncio.gather(
            *[r.get(timeout=30.0) for r in process_results],
            return_exceptions=True,
        )

        # Filter out any errors
        valid_results = [r for r in processed_items if not isinstance(r, Exception)]

        fan_out_time = time.time() - start_time
        logger.info(f"   ✓ Processed {len(valid_results)} items in {fan_out_time:.2f}s")

        logger.info("   Step 2: Fan-in - Aggregate results")

        # Fan-in: Aggregate results
        aggregate_result = await aggregate_results.delay(results=valid_results)
        aggregated = await aggregate_result.get(timeout=10.0)
        if aggregated is None:
            raise Exception("Task returned None unexpectedly")

        total_time = time.time() - start_time
        logger.info("   ✓ Aggregation complete")
        logger.info(f"   Total items: {aggregated['total_items']}")
        logger.info(f"   Processed: {aggregated['summary']['processed']}")
        logger.info(f"   Total time: {total_time:.2f}s")

        # ====================================================================
        # 4. Batched mathematical operations
        # ====================================================================
        logger.info("4. Batch mathematical operations...")

        # Generate computation pairs
        computations = [(i, i * 2) for i in range(1, 11)]

        logger.info(f"   Computing {len(computations)} additions in parallel...")

        # Dispatch all addition tasks
        add_results = [await add.delay(x, y) for x, y in computations]

        # Wait for results
        additions = await asyncio.gather(*[r.get(timeout=10.0) for r in add_results])

        logger.info(f"   ✓ Addition results: {additions}")

        # Now multiply all results by a constant
        logger.info("   Multiplying all results by 10...")

        multiply_results = [await multiply.delay(result, 10) for result in additions]

        multiplications = await asyncio.gather(
            *[r.get(timeout=10.0) for r in multiply_results]
        )

        logger.info(f"   ✓ Multiplication results: {multiplications}")

        # ====================================================================
        # 5. Chunked batch processing
        # ====================================================================
        logger.info("5. Chunked batch processing (for very large batches)...")

        total_items = 50
        chunk_size = 10

        logger.info(f"   Processing {total_items} items in chunks of {chunk_size}")

        all_results = []
        start_time = time.time()

        # Process in chunks
        for chunk_num in range(0, total_items, chunk_size):
            chunk_end = min(chunk_num + chunk_size, total_items)
            chunk_items = [(i, f"chunk_data_{i}") for i in range(chunk_num, chunk_end)]

            logger.info(
                f"   Chunk {chunk_num // chunk_size + 1}: "
                f"Processing items {chunk_num}-{chunk_end - 1}..."
            )

            # Dispatch chunk
            chunk_results = [
                await process_batch_item.delay(item_id=i, data=data)
                for i, data in chunk_items
            ]

            # Wait for chunk to complete before next chunk
            chunk_completed = await asyncio.gather(
                *[r.get(timeout=30.0) for r in chunk_results],
                return_exceptions=True,
            )

            all_results.extend(chunk_completed)

            successes = sum(1 for r in chunk_completed if not isinstance(r, Exception))
            logger.info(f"     ✓ Completed {successes}/{len(chunk_results)} tasks")

        total_time = time.time() - start_time

        logger.info("   ✓ All chunks processed")
        logger.info(f"   Total items: {len(all_results)}")
        logger.info(f"   Total time: {total_time:.2f}s")

        # ====================================================================
        # 6. Batch processing with error handling
        # ====================================================================
        logger.info("6. Batch processing with error handling...")

        from examples.shared_tasks import sometimes_fails_task

        batch_size = 20
        logger.info(f"   Processing {batch_size} tasks (some may fail randomly)...")

        start_time = time.time()

        # Dispatch tasks with 70% success rate
        results = [
            await sometimes_fails_task.delay(success_rate=0.7)
            for _ in range(batch_size)
        ]

        # Wait for all (including failures)
        completed = await asyncio.gather(
            *[r.get(timeout=20.0) for r in results],
            return_exceptions=True,
        )

        total_time = time.time() - start_time

        # Separate successes and failures
        successes = [r for r in completed if not isinstance(r, Exception)]
        failures = [r for r in completed if isinstance(r, Exception)]

        logger.info(f"   ✓ Batch completed in {total_time:.2f}s")
        logger.info(f"     Successes: {len(successes)}/{batch_size}")
        logger.info(f"     Failures: {len(failures)}/{batch_size}")

        # Process only successes
        if successes:
            logger.info(f"   Processing {len(successes)} successful results...")
            # Do something with successful results
            logger.info("   ✓ Processed successful results")

        if failures:
            logger.info(f"   ⚠️  {len(failures)} tasks failed (logged for retry)")

        logger.info("=" * 70)
        logger.info("All batch processing examples completed!")
        logger.info("=" * 70)

        logger.info("Key takeaways:")
        logger.info("  • Fan-out: Dispatch many tasks in parallel")
        logger.info("  • Use asyncio.gather() to wait for multiple results")
        logger.info("  • Poll task.ready() for progress tracking")
        logger.info("  • Fan-in: Aggregate results in a separate task")
        logger.info("  • Process large batches in chunks to avoid overwhelming system")
        logger.info("  • Use return_exceptions=True to handle partial failures")
        logger.info("  • Set appropriate worker concurrency for batch workloads")

        logger.info("Performance tips:")
        logger.info("  • Increase worker concurrency for I/O-bound tasks")
        logger.info("  • Use chunking for very large batches")
        logger.info("  • Consider AT_MOST_ONCE delivery for non-critical batch jobs")
        logger.info("  • Monitor worker resources (CPU, memory)")

    finally:
        await app.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
