import pytest

from triotp import application, supervisor
import trio

from .sample import app_c


async def test_app_stop(test_data, log_handler):
    async with trio.open_nursery() as nursery:
        application._init(nursery)

        await application.start(
            application.app_spec(
                module=app_c,
                start_arg=test_data,
                permanent=True,
            )
        )

        await trio.sleep(0.01)
        await application.stop(app_c.__name__)

    assert test_data.count == 1
