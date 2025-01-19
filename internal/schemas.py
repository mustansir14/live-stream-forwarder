from pydantic import BaseModel
from datetime import datetime
from internal.enums import StreamSource

class Stream(BaseModel):
    id: str
    name: str
    url: str
    source: StreamSource
    

class UpcomingStream(Stream):
    start_time: datetime


class BaseChatMessage(BaseModel):
    message: str
    author: str

class StreamChatMessage(BaseChatMessage):
    id: str
    time: datetime
    reply_to: BaseChatMessage | None