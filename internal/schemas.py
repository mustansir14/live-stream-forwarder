from datetime import datetime, timezone

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

    def is_expired(self) -> bool:
        return self.start_time < datetime.now(timezone.utc)


class BaseChatMessage(BaseModel):
    message: str
    author: str


class StreamChatMessage(BaseChatMessage):
    id: str
    time: str
    reply_to: BaseChatMessage | None
