from typing import List

from redis import Redis

from internal.schemas import TRWStream, TRWStreamChatMessage, TRWUpcomingStream, DudestreamStream

TRW_RUNNING_STREAMS = "trw_running_streams"
TRW_UPCOMING_STREAMS = "trw_upcoming_streams"
TRW_STREAM_CHAT_MESSAGES = "trw_stream_%s_chat_messages"
DUDESTREAM_STREAMS = "dudestream_streams"


class RedisClient:

    def __init__(self, host: str, port: int) -> None:
        self.redis = Redis(host=host, port=port)

    def get_trw_running_stream(self, stream_id: str) -> TRWStream | None:
        for stream in self.get_trw_running_streams():
            if stream.id == stream_id:
                return stream
        return None

    def add_trw_running_stream(self, stream: TRWStream) -> None:
        self.redis.sadd(TRW_RUNNING_STREAMS, stream.model_dump_json())

    def add_trw_upcoming_stream(self, stream: TRWUpcomingStream) -> None:
        self.redis.sadd(TRW_UPCOMING_STREAMS, stream.model_dump_json())

    def get_trw_running_streams(self) -> List[TRWStream]:
        running_streams = []
        for member in self.redis.smembers(TRW_RUNNING_STREAMS):
            stream = TRWStream.model_validate_json(member)
            running_streams.append(stream)
        return running_streams

    def get_trw_upcoming_streams(self) -> List[TRWUpcomingStream]:
        upcoming_streams = []
        for member in self.redis.smembers(TRW_UPCOMING_STREAMS):
            upcoming_stream = TRWUpcomingStream.model_validate_json(member)
            upcoming_streams.append(upcoming_stream)
        return upcoming_streams

    def delete_all_streams(self) -> None:
        for stream in self.get_trw_running_streams():
            self.redis.delete(TRW_STREAM_CHAT_MESSAGES % stream.id)
        self.redis.delete(TRW_RUNNING_STREAMS)
        self.redis.delete(TRW_UPCOMING_STREAMS)
        self.redis.delete(DUDESTREAM_STREAMS)

    def delete_trw_stream_by_id(self, stream_id: str) -> None:
        self.redis.delete(TRW_STREAM_CHAT_MESSAGES % stream_id)
        for stream in self.get_trw_running_streams():
            if stream.id == stream_id:
                self.redis.srem(TRW_RUNNING_STREAMS, stream.model_dump_json())
                return

        for stream in self.get_trw_upcoming_streams():
            if stream.name == stream_id:
                self.redis.srem(TRW_UPCOMING_STREAMS, stream.model_dump_json())
                return
    
    def delete_trw_upcoming_stream(self, stream: TRWUpcomingStream) -> None:
        self.redis.srem(TRW_UPCOMING_STREAMS, stream.model_dump_json())

    def enqueue_trw_stream_message(
        self, stream_id: str, message: TRWStreamChatMessage
    ) -> None:
        self.redis.lpush(TRW_STREAM_CHAT_MESSAGES % stream_id, message.model_dump_json())

    def dequeue_trw_stream_message(self, stream_id: str) -> TRWStreamChatMessage | None:
        message = self.redis.rpop(TRW_STREAM_CHAT_MESSAGES % stream_id)
        if message:
            return TRWStreamChatMessage.model_validate_json(message)
        return None
    
    def add_dudestream_stream(self, stream: DudestreamStream) -> None:
        self.redis.sadd(DUDESTREAM_STREAMS, stream.model_dump_json())

    def get_dudestream_streams(self) -> List[DudestreamStream]:
        streams = []
        for member in self.redis.smembers(DUDESTREAM_STREAMS):
            stream = DudestreamStream.model_validate_json(member)
            streams.append(stream)
        return streams

    def delete_dudestream_category_streams(self, category: str) -> None:
        for stream in self.get_dudestream_streams():
            if stream.category == category:
                self.redis.srem(DUDESTREAM_STREAMS, stream.model_dump_json())
                return
