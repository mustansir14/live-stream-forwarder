# create a fastapi app with two endpoints list running streams and list upcoming streams

import asyncio
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from internal.env import Env
from internal.redis import RedisClient
from internal.schemas import Stream, UpcomingStream
from internal.websocket import ConnectionManager

app = FastAPI()

# CORS allow all origins
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_client = RedisClient(host=Env.REDIS_HOST, port=Env.REDIS_PORT)


@app.get("/running-streams", response_model=List[Stream])
async def get_running_streams():
    return redis_client.get_running_streams()


@app.get("/upcoming-streams", response_model=List[UpcomingStream])
async def get_upcoming_streams():
    upcoming_streams = redis_client.get_upcoming_streams()

    upcoming_streams_to_return = []
    # remove old streams
    for upcoming_stream in upcoming_streams:
        if upcoming_stream.is_expired():
            redis_client.delete_upcoming_stream(upcoming_stream)
            continue
        upcoming_streams_to_return.append(upcoming_stream)
    
    return upcoming_streams_to_return


manager = ConnectionManager()


@app.websocket("/ws/stream-messages/{stream_id}")
async def get_stream_messages(websocket: WebSocket, stream_id: str):
    await manager.connect(websocket)
    try:
        while True:
            # Dequeue message from Redis
            message = redis_client.dequeue_stream_message(stream_id)
            if message:
                # Broadcast the message to all connected clients
                await manager.broadcast(message)
            await asyncio.sleep(0.1)

             # Check if the client is still connected
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)
        print(f"Client disconnected from stream {stream_id}")
