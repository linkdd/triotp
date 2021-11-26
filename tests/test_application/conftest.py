import pytest

import trio


class SampleData:
    def __init__(self):
        self.count = 0
        self.stop = trio.Event()


@pytest.fixture
def test_data():
    return SampleData()
