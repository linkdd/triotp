"""
A TriOTP node encapsulates the call to `trio.run` and allows you to specify a
list of application to start.

   **NB:** There is no dependency management between applications, it's up to
   you to start the correct applications in the right order.

.. code-block:: python
   :caption: Example

   from pyotp import node, application

   from myproject import myapp1, myapp2

   node.run(
       apps=[
           application.app_spec(
               module=myapp1,
               start_arg=[],
           ),
           application.app_spec(
               module=myapp2,
               start_arg=[],
               permanent=False,
           ),
       ],
   )
"""

from typing import Optional

import sys

from logbook import StreamHandler, NullHandler  # type: ignore[import-untyped]
import trio

from triotp import mailbox, application, logging


def run(
    apps: list[application.app_spec],
    loglevel: logging.LogLevel = logging.LogLevel.NONE,
    logformat: Optional[str] = None,
) -> None:
    """
    Start a new node by calling `trio.run`.

    :param apps: List of application to start
    :param loglevel: Logging Level of the node
    :param logformat: Format of log messages produced by the node
    """

    match loglevel:
        case logging.LogLevel.NONE:
            handler = NullHandler()

        case _:
            handler = StreamHandler(sys.stdout, level=loglevel.to_logbook())

    if logformat is not None:
        handler.format_string = logformat

    with handler.applicationbound():
        trio.run(_start, apps)


async def _start(apps: list[application.app_spec]) -> None:
    mailbox._init()

    async with trio.open_nursery() as nursery:
        application._init(nursery)

        for app_spec in apps:
            await application.start(app_spec)
