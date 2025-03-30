import pytest

from triotp import mailbox
import trio


class Producer:
    def __init__(self, mbox):
        self.mbox = mbox

    async def __call__(self, message):
        await mailbox.send(self.mbox, message)


class Consumer:
    def __init__(self, mbox, timeout=None, with_on_timeout=True):
        self.mbox = mbox
        self.timeout = timeout
        self.with_on_timeout = with_on_timeout

        self.received_message = None
        self.timed_out = False

    async def on_timeout(self):
        self.timed_out = True
        return None

    async def __call__(self, task_status=trio.TASK_STATUS_IGNORED):
        async with mailbox.open(self.mbox) as mid:
            task_status.started(mid)

            cb = self.on_timeout if self.with_on_timeout else None
            self.received_message = await mailbox.receive(
                mid,
                timeout=self.timeout,
                on_timeout=cb,
            )


async def test_receive_no_timeout(mailbox_env):
    producer = Producer("pytest")
    consumer = Consumer("pytest")

    async with trio.open_nursery() as nursery:
        await nursery.start(consumer)
        nursery.start_soon(producer, "foo")

    assert not consumer.timed_out
    assert consumer.received_message == "foo"


async def test_receive_on_timeout(mailbox_env):
    consumer = Consumer("pytest", timeout=0.01)

    async with trio.open_nursery() as nursery:
        await nursery.start(consumer)

    assert consumer.timed_out
    assert consumer.received_message is None


async def test_receive_too_slow(mailbox_env):
    consumer = Consumer("pytest", timeout=0.01, with_on_timeout=False)

    with trio.testing.RaisesGroup(trio.TooSlowError, flatten_subgroups=True):
        async with trio.open_nursery() as nursery:
            await nursery.start(consumer)

    assert not consumer.timed_out
    assert consumer.received_message is None


async def test_no_mailbox(mailbox_env):
    producer = Producer("pytest")

    with pytest.raises(mailbox.MailboxDoesNotExist):
        await producer("foo")

    with pytest.raises(mailbox.MailboxDoesNotExist):
        await mailbox.receive("pytest")


async def test_direct(mailbox_env):
    consumer = Consumer(None)

    async with trio.open_nursery() as nursery:
        mid = await nursery.start(consumer)
        producer = Producer(mid)
        nursery.start_soon(producer, "foo")

    assert not consumer.timed_out
    assert consumer.received_message == "foo"


async def test_register(mailbox_env):
    consumer = Consumer("pytest")

    with pytest.raises(mailbox.MailboxDoesNotExist):
        mailbox.register("not-found", "pytest")

    with trio.testing.RaisesGroup(mailbox.NameAlreadyExist, flatten_subgroups=True):
        async with trio.open_nursery() as nursery:
            await nursery.start(consumer)
            await nursery.start(consumer)


async def test_unregister(mailbox_env):
    consumer = Consumer("pytest")
    producer = Producer("pytest")

    with trio.testing.RaisesGroup(mailbox.MailboxDoesNotExist, flatten_subgroups=True):
        async with trio.open_nursery() as nursery:
            await nursery.start(consumer)

            mailbox.unregister("pytest")

            with pytest.raises(mailbox.NameDoesNotExist):
                mailbox.unregister("pytest")

            nursery.start_soon(producer, "foo")


async def test_destroy_unknown(mailbox_env):
    with pytest.raises(mailbox.MailboxDoesNotExist):
        await mailbox.destroy("not-found")
