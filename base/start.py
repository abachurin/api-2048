from datetime import datetime
import os
import json
from pprint import pprint


def full_s3_key(name, kind):
    return f'{kind}/{name}.pkl' if kind else name


def core_name(file):
    return file.split('/')[1].split('.')[0]


def kind_name(file):
    kind = file.split('/')[0]
    return 'dir' if file == f'{kind}/' else kind


def time_suffix(precision=1):
    return ''.join([v for v in str(datetime.utcnow()) if v.isnumeric()])[4:-precision]


def temp_local(name):
    ext = name.split('.')[1] if '.' in name else 'pkl'
    return f'tmp{time_suffix()}.{ext}', ext


def clock():
    return datetime.now().strftime('%H:%M:%S')
