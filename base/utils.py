from .redis import *
from .storage import *
from .mongo import *

import time

working_directory = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(working_directory, 'config.json'), 'r') as f:
    CONF = json.load(f)

if LOCAL:
    with open(CONF['s3_credentials'], 'r') as f:
        s3_credentials = json.load(f)
    with open(CONF['mongo_credentials'], 'r') as f:
        mongo_credentials = json.load(f)
else:
    s3_credentials = {
        'region': os.environ.get('S3_REGION', None),
        'access_key': os.environ.get('S3_ACCESS_KEY', None),
        'secret_key': os.environ.get('S3_SECRET_KEY', None)
    }
    mongo_credentials = {
        'user': os.environ.get('MG_USER', None),
        'pwd': os.environ.get('MG_PWD', None)
    }

S3 = Storage(s3_credentials)
DB = Mongo(mongo_credentials)
REDIS = Redis()
RQ = REDIS.q


def delete_item_total(name: str, kind: str):
    if kind == 'Jobs':
        DB.set_job_status(name, -1)
    else:
        DB.delete_item(name, kind)
        S3.delete(name, kind)


def delete_user_total(user: dict):
    for kind in ('Jobs', 'Agents', 'Games'):
        for item in user[kind]:
            delete_item_total(item, kind)
    DB.delete_user(user['name'])


def slow_task(params):
    idx = params['idx']
    name = params['name']
    DB.update_user(name, {'working': idx})
    print(f'Started {idx}')

    params['func'](params)

    print(f'Job {idx} is done')
    DB.set_job_status(idx, -1)
    DB.update_user(name, {'working': None})


def train_agent(params):
    for i in range(100):
        print(i, 'train', params['p'])
        time.sleep(params['p'])


def test_agent(params):
    for i in range(100):
        print(i, 'test', params['p'])
        time.sleep(params['p'])


SLOW_TASKS = {
    'train': train_agent,
    'test': test_agent
}
