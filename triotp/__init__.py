"""
TriOTP is built on top of the Trio_ async library. Therefore, it is not directly
compatible with AsyncIO libraries.

.. _trio: https://trio.readthedocs.io

This library revolves around the folllwing concepts:

 - a Node represent a single asynchronous loop (`trio.run`)
 - an application represent the root of a supervision tree
 - a supervisor handles automatic restart of child processes
 - a mailbox enables message passing between asynchronous tasks

On top of this concepts, this library provides:

 - generic servers to handle requests from other tasks
 - dynamic supervisors to schedule new tasks

.. _zeromq: https://zeromq.org/languages/python/

   **NB:** You don't get distributed computing out of the box like you would
   with Erlang_/Elixir_, this library is single-threaded and works within a
   Python application only.

.. _erlang: https://erlang.org
.. _elixir: https://elixir-lang.org/
"""
