from pymongo import MongoClient
from .start import *


class Mongo:

    max_logs = 500
    ARRAYS = ('Agents', 'Games', 'Jobs')
    user_pattern = {
            'time': 'registration datetime',
            'name': 'user name',
            'pwd': 'user password',
            'status': 'user status',
            'Agents': [],
            'Games': [],
            'Jobs': [],
            'logs': [f'Hello UserName! Click Help if unsure what this is about']
        }
    agent_pattern = {
        'idx': 'agent name',
        'creator': 'user name',
        'n': 0,
        'weight_signature': None,
        'alpha': 0.0,
        'decay': 0.0,
        'step': 0,
        'min_alpha': 0.0,
        'best_score': 0,
        'max_tile': 1,
        'train_eps': 0,
        'train_history': [],
        'collect_step': 100
    }
    game_pattern = {
        'idx': 'game name',
        'player': 'agent or user',
        'initial': [[0, 0, 1, 0], [0, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 0]],
        'current': [[0, 0, 1, 0], [0, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 0]],
        'score': 0,
        'num_of_moves': 0,
        'max_tile': 0,
        'moves': [0, 1, 2, 3],
        'tiles': [[0, 3, 2], [3, 0, 1], [2, 3, 1], [2, 1, 1]]
    }
    job_pattern = {
        'idx': 'job id',
        'status': 1,
        'creation_time': None,
        'launch_time': None,
        'name': 'user name',
        'mode': 'train, test or watch',
        'agent': 'agent name'
        # mode-specific params here
    }

    def __init__(self, credentials: dict):
        self.cluster = f'mongodb+srv://{credentials["user"]}:{credentials["pwd"]}@{credentials["location"]}'
        client = MongoClient(self.cluster)
        db = client[credentials['db']]
        self.users = db['users']

    def find_user(self, name: str):
        return self.users.find_one({'name': name}, {'_id': 0})

    def get_item(self, idx: str, kind: str):
        try:
            return self.users.find_one({f'{kind}.idx': idx}, {f'{kind}.$': 1})[kind][0]
        except TypeError:
            return None

    def get_game(self, idx):
        return self.get_item(idx, 'Games')

    def get_agent(self, idx):
        return self.get_item(idx, 'Agents')

    def delete_user(self, name: str):
        self.users.delete_one({'name': name})

    def delete_watch_user(self, idx: str):
        self.users.delete_one({'Jobs.idx': idx})

    def new_user(self, name: str, pwd: str, status: str):
        user = {
            **self.user_pattern,
            'time': time_now(),
            'name': name,
            'pwd': pwd,
            'status': status,
            'logs': [f'Hello {name}! Click Help if unsure what this is about']
        }
        self.users.insert_one(user)
        user.pop('_id')
        return user

    def update_user(self, name: str, fields: dict):
        self.users.update_one({'name': name}, {'$set': fields})

    def all_items(self, kind: str):
        if kind in self.ARRAYS:
            kind += '.idx'
        return self.users.distinct(kind)

    def admin_list(self):
        return self.users.distinct('name', {'status': 'admin'})

    def delete_array_item(self, idx: str, kind: str):
        return self.users.update_one({f'{kind}.idx': idx}, {'$pull': {kind: {'idx': idx}}}).modified_count

    def add_array_item(self, name: str, item: dict, kind: str):
        if item['idx'] in self.all_items(kind):
            return False
        self.users.update_one({'name': name}, {'$push': {kind: item}})
        return True

    def replace_agent(self, name: str, params: dict):
        idx = params['agent']
        if params['is_new']:
            current = self.agent_pattern.copy()
            current['idx'] = idx
            current['creator'] = name
        else:
            current = self.get_item(idx, 'Agents')
        for key in current:
            if key != 'idx' and key in params:
                current[key] = params[key]
        self.users.update_one({'name': name}, {'$pull': {'Agents': {'idx': idx}}})
        self.users.update_one({'name': name}, {'$push': {'Agents': current}})

    def add_log(self, name: str, log: str):
        self.users.update_one({'name': name}, {'$push': {'logs': log}})

    def clear_logs(self, name: str):
        self.users.update_one({'name': name}, {'logs': []})

    def adjust_logs(self, user: dict):
        if len(user['logs']) > self.max_logs:
            adjusted_logs = user['logs'][-self.max_logs:]
            self.update_user(user['name'], {'logs': adjusted_logs})
            return adjusted_logs
        return user['logs']

    # Job status: 1 = work, 0 = stop, -1 = kill
    def set_job_status(self, idx: str, status: str):
        if status == -1:
            self.delete_array_item(idx, 'Jobs')
        else:
            self.users.update_one({'Jobs.idx': idx}, {'$set': {'Jobs.$.status': status}})

    def check_job_status(self, idx: str):
        try:
            return self.get_item(idx, 'Jobs')['status']
        except TypeError:
            return -1

    def rerun_watch_job(self, idx: str, row: dict):
        return self.users.update_one({'Jobs.idx': idx}, {'$set': {
            'Jobs.$.new_game': 1,
            'Jobs.$.row': row,
            'Jobs.$.score': 0,
            'Jobs.$.odo': 0
        }}).modified_count
