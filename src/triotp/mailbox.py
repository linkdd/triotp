"""
In Erlang_/Elixir_, each process have a PID that can be used to receive message
from other processes.

.. _erlang: https://erlang.org
.. _elixir: https://elixir-lang.org/

With trio, there is no such thing as a process. There is only asynchronous tasks
started within a nursery.

This module provides an encapsulation of trio's memory channels_ which allows
tasks to communicate with each other.

.. _channels: https://trio.readthedocs.io/en/stable/reference-core.html#using-channels-to-pass-values-between-tasks

.. code-block:: python
   :caption: Example

   from triotp import mailbox


   async def task_a(task_status=trio.TASK_STATUS_IGNORED):
       async with mailbox.open(name='task_a') as mid:
           task_status.started(None)

           msg = await mailbox.receive(mid)
           print(msg)


   async def task_b():
       await mailbox.send('task_a', 'hello world')


   async def main():
       async with trio.open_nursery() as nursery:
           await nursery.start(task_a)
           nursery.start_soon(task_b)
"""

from collections.abc import Callable, Awaitable
from typing import Union, Optional, Any, AsyncIterator

from contextlib import asynccontextmanager
from contextvars import ContextVar
from uuid import uuid4

import trio


type MailboxID = str  #: Mailbox identifier (UUID4)

type MailboxRegistry = dict[
    MailboxID,
    tuple[trio.MemorySendChannel, trio.MemoryReceiveChannel],
]

type NameRegistry = dict[str, MailboxID]

context_mailbox_registry = ContextVar[MailboxRegistry]("mailbox_registry")
context_name_registry = ContextVar[NameRegistry]("name_registry")


class MailboxDoesNotExist(RuntimeError):
    """
    Error thrown when the mailbox identifier was not found.
    """

    def __init__(self, mid: MailboxID):
        super().__init__(f"mailbox {mid} does not exist")


class NameAlreadyExist(RuntimeError):
    """
    Error thrown when trying to register a mailbox to an already registered
    name.
    """

    def __init__(self, name: str):
        super().__init__(f"mailbox {name} already registered")


class NameDoesNotExist(RuntimeError):
    """
    Error thrown when trying to unregister a non-existing name.
    """

    def __init__(self, name: str):
        super().__init__(f"mailbox {name} does not exist")


def _init() -> None:
    context_mailbox_registry.set({})
    context_name_registry.set({})


def create() -> MailboxID:
    """
    Create a new mailbox.

    :returns: The mailbox unique identifier
    """

    mid = str(uuid4())

    mailbox_registry = context_mailbox_registry.get()
    mailbox_registry[mid] = trio.open_memory_channel(0)

    return mid


async def destroy(mid: MailboxID) -> None:
    """
    Close and destroy a mailbox.

    :param mid: The mailbox identifier
    :raises MailboxDoesNotExist: The mailbox identifier was not found
    """

    mailbox_registry = context_mailbox_registry.get()

    if mid not in mailbox_registry:
        raise MailboxDoesNotExist(mid)

    unregister_all(mid)

    wchan, rchan = mailbox_registry.pop(mid)
    await wchan.aclose()
    await rchan.aclose()


def register(mid: MailboxID, name: str) -> None:
    """
    Assign a name to a mailbox.

    :param mid: The mailbox identifier
    :param name: The new name

    :raises MailboxDoesNotExist: The mailbox identifier was not found
    :raises NameAlreadyExist: The name was already registered
    """

    mailbox_registry = context_mailbox_registry.get()

    if mid not in mailbox_registry:
        raise MailboxDoesNotExist(mid)

    name_registry = context_name_registry.get()
    if name in name_registry:
        raise NameAlreadyExist(name)

    name_registry[name] = mid


def unregister(name: str) -> None:
    """
    Unregister a mailbox's name.

    :param name: The name to unregister
    :raises NameDoesNotExist: The name was not found
    """

    name_registry = context_name_registry.get()
    if name not in name_registry:
        raise NameDoesNotExist(name)

    name_registry.pop(name)


def unregister_all(mid: MailboxID) -> None:
    """
    Unregister all names associated to a mailbox.

    :param mid: The mailbox identifier
    """

    name_registry = context_name_registry.get()

    for name, mailbox_id in list(name_registry.items()):
        if mailbox_id == mid:
            name_registry.pop(name)


@asynccontextmanager
async def open(name: Optional[str] = None) -> AsyncIterator[MailboxID]:
    """
    Shortcut for `create()`, `register()` followed by a `destroy()`.

    :param name: Optional name to register the mailbox
    :returns: Asynchronous context manager for the mailbox
    :raises NameAlreadyExist: If the `name` was already registered

    .. code-block:: python
       :caption: Example

       async with mailbox.open(name='foo') as mid:
           message = await mailbox.receive()
           print(message)
    """

    mid = create()

    try:
        if name is not None:
            register(mid, name)

        yield mid

    finally:
        await destroy(mid)


def _resolve(name: str) -> Optional[MailboxID]:
    name_registry = context_name_registry.get()
    return name_registry.get(name)


async def send(name_or_mid: Union[str, MailboxID], message: Any) -> None:
    """
    Send a message to a mailbox.

    :param name_or_mid: Either a registered name, or the mailbox identifier
    :param message: The message to send
    :raises MailboxDoesNotExist: The mailbox was not found
    """

    mailbox_registry = context_mailbox_registry.get()

    mid = _resolve(name_or_mid)
    if mid is None:
        mid = name_or_mid

    if mid not in mailbox_registry:
        raise MailboxDoesNotExist(mid)

    wchan, _ = mailbox_registry[mid]
    await wchan.send(message)


async def receive(
    mid: MailboxID,
    timeout: Optional[float] = None,
    on_timeout: Optional[Callable[[], Awaitable[Any]]] = None,
) -> Any:
    """
    Consume a message from a mailbox.

    :param mid: The mailbox identifier
    :param timeout: If set, the call will fail after the timespan set in seconds
    :param on_timeout: If set and `timeout` is set, instead of raising an
                       exception, the result of this async function will be
                       returned

    :raises MailboxDoesNotExist: The mailbox was not found
    :raises trio.TooSlowError: If `timeout` is set, but `on_timeout` isn't, and
                               no message was received during the timespan set
    """

    mailbox_registry = context_mailbox_registry.get()

    if mid not in mailbox_registry:
        raise MailboxDoesNotExist(mid)

    _, rchan = mailbox_registry[mid]

    if timeout is not None:
        try:
            with trio.fail_after(timeout):
                return await rchan.receive()

        except trio.TooSlowError:
            if on_timeout is None:
                raise

            return await on_timeout()

    else:
        return await rchan.receive()
