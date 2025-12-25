import logging
from typing import TYPE_CHECKING, Any

from chicory.backend import Backend, RedisBackend
from chicory.broker import Broker, RedisBroker
from chicory.config import ChicoryConfig
from chicory.exceptions import TaskNotFoundError
from chicory.task import Task
from chicory.types import (
    BackendType,
    BrokerType,
    DeliveryMode,
    P,
    R,
    RetryPolicy,
    TaskOptions,
    ValidationMode,
)

if TYPE_CHECKING:
    from collections.abc import Callable


class Chicory:
    def __init__(
        self,
        broker: BrokerType,
        backend: BackendType | None = None,
        validation_mode: ValidationMode = ValidationMode.INPUTS,
    ) -> None:
        self.config = ChicoryConfig()
        self.config.validation_mode = validation_mode

        self._broker = self._create_broker(broker)
        self._backend = self._create_backend(backend) if backend else None

        self._tasks: dict[str, Task[Any, Any]] = {}

        self.logger = logging.getLogger("chicory")

    def _create_broker(self, broker_type: BrokerType) -> Broker:
        match broker_type:
            case BrokerType.REDIS:
                return RedisBroker(redis_dsn="redis://localhost:6379/0")
            case _:
                raise NotImplementedError

    def _create_backend(self, backend_type: BackendType) -> Backend:
        match backend_type:
            case BackendType.REDIS:
                return RedisBackend(redis_dsn="redis://localhost:6379/1")
            case _:
                raise NotImplementedError

    @property
    def broker(self) -> Broker:
        return self._broker

    @property
    def backend(self) -> Backend | None:
        return self._backend

    def task(
        self,
        *,
        name: str | None = None,
        delivery_mode: DeliveryMode = DeliveryMode.AT_LEAST_ONCE,
        retry_policy: RetryPolicy | None = None,
        ignore_result: bool = False,
        validation_mode: ValidationMode | None = None,
    ) -> Callable[[Callable[P, R]], Task[P, R]]:
        options = TaskOptions(
            name=name,
            retry_policy=retry_policy,
            delivery_mode=delivery_mode,
            ignore_result=ignore_result,
            validation_mode=validation_mode or self.config.validation_mode,
        )

        def decorator(fn: Callable[P, R]) -> Task[P, R]:
            task = Task(fn=fn, app=self, options=options)
            self._tasks[task.name] = task
            return task

        return decorator

    def get_task(self, name: str) -> Task[Any, Any]:
        """Retrieve a registered task by name."""
        if name not in self._tasks:
            raise TaskNotFoundError(f"Task '{name}' not found")
        return self._tasks[name]

    async def connect(self) -> None:
        """Connect to broker and backend."""
        await self._broker.connect()
        if self._backend:
            await self._backend.connect()

    async def disconnect(self) -> None:
        """Disconnect from broker and backend."""
        await self._broker.disconnect()
        if self._backend:
            await self._backend.disconnect()
