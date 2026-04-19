from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import redis.asyncio
from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker

sys.path.insert(0, str(Path(__file__).parent.parent))

from framework.config import BenchmarkConfig, WorkloadType
from framework.metrics import BenchmarkResult, MetricsCollector

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("bench_taskiq")

broker = RedisStreamBroker(
    "redis://localhost:6379/0",
    unacknowledged_batch_size=10,
).with_result_backend(
    RedisAsyncResultBackend(
        "redis://localhost:6379/1",
        result_ex_time=3600,
    )
)


@broker.task(name="bench.increment")
async def increment(value: int) -> int:
    return value + 1


@broker.task(name="bench.cpu_bound")
async def cpu_bound(value: int) -> int:
    result = value
    for _ in range(10000):
        result = (result * 31 + 17) % 1000000007
    return result


@broker.task(name="bench.io_bound")
async def io_bound(value: int) -> int:
    await asyncio.sleep(0.01)
    return value * 2


_WORKLOAD_TASKS = {
    WorkloadType.INCREMENT: increment,
    WorkloadType.CPU_BOUND: cpu_bound,
    WorkloadType.IO_BOUND: io_bound,
}


async def _flush_redis() -> None:
    """Flush both Redis db 0 (broker) and db 1 (backend)."""
    for db in (0, 1):
        async with redis.asyncio.from_url(
            f"redis://localhost:6379/{db}", decode_responses=True
        ) as client:
            await client.flushdb()
    logger.debug("Redis db 0 and 1 flushed")


async def _run_batch(
    task_count: int,
    workload_type: WorkloadType,
) -> BenchmarkResult:
    task_func = _WORKLOAD_TASKS[workload_type]
    loop = asyncio.get_running_loop()

    # startup per batch — FLUSHDB between batches destroys consumer groups
    await broker.startup()

    logger.info("enqueuing tasks...")
    enqueue_start = loop.time()
    enqueue_results = await asyncio.gather(
        *[task_func.kiq(i) for i in range(task_count)]
    )
    enqueue_end = loop.time()
    enqueue_time = enqueue_end - enqueue_start
    logger.info(f"enqueuing done in {enqueue_time:.3f}s")

    logger.info("retrieving results...")
    dequeue_start = loop.time()
    retrieved_values = await asyncio.gather(
        *[r.wait_result(timeout=200, check_interval=0.1) for r in enqueue_results]
    )
    dequeue_end = loop.time()
    dequeue_time = dequeue_end - dequeue_start
    logger.info(f"retrieving done in {dequeue_time:.3f}s")

    await broker.shutdown()

    success_count = 0
    failure_count = 0
    invalid_count = 0
    for val in retrieved_values:
        if val is None or val.is_err:
            if val is None:
                invalid_count += 1
            else:
                failure_count += 1
        else:
            success_count += 1

    if invalid_count > 0:
        logger.warning(f"found {invalid_count} invalid results")

    return BenchmarkResult(
        task_count=task_count,
        workload_type=workload_type.value,
        enqueue_time=enqueue_time,
        dequeue_time=dequeue_time,
        success_count=success_count,
        failure_count=failure_count,
        invalid_count=invalid_count,
    )


async def main_async(
    tasks: list[int],
    workload_types: list[WorkloadType],
    enable_prometheus: bool = True,
) -> None:
    config = BenchmarkConfig(
        tasks_counts=tasks,
        workload_types=workload_types,
        enable_prometheus=enable_prometheus,
        prometheus_port=9091,
    )
    metrics = MetricsCollector(
        enable_prometheus=enable_prometheus,
        port=config.prometheus_port,
    )

    if enable_prometheus:
        metrics.start_prometheus_server()

    for workload_type in workload_types:
        logger.info(f"=== Running TaskIQ benchmark for {workload_type.value} ===")

        for task_count in tasks:
            logger.info(f"starting benchmark for {task_count} tasks...")
            result = await _run_batch(task_count, workload_type)
            metrics.record_result(result, "taskiq")
            logger.info(
                f"tasks: {task_count:>6}, enqueue: {result.enqueue_time:>8.3f}s, "
                f"dequeue: {result.dequeue_time:>8.3f}s, "
                f"throughput: {result.throughput:>8.2f} tasks/s"
            )
            await _flush_redis()

    metrics.log_results("taskiq")

    if enable_prometheus:
        logger.info("Waiting 30s for Prometheus to scrape final metrics...")
        await asyncio.sleep(30)


def main() -> None:
    tasks = [8, 16, 32, 64, 128, 256, 1024, 2048, 4096, 8192, 16384]
    workload_types = [
        WorkloadType.INCREMENT,
        WorkloadType.CPU_BOUND,
        WorkloadType.IO_BOUND,
    ]

    parser = argparse.ArgumentParser(description="Run TaskIQ benchmarks")
    parser.add_argument(
        "--no-prometheus", action="store_true", help="Disable Prometheus metrics"
    )
    parser.add_argument(
        "--workload",
        type=str,
        default="increment",
        choices=["increment", "cpu_bound", "io_bound", "all"],
        help="Workload type to run",
    )
    args = parser.parse_args()

    if args.workload == "all":
        workloads = workload_types
    else:
        workloads = [WorkloadType(args.workload)]

    asyncio.run(main_async(tasks, workloads, enable_prometheus=not args.no_prometheus))


if __name__ == "__main__":
    main()
