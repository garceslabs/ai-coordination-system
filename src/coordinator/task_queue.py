"""Thread-safe FIFO task queue for pending work items."""

from __future__ import annotations

import threading
from collections import deque

from models.task import Task
from utils.logging_utils import get_logger


class TaskQueue:
    """Thread-safe FIFO queue for pending tasks.

    Intentionally simple: topology-aware ordering and dependency resolution
    are the Coordinator's responsibility. This queue only manages FIFO
    dispatch and exposes queue depth for observability.
    """

    def __init__(self) -> None:
        self._queue: deque[Task] = deque()
        self._lock = threading.Lock()
        self._logger = get_logger("coordinator.task_queue")

    def enqueue(self, task: Task) -> None:
        with self._lock:
            self._queue.append(task)
            self._logger.info(
                "Task enqueued",
                extra={
                    "task_id": task.id,
                    "task_type": task.type,
                    "queue_depth": len(self._queue),
                },
            )

    def enqueue_batch(self, tasks: list[Task]) -> None:
        for task in tasks:
            self.enqueue(task)

    def dequeue(self) -> Task | None:
        with self._lock:
            if not self._queue:
                return None
            task = self._queue.popleft()
            self._logger.info(
                "Task dequeued",
                extra={"task_id": task.id, "task_type": task.type},
            )
            return task

    def peek(self) -> Task | None:
        with self._lock:
            return self._queue[0] if self._queue else None

    def drain(self) -> list[Task]:
        """Return all queued tasks and clear the queue. Useful for testing."""
        with self._lock:
            tasks = list(self._queue)
            self._queue.clear()
            return tasks

    @property
    def depth(self) -> int:
        with self._lock:
            return len(self._queue)

    @property
    def is_empty(self) -> bool:
        return self.depth == 0
