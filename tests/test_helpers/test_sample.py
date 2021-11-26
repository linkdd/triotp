from . import sample


def test_current_module():
    assert sample is sample.__module__
    assert sample is not sample.get_module()
