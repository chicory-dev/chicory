from __future__ import annotations

from typing import TYPE_CHECKING

import pytest_asyncio

from chicory.app import Chicory
from chicory.config import (
    ChicoryConfig,
    PostgresBackendConfig,
    RabbitMQBrokerConfig,
    RedisBackendConfig,
    RedisBrokerConfig,
)
from chicory.types import BackendType, BrokerType
from chicory.worker import Worker

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    import pytest

REDIS_URL = "redis://localhost:6379"
POSTGRES_URL = "postgresql+asyncpg://chicory:chicory@localhost:5432/chicory"
RABBITMQ_URL = "amqp://guest:guest@localhost:5672//"


async def _setup_app(broker_type: BrokerType, backend_type: BackendType) -> Chicory:
    config = ChicoryConfig()
    if broker_type == BrokerType.REDIS:
        config.broker.redis = RedisBrokerConfig(url=f"{REDIS_URL}/0")
    else:
        config.broker.rabbitmq = RabbitMQBrokerConfig(url=RABBITMQ_URL)

    if backend_type == BackendType.REDIS:
        config.backend.redis = RedisBackendConfig(url=f"{REDIS_URL}/1")
    elif backend_type == BackendType.POSTGRES:
        config.backend.postgres = PostgresBackendConfig(url=POSTGRES_URL)

    app = Chicory(broker=broker_type, backend=backend_type, config=config)
    await app.connect()

    if backend_type == BackendType.POSTGRES:
        from chicory.backend.database import DatabaseBackend

        if isinstance(app.backend, DatabaseBackend):
            if app.backend._engine is None:
                raise RuntimeError("Database engine is not initialized.")
            async with app.backend._engine.begin() as conn:
                from chicory.backend.models import Base

                await conn.run_sync(Base.metadata.create_all)

    await app.broker.purge_queue()
    await app.broker.purge_dlq()
    return app


@pytest_asyncio.fixture(
    params=[
        (BrokerType.REDIS, BackendType.REDIS),
        (BrokerType.RABBITMQ, BackendType.POSTGRES),
        (BrokerType.REDIS, BackendType.POSTGRES),
        (BrokerType.RABBITMQ, BackendType.REDIS),
    ],
    ids=["redis-redis", "rabbitmq-postgres", "redis-postgres", "rabbitmq-redis"],
)
async def chicory_app(request: pytest.FixtureRequest) -> AsyncGenerator[Chicory]:
    broker_type, backend_type = request.param
    app = await _setup_app(broker_type, backend_type)
    yield app
    await app.disconnect()


@pytest_asyncio.fixture
async def chicory_worker(chicory_app: Chicory) -> AsyncGenerator[Worker]:
    chicory_app.config.worker.use_dead_letter_queue = True
    worker = Worker(chicory_app)
    await worker.start()
    yield worker
    await worker.stop(timeout=5)
