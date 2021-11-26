A simple application
====================

In this tutorial, we will create a single application with 2 processes:

 - a generic server which echo messages
 - a client to interact with the generic server

First, let's create our folder structure:

.. code-block:: shell

   $ mkdir simple_triotp
   $ touch simple_triotp/__init__.py

The Generic Server
------------------

A generic server is an abstract of a process with a mailbox receiving messages
and sending responses back to the caller (server/client architecture).

Let's create a file `simple_triotp/echo_server.py`:

.. code-block:: python

   from triotp.helpers import current_module
   from triotp import gen_server


   __module__ = current_module()


   async def start():
       await gen_server.start(__module__, init_arg=None, name=__name__)


   async def echo(message):
       return await gen_server.call(__name__, ('echo', message))


   async def stop():
       await gen_server.cast(__name__, 'stop')

   # gen_server callbacks

   async def init(_init_arg):
       return 'nostate'


   async def terminate(reason, state):
       print('exited with reason', reason, 'and state', state)


   async def handle_call(message, _caller, state):
       match message:
           case ('echo', message):
               return (gen_server.Reply(message), state)

           case _:
               exc = NotImplementedError('unkown command')
               return (gen_server.Reply(exc), state)


   async def handle_cast(message, state):
       match message:
           case 'stop':
               return (gen_server.Stop(), state)

           case _:
               exc = NotImplementedError('unknown command')
               return (gen_server.Stop(exc), state)

Let's look at it step by step:

.. code-block:: python

   async def start():
       await gen_server.start(__module__, init_arg=None, name=__name__)

This function will start our generic server:

 - the first argument is the module which defines our callbacks:
    - `init`: to create the state of the server
    - `terminate`: called whenever the generic server stops
    - `handle_call`: called whenever a call to the generic server is made
    - `handle_cast`: called whenever a cast to the generic server is made
    - `handle_info`: called whenever a message is sent directly to the generic server's mailbox
 - the second argument is the value passed to the `init` callback
 - the third argument is the name to use to send message to the generic server's mailbox

.. code-block:: python

   async def echo(message):
       return await gen_server.call(__name__, ('echo', message))

The `gen_server.call()` function sends a message to the generic server's mailbox,
and then wait for a response. The request is handled by the `handle_call` callback.

**NB:** If the response is an exception, it will be raised as soon as it is
received, delegating the error handling to the caller.

.. code-block:: python

   async def stop():
       await gen_server.cast(__name__, 'stop')

The `gen_server.cast()` function sends a message to the generic server's mailbox,
but it does not wait for a response and returns immediately. The request will be
handled by the `handle_cast` callback.

You can also send messages directly to the generic server's maiblox:

.. code-block:: python

   async def notify():
       await mailbox.send(__name__, 'notify')

The message will then be handled by the `handle_info` callback.
This is useful to allow a generic server to send messages to itself.

.. code-block:: python

   async def init(_init_arg):
       return 'nostate'

This callback creates and return the state for the generic server. This state
will be passed to every other callback. It can be anything like:

 - a data structure
 - a database connection
 - a state machine
 - ...

.. code-block:: python

   async def terminate(reason, state):
       print('exited with reason', reason, 'and state', state)

This callback is called when the generic server is stopped. The `reason` is either
`None` or the exception that triggered the generic server to stop.

.. code-block:: python

   async def handle_call(message, _caller, state):
       match message:
           case ('echo', message):
               return (gen_server.Reply(message), state)

           case _:
               exc = NotImplementedError('unkown command')
               return (gen_server.Reply(exc), state)

This callback is called to handle requests made with `gen_server.call()`, it
must always return a tuple whose second element is the new state (for later calls
to any callback function).

The first argument can be either:

 - `gen_server.NoReply()`: implying a call to `gen_server.reply()` will be made
   in the future to send the response back to the caller
 - `gen_server.Reply()`: to send a response back to the caller
 - `gen_server.Stop(reason=None)`: to exit the generic server. The caller will
   then raise a `GenServerExited` exception

.. code-block:: python

   async def handle_cast(message, state):
       match message:
           case 'stop':
               return (gen_server.Stop(), state)

           case _:
               exc = NotImplementedError('unknown command')
               return (gen_server.Stop(exc), state)

This callback is called to handle requests made with `gen_server.call()`, it
must always return a tuple whose second element is the new state (for later calls
to any callback function).

The first argument can be either:

 - `gen_server.NoReply()`: no reply will be sent to the caller
 - `gen_server.Stop(reason=None)`: to exit the generic server

**NB:** the `handle_info` callback works exactly the same.

The client process
------------------

This task will only send some messages to the generic server, and finally stop it.

Let's create a `simple_triotp/echo_client.py` file:

.. code-block:: python

   from . import echo_server


   async def run():
       response = await echo_server.echo('hello')
       assert response == 'hello'

       response = await echo_server.echo('world')
       assert response == 'world'

       await echo_server.stop()

The supervisor
--------------

A supervisor handles automatic restart of its children whenever they exit
prematurely, or after a crash.

It is useful to restart a generic server handling connections to a database,
after a temporary network failure.

In this case, the supervisor will have 2 children, the generic server and the
client:

.. code-block:: python

   from triotp import supervisor
   from . import echo_server, echo_client


   async def start():
       children = [
           supervisor.child_spec(
               id='server',
               task=echo_server.start,
               args=[],
               restart=supervisor.restart_strategy.TRANSIENT,
           ),
           supervisor.child_spec(
               id='client',
               task=echo_client.run,
               args=[],
               restart=supervisor.restart_strategy.TRANSIENT,
           ),
       ]
       opts = supervisor.options(
           max_restarts=3,
           max_seconds=5,
       )
       await supervisor.start(children, opts)

There are 3 supported restart strategy:

 - `PERMANENT`: the task should always be restarted
 - `TRANSIENT`: the task should be restarted only if it crashed
 - `TEMPORARY`: the task should never be restarted

If a child restart more than `max_restarts` within a `max_seconds` period, the
supervisor will also crash (maybe a parent supervisor will try to restart it).

The application
---------------

An application is the root of a supervision tree.

We'll use this to start our supervisor, let's create a file
`simple_triotp/echo_app.py`:

.. code-block:: python

   from triotp.helpers import current_module
   from triotp import application
   from . import echo_supervisor


   __module__ = current_module()


   def spec():
       return application.app_spec(
           module=__module__,
           start_arg=None,
           permanent=False,
       )


   async def start(_start_arg):
       await echo_supervisor.start()

Starting the node
-----------------

Finally, we need to create our entrypoint, this can be done in the file
`simple_triotp/main.py`:

.. code-block:: python

   from triotp import node
   from . import echo_app


   def main():
       node.run(apps=[
           echo_app.spec(),
       ])


   if __name__ == '__main__':
       main()

Now, you can run the whole program with:

.. code-block:: shell

   $ python -m simple_triotp.main
