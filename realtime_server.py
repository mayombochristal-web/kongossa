import asyncio
import websockets

clients = set()

async def handler(ws):
    clients.add(ws)
    try:
        async for message in ws:
            for c in clients:
                if c != ws:
                    await c.send(message)
    finally:
        clients.remove(ws)

async def main():
    async with websockets.serve(handler, "localhost", 8765):
        print("KONGOSSA Realtime Server ON")
        await asyncio.Future()

asyncio.run(main())

python realtime_server.py