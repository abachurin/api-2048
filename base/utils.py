from .redis import *
from .storage import *
from .mongo import *

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
REDIS = RedisQueue()
RQ = REDIS.q


def delete_item_total(name: str, kind: str):
    DB.delete_item(name, kind)
    S3.delete(name, kind)


def delete_user_total(user: dict):
    for agent in user['Agents']:
        delete_item_total(agent, 'Agents')
    for game in user['Games']:
        delete_item_total(game, 'Games')
    DB.stop_job(user['working'])
    DB.delete_user(user['name'])
