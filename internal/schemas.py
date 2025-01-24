from datetime import datetime

from pydantic import BaseModel

from internal.enums import StreamSource


class StreamBase(BaseModel):
    name: str
    source: StreamSource


class Stream(StreamBase):
    id: str
    url: str


class UpcomingStream(StreamBase):
    start_time: datetime


class BaseChatMessage(BaseModel):
    message: str
    author: str


class StreamChatMessage(BaseChatMessage):
    id: str
    time: str
    reply_to: BaseChatMessage | None
