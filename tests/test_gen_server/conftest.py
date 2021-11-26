import pytest

from . import sample_kvstore
import trio


class GenServerTestState:
    def __init__(self):
        self.ready = trio.Event()
        self.stopped = trio.Event()
        self.info = trio.Event()
        self.casted = trio.Event()

        self.data = {}
        self.did_raise = None
        self.terminated_with = None

        self.info_val = None
        self.unknown_info = []


@pytest.fixture
async def test_state(mailbox_env):
    test_state = GenServerTestState()

    async with trio.open_nursery() as nursery:
        nursery.start_soon(sample_kvstore.start, test_state)

        with trio.fail_after(0.1):
            await test_state.ready.wait()

        yield test_state

        nursery.cancel_scope.cancel()
