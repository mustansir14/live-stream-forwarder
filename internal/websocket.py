from typing import List

from fastapi import WebSocket
from fastapi.websockets import WebSocketState

from internal.schemas import TRWStreamChatMessage


# A manager to keep track of connected WebSocket clients
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: TRWStreamChatMessage):
        for connection in self.active_connections:
            if connection.application_state == WebSocketState.CONNECTED:
                try:
                    await connection.send_json(message.model_dump())
                except Exception as e:
                    print(f"Error sending message to client: {e}")
