import pytest

from triotp import application, supervisor
import trio

from .sample import app_a, app_b


@pytest.mark.parametrize("max_restarts", [1, 3, 5])
async def test_app_automatic_restart_permanent(test_data, max_restarts, log_handler):
    async with trio.open_nursery() as nursery:
        application._init(nursery)

        await application.start(
            application.app_spec(
                module=app_a,
                start_arg=test_data,
                permanent=True,
                opts=supervisor.options(
                    max_restarts=max_restarts,
                ),
            )
        )

    assert test_data.count == (max_restarts + 1)
    assert log_handler.has_errors


@pytest.mark.parametrize("max_restarts", [1, 3, 5])
async def test_app_automatic_restart_crash(test_data, max_restarts, log_handler):
    with trio.testing.RaisesGroup(RuntimeError, flatten_subgroups=True):
        async with trio.open_nursery() as nursery:
            application._init(nursery)

            await application.start(
                application.app_spec(
                    module=app_b,
                    start_arg=test_data,
                    permanent=False,
                    opts=supervisor.options(
                        max_restarts=max_restarts,
                    ),
                )
            )

    assert test_data.count == (max_restarts + 1)
    assert log_handler.has_errors


async def test_app_no_automatic_restart(test_data, log_handler):
    async with trio.open_nursery() as nursery:
        application._init(nursery)

        await application.start(
            application.app_spec(
                module=app_a,
                start_arg=test_data,
                permanent=False,
            )
        )

    assert test_data.count == 1
    assert not log_handler.has_errors
