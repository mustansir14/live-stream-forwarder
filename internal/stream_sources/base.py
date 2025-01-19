from abc import ABC, abstractmethod
from typing import Generator

from internal.schemas import StreamChatMessage


class IStreamSource(ABC):
    @abstractmethod
    def monitor_streams(self) -> None:
        pass
