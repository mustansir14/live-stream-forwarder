# create a fastapi app with two endpoints list running streams and list upcoming streams

from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from internal.env import Env
from internal.redis import RedisClient
from internal.schemas import Stream, UpcomingStream

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
    return redis_client.get_upcoming_streams()
