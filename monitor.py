from internal.env import Env
from internal.redis import RedisClient
from internal.stream_sources.trw import TRW
from internal.stream_sources.dudestream import DudeStream
from internal.stream_sources.hurawatch import Hurawatch
from internal.database import init_db, SessionLocal

import multiprocessing

if __name__ == "__main__":

    # Initialize the database
    init_db()

    try:
        redis_client = RedisClient(host=Env.REDIS_HOST, port=Env.REDIS_PORT)
        redis_client.delete_all_streams()

        stream_sources = [
            TRW(Env.TRW_EMAIL, Env.TRW_PASSWORD, Env.RTMP_SERVER_KEY, Env.RTMP_SERVER, redis_client, Env.OPENAI_API_KEY, Env.OTP_EMAIL, Env.OTP_EMAIL_PASSWORD, Env.DEBUG),
            DudeStream(redis_client),
            Hurawatch(SessionLocal)
        ]

        # monitor each source in a separate parallel process using multiprocessing
        processes = []
        for source in stream_sources:
            process = multiprocessing.Process(target=source.monitor_streams)
            processes.append(process)
            process.start()

        # wait for all processes to finish
        for process in processes:
            process.join()



    finally:
        redis_client.delete_all_streams()
