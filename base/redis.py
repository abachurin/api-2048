from rq import Queue, get_current_job
from rq.job import Job
import redis
from .start import *


class RedisQueue:

    def __init__(self):
        def_host = '127.0.0.1' if LOCAL else 'redis'
        self.conn = redis.Redis(
            host=os.getenv('REDIS_HOST', def_host),
            port=os.getenv('REDIS_PORT', 6379)
        )
        self.q = Queue(connection=self.conn)
