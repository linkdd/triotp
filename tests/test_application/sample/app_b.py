async def start(test_data):
    test_data.count += 1
    raise RuntimeError('pytest')
