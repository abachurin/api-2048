from pymongo import MongoClient


class Mongo:

    def __init__(self, credentials: dict):
        self.cluster = f'mongodb+srv://{credentials["user"]}:{credentials["pwd"]}@instance-0' \
                       f'.55byx.mongodb.net/?retryWrites=true&w=majority'
        self.client = MongoClient(self.cluster)
        self.db = self.client['robot-2048']
        self.users = self.db['users']
        self.jobs = self.db['jobs']

    def find_user(self, name: str, ex_id=True):
        user = self.users.find_one({'name': name})
        if ex_id and user is not None:
            user.pop('_id')
        return user

    def delete_user(self, name: str):
        return self.users.delete_one({'name': name}).deleted_count

    def new_user(self, name: str, pwd: str, status: str):
        user = {
            'name': name,
            'pwd': pwd,
            'status': status,
            'Agents': [],
            'Games': [],
            'jobs': [],
            'working': None,
            'logs': [],
            'log_break': 0
        }
        self.users.insert_one(user)
        user.pop('_id')
        return user

    def update_user(self, name, fields):
        self.users.update_one({'name': name}, {'$set': fields})

    def all_items(self, item: str):
        return self.users.distinct(item)

    def admin_list(self):
        return [user['name'] for user in self.users.find({'status': 'admin'})]

    def delete_item(self, name: str, kind: str):
        return self.users.update_many({}, {'$pull': {kind: name}}).modified_count

    def add_item(self, user: str, name: str, kind: str):
        if name in self.all_items(kind):
            return -1
        affected = self.admin_list()
        if user not in affected:
            affected.append(user)
        return self.users.update_many({'name': {'$in': affected}}, {'$push': {kind: name}}).modified_count

    def new_job(self, name, idx):
        job = {
            '_id': idx,
            'name': name,
            'status': 0
        }
        self.jobs.insert_one(job)

    def stop_job(self, name):
        if name:
            self.jobs.update_one({'name': name}, {'status': -1})
