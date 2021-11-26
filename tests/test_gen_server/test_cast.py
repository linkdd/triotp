from . import sample_kvstore as kvstore
import trio


async def test_kvstore_cast_normal(test_state):
    await kvstore.special_cast.normal()

    with trio.fail_after(0.1):
        await test_state.casted.wait()


async def tests_kvstore_cast_stop(test_state):
    await kvstore.special_cast.stop()

    with trio.fail_after(0.1):
        await test_state.stopped.wait()

    assert test_state.terminated_with is None
    assert test_state.did_raise is None


async def test_kvstore_cast_fail(test_state):
    await kvstore.special_cast.fail()

    with trio.fail_after(0.1):
        await test_state.stopped.wait()

    assert isinstance(test_state.terminated_with, NotImplementedError)
    assert test_state.did_raise is test_state.terminated_with
