from pymongo import MongoClient


class Mongo:

    max_logs = 2000
    FIELDS = ('Agents', 'Games', 'Jobs')
    agent_pattern = {
        'idx': 'some name',
        'n': 0,
        'alpha': 0.0,
        'decay': 0.0,
        'step': 2000,
        'min_alpha': 0.0,
        'best_score': 0,
        'max_tile': 0,
        'train_history': []
    }

    def __init__(self, credentials: dict):
        self.cluster = f'mongodb+srv://{credentials["user"]}:{credentials["pwd"]}@instance-0' \
                       f'.55byx.mongodb.net/?retryWrites=true&w=majority'
        client = MongoClient(self.cluster)
        db = client[credentials['db']]
        self.users = db['users']
        self.array_names = ('Agents', 'Games', 'Jobs', 'watch')

    def find_user(self, name: str):
        user = self.users.find_one({'name': name})
        if user is not None:
            del user['_id']
        return user

    def delete_user(self, name: str):
        self.users.delete_one({'name': name})

    def new_user(self, name: str, pwd: str, status: str):
        user = {
            'name': name,
            'pwd': pwd,
            'status': status,
            'Agents': [
                {
                    'idx': 'A',
                    'n': 4,
                    'alpha': 0.2,
                    'decay': 0.9,
                    'step': 2000,
                    'min_alpha': 0.01,
                    'best_score': 0,
                    'max_tile': 0,
                    'train_history': []
                }
            ],
            'Games': [
                # {
                #     'idx': 'Best_of_A',
                #     'final_score': 0,
                #     'max_tile': 0
                #     'initial': [[0, 0, 1, 0], [0, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 0]],
                #     'moves': [0, 1, 2, 3],
                #     'tiles': [[0, 3, 2], [3, 0, 1], [2, 3, 1], [2, 1, 1]],
                # }
            ],
            'Jobs': [
                # {
                #             'idx': idx,
                #             'status': 'created',
                #             'launch': 'sent to job queue',
                #             'name': name,
                #             'mode': mode,
                #             'new': True/False,
                #             'agent': {'idx': agent_name, **params}
                # }
            ],
            'watch': None,      # 'idx': agent idx,
            'logs': [f'Hello {name}! Click Help if unsure what this is about']
        }
        self.users.insert_one(user)
        user.pop('_id')
        return user

    def update_user(self, name: str, fields: dict):
        self.users.update_one({'name': name}, {'$set': fields})

    def all_items(self, kind: str):
        if kind in self.array_names:
            kind += '.idx'
        return self.users.distinct(kind)

    def admin_list(self):
        return [user['name'] for user in self.users.find({'status': 'admin'})]

    def delete_array_item(self, idx: str, kind: str):
        return self.users.update_one({}, {'$pull': {kind: {'idx': idx}}}).modified_count

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
        else:
            current = self.users.find_one({'Agents.idx': idx})['Agents'][0]
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
        if status == 'kill':
            self.delete_array_item(idx, 'Jobs')
        else:
            self.users.update_one({'Jobs.idx': idx}, {'$set': {'Jobs.$.status': status}})

    def get_job_status(self, idx: str):
        try:
            return self.users.find_one({'Jobs.idx': idx}, {'Jobs.$': 1})['Jobs'][0]['status']
        except TypeError:
            return 'kill'

    def get_game(self, idx):
        arr = self.users.find_one({'Games.idx': idx}, {'Games.$': 1})['Games']
        return arr[0] if arr else None
