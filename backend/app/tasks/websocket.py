from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from .redis_client import redis_client
import asyncio

router = APIRouter()

connected_clients = []

@router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):

    await websocket.accept()

    connected_clients.append(websocket)

    pubsub = redis_client.pubsub()

    await pubsub.subscribe("risk-alerts")

    print("Client connected")

    try:

        while True:

            message = await pubsub.get_message(
                ignore_subscribe_messages=True
            )

            if message:

                data = message["data"]

                disconnected_clients = []

                for client in connected_clients:

                    try:
                        await client.send_text(data)

                    except:
                        disconnected_clients.append(client)

                for client in disconnected_clients:
                    connected_clients.remove(client)

            await asyncio.sleep(0.1)

    except WebSocketDisconnect:

        connected_clients.remove(websocket)

        print("Client disconnected")