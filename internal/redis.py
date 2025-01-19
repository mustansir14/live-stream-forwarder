from typing import List

from redis import Redis

from internal.schemas import Stream, StreamChatMessage, UpcomingStream

RUNNING_STREAMS = "running_streams"
UPCOMING_STREAMS = "upcoming_streams"
STREAM_CHAT_MESSAGES = "stream_%s_chat_messages"


class RedisClient:

    def __init__(self, host: str, port: int) -> None:
        self.redis = Redis(host=host, port=port)

    def add_running_stream(self, stream: Stream) -> None:
        self.redis.sadd(RUNNING_STREAMS, stream.model_dump_json())

    def add_upcoming_stream(self, stream: UpcomingStream) -> None:
        self.redis.sadd(UPCOMING_STREAMS, stream.model_dump_json())

    def get_running_streams(self) -> List[Stream]:
        running_streams = []
        for member in self.redis.smembers(RUNNING_STREAMS):
            stream = Stream.model_validate_json(member)
            running_streams.append(stream)
        return running_streams

    def get_upcoming_streams(self) -> List[UpcomingStream]:
        upcoming_streams = []
        for member in self.redis.smembers(UPCOMING_STREAMS):
            upcoming_stream = UpcomingStream.model_validate_json(member)
            upcoming_streams.append(upcoming_stream)
        return upcoming_streams

    def delete_all_streams(self) -> None:
        for stream in self.get_running_streams():
            self.redis.delete(STREAM_CHAT_MESSAGES % stream.id)
        for stream in self.get_upcoming_streams():
            self.redis.delete(STREAM_CHAT_MESSAGES % stream.id)
        self.redis.delete(RUNNING_STREAMS)
        self.redis.delete(UPCOMING_STREAMS)

    def delete_stream_by_id(self, stream_id: str) -> None:
        self.redis.delete(STREAM_CHAT_MESSAGES % stream_id)
        for stream in self.get_running_streams():
            if stream.id == stream_id:
                self.redis.srem(RUNNING_STREAMS, stream.model_dump_json())
                return

        for stream in self.get_upcoming_streams():
            if stream.id == stream_id:
                self.redis.srem(UPCOMING_STREAMS, stream.model_dump_json())
                return
        raise ValueError(f"Stream with id {stream_id} not found")

    def enqueue_stream_message(
        self, stream_id: str, message: StreamChatMessage
    ) -> None:
        self.redis.lpush(STREAM_CHAT_MESSAGES % stream_id, message.model_dump_json())

    def dequeue_stream_message(self, stream_id: str) -> StreamChatMessage | None:
        message = self.redis.rpop(STREAM_CHAT_MESSAGES % stream_id)
        if message:
            return StreamChatMessage.model_validate_json(message)
        return None
