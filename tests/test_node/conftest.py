import pytest


class SampleData:
    def __init__(self):
        self.count = 0


@pytest.fixture
def test_data():
    return SampleData()
