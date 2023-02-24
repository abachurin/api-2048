import boto3
import pickle
from .start import *


class Storage:

    def __init__(self, credentials: dict):
        qwargs = {
            'service_name': 's3',
            'endpoint_url': f'https://{credentials["region"]}.digitaloceanspaces.com',
            'region_name': credentials['region'],
            'aws_access_key_id': credentials['access_key'],
            'aws_secret_access_key': credentials['secret_key']
        }
        self.engine = boto3.resource(**qwargs)
        self.client = boto3.client(**qwargs)
        self.space_name = credentials['space']
        self.space = self.engine.Bucket(self.space_name)

    def list_files(self):
        return [o.key for o in self.space.objects.all()]

    def delete(self, name):
        key = full_key(name)
        if key in self.list_files():
            self.engine.Object(self.space_name, key).delete()

    def save_file(self, local, key):
        self.space.upload_file(local, key)

    def save(self, data, key):
        temp = temp_local()
        with open(temp, 'w') as f:
            pickle.dump(data, f, -1)
        self.save_file(temp, key)
        os.remove(temp)

    def load(self, name):
        key = full_key(name)
        if key not in self.list_files():
            return
        temp = temp_local()
        self.space.download_file(key, temp)
        with open(temp, 'rb') as f:
            result = pickle.load(f)
        os.remove(temp)
        return result
