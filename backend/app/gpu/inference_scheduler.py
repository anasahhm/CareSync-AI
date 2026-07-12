"""
Inference Scheduler

Async inference queue with dynamic micro-batching. Any callable
`batch_fn(list_of_inputs) -> list_of_outputs` can be scheduled through this
- individual `submit()` calls arriving within `max_wait_ms` of each other
get grouped into one batch call, which matters for GPU throughput (batching
is where most of the throughput win comes from) but is harmless on CPU too.
Falls back to per-item execution if batch_fn raises, so one bad input in a
batch doesn't fail the whole group.
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class _PendingRequest:
    payload: Any
    future: asyncio.Future
    enqueued_at: float = field(default_factory=time.time)


class InferenceScheduler:
    def __init__(self, batch_fn: Callable[[List[Any]], List[Any]], max_batch_size: int = 8, max_wait_ms: int = 50):
        self.batch_fn = batch_fn
        self.max_batch_size = max_batch_size
        self.max_wait_ms = max_wait_ms
        self._queue: "asyncio.Queue[_PendingRequest]" = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info(f"InferenceScheduler started (max_batch_size={self.max_batch_size}, max_wait_ms={self.max_wait_ms})")

    async def stop(self):
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

    async def submit(self, payload: Any) -> Any:
        future = asyncio.get_event_loop().create_future()
        await self._queue.put(_PendingRequest(payload=payload, future=future))
        return await future

    async def _worker_loop(self):
        while self._running:
            try:
                batch: List[_PendingRequest] = [await self._queue.get()]
                deadline = time.time() + (self.max_wait_ms / 1000)
                while len(batch) < self.max_batch_size and time.time() < deadline:
                    try:
                        remaining = max(0.0, deadline - time.time())
                        item = await asyncio.wait_for(self._queue.get(), timeout=remaining)
                        batch.append(item)
                    except asyncio.TimeoutError:
                        break

                await self._run_batch(batch)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"InferenceScheduler: worker loop error: {e}")

    async def _run_batch(self, batch: List[_PendingRequest]):
        payloads = [item.payload for item in batch]
        try:
            results = self.batch_fn(payloads)
            if asyncio.iscoroutine(results):
                results = await results
            for item, result in zip(batch, results):
                if not item.future.done():
                    item.future.set_result(result)
        except Exception as e:
            logger.warning(f"InferenceScheduler: batch of {len(batch)} failed ({e}); retrying items individually")
            for item in batch:
                try:
                    result = self.batch_fn([item.payload])
                    if asyncio.iscoroutine(result):
                        result = await result
                    if not item.future.done():
                        item.future.set_result(result[0] if isinstance(result, list) else result)
                except Exception as item_error:
                    if not item.future.done():
                        item.future.set_exception(item_error)
