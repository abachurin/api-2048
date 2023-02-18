from rq import Queue, Connection, Worker
from rq.registry import FailedJobRegistry, Job
from rq.command import send_shutdown_command

import redis
from .start import *


class Redis:

    def __init__(self):
        def_host = '127.0.0.1' if LOCAL else 'redis'
        self.conn = redis.Redis(
            host=os.getenv('REDIS_HOST', def_host),
            port=os.getenv('REDIS_PORT', 6379)
        )
