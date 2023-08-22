from pymongo import MongoClient
from typing import Union
from .start import *
from .types import *


class Mongo:

    max_logs = 500
    watch_game_pattern = {"$regex": r'^\*'}
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

    def __init__(self, credentials: dict):
        self.cluster = f'mongodb+srv://{credentials["user"]}:{credentials["pwd"]}@{credentials["location"]}'
        client = MongoClient(self.cluster)
        db = client[credentials['db']]
        self.users = db['users']
        self.agents = db['agents']
        self.games = db['games']
        self.jobs = db['jobs']

    def get_pwd(self, name: str) -> Union[None, User]:
        pwd = self.users.find_one({'name': name}, {'pwd': 1})
        return pwd['pwd'] if pwd is not None else None

    def find_user(self, name: str) -> Union[None, User]:
        user_dict = self.users.find_one({'name': name})
        if user_dict is None:
            return None
        return User.parse_obj(user_dict)

    def new_user(self, name: str, pwd: str, status: UserLevel = UserLevel.USER) -> User:
        user = User(name=name, pwd=pwd, status=status)
        self.users.insert_one(pydantic_to_mongo(user))
        return user

    def delete_user(self, name: str):
        self.jobs.delete_many({'user': name})
        self.agents.delete_many({'user': name})
        self.games.delete_many({'user': name})
        self.users.delete_one({'name': name})

    def update_user_settings(self, values: UserUpdateSettings):
        self.users.update_one({'name': values.name}, {'$set': values.dict()})

    def check_agent(self, name: str) -> bool:
        return self.agents.find_one({'name': name}) is not None

    def new_agent(self, job: TrainingAgentJob) -> Agent:
        agent_core = AgentCore(**job.dict())
        agent_dict = {**agent_core.dict(), 'weightSignature': [], 'bestScore': 0, 'maxTile': 0,
                      'lastTrainingEpisode': 0, 'initialAlpha': job.alpha, 'history': [], 'collectStep': 100}
        self.agents.insert_one(agent_dict)
        return Agent.parse_obj(agent_dict)

    def agent_list(self, req: ItemListRequest) -> AgentListResponse:
        agents = self.agents.find({})
        if agents is None:
            return AgentListResponse(status='Unable to get Agents from DB', list=None)
        if req.scope == ItemRequestScope.USER:
            agents = {v['name']: v for v in agents if v['user'] == req.userName}
        else:
            agents = {v['name']: v for v in agents}
        for v in agents:
            agents[v]['maxTile'] = 1 << agents[v]['maxTile']
        return AgentListResponse(status='ok', list=agents)

    def just_names(self, req: ItemListRequest, item_type: ItemType) -> JustNamesResponse:
        if item_type == ItemType.AGENTS:
            items = self.agents.find({})
        else:
            items = self.games.find({"name": self.watch_game_pattern})
        if items is None:
            return JustNamesResponse(status='Unable to get Agents from DB', list=None)
        if req.scope == ItemRequestScope.USER:
            items = [v['name'] for v in items if v['user'] == req.userName]
        else:
            items = [v['name'] for v in items]
        return JustNamesResponse(status='ok', list=items)

    def check_train_test_job(self, user_name: str) -> JobDescription:
        job = self.jobs.find_one({'user': user_name})
        if job is None or job['type'] == JobType.WATCH.value:
            return None
        job['start'] = 'in the queue ..' if job['start'] == 0 else time_from_ts(job['start'])
        job['timeElapsed'] = timedelta_from_ts(job['timeElapsed'])
        job['remainingTimeEstimate'] = timedelta_from_ts(job['remainingTimeEstimate'])
        if job['type'] == JobType.TRAIN.value:
            job['currentAlpha'] = job['alpha']
            return TrainJobDescription(**job)
        return TestJobDescription(**job)

    def new_job(self, job: Job):
        job.status = JobStatus.PENDING
        job.start = 0
        job.timeElapsed = 0
        job.remainingTimeEstimate = 0
        self.jobs.insert_one(pydantic_to_mongo(job))

    def new_watch_job(self, job: WatchAgentJob):
        job.type = JobType.WATCH
        job.status = JobStatus.PENDING
        job.description = job.user
        job.newGame = True
        job.loadingWeights = True
        self.jobs.insert_one(pydantic_to_mongo(job))

    def new_watch_game(self, job: GameWatchNew):
        self.games.delete_one({'name': job.user})
        self.jobs.update_one({'description': job.user}, {'$set': {'startGame': pydantic_to_mongo(job.startGame),
                                                                  'loadingWeights': True, 'newGame': True}})

    def new_watch_moves(self, req: NewMovesRequest) -> NewMovesResponse:
        game = self.games.find_one({'name': req.name}, {'moves': 1, 'tiles': 1, 'numMoves': 1})
        job = self.jobs.find_one({'description': req.userName}, {'loadingWeights': 1})
        if not job:
            return NewMovesResponse(moves=[], tiles=[], loadingWeights=False)
        loading = job['loadingWeights']
        if not game:
            moves = []
            tiles = []
        else:
            cutoff = req.numMoves - game['numMoves']
            moves = game['moves'][cutoff:]
            tiles = [{'position': {'x': v[0], 'y': v[1]}, 'value': v[2]} for v in game['tiles'][cutoff:]]
        return NewMovesResponse(moves=moves, tiles=tiles, loadingWeights=loading)

    def cancel_job(self, description: str, cancel_type: JobCancelType):
        cancel_count = self.jobs.update_one({'description': description},
                                            {'$set': {'status': JobStatus.STOP.value}}).modified_count \
            if cancel_type == JobCancelType.STOP \
            else self.jobs.delete_one({'description': description}).deleted_count
        return cancel_count

    def reset_last_log(self, user_name: str):
        self.users.update_one({'name': user_name}, {'$set': {'lastLog': 0}})

    def update_logs(self, user_name: str) -> Union[None, List[str]]:
        user = self.find_user(user_name)
        if user is None:
            return None
        logs = user.logs
        last_log = user.lastLog
        new_logs = logs[last_log:]
        if len(new_logs) > self.max_logs:
            new_logs = new_logs[-self.max_logs:]
        if len(logs) > self.max_logs:
            logs = logs[-self.max_logs:]
            self.users.update_one({'name': user_name}, {'$set': {'logs': logs}})
        self.users.update_one({'name': user_name}, {'$set': {'lastLog': len(logs)}})
        return new_logs

    def clear_logs(self, name: str):
        self.users.update_one({'name': name}, {'$set': {'logs': []}})

    def game_list(self, req: ItemListRequest) -> GameListResponse:
        games = self.games.find({"name": self.watch_game_pattern})
        if games is None:
            return GameListResponse(status='Unable to get Games from DB', list=None)
        if req.scope == ItemRequestScope.USER:
            games = {v['name']: v for v in games if v['user'] == req.userName}
        else:
            games = {v['name']: v for v in games}
        return GameListResponse(status='ok', list=games)

    def delete_item(self, req: ItemDeleteRequest):
        if req.kind == ItemType.AGENTS:
            self.jobs.delete_many({'name': req.name})
            self.agents.delete_one({'name': req.name})
        else:
            self.games.delete_one({'name': req.name})

    def full_game(self, game_name: str) -> FullGameResponse:
        game = self.games.find_one({'name': game_name})
        if game is None:
            return FullGameResponse(status='No game with this name in DB')
        game['tiles'] = [{'position': {'x': v[0], 'y': v[1]}, 'value': v[2]} for v in game['tiles']]
        return FullGameResponse(status='ok', game=game)
