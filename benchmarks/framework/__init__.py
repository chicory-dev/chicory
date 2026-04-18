from __future__ import annotations

from framework.config import BenchmarkConfig
from framework.metrics import BenchmarkResult, MetricsCollector
from framework.runner import BenchmarkRunner
from framework.workloads import (
    WorkloadType,
    create_cpu_workload_task,
    create_increment_task,
    create_io_workload_task,
    get_workload_tasks,
)

__all__ = [
    "BenchmarkConfig",
    "BenchmarkResult",
    "BenchmarkRunner",
    "MetricsCollector",
    "WorkloadType",
    "get_workload_tasks",
    "create_increment_task",
    "create_cpu_workload_task",
    "create_io_workload_task",
]
