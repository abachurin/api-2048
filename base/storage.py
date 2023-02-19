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

    def list_files(self, kind=None):
        files = [o.key for o in self.space.objects.all()]
        if kind:
            return [core_name(f) for f in files if kind_name(f) == kind]
        else:
            return files

    def delete(self, name, kind=None):
        name = full_s3_key(name, kind)
        if name in self.list_files():
            self.engine.Object(self.space_name, name).delete()

    def copy(self, src, dst):
        self.space.copy({'Bucket': self.space_name, 'Key': src}, dst)

    def save_file(self, file, name, kind=None):
        self.space.upload_file(file, full_s3_key(name, kind))

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
