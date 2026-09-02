from __future__ import annotations

from chicory.app import Chicory
from chicory.config import (
    ChicoryConfig,
    PostgresBackendConfig,
    RabbitMQBrokerConfig,
    RedisBackendConfig,
    RedisBrokerConfig,
    WorkerConfig,
)
from chicory.context import TaskContext
from chicory.exceptions import (
    BackendNotConfiguredError,
    BrokerConnectionError,
    ChicoryError,
    DbPoolExhaustedException,
    MaxRetriesExceededError,
    RetryError,
    TaskFailedException,
    TaskNotFoundError,
    ValidationError,
)
from chicory.result import AsyncResult
from chicory.task import Task
from chicory.types import (
    BackendType,
    BrokerType,
    DeliveryMode,
    RetryBackoff,
    RetryPolicy,
    TaskMessage,
    TaskOptions,
    TaskResult,
    TaskState,
    ValidationMode,
    WorkerStats,
)
from chicory.worker import Worker

__all__ = [
    "AsyncResult",
    "BackendNotConfiguredError",
    "BackendType",
    "BrokerConnectionError",
    "BrokerType",
    "Chicory",
    "ChicoryConfig",
    "ChicoryError",
    "DbPoolExhaustedException",
    "DeliveryMode",
    "MaxRetriesExceededError",
    "PostgresBackendConfig",
    "RabbitMQBrokerConfig",
    "RedisBackendConfig",
    "RedisBrokerConfig",
    "RetryBackoff",
    "RetryError",
    "RetryPolicy",
    "Task",
    "TaskContext",
    "TaskFailedException",
    "TaskMessage",
    "TaskNotFoundError",
    "TaskOptions",
    "TaskResult",
    "TaskState",
    "ValidationError",
    "ValidationMode",
    "Worker",
    "WorkerConfig",
    "WorkerStats",
]

try:
    from chicory.broker.rabbitmq import RabbitMQBroker

    __all__.append("RabbitMQBroker")
except ImportError:
    pass

try:
    from chicory.backend.redis import RedisBackend
    from chicory.broker.redis import RedisBroker

    __all__.extend(
        [
            "RedisBackend",
            "RedisBroker",
        ]
    )
except ImportError:
    pass

try:
    from chicory.backend.database import DatabaseBackend

    __all__.append("DatabaseBackend")
except ImportError:
    pass
