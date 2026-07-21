"""
Shared helper for fire-and-forget background tasks.

`asyncio.create_task(...)` without keeping a reference is a real footgun:
the event loop only holds a *weak* reference to the task, so it can be
garbage-collected mid-execution with no warning (see the note in the
asyncio docs on "Save a reference to the result"). `track()` keeps a
strong reference in a module-level set for the task's lifetime and
removes it automatically on completion, so callers get fire-and-forget
semantics without risking early GC.
"""
import asyncio
from collections.abc import Coroutine
from typing import Any

# Strong references to in-flight background tasks, keyed by nothing —
# just held until each task finishes, then discarded via the done callback.
_background_tasks: set[asyncio.Task] = set()


def track(coro: Coroutine[Any, Any, Any]) -> asyncio.Task:
    """
    Schedule `coro` as a background task and keep a strong reference to it
    until it completes, so it can't be garbage-collected mid-execution.
    """
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task
