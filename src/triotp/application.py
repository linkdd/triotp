"""
An application is a Python module defining an asynchronous function `start`.

.. code-block:: python
   :caption: Example

   async def start(_start_arg):
       print('Hello world')

Usually, the application will start a supervisor containing the child tasks to
run.
"""

from typing import Optional, Any
from types import ModuleType


from contextvars import ContextVar
from dataclasses import dataclass

import trio

from triotp import supervisor


context_app_nursery = ContextVar[trio.Nursery]("app_nursery")
context_app_registry = ContextVar[dict[str, trio.Nursery]]("app_registry")


@dataclass
class app_spec:
    """Describe an application"""

    module: ModuleType  #: Application module
    start_arg: Any  #: Argument to pass to the module's start function
    permanent: bool = (
        True  #: If `False`, the application won't be restarted if it exits
    )
    opts: Optional[supervisor.options] = (
        None  #: Options for the supervisor managing the application task
    )


def _init(nursery: trio.Nursery) -> None:
    context_app_nursery.set(nursery)
    context_app_registry.set({})


async def start(app: app_spec) -> None:
    """
    Starts an application on the current node. If the application is already
    started, it does nothing.

       **NB:** This function cannot be called outside a node.

    :param app: The application to start
    """

    nursery = context_app_nursery.get()
    registry = context_app_registry.get()

    if app.module.__name__ not in registry:
        local_nursery = await nursery.start(_app_scope, app)
        assert local_nursery is not None

        registry[app.module.__name__] = local_nursery


async def stop(app_name: str) -> None:
    """
    Stops an application. If the application was not running, it does nothing.

       **NB:** This function cannot be called outside a node.

    :param app_name: `__name__` of the application module
    """

    registry = context_app_registry.get()

    if app_name in registry:
        local_nursery = registry.pop(app_name)
        local_nursery.cancel_scope.cancel()


async def _app_scope(app: app_spec, task_status=trio.TASK_STATUS_IGNORED):
    if app.permanent:
        restart = supervisor.restart_strategy.PERMANENT

    else:
        restart = supervisor.restart_strategy.TRANSIENT

    async with trio.open_nursery() as nursery:
        task_status.started(nursery)

        children = [
            supervisor.child_spec(
                id=app.module.__name__,
                task=app.module.start,
                args=[app.start_arg],
                restart=restart,
            )
        ]
        opts = app.opts if app.opts is not None else supervisor.options()

        nursery.start_soon(supervisor.start, children, opts)
