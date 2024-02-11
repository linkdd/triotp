"""
A supervisor is used to handle a set of asynchronous tasks. It takes care of
restarting them if they exit prematurely or if they crash.

.. code-block:: python
   :caption: Example

   from triotp import supervisor
   from random import random
   import trio

   async def loop(threshold):
       while True:
           if random() < threshold:
               raise RuntimeError('bad luck')

           else:
               await trio.sleep(0.1)

   async def start_supervisor():
       children = [
           supervisor.child_spec(
               id='loop',
               task=loop,
               args=[0.5],
               restart=supervisor.restart_strategy.PERMANENT,
           ),
       ]
       opts = supervisor.options(
           max_restarts=3,
           max_seconds=5
       )
       await supervisor.start(children, opts)
"""

from dataclasses import dataclass
from collections import deque
from enum import Enum, auto
from logbook import Logger
import tenacity

import trio_util
import trio

from collections.abc import Callable, Awaitable
from typing import Any


class restart_strategy(Enum):
    """
    Describe when to restart an asynchronous task.
    """

    PERMANENT = auto()  #: Always restart the task
    TRANSIENT = auto()  #: Restart the task only if it raises an exception
    TEMPORARY = auto()  #: Never restart a task


@dataclass
class child_spec:
    """
    Describe an asynchronous task to supervise.
    """

    id: str  #: Task identifier
    task: Callable[..., Awaitable[None]]  #: The task to run
    args: list[Any]  #: Arguments to pass to the task
    restart: restart_strategy = restart_strategy.PERMANENT  #: When to restart the task


@dataclass
class options:
    """
    Describe the options for the supervisor.
    """

    max_restarts: int = 3  #: Maximum number of restart during a limited timespan
    max_seconds: int = 5  #: Timespan duration


class _retry_strategy:
    def __init__(
        self,
        restart: restart_strategy,
        max_restarts: int,
        max_seconds: float,
    ):
        self.restart = restart
        self.max_restarts = max_restarts
        self.max_seconds = max_seconds

        self.failure_times = deque()

    def __call__(self, retry_state: tenacity.RetryCallState):
        match self.restart:
            case restart_strategy.PERMANENT:
                pass

            case restart_strategy.TRANSIENT:
                if not retry_state.outcome.failed:
                    return False

            case restart_strategy.TEMPORARY:
                return False

        now = trio.current_time()
        self.failure_times.append(now)

        if len(self.failure_times) <= self.max_restarts:
            return True

        oldest_failure = self.failure_times.popleft()
        return now - oldest_failure >= self.max_seconds


class _retry_logger:
    def __init__(self, child_id: str):
        self.logger = Logger(child_id)

    def __call__(self, retry_state: tenacity.RetryCallState) -> None:
        if isinstance(retry_state.outcome.exception(), trio.Cancelled):
            self.logger.info("task cancelled")

        elif retry_state.outcome.failed:
            exception = retry_state.outcome.exception()
            exc_info = (exception.__class__, exception, exception.__traceback__)
            self.logger.error("restarting task after failure", exc_info=exc_info)

        else:
            self.logger.error("restarting task after unexpected exit")


async def start(
    child_specs: list[child_spec],
    opts: options,
    task_status=trio.TASK_STATUS_IGNORED,
) -> None:
    """
    Start the supervisor and its children.

    :param child_specs: Asynchronous tasks to supervise
    :param opts: Supervisor options
    :param task_status: Used to notify the trio nursery that the task is ready

    .. code-block:: python
       :caption: Example

       from triotp import supervisor
       import trio

       async def example():
           children_a = [
               # ...
           ]
           children_b = [
               # ...
           ]
           opts = supervisor.options()

           async with trio.open_nursery() as nursery:
               await nursery.start(supervisor.start, children_a, opts)
               await nursery.start(supervisor.start, children_b, opts)
    """

    async with trio.open_nursery() as nursery:
        for spec in child_specs:
            await nursery.start(_child_monitor, spec, opts)

        task_status.started(None)


async def _child_monitor(
    spec: child_spec,
    opts: options,
    task_status=trio.TASK_STATUS_IGNORED,
) -> None:
    task_status.started(None)

    @tenacity.retry(
        retry=_retry_strategy(spec.restart, opts.max_restarts, opts.max_seconds),
        reraise=True,
        sleep=trio.sleep,
        after=_retry_logger(spec.id),
    )
    async def _child_runner():
        with trio_util.defer_to_cancelled():
            async with trio.open_nursery() as nursery:
                nursery.start_soon(spec.task, *spec.args)

    await _child_runner()
