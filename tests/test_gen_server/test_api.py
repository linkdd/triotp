import pytest

from . import sample_kvstore as kvstore


async def test_kvstore_api(test_state):
    val = await kvstore.api.get('foo')
    assert val is None

    val = await kvstore.api.set('foo', 'bar')
    assert val is None

    val = await kvstore.api.get('foo')
    assert val == 'bar'

    val = await kvstore.api.set('foo', 'baz')
    assert val == 'bar'

    val = await kvstore.api.get('foo')
    assert val == 'baz'

    with pytest.raises(NotImplementedError):
        await kvstore.api.clear()
