import asyncio
import time

async def func():
    time.sleep(10)
    print("done")
    return("doneV2")

async def main():
    asyncio.create_task(func())
    await asyncio.sleep(60)

asyncio.run(main())