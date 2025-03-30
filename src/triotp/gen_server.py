"""
A generic server is an abstraction of a server loop built on top of the mailbox
module.

It is best used to build components that accept request from other components in
your application such as:

 - an in-memory key-value store
 - a TCP server handler
 - a finite state machine

There are 3 ways of sending messages to a generic server:

 - **cast:** send a message
 - **call:** send a message an wait for a response
 - directly to the mailbox

> **NB:** If a call returns an exception to the caller, the exception will be
> raised on the caller side.

.. code-block:: python
   :caption: Example

   from triotp.helpers import current_module
   from triotp import gen_server, mailbox


   __module__ = current_module()


   async def start():
       await gen_server.start(__module__, name='kvstore')


   async def get(key):
       return await gen_server.call('kvstore', ('get', key))


   async def set(key, val):
       return await gen_server.call('kvstore', ('set', key, val))


   async def stop():
       await gen_server.cast('kvstore', 'stop')


   async def printstate():
       await mailbox.send('kvstore', 'printstate')

   # gen_server callbacks

   async def init(_init_arg):
       state = {}
       return state


   # optional
   async def terminate(reason, state):
       if reason is not None:
           print('An error occured:', reason)

       print('Exited with state:', state)


   # if not defined, the gen_server will stop with a NotImplementedError when
   # receiving a call
   async def handle_call(message, _caller, state):
       match message:
           case ('get', key):
               val = state.get(key, None)
               return (gen_server.Reply(payload=val), state)

           case ('set', key, val):
               prev = state.get(key, None)
               state[key] = val
               return (gen_server.Reply(payload=prev), state)

           case _:
               exc = NotImplementedError('unknown request')
               return (gen_server.Reply(payload=exc), state)


   # if not defined, the gen_server will stop with a NotImplementedError when
   # receiving a cast
   async def handle_cast(message, state):
       match message:
           case 'stop':
               return (gen_server.Stop(), state)

           case _:
               print('unknown request')
               return (gen_server.NoReply(), state)


   # optional
   async def handle_info(message, state):
       match message:
           case 'printstate':
               print(state)

           case _:
               pass

       return (gen_server.NoReply(), state)
"""

from typing import TypeVar, Union, Optional, Any
from types import ModuleType

from dataclasses import dataclass

import trio

from triotp import mailbox, logging


State = TypeVar("State")


class GenServerExited(Exception):
    """
    Raised when the generic server exited during a call.
    """


@dataclass
class _Loop:
    yes: bool


@dataclass
class _Raise:
    exc: BaseException


Continuation = Union[_Loop, _Raise]


@dataclass
class Reply:
    """
    Return an instance of this class to send a reply to the caller.
    """

    payload: Any  #: The response to send back


@dataclass
class NoReply:
    """
    Return an instance of this class to not send a reply to the caller.
    """


@dataclass
class Stop:
    """
    Return an instance of this class to stop the generic server.
    """

    reason: Optional[BaseException] = (
        None  #: Eventual exception that caused the gen_server to stop
    )


@dataclass
class _CallMessage:
    source: trio.MemorySendChannel
    payload: Any


@dataclass
class _CastMessage:
    payload: Any


async def start(
    module: ModuleType,
    init_arg: Optional[Any] = None,
    name: Optional[str] = None,
) -> None:
    """
    Starts the generic server loop.

    :param module: Module containing the generic server's callbacks
    :param init_arg: Optional argument passed to the `init` callback
    :param name: Optional name to use to register the generic server's mailbox

    :raises triotp.mailbox.NameAlreadyExist: If the `name` was already registered
    :raises Exception: If the generic server terminated with a non-null reason
    """

    await _loop(module, init_arg, name)


async def call(
    name_or_mid: Union[str, mailbox.MailboxID],
    payload: Any,
    timeout: Optional[float] = None,
) -> Any:
    """
    Send a request to the generic server and wait for a response.

    This function creates a temporary bi-directional channel. The writer is
    passed to the `handle_call` function and is used to send the response back
    to the caller.

    :param name_or_mid: The generic server's mailbox identifier
    :param payload: The message to send to the generic server
    :param timeout: Optional timeout after which this function fails
    :returns: The response from the generic server
    :raises GenServerExited: If the generic server exited after handling the call
    :raises Exception: If the response is an exception

    """

    wchan, rchan = trio.open_memory_channel[Exception | Any](0)
    message = _CallMessage(source=wchan, payload=payload)

    await mailbox.send(name_or_mid, message)

    try:
        if timeout is not None:
            with trio.fail_after(timeout):
                val = await rchan.receive()

        else:
            val = await rchan.receive()

        if isinstance(val, Exception):
            raise val

        return val

    finally:
        await wchan.aclose()
        await rchan.aclose()


async def cast(
    name_or_mid: Union[str, mailbox.MailboxID],
    payload: Any,
) -> None:
    """
    Send a message to the generic server without expecting a response.

    :param name_or_mid: The generic server's mailbox identifier
    :param payload: The message to send
    """

    message = _CastMessage(payload=payload)
    await mailbox.send(name_or_mid, message)


async def reply(caller: trio.MemorySendChannel[Any], response: Any) -> None:
    """
    The `handle_call` callback can start a background task to handle a slow
    request and return a `NoReply` instance. Use this function in the background
    task to send the response to the caller at a later time.

    :param caller: The caller `SendChannel` to use to send the response
    :param response: The response to send back to the caller

    .. code-block:: python
       :caption: Example

       from triotp import gen_server, supervisor, dynamic_supervisor
       import trio


       async def slow_task(message, caller):
           # do stuff with message
           await gen_server.reply(caller, response)


       async def handle_call(message, caller, state):
           await dynamic_supervisor.start_child(
               'slow-task-pool',
               supervisor.child_spec(
                   id='some-slow-task',
                   task=slow_task,
                   args=[message, caller],
                   restart=supervisor.restart_strategy.TEMPORARY,
               ),
           )

           return (gen_server.NoReply(), state)
    """

    await caller.send(response)


async def _loop(
    module: ModuleType,
    init_arg: Optional[Any],
    name: Optional[str],
) -> None:
    async with mailbox.open(name) as mid:
        try:
            state: Any = await _init(module, init_arg)
            looping = True

            while looping:
                message = await mailbox.receive(mid)

                match message:
                    case _CallMessage(source, payload):
                        continuation, state = await _handle_call(
                            module, payload, source, state
                        )

                    case _CastMessage(payload):
                        continuation, state = await _handle_cast(module, payload, state)

                    case _:
                        continuation, state = await _handle_info(module, message, state)

                match continuation:
                    case _Loop(yes=False):
                        looping = False

                    case _Loop(yes=True):
                        looping = True

                    case _Raise(exc=err):
                        raise err

        except Exception as err:
            await _terminate(module, err, state)
            raise err from None

        else:
            await _terminate(module, None, state)


async def _init(module: ModuleType, init_arg: Any) -> State:
    return await module.init(init_arg)


async def _terminate(
    module: ModuleType,
    reason: Optional[BaseException],
    state: State,
) -> None:
    handler = getattr(module, "terminate", None)
    if handler is not None:
        await handler(reason, state)

    elif reason is not None:
        logger = logging.getLogger(module.__name__)
        logger.exception(reason)


async def _handle_call(
    module: ModuleType,
    message: Any,
    source: trio.MemorySendChannel,
    state: State,
) -> tuple[Continuation, State]:
    handler = getattr(module, "handle_call", None)
    if handler is None:
        raise NotImplementedError(f"{module.__name__}.handle_call")

    result = await handler(message, source, state)
    continuation: _Loop | _Raise

    match result:
        case (Reply(payload), new_state):
            state = new_state
            await reply(source, payload)
            continuation = _Loop(yes=True)

        case (NoReply(), new_state):
            state = new_state
            continuation = _Loop(yes=True)

        case (Stop(reason), new_state):
            state = new_state
            await reply(source, GenServerExited())

            if reason is not None:
                continuation = _Raise(reason)

            else:
                continuation = _Loop(yes=False)

        case _:
            raise TypeError(
                f"{module.__name__}.handle_call did not return a valid value"
            )

    return continuation, state


async def _handle_cast(
    module: ModuleType,
    message: Any,
    state: State,
) -> tuple[Continuation, State]:
    handler = getattr(module, "handle_cast", None)
    if handler is None:
        raise NotImplementedError(f"{module.__name__}.handle_cast")

    result = await handler(message, state)
    continuation: _Loop | _Raise

    match result:
        case (NoReply(), new_state):
            state = new_state
            continuation = _Loop(yes=True)

        case (Stop(reason), new_state):
            state = new_state

            if reason is not None:
                continuation = _Raise(reason)

            else:
                continuation = _Loop(yes=False)

        case _:
            raise TypeError(
                f"{module.__name__}.handle_cast did not return a valid value"
            )

    return continuation, state


async def _handle_info(
    module: ModuleType,
    message: Any,
    state: State,
) -> tuple[Continuation, State]:
    handler = getattr(module, "handle_info", None)
    if handler is None:
        return _Loop(yes=True), state

    result = await handler(message, state)
    continuation: _Loop | _Raise

    match result:
        case (NoReply(), new_state):
            state = new_state
            continuation = _Loop(yes=True)

        case (Stop(reason), new_state):
            state = new_state

            if reason is not None:
                continuation = _Raise(reason)

            else:
                continuation = _Loop(yes=False)

        case _:
            raise TypeError(
                f"{module.__name__}.handle_info did not return a valid value"
            )

    return continuation, state
