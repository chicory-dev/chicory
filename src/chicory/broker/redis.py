from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

import redis.asyncio as redis

from chicory.config import RedisBrokerConfig  # noqa: TC001
from chicory.types import BrokerStatus, DeliveryMode, TaskMessage

from .base import DEFAULT_QUEUE, Broker, DLQMessage, TaskEnvelope

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Awaitable

_logger = logging.getLogger("chicory.broker.redis")

# Lua script: atomically move delayed tasks whose score <= now from the
# sorted set (KEYS[1]) to the stream (KEYS[2]).  Returns the number of
# tasks moved.  Because the ZRANGEBYSCORE + ZREM happen inside a single
# EVAL, no two workers can promote the same task.
_LUA_MOVE_DELAYED = """
local delayed_key = KEYS[1]
local stream_key  = KEYS[2]
local now         = ARGV[1]
local ready = redis.call('ZRANGEBYSCORE', delayed_key, 0, now)
local moved = 0
for _, data in ipairs(ready) do
    redis.call('XADD', stream_key, '*', 'data', data)
    redis.call('ZREM', delayed_key, data)
    moved = moved + 1
end
return moved
"""


class RedisBroker(Broker):
    """
    Redis Streams-based message broker with DLQ and configurable delivery semantics.
    """

    def __init__(
        self,
        config: RedisBrokerConfig,
        delivery_mode: DeliveryMode = DeliveryMode.AT_MOST_ONCE,
        consumer_name: str | None = None,
    ) -> None:
        self.dsn = config.dsn
        self.consumer_group = config.consumer_group
        self.block_ms = config.block_ms
        self.claim_min_idle_ms = config.claim_min_idle_ms
        self.max_stream_length = config.max_stream_length
        self.dlq_max_length = config.dlq_max_length

        self.delivery_mode = delivery_mode
        self.consumer_name = consumer_name or f"worker-{uuid.uuid4().hex[:8]}"

        self._pool: redis.ConnectionPool | None = None
        self._client: redis.Redis | None = None
        self._running = False

    async def connect(self) -> None:
        self._pool = redis.ConnectionPool.from_url(self.dsn)
        self._client = redis.Redis(
            connection_pool=self._pool,
            decode_responses=False,  # Keep as bytes for consistency
        )
        await cast("Awaitable[bool]", self._client.ping())

    async def disconnect(self) -> None:
        self.stop()

        if self._client:
            await self._client.aclose()
            self._client = None
        if self._pool:
            await self._pool.aclose()
            self._pool = None

    @staticmethod
    def _stream_key(queue: str) -> str:
        return f"chicory:stream:{queue}"

    @staticmethod
    def _delayed_key(queue: str) -> str:
        return f"chicory:delayed:{queue}"

    @staticmethod
    def _dlq_key(queue: str) -> str:
        return f"chicory:dlq:{queue}"

    async def _ensure_consumer_group(self, queue: str) -> None:
        """Create consumer group if it doesn't exist."""
        if not self._client:
            return

        stream_key = self._stream_key(queue)
        try:
            await self._client.xgroup_create(
                stream_key,
                self.consumer_group,
                id="0",
                mkstream=True,
            )
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):  # Group already exists
                raise

    async def publish(self, message: TaskMessage, queue: str = DEFAULT_QUEUE) -> None:
        """Publish a message to the stream."""
        if not self._client:
            raise RuntimeError("Broker not connected")

        data = TaskMessage.dumps(message)

        if message.eta and message.eta > datetime.now(UTC):
            # Use sorted set for delayed tasks
            score = message.eta.timestamp()
            await self._client.zadd(self._delayed_key(queue), {data: score})
            return

        stream_key = self._stream_key(queue)

        # XADD with optional MAXLEN for stream trimming
        kwargs: dict[str, Any] = {"fields": {"data": data, "task_id": message.id}}
        if self.max_stream_length:
            kwargs["maxlen"] = self.max_stream_length
            kwargs["approximate"] = True

        await self._client.xadd(stream_key, **kwargs)

    async def _move_ready_delayed(self, queue: str) -> int:
        """Atomically move delayed tasks that are ready to the stream.

        Uses a Lua script so that the read-from-sorted-set and write-to-stream
        happen in a single Redis operation.  This prevents multiple workers from
        promoting the same task concurrently (the PERF-1 race condition).

        Returns:
            The number of tasks that were moved.
        """
        if not self._client:
            return 0

        now = datetime.now(UTC).timestamp()
        delayed_key = self._delayed_key(queue)
        stream_key = self._stream_key(queue)

        moved: int = await self._client.eval(  # ty: ignore[invalid-await]
            _LUA_MOVE_DELAYED, 2, delayed_key, stream_key, now
        )
        return moved

    async def _next_delayed_score(self, queue: str) -> float | None:
        """Return the ETA timestamp of the earliest delayed task, or None."""
        if not self._client:
            return None
        items = await self._client.zrange(
            self._delayed_key(queue), 0, 0, withscores=True,
        )
        if items:
            _member, score = items[0]
            return float(score)
        return None

    _MOVER_MIN_SLEEP: float = 0.05   # 50 ms — fastest we ever poll
    _MOVER_MAX_SLEEP: float = 1.0    # 1 s  — idle cadence

    async def _delayed_mover_loop(self, queue: str) -> None:
        """Background loop: promote ready delayed tasks to the stream.

        The loop adapts its polling interval based on the next known ETA:

        * **Tasks just moved** — re-check quickly (50 ms) in case more are
          ready in a burst.
        * **Delayed tasks pending** — sleep until the earliest one matures
          (clamped to [50 ms, 1 s]).
        * **No delayed tasks** — sleep for 1 s to minimise idle Redis traffic.

        All exceptions except ``CancelledError`` are caught so transient Redis
        errors (pool exhaustion, network blips) cannot kill the loop.
        """
        try:
            while self._running:
                try:
                    moved = await self._move_ready_delayed(queue)
                    if moved:
                        # More may be ready right behind; re-check fast.
                        await asyncio.sleep(self._MOVER_MIN_SLEEP)
                        continue

                    # Peek at the next delayed task to decide how long to
                    # sleep.
                    score = await self._next_delayed_score(queue)
                    if score is not None:
                        wait = score - datetime.now(UTC).timestamp()
                        wait = max(self._MOVER_MIN_SLEEP, wait)
                        wait = min(self._MOVER_MAX_SLEEP, wait)
                    else:
                        wait = self._MOVER_MAX_SLEEP

                    await asyncio.sleep(wait)

                except asyncio.CancelledError:
                    raise
                except Exception:
                    _logger.exception(
                        "delayed-mover iteration failed, will retry"
                    )
                    await asyncio.sleep(self._MOVER_MAX_SLEEP)
        except asyncio.CancelledError:
            pass


    async def _claim_stale_messages(self, queue: str) -> list[TaskEnvelope]:
        """Claim messages that have been pending too long (dead consumer recovery)."""
        if not self._client:
            return []

        stream_key = self._stream_key(queue)
        envelopes = []

        try:
            # XAUTOCLAIM: automatically claim messages idle for too long
            result = await self._client.xautoclaim(
                stream_key,
                self.consumer_group,
                self.consumer_name,
                min_idle_time=self.claim_min_idle_ms,
                start_id="0-0",
                count=10,
            )

            if result and len(result) >= 2:
                messages = result[1]  # Format: [cursor, messages, ...]
                for msg_id, fields in messages:
                    if fields and b"data" in fields:
                        data = fields[b"data"]
                        message = TaskMessage.loads(data)
                        envelopes.append(
                            TaskEnvelope(
                                message=message,
                                delivery_tag=msg_id.decode()
                                if isinstance(msg_id, bytes)
                                else msg_id,
                                raw_data=data,
                            )
                        )
        except redis.ResponseError:
            pass  # Group might not exist yet

        return envelopes

    async def consume(self, queue: str = DEFAULT_QUEUE) -> AsyncGenerator[TaskEnvelope]:
        if not self._client:
            raise RuntimeError("Broker not connected")

        await self._ensure_consumer_group(queue)

        self._running = True
        stream_key = self._stream_key(queue)
        last_claim_check = 0.0

        # Run delayed-task promotion in the background so short-countdown retries
        # are moved to the stream every ~100 ms, independently of block_ms.
        delayed_mover = asyncio.create_task(self._delayed_mover_loop(queue))
        try:
            while self._running:
                # Periodically check for stale messages to reclaim (at-least-once)
                now = asyncio.get_running_loop().time()
                if (
                    self.delivery_mode == DeliveryMode.AT_LEAST_ONCE
                    and now - last_claim_check > 10
                ):
                    stale = await self._claim_stale_messages(queue)
                    for envelope in stale:
                        yield envelope
                    last_claim_check = now

                try:
                    # XREADGROUP: read new messages for this consumer.
                    # Use ">" to read only messages not yet delivered to any consumer.
                    result = await self._client.xreadgroup(
                        groupname=self.consumer_group,
                        consumername=self.consumer_name,
                        streams={stream_key: ">"},
                        count=1,
                        block=self.block_ms,
                    )

                    if result:
                        for stream_name, messages in result:
                            for msg_id, fields in messages:
                                if fields and b"data" in fields:
                                    data = fields[b"data"]
                                    message = TaskMessage.loads(data)

                                    delivery_tag = (
                                        msg_id.decode()
                                        if isinstance(msg_id, bytes)
                                        else msg_id
                                    )

                                    yield TaskEnvelope(
                                        message=message,
                                        delivery_tag=delivery_tag,
                                        raw_data=data,
                                    )

                except redis.ResponseError as e:
                    if "NOGROUP" in str(e):
                        await self._ensure_consumer_group(queue)
                    else:
                        raise
        finally:
            delayed_mover.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await delayed_mover

    async def ack(self, envelope: TaskEnvelope, queue: str = DEFAULT_QUEUE) -> None:
        """Acknowledge successful processing (only meaningful for at-least-once)."""
        if self.delivery_mode == DeliveryMode.AT_LEAST_ONCE and self._client:
            await self._client.xack(
                self._stream_key(queue),
                self.consumer_group,
                envelope.delivery_tag,
            )

    async def nack(
        self, envelope: TaskEnvelope, requeue: bool = True, queue: str = DEFAULT_QUEUE
    ) -> None:
        """Negative acknowledgment - handle failed processing."""
        if not self._client:
            return

        stream_key = self._stream_key(queue)

        if self.delivery_mode == DeliveryMode.AT_LEAST_ONCE:
            if requeue:
                # Don't ack - message stays in PEL and will be reclaimed
                pass
            else:
                # Acknowledge to remove from PEL
                await self._client.xack(
                    stream_key, self.consumer_group, envelope.delivery_tag
                )

    async def move_to_dlq(
        self,
        envelope: TaskEnvelope,
        error: str | None = None,
        queue: str = DEFAULT_QUEUE,
    ) -> None:
        """Move a failed message to the Dead Letter Queue."""
        if not self._client:
            raise RuntimeError("Broker not connected")

        dlq_key = self._dlq_key(queue)
        stream_key = self._stream_key(queue)

        # Build DLQ entry with metadata
        dlq_entry = {
            "data": TaskMessage.dumps(envelope.message),
            "failed_at": datetime.now(UTC).isoformat(),
            "error": error or "",
            "retry_count": str(envelope.message.retries),
            "original_stream_id": envelope.delivery_tag,
            "task_id": envelope.message.id,
            "task_name": envelope.message.name,
        }

        # Use pipeline for atomicity
        pipe = self._client.pipeline()

        # Add to DLQ stream
        kwargs: dict[str, Any] = {"fields": dlq_entry}
        if self.dlq_max_length:
            kwargs["maxlen"] = self.dlq_max_length
            kwargs["approximate"] = True

        pipe.xadd(dlq_key, **kwargs)

        # ACK from main stream to remove from PEL
        if self.delivery_mode == DeliveryMode.AT_LEAST_ONCE:
            pipe.xack(stream_key, self.consumer_group, envelope.delivery_tag)

        await pipe.execute()

    async def get_dlq_messages(
        self,
        queue: str = DEFAULT_QUEUE,
        count: int = 100,
        start_id: str = "-",
        end_id: str = "+",
    ) -> list[DLQMessage]:
        """Retrieve messages from the Dead Letter Queue."""
        if not self._client:
            return []

        dlq_key = self._dlq_key(queue)

        try:
            messages = await self._client.xrange(dlq_key, start_id, end_id, count=count)
        except redis.ResponseError:
            return []

        result = []
        for msg_id, fields in messages:
            stream_id = msg_id.decode() if isinstance(msg_id, bytes) else msg_id

            # Parse message data
            data = fields.get(b"data", b"{}")

            try:
                original_message = TaskMessage.loads(data)
            except Exception:
                continue  # Skip malformed messages

            error = fields.get(b"error", b"")
            if isinstance(error, bytes):
                error = error.decode()

            failed_at = fields.get(b"failed_at", b"")
            if isinstance(failed_at, bytes):
                failed_at = failed_at.decode()

            retry_count_raw = fields.get(b"retry_count", b"0")
            if isinstance(retry_count_raw, bytes):
                retry_count_raw = retry_count_raw.decode()
            retry_count = int(retry_count_raw)

            result.append(
                DLQMessage(
                    original_message=original_message,
                    failed_at=failed_at,
                    error=error if error else None,
                    retry_count=retry_count,
                    message_id=stream_id,
                )
            )

        return result

    async def replay_from_dlq(
        self,
        message_id: str,
        queue: str = DEFAULT_QUEUE,
        reset_retries: bool = True,
    ) -> bool:
        """Move a message from DLQ back to the main queue for reprocessing."""
        if not self._client:
            return False

        dlq_key = self._dlq_key(queue)

        # Get the message from DLQ
        try:
            messages = await self._client.xrange(
                dlq_key, message_id, message_id, count=1
            )
        except redis.ResponseError:
            return False

        if not messages:
            return False

        _, fields = messages[0]
        data = fields.get(b"data", b"{}")

        try:
            message = TaskMessage.loads(data)
        except Exception:
            return False

        # Reset retry count if requested
        if reset_retries:
            message = TaskMessage(
                id=message.id,
                name=message.name,
                args=message.args,
                kwargs=message.kwargs,
                retries=0,
                eta=None,
                first_failure_at=None,
                last_error=None,
            )

        # Use pipeline for atomicity
        pipe = self._client.pipeline()

        # Publish back to main queue
        stream_key = self._stream_key(queue)
        publish_kwargs: dict[str, Any] = {
            "fields": {"data": TaskMessage.dumps(message), "task_id": message.id}
        }
        if self.max_stream_length:
            publish_kwargs["maxlen"] = self.max_stream_length
            publish_kwargs["approximate"] = True

        pipe.xadd(stream_key, **publish_kwargs)

        # Remove from DLQ
        pipe.xdel(dlq_key, message_id)

        await pipe.execute()
        return True

    async def delete_from_dlq(
        self,
        message_id: str,
        queue: str = DEFAULT_QUEUE,
    ) -> bool:
        """Permanently delete a message from the DLQ."""
        if not self._client:
            return False

        dlq_key = self._dlq_key(queue)

        try:
            deleted = await self._client.xdel(dlq_key, message_id)
            return deleted > 0
        except redis.ResponseError:
            return False

    async def purge_dlq(self, queue: str = DEFAULT_QUEUE) -> int:
        """Delete all messages from the DLQ. Returns count of deleted messages."""
        if not self._client:
            return 0

        dlq_key = self._dlq_key(queue)

        try:
            # Get count before deleting
            info = await self._client.xlen(dlq_key)
            await self._client.delete(dlq_key)
            return info
        except redis.ResponseError:
            return 0

    async def get_dlq_count(self, queue: str = DEFAULT_QUEUE) -> int:
        """Get the number of messages in the Dead Letter Queue."""
        if not self._client:
            return 0

        dlq_key = self._dlq_key(queue)

        try:
            return await self._client.xlen(dlq_key)
        except redis.ResponseError:
            return 0

    async def get_pending_count(self, queue: str = DEFAULT_QUEUE) -> int:
        """Get the number of pending (unacknowledged) messages."""
        if not self._client:
            return 0

        try:
            info = await self._client.xpending(
                self._stream_key(queue), self.consumer_group
            )
            return (
                info.get("pending", 0)
                if isinstance(info, dict)
                else (info[0] if info else 0)
            )
        except redis.ResponseError:
            return 0

    def stop(self) -> None:
        self._running = False

    async def get_queue_size(self, queue: str = DEFAULT_QUEUE) -> int:
        """Get number of ready messages in queue."""
        if not self._client:
            return 0

        stream_key = self._stream_key(queue)

        try:
            return await self._client.xlen(stream_key)
        except redis.ResponseError:
            return 0

    async def get_consumer_count(self, queue: str = DEFAULT_QUEUE) -> int:
        """Get number of active consumers."""
        if not self._client:
            return 0

        try:
            info = await self._client.xinfo_consumers(
                self._stream_key(queue), self.consumer_group
            )
            return len(info)
        except redis.ResponseError:
            return 0

    async def purge_queue(self, queue: str = DEFAULT_QUEUE) -> int:
        """Delete all messages from queue. Returns count deleted."""
        if not self._client:
            return 0

        stream_key = self._stream_key(queue)

        try:
            count = await self._client.xlen(stream_key)
            await self._client.delete(stream_key)
            return count
        except redis.ResponseError:
            return 0

    async def cleanup_stale_clients(
        self, queue: str = DEFAULT_QUEUE, stale_seconds: float = 60.0
    ) -> int:
        if not self._client:
            return 0

        try:
            consumers_info = await self._client.xinfo_consumers(
                self._stream_key(queue), self.consumer_group
            )
        except redis.ResponseError:
            # Consumer group may not exist yet
            return 0

        removed = 0
        for consumer in consumers_info:
            if consumer["pending"] > 0:
                # Don't delete consumers with pending messages: wait for the autoclaim
                # procedure to empty the queue before deleting the consumer.
                continue

            if consumer["idle"] / 1000 > stale_seconds:
                await self._client.xgroup_delconsumer(
                    self._stream_key(queue), self.consumer_group, consumer["name"]
                )
                removed += 1

        return removed

    async def healthcheck(self) -> BrokerStatus:
        """Check the health of the broker connection."""
        if not self._client:
            return BrokerStatus(connected=False, error="Not connected")

        try:
            await cast("Awaitable[bool]", self._client.ping())
            return BrokerStatus(connected=True)
        except Exception as e:
            return BrokerStatus(connected=False, error=str(e))
