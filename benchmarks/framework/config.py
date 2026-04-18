from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class WorkloadType(str, Enum):
    INCREMENT = "increment"
    CPU_BOUND = "cpu_bound"
    IO_BOUND = "io_bound"
    RETRY = "retry"
    DELAYED = "delayed"
    PRIORITY = "priority"


class BenchmarkTarget(str, Enum):
    CHICORY = "chicory"
    TASKIQ = "taskiq"


@dataclass
class BenchmarkConfig:
    tasks_counts: list[int] = field(
        default_factory=lambda: [8, 16, 32, 64, 128, 256, 1024, 2048, 4096, 8192, 16384]
    )
    workload_types: list[WorkloadType] = field(
        default_factory=lambda: [WorkloadType.INCREMENT]
    )
    result_timeout: float = 200.0
    poll_interval: float = 0.1
    warmup_tasks: int = 0
    warmup_delay: float = 0.0
    enable_prometheus: bool = True
    prometheus_port: int = 9090
    redis_url: str = "redis://localhost:6379"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672//"
    workers_count: int = 1
    max_async_tasks: int = 32
    max_prefetch: int = 32
    clear_between_runs: bool = True
    reconnect_delay: float = 3.0


class WorkloadTaskSpec(BaseModel):
    name: str
    task_type: WorkloadType
    params: dict[str, Any] = Field(default_factory=dict)
