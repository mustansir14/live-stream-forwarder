from abc import ABC, abstractmethod
from typing import List
from internal.schemas import Stream, UpcomingStream, StreamChatMessage
from typing import Generator

class IStreamSource(ABC):
    @abstractmethod
    def monitor_streams(self) -> None:
        pass

    @abstractmethod
    def get_stream_messages(self, stream_id: str) -> Generator[StreamChatMessage, None, None]:
        pass