from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, TypeVar

import redis.asyncio

from framework.metrics import BenchmarkResult, MetricsCollector

if TYPE_CHECKING:
    from framework.config import BenchmarkConfig, WorkloadType

logger = logging.getLogger("benchmark_runner")

T = TypeVar("T")


class BrokerAdapter[T](ABC):
    @abstractmethod
    async def connect(self) -> None:
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        pass

    @abstractmethod
    async def enqueue_task(self, task: Any, *args: Any, **kwargs: Any) -> Any:
        pass

    @abstractmethod
    async def get_result(
        self, result: Any, timeout: float, poll_interval: float
    ) -> Any:
        pass


class BenchmarkRunner:
    def __init__(
        self,
        config: BenchmarkConfig,
        metrics_collector: MetricsCollector,
    ) -> None:
        self.config = config
        self.metrics = metrics_collector

    async def run_workload(
        self,
        broker: BrokerAdapter[Any],
        workload_type: WorkloadType,
        task_count: int,
        enqueue_func: Any,
        result_func: Any,
    ) -> BenchmarkResult:
        loop = asyncio.get_event_loop()

        logger.info(f"Running workload {workload_type.value} with {task_count} tasks")

        logger.info("Enqueuing tasks...")
        await broker.connect()
        enqueue_start = loop.time()

        try:
            enqueue_results = await asyncio.gather(
                *[enqueue_func(i) for i in range(task_count)]
            )
        except Exception as e:
            logger.error(f"Enqueue failed: {e}")
            await broker.disconnect()
            raise

        enqueue_end = loop.time()
        enqueue_time = enqueue_end - enqueue_start
        logger.info(f"Enqueuing done in {enqueue_time:.3f}s")

        logger.info("Retrieving results...")
        dequeue_start = loop.time()

        try:
            retrieved_values = await asyncio.gather(
                *[
                    result_func(
                        res, self.config.result_timeout, self.config.poll_interval
                    )
                    for res in enqueue_results
                ]
            )
        except Exception as e:
            logger.error(f"Result retrieval failed: {e}")
            await broker.disconnect()
            raise

        dequeue_end = loop.time()
        dequeue_time = dequeue_end - dequeue_start
        logger.info(f"Retrieving done in {dequeue_time:.3f}s")

        await broker.disconnect()

        success_count = 0
        failure_count = 0
        invalid_count = 0

        for result in retrieved_values:
            if result is None:
                invalid_count += 1
            elif (
                isinstance(result, Exception)
                or hasattr(result, "is_err")
                and result.is_err
            ):
                failure_count += 1
            else:
                success_count += 1

        benchmark_result = BenchmarkResult(
            task_count=task_count,
            workload_type=workload_type.value,
            enqueue_time=enqueue_time,
            dequeue_time=dequeue_time,
            success_count=success_count,
            failure_count=failure_count,
            invalid_count=invalid_count,
        )

        if invalid_count > 0:
            logger.warning(f"Found {invalid_count} invalid results")
        else:
            logger.debug("All results are valid")

        return benchmark_result

    async def run_benchmark(
        self,
        broker: BrokerAdapter[Any],
        workload_type: WorkloadType,
        task_counts: list[int] | None = None,
        enqueue_func: Any = None,
        result_func: Any = None,
    ) -> list[BenchmarkResult]:
        if task_counts is None:
            task_counts = self.config.tasks_counts

        results: list[BenchmarkResult] = []

        for task_count in task_counts:
            if self.config.warmup_tasks > 0 and enqueue_func and result_func:
                logger.info(f"Warming up with {self.config.warmup_tasks} tasks...")
                await self.run_workload(
                    broker,
                    workload_type,
                    self.config.warmup_tasks,
                    enqueue_func,
                    result_func,
                )
                if self.config.warmup_delay > 0:
                    await asyncio.sleep(self.config.warmup_delay)

            result = await self.run_workload(
                broker,
                workload_type,
                task_count,
                enqueue_func,
                result_func,
            )
            results.append(result)

            if self.config.clear_between_runs:
                await self._clear_redis()

            if self.config.reconnect_delay > 0:
                await asyncio.sleep(self.config.reconnect_delay)

        return results

    async def _clear_redis(self) -> None:
        try:
            for db in (0, 1):
                url = f"{self.config.redis_url.rstrip('/')}/{db}"
                async with redis.asyncio.from_url(url, decode_responses=True) as client:
                    await client.flushdb()
            logger.debug("Redis db 0 and 1 cleared")
        except Exception as e:
            logger.warning(f"Failed to clear Redis: {e}")


async def run_benchmark_for_target(
    target: str,
    config: BenchmarkConfig,
    metrics: MetricsCollector,
    broker: BrokerAdapter[Any],
    enqueue_func: Any,
    result_func: Any,
    workload_types: list[WorkloadType] | None = None,
) -> None:
    if workload_types is None:
        workload_types = config.workload_types

    runner = BenchmarkRunner(config, metrics)

    for workload_type in workload_types:
        logger.info(f"=== Running {target} benchmark for {workload_type.value} ===")

        results = await runner.run_benchmark(
            broker=broker,
            workload_type=workload_type,
            enqueue_func=enqueue_func,
            result_func=result_func,
        )

        for result in results:
            metrics.record_result(result, target)


def create_redis_clear_func(redis_url: str):
    async def clear_redis() -> None:
        async with redis.asyncio.from_url(redis_url, decode_responses=True) as client:
            await client.flushdb()

    return clear_redis
