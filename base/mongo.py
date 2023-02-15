from pymongo import MongoClient


class Mongo:

    max_logs = 5
    FIELDS = ('Agents', 'Games', 'Jobs')

    def __init__(self, credentials: dict):
        self.cluster = f'mongodb+srv://{credentials["user"]}:{credentials["pwd"]}@instance-0' \
                       f'.55byx.mongodb.net/?retryWrites=true&w=majority'
        self.client = MongoClient(self.cluster)
        self.db = self.client['robot-2048']
        self.users = self.db['users']
        self.jobs = self.db['jobs']

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
            'Agents': [],
            'Games': [],
            'Jobs': [],
            'logs': [f'Hello {name}']
        }
        self.users.insert_one(user)
        user.pop('_id')
        return user

    def update_user(self, name: str, fields: dict):
        self.users.update_one({'name': name}, {'$set': fields})

    def all_items(self, item: str):
        return self.users.distinct(item)

    def admin_list(self):
        return [user['name'] for user in self.users.find({'status': 'admin'})]

    def delete_item(self, name: str, kind: str):
        return self.users.update_many({}, {'$pull': {kind: name}}).modified_count

    def add_item(self, user_name: str, item_name: str, kind: str):
        if item_name in self.all_items(kind):
            return False
        self.users.update_one({'name': user_name}, {'$push': {kind: item_name}})
        return True

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
    def set_job_status(self, idx, status):
        if status == -1:
            self.jobs.delete_one({'_id': idx})
        else:
            self.jobs.update_one({'_id': idx}, {'$set': {'status': status}}, upsert=True)

    def get_job_status(self, idx):
        job = self.jobs.find_one({'_id': idx})
        return -1 if job is None else job['status']

