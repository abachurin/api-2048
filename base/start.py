from datetime import datetime
import os
import json
from pprint import pprint


def full_key(name):
    return f'{name}.pkl'


def time_suffix():
    return str(datetime.now())[-6:]


def temp_local():
    return f'tmp{time_suffix()}.pkl'


def time_now():
    return str(datetime.now())[:19]
