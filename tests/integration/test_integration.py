from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio

from chicory.broker.base import TaskEnvelope
from chicory.exceptions import ValidationError
from chicory.result import AsyncResult
from chicory.types import (
    DeliveryMode,
    RetryBackoff,
    RetryPolicy,
    TaskMessage,
    TaskResult,
    TaskState,
    ValidationMode,
)
from chicory.worker import Worker

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from chicory.app import Chicory
    from chicory.context import TaskContext


@pytest_asyncio.fixture
async def clean_queue(chicory_app: Chicory) -> AsyncGenerator[None]:
    """Ensure queue is empty before and after test."""
    await chicory_app.broker.purge_queue()
    await chicory_app.broker.purge_dlq()
    yield
    await chicory_app.broker.purge_queue()
    await chicory_app.broker.purge_dlq()


@pytest.fixture
def unique_task_id() -> str:
    """Generate a unique task ID for test isolation."""
    return str(uuid.uuid4())


@pytest.fixture
def unique_task_name() -> str:
    """Generate a unique task name for test isolation."""
    return f"test.{uuid.uuid4().hex}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_basic_execution(chicory_worker: Worker, clean_queue: None) -> None:
    app = chicory_worker.app
    test_id = uuid.uuid4().hex

    @app.task(name=f"test.add.{test_id}")
    async def add(x: int, y: int) -> int:
        return x + y

    @app.task(name=f"test.sync_add.{test_id}")
    def sync_add(x: int, y: int) -> int:
        return x + y

    # Async task
    result = await add.delay(5, 7)
    value = await result.get(timeout=10)
    assert value == 12
    assert await result.state() == TaskState.SUCCESS

    # Sync task
    result_sync = await sync_add.delay(10, 20)
    value_sync = await result_sync.get(timeout=10)
    assert value_sync == 30


@pytest.mark.integration
@pytest.mark.asyncio
async def test_retry_policies(chicory_worker: Worker, clean_queue: None) -> None:
    app = chicory_worker.app
    test_id = uuid.uuid4().hex

    @app.task(
        name=f"test.flaky.{test_id}",
        retry_policy=RetryPolicy(
            max_retries=2, retry_delay=0.1, backoff=RetryBackoff.FIXED
        ),
    )
    async def flaky(ctx: TaskContext) -> str:
        if ctx.retries < 1:
            raise ValueError("Fail once")
        return "Success"

    result = await flaky.delay()
    value = await result.get(timeout=10)
    assert value == "Success"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_dlq_operations(chicory_worker: Worker, clean_queue: None) -> None:
    app = chicory_worker.app
    test_id = uuid.uuid4().hex
    task_name = f"test.fail.{test_id}"

    @app.task(name=task_name, retry_policy=RetryPolicy(max_retries=1, retry_delay=0.1))
    async def fail_task():
        raise RuntimeError("Permanent failure")

    result = await fail_task.delay()
    with pytest.raises(Exception, match="Permanent failure"):
        await result.get(timeout=10)

    # Wait for movement to DLQ
    await asyncio.sleep(1.0)

    # Check DLQ count
    count = await app.broker.get_dlq_count()
    assert count >= 1

    # Get DLQ messages - filter by our specific task
    msgs = await app.broker.get_dlq_messages(count=100)
    target = next((m for m in msgs if m.original_message.name == task_name), None)
    assert target is not None

    # Replay from DLQ
    success = await app.broker.replay_from_dlq(target.message_id)
    assert success is True

    # Wait for replayed task to fail again and move back to DLQ
    await asyncio.sleep(1.0)

    # Delete from DLQ - find our specific message again
    msgs = await app.broker.get_dlq_messages(count=10)
    target = next((m for m in msgs if m.original_message.name == task_name), None)
    if target:
        deleted = await app.broker.delete_from_dlq(target.message_id)
        assert deleted is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_monitoring(chicory_app: Chicory, clean_queue: None) -> None:
    test_id = uuid.uuid4().hex

    # Healthcheck
    status = await chicory_app.broker.healthcheck()
    assert status.connected is True

    if chicory_app.backend:
        status_backend = await chicory_app.backend.healthcheck()
        assert status_backend.connected is True

    # Queue should be empty after clean_queue fixture
    size = await chicory_app.broker.get_queue_size()
    assert size == 0

    @chicory_app.task(name=f"test.dummy.{test_id}")
    async def dummy():
        pass

    await dummy.delay()
    await dummy.delay()

    size = await chicory_app.broker.get_queue_size()
    assert size >= 2

    purged = await chicory_app.broker.purge_queue()
    assert purged >= 2
    assert await chicory_app.broker.get_queue_size() == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_backend_worker_heartbeat(chicory_worker: Worker) -> None:
    """Test worker heartbeat storage and retrieval."""
    app = chicory_worker.app
    if not app.backend:
        pytest.skip("No backend configured")
        return

    # Wait for heartbeat to be stored
    await asyncio.sleep(0.5)

    # Check active workers includes this worker
    workers = await app.backend.get_active_workers()
    assert any(w.worker_id == chicory_worker.worker_id for w in workers)

    # Check specific heartbeat retrieval
    hb = await app.backend.get_heartbeat(chicory_worker.worker_id)
    assert hb is not None
    assert hb.worker_id == chicory_worker.worker_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_backend_result_storage(chicory_worker: Worker) -> None:
    """Test task result storage, retrieval, and deletion."""
    app = chicory_worker.app
    if not app.backend:
        pytest.skip("No backend configured")
        return

    # Use unique task_id to avoid conflicts
    task_id = str(uuid.uuid4())
    res_obj = TaskResult[str](
        task_id=task_id,
        state=TaskState.SUCCESS,
        result="some-result",
    )

    # Store result
    await app.backend.store_result(task_id, res_obj)

    # Retrieve result
    retrieved: TaskResult[str] | None = await app.backend.get_result(task_id)
    assert retrieved is not None
    assert retrieved.result == "some-result"

    # Delete result (cleanup)
    await app.backend.delete_result(task_id)
    assert await app.backend.get_result(task_id) is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_backend_cleanup_stale_workers(chicory_app: Chicory) -> None:
    """Test cleanup of stale worker heartbeats."""
    if not chicory_app.backend:
        pytest.skip("No backend configured")
        return

    # Create a stale heartbeat with unique worker_id
    from chicory.types import WorkerStats

    stale_worker_id = f"stale-worker-{uuid.uuid4().hex}"
    stats = WorkerStats(
        worker_id=stale_worker_id,
        is_running=False,
        tasks_processed=0,
        tasks_failed=0,
        active_tasks=0,
        started_at=datetime.now(UTC) - timedelta(hours=1),
        hostname="test",
        pid=123,
        queue="default",
        concurrency=1,
    )
    # Store with very short TTL so it expires immediately
    await chicory_app.backend.store_heartbeat(stale_worker_id, stats, ttl=1)
    await asyncio.sleep(1.1)  # Wait for TTL to expire

    # Cleanup stale workers
    removed = await chicory_app.backend.cleanup_stale_clients(stale_seconds=0)
    assert isinstance(removed, int)
    assert removed >= 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_scheduled_task_eta(chicory_worker: Worker, clean_queue: None) -> None:
    app = chicory_worker.app
    test_id = uuid.uuid4().hex
    task_name = f"test.eta.{test_id}"

    @app.task(name=task_name)
    async def eta_task():
        return "Late"

    eta = datetime.now(UTC) + timedelta(seconds=3)
    msg = TaskMessage(
        id=str(uuid.uuid4()), name=task_name, args=[], kwargs={}, retries=0, eta=eta
    )
    await app.broker.publish(msg)

    res = AsyncResult(msg.id, app.backend)

    # Should not be ready before ETA
    with pytest.raises(TimeoutError):
        await res.get(timeout=1)

    # Should be ready after ETA
    val = await res.get(timeout=5)
    assert val == "Late"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_large_payload(chicory_worker: Worker, clean_queue: None) -> None:
    app = chicory_worker.app
    test_id = uuid.uuid4().hex

    @app.task(name=f"test.large.{test_id}")
    async def echo(data: dict):
        return data

    large_data = {"key": "x" * 5000, "items": list(range(500))}
    result = await echo.delay(large_data)
    value = await result.get(timeout=10)
    assert value == large_data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_context_advanced(chicory_worker: Worker, clean_queue: None) -> None:
    app = chicory_worker.app
    test_id = uuid.uuid4().hex

    @app.task(
        name=f"test.manual_retry.{test_id}",
        retry_policy=RetryPolicy(max_retries=3),
    )
    async def manual_retry(ctx: TaskContext):
        if ctx.retries < 2:
            ctx.retry(countdown=0.1)
        return ctx.retries

    result = await manual_retry.delay()
    assert await result.get(timeout=10) == 2

    @app.task(name=f"test.manual_fail.{test_id}")
    async def manual_fail(ctx: TaskContext):
        ctx.fail(RuntimeError("Forced failure"))

    result2 = await manual_fail.delay()
    with pytest.raises(Exception, match="Forced failure"):
        await result2.get(timeout=10)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_validation_modes(chicory_app: Chicory) -> None:
    test_id = uuid.uuid4().hex

    @chicory_app.task(
        name=f"test.validated.{test_id}", validation_mode=ValidationMode.INPUTS
    )
    async def validated(x: int, y: str):
        return f"{x}-{y}"

    # Valid - don't await result, just test validation
    await validated.delay(1, "a")

    # Invalid
    with pytest.raises(ValidationError):
        await validated.delay("not-int", 1)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_worker_recovery_stale_messages(
    chicory_app: Chicory, clean_queue: None
) -> None:
    from chicory.broker.redis import RedisBroker

    if not isinstance(chicory_app.broker, RedisBroker):
        pytest.skip("Only for RedisBroker")
        return

    test_id = uuid.uuid4().hex

    # Reduce claim time for testing
    original_claim_ms = chicory_app.broker.claim_min_idle_ms
    chicory_app.broker.claim_min_idle_ms = 100  # 100ms

    try:

        @chicory_app.task(name=f"test.stale.{test_id}")
        async def stale_task():
            return "recovered"

        # Publish message
        await stale_task.delay()

        # Consume it but don't ack it
        envelopes = []
        async for env in chicory_app.broker.consume():
            envelopes.append(env)
            break  # Only one

        assert len(envelopes) == 1

        # Wait for it to become stale
        await asyncio.sleep(0.5)

        # Now start a worker, it should claim the stale message
        worker_handle = Worker(chicory_app)
        await worker_handle.start()
        try:
            res = AsyncResult(envelopes[0].message.id, chicory_app.backend)
            assert await res.get(timeout=5) == "recovered"
        finally:
            await worker_handle.stop()
    finally:
        # Restore original claim time
        chicory_app.broker.claim_min_idle_ms = original_claim_ms


@pytest.mark.integration
@pytest.mark.asyncio
async def test_manual_dlq_move(chicory_app: Chicory, clean_queue: None) -> None:
    test_id = uuid.uuid4().hex
    task_name = f"test.manual_dlq.{test_id}"

    @chicory_app.task(name=task_name)
    async def dummy():
        pass

    msg = TaskMessage(
        id=str(uuid.uuid4()), name=task_name, args=[], kwargs={}, retries=0
    )
    envelope = TaskEnvelope(message=msg, delivery_tag=f"manual-tag-{test_id}")

    await chicory_app.broker.move_to_dlq(envelope, error="Manual error")

    # Check if it's there - filter by our specific message
    msgs = await chicory_app.broker.get_dlq_messages(count=10)
    found = next((m for m in msgs if m.original_message.id == msg.id), None)
    assert found is not None
    assert "Manual error" in found.error

    # Cleanup: delete our message from DLQ
    await chicory_app.broker.delete_from_dlq(found.message_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_backend_cleanup_old_results(chicory_app: Chicory) -> None:
    if chicory_app.backend is None:
        pytest.skip("No backend")
        return
    from chicory.backend.database import DatabaseBackend

    if not isinstance(chicory_app.backend, DatabaseBackend):
        pytest.skip("Only for DatabaseBackend")
        return

    # Create a test result to clean up
    task_id = str(uuid.uuid4())
    res_obj = TaskResult[str](
        task_id=task_id,
        state=TaskState.SUCCESS,
        result="old-result",
    )
    await chicory_app.backend.store_result(task_id, res_obj)

    # Call cleanup_old_results with 0 seconds (cleans everything)
    count = await chicory_app.backend.cleanup_old_results(older_than_seconds=0)
    assert isinstance(count, int)
    assert count >= 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_broker_edge_cases(chicory_app: Chicory, clean_queue: None) -> None:
    # Test delete_from_dlq with non-existent ID
    res = await chicory_app.broker.delete_from_dlq(f"non-existent-{uuid.uuid4().hex}")
    assert res is False

    # Test replay_from_dlq with non-existent ID
    res = await chicory_app.broker.replay_from_dlq(f"non-existent-{uuid.uuid4().hex}")
    assert res is False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_broker_malformed_dlq_message(
    chicory_app: Chicory, clean_queue: None
) -> None:
    """Test that malformed DLQ messages are skipped gracefully."""
    from chicory.broker.rabbitmq import RabbitMQBroker
    from chicory.broker.redis import RedisBroker

    test_id = uuid.uuid4().hex

    if isinstance(chicory_app.broker, RedisBroker):
        assert chicory_app.broker._client is not None
        # Add malformed message with unique field
        await chicory_app.broker._client.xadd(
            chicory_app.broker._dlq_key("default"), {"data": f"malformed-{test_id}"}
        )
        msgs = await chicory_app.broker.get_dlq_messages(count=10)
        # Should skip malformed
        assert all(m.original_message is not None for m in msgs)
    elif isinstance(chicory_app.broker, RabbitMQBroker):
        async with chicory_app.broker._acquire_channel() as channel:
            dlq = await chicory_app.broker._declare_dlq(channel, "default")
            import aio_pika

            await channel.default_exchange.publish(
                aio_pika.Message(body=f"malformed-{test_id}".encode()),
                routing_key=dlq.name,
            )
        msgs = await chicory_app.broker.get_dlq_messages(count=10)
        # Should skip malformed
        assert all(m.original_message is not None for m in msgs)
    else:
        pytest.skip("Unknown broker type")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_retry_backoffs(chicory_worker: Worker, clean_queue: None) -> None:
    app = chicory_worker.app
    test_id = uuid.uuid4().hex

    for backoff in [RetryBackoff.LINEAR, RetryBackoff.EXPONENTIAL, RetryBackoff.FIXED]:
        task_name = f"test.backoff.{backoff}.{test_id}.{uuid.uuid4().hex}"

        @app.task(
            name=task_name,
            retry_policy=RetryPolicy(max_retries=2, retry_delay=0.1, backoff=backoff),
        )
        async def flaky(ctx: TaskContext):
            if ctx.retries < 2:
                raise ValueError("Fail")
            return "Success"

        result = await flaky.delay()
        assert await result.get(timeout=10) == "Success"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_worker_stats_and_health(chicory_worker: Worker) -> None:
    stats = chicory_worker.get_stats()
    assert stats.worker_id == chicory_worker.worker_id
    assert stats.is_running is True

    health = await chicory_worker.healthcheck()
    assert health.broker is not None
    assert health.broker.connected is True
    if health.backend:
        assert health.backend.connected is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_backend_heartbeat_edge_cases(chicory_app: Chicory) -> None:
    if not chicory_app.backend:
        pytest.skip("No backend")
        return

    test_id = uuid.uuid4().hex

    # get_heartbeat for non-existent worker
    hb = await chicory_app.backend.get_heartbeat(f"non-existent-{test_id}")
    assert hb is None

    # store_heartbeat for new worker
    from chicory.types import WorkerStats

    worker_id = f"new-worker-{test_id}"
    stats = WorkerStats(
        worker_id=worker_id,
        is_running=True,
        tasks_processed=0,
        tasks_failed=0,
        active_tasks=0,
        started_at=datetime.now(UTC),
        hostname="test",
        pid=123,
        queue="default",
        concurrency=1,
    )
    await chicory_app.backend.store_heartbeat(worker_id, stats, ttl=5)
    hb = await chicory_app.backend.get_heartbeat(worker_id)
    assert hb is not None
    assert hb.worker_id == worker_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_broker_extra_monitoring(chicory_app: Chicory, clean_queue: None) -> None:
    from chicory.broker.rabbitmq import RabbitMQBroker
    from chicory.broker.redis import RedisBroker

    if isinstance(chicory_app.broker, RabbitMQBroker):
        await chicory_app.broker.get_dlq_count()
        pending = await chicory_app.broker.get_pending_count()
        assert pending == 0
        consumers = await chicory_app.broker.get_consumer_count()
        assert isinstance(consumers, int)
    elif isinstance(chicory_app.broker, RedisBroker):
        pending = await chicory_app.broker.get_pending_count()
        assert isinstance(pending, int)
    else:
        pytest.skip("Unknown broker type")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_nack_requeue_false(chicory_app: Chicory, clean_queue: None) -> None:
    test_id = uuid.uuid4().hex

    @chicory_app.task(
        name=f"test.nack.{test_id}", delivery_mode=DeliveryMode.AT_LEAST_ONCE
    )
    async def dummy():
        pass

    await dummy.delay()

    # Consume but nack with requeue=False
    async for envelope in chicory_app.broker.consume():
        await chicory_app.broker.nack(envelope, requeue=False)
        break

    # Just verify it doesn't crash
    assert True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrency(chicory_worker: Worker, clean_queue: None) -> None:
    app = chicory_worker.app
    test_id = uuid.uuid4().hex

    @app.task(name=f"test.sleep.{test_id}")
    async def slow_echo(x: int):
        await asyncio.sleep(0.1)
        return x

    results = [await slow_echo.delay(i) for i in range(10)]
    values = [await res.get(timeout=10) for res in results]
    assert values == list(range(10))
