from datetime import datetime, timedelta
# import numpy as np
import time
import sys
from pprint import pprint, pformat
import random
import pickle
import json
from collections import deque
import os
import time
import boto3
import botocore
import psutil
from dateutil import parser

from pymongo import MongoClient
from fastapi import FastAPI, HTTPException
import uvicorn
from pydantic import BaseModel
from typing import List, Iterable, Dict, Tuple, Optional, Any


def full_s3_key(name, folder):
    return f'{folder}/{name}' if folder else name


def core_s3_key(name):
    return name.split('/')[-1]


def time_suffix(precision=1):
    return ''.join([v for v in str(datetime.utcnow()) if v.isnumeric()])[4:-precision]


def temp_local(name):
    body, ext = name.split('.')
    return f'temp{time_suffix()}.{ext}', ext


def clock():
    return datetime.now().strftime('%H:%M:%S')


class Storage:

    def __init__(self, credentials=None, space='robot-2048'):
        if credentials is not None:
            self.engine = boto3.resource(
                service_name='s3',
                endpoint_url=f'https://{credentials["region"]}.digitaloceanspaces.com',
                region_name=credentials['region'],
                aws_access_key_id=credentials['access_key'],
                aws_secret_access_key=credentials['secret_key']
            )
        else:
            self.engine = boto3.resource('s3')
        self.space = self.engine.Bucket(space)
        self.space_name = space

    def list_files(self, folder=None):
        files = [o.key for o in self.space.objects.all()]
        if folder:
            return [f for f in files if (f.startswith(f'{folder}/') and f != f'{folder}/')]
        else:
            return files

    def delete(self, name, folder=None):
        name = full_s3_key(name, folder)
        if name in self.list_files():
            self.engine.Object(self.space_name, name).delete()

    def copy(self, src, dst):
        self.space.copy({'Bucket': self.space_name, 'Key': src}, dst)

    def save_file(self, file, name, folder=None):
        self.space.upload_file(file, full_s3_key(name, folder))

    def save(self, data, name, folder=None):
        temp, ext = temp_local(name)
        with open(temp, 'w') as f:
            match ext:
                case 'json':
                    json.dump(data, f)
                case 'txt':
                    f.write(data)
                case 'pkl':
                    pickle.dump(data, f, -1)
                case _:
                    return
        self.save_file(temp, name, folder)
        os.remove(temp)

    def load(self, name, folder=None):
        full = full_s3_key(name, folder)
        if full not in self.list_files():
            return
        temp, ext = temp_local(name)
        self.space.download_file(full, temp)
        match ext:
            case 'json':
                with open(temp, 'r', encoding='utf-8') as f:
                    result = json.load(f)
            case 'txt':
                with open(temp, 'r') as f:
                    result = f.read()
            case 'pkl':
                with open(temp, 'rb') as f:
                    result = pickle.load(f)
            case _:
                result = None
        os.remove(temp)
        return result

    def add_to_memo(self, text):
        memo = self.load('memory_usage.txt') or ''
        self.save(memo + text + '\n', 'memory_usage.txt')

    def add_log(self, text, user):
        log_file = f'logs_{user}'
        if text:
            memo = self.load(log_file, 'user_logs') or ''
            memo += text + '\n'
            self.save(memo, log_file, 'user_logs')


class User(BaseModel):
    name: str
    pwd: str
    agents: Optional[List[str]]

    @classmethod
    def from_dict(cls, user_dict):
        user_dict['agents'] = user_dict.get('agents', [])
        return cls(**user_dict)

    def __repr__(self):
        return pformat(self.to_dict())

    def to_dict(self):
        return {'name': self.name, 'pwd': self.pwd, 'agents': self.agents or []}


class Mongo:

    def __init__(self, credentials):
        self.cluster = f'mongodb+srv://{credentials["user"]}:{credentials["pwd"]}@instance-0' \
                       f'.55byx.mongodb.net/?retryWrites=true&w=majority'
        self.client = MongoClient(self.cluster)
        self.db = self.client['robot-2048']
        self.coll = self.db['users']

    def find_user(self, name: str):
        return self.coll.find_one({'name': name})

    def user_list(self):
        return [user['name'] for user in self.coll.find({})]

    def delete_user(self, name: str):
        return self.coll.delete_one({'name': name}).deleted_count

    def insert_user(self, user: User):
        return self.coll.insert_one(user.to_dict())

    def update_one(self, query, fields):
        return self.coll.update_one(query, {'$set': fields, '$currentDate': {'time': True}}).modified_count


working_directory = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(working_directory, 'config.json'), 'r') as f:
    CONF = json.load(f)
LOCAL = os.environ.get('S3_URL', 'local') == 'local'
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
