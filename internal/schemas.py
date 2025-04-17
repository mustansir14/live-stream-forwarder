from datetime import datetime, timezone, date

from pydantic import BaseModel


class StreamBase(BaseModel):
    name: str


class TRWStream(StreamBase):
    id: str
    url: str


class DudestreamStream(TRWStream):
    date: date
    category: str

class TRWUpcomingStream(StreamBase):
    start_time: datetime

    def is_expired(self) -> bool:
        return self.start_time < datetime.now(timezone.utc)

class BaseChatMessage(BaseModel):
    message: str
    author: str


class TRWStreamChatMessage(BaseChatMessage):
    id: str
    time: str
    reply_to: BaseChatMessage | None
