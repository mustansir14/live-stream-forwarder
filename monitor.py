from internal.env import Env
from internal.redis import RedisClient
from internal.stream_sources.trw import TRW

if __name__ == "__main__":

    try:
        redis_client = RedisClient(host=Env.REDIS_HOST, port=Env.REDIS_PORT)
        redis_client.delete_all_streams()

        trw = TRW(Env.TRW_EMAIL, Env.TRW_PASSWORD, Env.RTMP_SERVER_KEY, redis_client)
        trw.monitor_streams(Env.RTMP_SERVER)
    finally:
        redis_client.delete_all_streams()
