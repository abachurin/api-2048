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
RQ = {
    'User name': {
        'q': 'Redis Queue object',
        'fail': 'FailedJobRegistry object for that Queue',
        'worker': 'Worker listening tio that Queue'
    }
}


def delete_item_total(name: str, kind: str):
    if kind == 'Jobs':
        DB.set_job_status(name, -1)
    else:
        DB.delete_array_item(name, kind)
        S3.delete(name, kind)


def delete_user_total(user: dict):
    for kind in ('Jobs', 'Agents', 'Games'):
        for item in user[kind]:
            delete_item_total(item, kind)
    DB.delete_user(user['name'])


def train_agent(params):
    name = params['name']
    idx = params['idx']
    new = params['new']
    if new:
        agent = params['agent']
        DB.add_array_item(name, agent, 'Agents')
    status = 1
    for i in range(100):
        print(i, 'train', name)
        status = DB.get_job_status(idx)
        if status == 0:
            DB.add_log(name, f'STOP!: {idx}')
            break
        elif status == -1:
            DB.add_log(name, f'KILL!: {idx}')
            break
        time.sleep(2)
    return status


def test_agent(params):
    name = params['name']
    idx = params['idx']
    status = 1
    for i in range(100):
        print(i, 'test', name)
        status = DB.get_job_status(idx)
        if status == 0:
            DB.add_log(name, f'STOP!: {idx}')
            break
        elif status == -1:
            DB.add_log(name, f'KILL!: {idx}')
            break
        time.sleep(2)
    return status


SLOW_TASKS = {
    'train': train_agent,
    'test': test_agent
}


def slow_task(params):
    idx = params['idx']
    name = params['name']
    DB.update_user(name, {'current_job': idx})
    DB.add_log(name, f'Started Job: {idx}')

    status = params['func'](params)
    match status:
        case 1:
            msg = f'Job {idx} complete'
        case 0:
            msg = f'Job {idx} stopped by {name}'
        case -1:
            msg = f'Job {idx} killed by {name}'
        case _:
            msg = f'Strange, no output from job {idx}'

    DB.add_log(name, msg)
    DB.delete_array_item(idx, 'Jobs')
    DB.update_user(name, {'current_job': None})
