from abc import ABC, abstractmethod
class IStreamSource(ABC):
    @abstractmethod
    def monitor_streams(self) -> None:
        pass
