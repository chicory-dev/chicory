from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

from framework.config import WorkloadType


def create_increment_task() -> Callable[[int], int]:
    async def increment(value: int) -> int:
        return value + 1

    return increment


def create_cpu_workload_task(iterations: int = 10000) -> Callable[[int], int]:
    async def cpu_bound(value: int) -> int:
        result = value
        for _ in range(iterations):
            result = (result * 31 + 17) % 1000000007
        return result

    return cpu_bound


def create_io_workload_task(delay: float = 0.01) -> Callable[[int], int]:
    async def io_bound(value: int) -> int:
        await asyncio.sleep(delay)
        return value * 2

    return io_bound


def create_retry_task(
    fail_until_attempt: int = 3,
) -> Callable[[int], int]:
    attempt_counter: dict[str, int] = {}

    async def retry_task(value: int) -> int:
        key = f"retry_{value}"
        attempt_counter[key] = attempt_counter.get(key, 0) + 1
        if attempt_counter[key] < fail_until_attempt:
            raise RuntimeError(f"Attempt {attempt_counter[key]} failed")
        return value + 100

    return retry_task


def create_delayed_task(delay: float = 0.1) -> Callable[[int], int]:
    async def delayed_task(value: int) -> int:
        await asyncio.sleep(delay)
        return value + 50

    return delayed_task


def create_priority_task() -> Callable[[int, int], int]:
    async def priority_task(value: int, priority: int = 0) -> int:
        return value + priority

    return priority_task


WORKLOAD_TASK_CREATORS: dict[WorkloadType, Callable[..., Callable[..., Any]]] = {
    WorkloadType.INCREMENT: create_increment_task,
    WorkloadType.CPU_BOUND: create_cpu_workload_task,
    WorkloadType.IO_BOUND: create_io_workload_task,
    WorkloadType.RETRY: create_retry_task,
    WorkloadType.DELAYED: create_delayed_task,
    WorkloadType.PRIORITY: create_priority_task,
}


def get_workload_tasks(
    workload_type: WorkloadType, **kwargs: Any
) -> Callable[..., Any]:
    creator = WORKLOAD_TASK_CREATORS.get(workload_type)
    if creator is None:
        msg = f"Unknown workload type: {workload_type}"
        raise ValueError(msg)
    return creator(**kwargs)
