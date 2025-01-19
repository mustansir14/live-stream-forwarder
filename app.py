# create a fastapi app with two endpoints list running streams and list upcoming streams

from fastapi import FastAPI
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from internal.schemas import Stream, UpcomingStream

app = FastAPI()

# CORS allow all origins
origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_SERVER_URL = "45.33.122.143/live"

streams = [
    Stream(name="test", url=f"rtmp://{BASE_SERVER_URL}/test"),
    Stream(name="test2", url=f"rtmp://{BASE_SERVER_URL}/test2"),
]

upcoming_streams = [
    UpcomingStream(name="test3", url=f"rtmp://{BASE_SERVER_URL}/test3", start_time=datetime.now() + timedelta(hours=1)),
    UpcomingStream(name="test4", url=f"rtmp://{BASE_SERVER_URL}/test4", start_time=datetime.now() + timedelta(hours=2)),
]

@app.get("/running-streams", response_model=List[Stream])
async def get_running_streams():
    return streams

@app.get("/upcoming-streams", response_model=List[UpcomingStream])
async def get_upcoming_streams():
    return upcoming_streams