import pytest

from . import sample_kvstore as kvstore

from triotp.gen_server import GenServerExited
import trio


async def test_kvstore_call_delayed(test_state):
    async with trio.open_nursery() as nursery:
        resp = await kvstore.special_call.delayed(nursery)

    assert resp == "done"


async def test_kvstore_call_timeout(test_state):
    with pytest.raises(trio.TooSlowError):
        await kvstore.special_call.timedout(0.01)


async def test_kvstore_call_stopped(test_state):
    with pytest.raises(GenServerExited):
        await kvstore.special_call.stopped()

    with trio.fail_after(0.1):
        await test_state.stopped.wait()

    assert test_state.terminated_with is None
    assert test_state.did_raise is None


async def test_kvstore_call_failure(test_state):
    with pytest.raises(GenServerExited):
        await kvstore.special_call.failure()

    with trio.fail_after(0.1):
        await test_state.stopped.wait()

    assert isinstance(test_state.terminated_with, RuntimeError)
    assert test_state.did_raise is test_state.terminated_with
