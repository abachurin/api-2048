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

    def find_owners(self, name: str, kind: str):
        return self.users.find({kind: {"$in": [name]}})

    def user_list(self):
        return [user['name'] for user in self.users.find({})]

    def all_items(self, kind: str):
        res = []
        for u in self.users.find({}, {kind: 1}):
            res += u[kind]
        return res

    def delete_user(self, name: str):
        return self.users.delete_one({'name': name}).deleted_count

    def delete_item(self, name: str, kind: str):
        return self.users.update_many({}, {'$pull': {kind: name}}).modified_count

    def new_user(self, name: str, pwd: str, status: str):
        user = {
            'name': name,
            'pwd': pwd,
            'status': status,
            'Agents': [],
            'Games': [],
            'jobs': [],
            'logs': [],
            'log_break': 0
        }
        self.users.insert_one(user)
        user.pop('_id')
        return user
