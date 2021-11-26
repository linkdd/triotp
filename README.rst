TriOTP, the OTP framework for Python Trio
=========================================

See documentation_ for more informations.

.. _documentation: https://linkdd.github.io/triotp

.. image:: https://img.shields.io/pypi/l/triotp.svg?style=flat-square
   :target: https://pypi.python.org/pypi/triotp/
   :alt: License

.. image:: https://img.shields.io/pypi/status/triotp.svg?style=flat-square
   :target: https://pypi.python.org/pypi/triotp/
   :alt: Development Status

.. image:: https://img.shields.io/pypi/v/triotp.svg?style=flat-square
   :target: https://pypi.python.org/pypi/triotp/
   :alt: Latest release

.. image:: https://img.shields.io/pypi/pyversions/triotp.svg?style=flat-square
   :target: https://pypi.python.org/pypi/triotp/
   :alt: Supported Python versions

.. image:: https://img.shields.io/pypi/implementation/triotp.svg?style=flat-square
   :target: https://pypi.python.org/pypi/triotp/
   :alt: Supported Python implementations

.. image:: https://img.shields.io/pypi/wheel/triotp.svg?style=flat-square
   :target: https://pypi.python.org/pypi/triotp
   :alt: Download format

.. image:: https://github.com/linkdd/triotp/actions/workflows/test-suite.yml/badge.svg
   :target: https://github.com/linkdd/triotp
   :alt: Build status

.. image:: https://coveralls.io/repos/github/linkdd/triotp/badge.svg?style=flat-square
   :target: https://coveralls.io/r/linkdd/triotp
   :alt: Code test coverage

.. image:: https://img.shields.io/pypi/dm/triotp.svg?style=flat-square
   :target: https://pypi.python.org/pypi/triotp/
   :alt: Downloads

Introduction
------------

This project is a simplified implementation of the Erlang_/Elixir_ OTP_
framework.

.. _erlang: https://erlang.org
.. _elixir: https://elixir-lang.org/
.. _otp: https://en.wikipedia.org/wiki/Open_Telecom_Platform

It is built on top of the Trio_ async library and provides:

 - **applications:** the root of a supervision tree
 - **supervisors:** automatic restart of children tasks
 - **mailboxes:** message-passing between tasks
 - **gen_servers:** generic server task

.. _trio: https://trio.readthedocs.io

Why ?
-----

Since I started writing Erlang/Elixir code, I've always wanted to use its
concepts in other languages.

I made this library for fun and most importantly: to see if it was possible.
As it turns out, it is!