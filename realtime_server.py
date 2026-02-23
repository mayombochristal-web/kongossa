import asyncio
import websockets
import json
import os

tunnels = {}

async def broadcast(tunnel, payload, sender=None):
    if tunnel not in tunnels: return
    dead = set()
    for client in tunnels[tunnel]:
        try:
            if client != sender: await client.send(json.dumps(payload))
        except: dead.add(client)
    for d in dead: tunnels[tunnel].discard(d)

async def handler(ws):
    tunnel_id = None
    try:
        async for message in ws:
            data = json.loads(message)
            if data["type"] == "join":
                tunnel_id = data["tunnel"]
                if tunnel_id not in tunnels: tunnels[tunnel_id] = set()
                tunnels[tunnel_id].add(ws)
                await broadcast(tunnel_id, {"type": "presence", "count": len(tunnels[tunnel_id])})
            elif data["type"] == "message":
                await broadcast(tunnel_id, data, sender=ws)
    except: pass
    finally:
        if tunnel_id and tunnel_id in tunnels:
            tunnels[tunnel_id].discard(ws)
            await broadcast(tunnel_id, {"type": "presence", "count": len(tunnels[tunnel_id])})

async def main():
    port = int(os.environ.get("PORT", 8765))
    async with websockets.serve(handler, "0.0.0.0", port, ping_interval=20, ping_timeout=20):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
