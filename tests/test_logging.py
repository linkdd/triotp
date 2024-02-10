import pytest

from triotp import logging
import logbook


def test_logenum():
    assert logging.LogLevel.DEBUG.to_logbook() == logbook.DEBUG
    assert logging.LogLevel.INFO.to_logbook() == logbook.INFO
    assert logging.LogLevel.WARNING.to_logbook() == logbook.WARNING
    assert logging.LogLevel.ERROR.to_logbook() == logbook.ERROR
    assert logging.LogLevel.CRITICAL.to_logbook() == logbook.CRITICAL

    with pytest.raises(LookupError):
        logging.LogLevel.NONE.to_logbook()


def test_logger(log_handler):
    logger = logging.getLogger("pytest")

    logger.debug("foo")
    assert log_handler.has_debug("foo", channel="pytest")

    logger.info("foo")
    assert log_handler.has_info("foo", channel="pytest")

    logger.warn("foo")
    assert log_handler.has_warning("foo", channel="pytest")

    logger.error("foo")
    assert log_handler.has_error("foo", channel="pytest")

    logger.critical("foo")
    assert log_handler.has_critical("foo", channel="pytest")
