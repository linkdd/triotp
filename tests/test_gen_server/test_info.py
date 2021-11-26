from . import sample_kvstore as kvstore
import trio

async def test_kvstore_info_stop(test_state):
    await kvstore.special_info.stop()

    with trio.fail_after(0.1):
        await test_state.stopped.wait()

    assert test_state.terminated_with is None
    assert test_state.did_raise is None


async def test_kvstore_info_fail(test_state):
    await kvstore.special_info.fail()

    with trio.fail_after(0.1):
        await test_state.stopped.wait()

    assert isinstance(test_state.terminated_with, RuntimeError)
    assert test_state.did_raise is test_state.terminated_with


async def test_kvstore_info_matched(test_state):
    await kvstore.special_info.matched('foo')

    with trio.fail_after(0.1):
        await test_state.info.wait()

    assert test_state.info_val == 'foo'


async def test_kvstore_info_no_match(test_state):
    await kvstore.special_info.no_match('foo')

    with trio.fail_after(0.1):
        await test_state.info.wait()

    assert test_state.info_val is None
    assert len(test_state.unknown_info) == 1
    assert test_state.unknown_info[0] == ('special_info_no_match', 'foo')
