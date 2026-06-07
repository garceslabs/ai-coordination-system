"""Tests for TaskQueue — FIFO ordering and concurrency safety."""

from coordinator.task_queue import TaskQueue
from models.task import Task, TaskType


def _task(task_type: TaskType = TaskType.RESEARCH) -> Task:
    return Task.create(task_type, "goal", "wf-test")


def test_enqueue_dequeue_preserves_fifo_order():
    q = TaskQueue()
    t1 = _task(TaskType.RESEARCH)
    t2 = _task(TaskType.ANALYSIS)
    q.enqueue(t1)
    q.enqueue(t2)
    assert q.dequeue().id == t1.id
    assert q.dequeue().id == t2.id


def test_dequeue_on_empty_queue_returns_none():
    assert TaskQueue().dequeue() is None


def test_depth_reflects_current_size():
    q = TaskQueue()
    assert q.depth == 0
    q.enqueue(_task())
    assert q.depth == 1
    q.dequeue()
    assert q.depth == 0


def test_is_empty_true_when_no_items():
    assert TaskQueue().is_empty


def test_is_empty_false_after_enqueue():
    q = TaskQueue()
    q.enqueue(_task())
    assert not q.is_empty


def test_enqueue_batch_adds_all_items():
    q = TaskQueue()
    tasks = [_task() for _ in range(4)]
    q.enqueue_batch(tasks)
    assert q.depth == 4


def test_peek_returns_head_without_removing():
    q = TaskQueue()
    task = _task()
    q.enqueue(task)
    assert q.peek().id == task.id
    assert q.depth == 1


def test_drain_returns_all_tasks_and_clears_queue():
    q = TaskQueue()
    tasks = [_task() for _ in range(3)]
    q.enqueue_batch(tasks)
    drained = q.drain()
    assert len(drained) == 3
    assert q.is_empty
