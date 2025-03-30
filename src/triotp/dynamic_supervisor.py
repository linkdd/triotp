"""
A dynamic supervisor is almost identical to a normal supervisor.

The only difference is that a dynamic supervisor creates a mailbox in order to
receive requests to start new children from other tasks.

.. code-block:: python
   :caption: Example

   # app.py

   from triotp import supervisor, dynamic_supervisor
   import trio

   from . import worker


   async def start():
       opts = supervisor.options()
       children = [
           supervisor.child_spec(
               id='worker_pool',
               task=dynamic_supervisor.start,
               args=[opts, 'worker-pool'],
           ),
       ]

       async with trio.open_nursery() as nursery:
           await nursery.start_soon(supervisor.start, children, opts)

           await dynamic_supervisor.start_child(
               'worker-pool',
               supervisor.child_spec(
                   id='worker-0',
                   task=worker.start,
                   args=[],
                   restart=supervisor.restart_strategy.TRANSIENT,
               ),
           )
"""

from typing import Optional, Union

import trio

from triotp import supervisor, mailbox


async def start(
    opts: supervisor.options,
    name: Optional[str] = None,
    task_status=trio.TASK_STATUS_IGNORED,
) -> None:
    """
    Starts a new dynamic supervisor.

    This function creates a new mailbox to receive request for new children.

    :param opts: Supervisor options
    :param name: Optional name to use to register the supervisor's mailbox
    :param task_status: Used to notify the trio nursery that the supervisor is ready
    :raises triotp.mailbox.NameAlreadyExist: If the `name` was already registered

    .. code-block:: python
       :caption: Example

       from triotp import dynamic_supervisor, supervisor
       import trio


       async def example():
           opts = supervisor.options()
           child_spec = # ...

           async with trio.open_nursery() as nursery:
               mid = await nursery.start(dynamic_supervisor.start, opts)
               await dynamic_supervisor.start_child(mid, child_spec)
    """

    async with mailbox.open(name) as mid:
        task_status.started(mid)

        async with trio.open_nursery() as nursery:
            await nursery.start(_child_listener, mid, opts, nursery)


async def start_child(
    name_or_mid: Union[str, mailbox.MailboxID],
    child_spec: supervisor.child_spec,
) -> None:
    """
    Start a new task in the specified supervisor.

    :param name_or_mid: Dynamic supervisor's mailbox identifier
    :param child_spec: Child specification to start
    """

    await mailbox.send(name_or_mid, child_spec)


async def _child_listener(
    mid: mailbox.MailboxID,
    opts: supervisor.options,
    nursery: trio.Nursery,
    task_status=trio.TASK_STATUS_IGNORED,
) -> None:
    task_status.started(None)

    while True:
        request = await mailbox.receive(mid)

        match request:
            case supervisor.child_spec() as spec:
                await nursery.start(supervisor._child_monitor, spec, opts)

            case _:
                pass
