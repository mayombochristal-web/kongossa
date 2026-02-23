# ==========================================================
# FREE-KONGOSSA REALTIME SERVER v1
# TTU-MC3 / TST Synchronisation Engine
# ==========================================================

import asyncio
import websockets
import json
import time

# tunnels actifs
tunnels = {}

# statistiques
stats = {
    "users": 0,
    "messages": 0
}


# ----------------------------------------------------------
# Broadcast sécurisé
# ----------------------------------------------------------
async def broadcast(tunnel, payload, sender=None):

    if tunnel not in tunnels:
        return

    dead = set()

    for client in tunnels[tunnel]:
        try:
            if client != sender:
                await client.send(payload)
        except:
            dead.add(client)

    # nettoyage connexions mortes
    for d in dead:
        tunnels[tunnel].discard(d)


# ----------------------------------------------------------
# Handler principal
# ----------------------------------------------------------
async def handler(ws):

    tunnel = None

    stats["users"] += 1

    try:
        async for message in ws:

            data = json.loads(message)

            # ================= JOIN =================
            if data["type"] == "join":

                tunnel = data["tunnel"]

                if tunnel not in tunnels:
                    tunnels[tunnel] = set()

                tunnels[tunnel].add(ws)

                await broadcast(
                    tunnel,
                    json.dumps({
                        "type": "presence",
                        "count": len(tunnels[tunnel])
                    })
                )

            # ================= MESSAGE =================
            elif data["type"] == "message":

                stats["messages"] += 1

                data["server_ts"] = time.time()

                await broadcast(
                    tunnel,
                    json.dumps(data),
                    sender=ws
                )

    except Exception as e:
        print("Client error:", e)

    finally:

        stats["users"] -= 1

        if tunnel and ws in tunnels.get(tunnel, set()):
            tunnels[tunnel].remove(ws)

            await broadcast(
                tunnel,
                json.dumps({
                    "type": "presence",
                    "count": len(tunnels[tunnel])
                })
            )


# ----------------------------------------------------------
# Lancement serveur
# ----------------------------------------------------------
async def main():

    print("🚀 FREE-KONGOSSA REALTIME ONLINE")

    async with websockets.serve(
        handler,
        "0.0.0.0",
        8765,
        ping_interval=20,
        ping_timeout=20,
        max_size=10_000_000
    ):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())