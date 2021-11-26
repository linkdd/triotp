Message-Passing between tasks with mailboxes
============================================

**trio** provides a mechanism to exchange messages between asynchronous tasks.

The **triotp** mailbox is an abstraction of that mechanism. This abstraction can
be used without the rest of **triotp**.

In this tutorial, we'll see how it works.

Initializing the mailbox registry
---------------------------------

This step is done automatically when a node starts, but it is required if you
want to use it standalone:

.. code-block:: python

   from triotp import mailbox
   import trio


   async def main():
       mailbox._init()


   trio.run(main)


Creating a mailbox
------------------

There is 2 ways of creating a mailbox:

.. code-block:: python

   async def your_task():
       mid = mailbox.create()
       # do stuff
       await mailbox.destroy(mid)

Or:

.. code-block:: python

   async def your_task():
       async with mailbox.open() as mid:
           # do stuff

The `mid` variable holds a unique reference to the mailbox. But it can be hard to
pass this reference between tasks. Therefore, you can register a name referencing
this identifier:

.. code-block:: python

   async def your_task():
       mid = mailbox.create()
       mailbox.register(mid, 'foo')
       # do stuff
       await mailbox.destroy()

Or:

.. code-block:: python

   async def your_task():
       async with mailbox.open(name='foo'):
           # do stuff

Sending and receiving messages
------------------------------

In this example, we create a mailbox, wait for a single message, then close it:

.. code-block:: python

   from triotp import mailbox
   import trio


   async def consumer(task_status=trio.TASK_STATUS_IGNORED):
       async with mailbox.open('foo') as mid:
           task_status.started(None)

           message = await mailbox.receive(mid)
           print(message)


   async def producer():
       await mailbox.send('foo', 'Hello World!')


   async def main():
       async with trio.open_nursery() as nursery:
           await nursery.start(consumer)
           nursery.start_soon(producer)


   trio.run(main)
