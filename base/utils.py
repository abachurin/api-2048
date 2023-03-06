from .storage import *
from .mongo import *

working_directory = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(working_directory, 'config.json'), 'r') as f:
    CONF = json.load(f)
LOCAL = os.environ.get('AT_HOME', 'local') == 'local'

if LOCAL:
    with open(CONF['s3_credentials'], 'r') as f:
        s3_credentials = json.load(f)
    with open(CONF['mongo_credentials'], 'r') as f:
        mongo_credentials = json.load(f)
else:
    s3_credentials = {
        'region': os.getenv('S3_REGION', None),
        'space': os.getenv('S3_SPACE', 'robot-2048'),
        'access_key': os.getenv('S3_ACCESS_KEY', None),
        'secret_key': os.getenv('S3_SECRET_KEY', None)
    }
    mongo_credentials = {
        'user': os.getenv('MG_USER', None),
        'pwd': os.getenv('MG_PWD', None),
        'location': os.getenv('MG_LOCATION', None),
        'db': os.getenv('MG_DB', 'robot-2048'),
    }


S3 = Storage(s3_credentials)
DB = Mongo(mongo_credentials)


def delete_item_total(idx: str, kind: str):
    count = DB.delete_array_item(idx, kind)
    if kind == 'Agents':
        S3.delete(idx)
    return count


def delete_user_total(user: dict):
    for kind in ('Jobs', 'Agents', 'Games'):
        for item in user[kind]:
            delete_item_total(item, kind)
    DB.delete_user(user['name'])
