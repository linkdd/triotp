async def start(test_data):
    test_data.count += 1
    await test_data.stop.wait()
