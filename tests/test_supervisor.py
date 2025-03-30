import pytest

from triotp import supervisor
import trio


class SampleData:
    def __init__(self):
        self.exec_count = 0


async def sample_task(test_data):
    test_data.exec_count += 1


async def sample_task_error(test_data):
    test_data.exec_count += 1
    raise RuntimeError("pytest")


@pytest.mark.parametrize("max_restarts", [1, 3, 5])
async def test_automatic_restart_permanent(max_restarts, log_handler):
    test_data = SampleData()

    async with trio.open_nursery() as nursery:
        children = [
            supervisor.child_spec(
                id="sample_task",
                task=sample_task,
                args=[test_data],
                restart=supervisor.restart_strategy.PERMANENT,
            ),
        ]
        opts = supervisor.options(
            max_restarts=max_restarts,
            max_seconds=5,
        )
        await nursery.start(supervisor.start, children, opts)

    assert test_data.exec_count == (max_restarts + 1)
    assert log_handler.has_errors


@pytest.mark.parametrize("max_restarts", [1, 3, 5])
@pytest.mark.parametrize(
    "strategy",
    [
        supervisor.restart_strategy.PERMANENT,
        supervisor.restart_strategy.TRANSIENT,
    ],
)
async def test_automatic_restart_crash(max_restarts, strategy, log_handler):
    test_data = SampleData()

    with trio.testing.RaisesGroup(RuntimeError, flatten_subgroups=True):
        async with trio.open_nursery() as nursery:
            children = [
                supervisor.child_spec(
                    id="sample_task",
                    task=sample_task_error,
                    args=[test_data],
                    restart=strategy,
                ),
            ]
            opts = supervisor.options(
                max_restarts=max_restarts,
                max_seconds=5,
            )
            await nursery.start(supervisor.start, children, opts)

    assert test_data.exec_count == (max_restarts + 1)
    assert log_handler.has_errors


@pytest.mark.parametrize(
    "strategy",
    [
        supervisor.restart_strategy.TEMPORARY,
        supervisor.restart_strategy.TRANSIENT,
    ],
)
async def test_no_restart(strategy, log_handler):
    test_data = SampleData()

    async with trio.open_nursery() as nursery:
        children = [
            supervisor.child_spec(
                id="sample_task",
                task=sample_task,
                args=[test_data],
                restart=strategy,
            ),
        ]
        opts = supervisor.options(
            max_restarts=3,
            max_seconds=5,
        )
        await nursery.start(supervisor.start, children, opts)

    assert test_data.exec_count == 1
    assert not log_handler.has_errors
