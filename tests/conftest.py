import pytest

from triotp import mailbox, application
import trio

import logbook


@pytest.fixture
def log_handler():
    handler = logbook.TestHandler(level=logbook.DEBUG)

    with handler.applicationbound():
        yield handler


@pytest.fixture
def mailbox_env():
    mailbox._init()
