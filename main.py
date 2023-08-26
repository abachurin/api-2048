import threading
import time

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

import uvicorn
from base.utils import *

ACTIVE_USERS = {}
RESTRICTED_USERNAMES = {"Login"}


def set_inactive():
    while True:
        to_delete = []
        for name in ACTIVE_USERS:
            ACTIVE_USERS[name] += 1
            if ACTIVE_USERS[name] == 2:
                to_delete.append(name)
        for name in to_delete:
            ACTIVE_USERS.pop(name, None)
        time.sleep(5)


threading.Thread(target=set_inactive, daemon=True).start()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get('/')
async def root():
    return {'message': 'Robot-2048 backend, made with FastAPI, go to /docs to see all available endpoints'}


@app.post('/users/login')
async def users_login(login_data: UserLogin) -> UserLoginResponse:
    name = login_data.name
    pwd = login_data.pwd
    print(ACTIVE_USERS)
    if name in ACTIVE_USERS:
        return UserLoginResponse(status=f'{name} is already logged in', content=None)
    db_pwd = DB.get_pwd(name)
    if db_pwd is None:
        return UserLoginResponse(status=f'User {name} does not exist', content=None)
    if db_pwd != pwd:
        return UserLoginResponse(status=f'Wrong password for {name}!', content=None)
    DB.reset_last_log(name)
    db_user = DB.find_user(name)
    user_frontend = restrict(UserCore, db_user)
    ACTIVE_USERS[name] = 0
    return UserLoginResponse(status='ok', content=user_frontend)


@app.post('/users/register')
async def users_register(login_data: UserLogin) -> UserLoginResponse:
    name = login_data.name
    pwd = login_data.pwd
    db_pwd = DB.get_pwd(name)
    if db_pwd is not None or name in RESTRICTED_USERNAMES:
        return UserLoginResponse(status=f'User {name} already exists!', content=None)
    new_user = DB.new_user(name, pwd)
    user_frontend = restrict(UserCore, new_user)
    return UserLoginResponse(status='ok', content=user_frontend)


@app.delete('/users/delete')
async def users_delete(login_data: UserLogin) -> UserLoginResponse:
    name = login_data.name
    pwd = login_data.pwd
    db_pwd = DB.get_pwd(name)
    if db_pwd is None:
        return UserLoginResponse(status=f'User {name} does not exist', content=None)
    if db_pwd != pwd:
        return UserLoginResponse(status=f'Wrong password for {name}!', content=None)
    delete_user_total(name)
    return UserLoginResponse(status='ok', content=None)


@app.put('/users/settings')
async def users_settings(values: UserUpdateSettings) -> Response:
    name = values.name
    db_user = DB.find_user(name)
    if db_user is None:
        return Response(status_code=404)
    DB.update_user_settings(values)
    return Response(status_code=200)


@app.post('/jobs/train')
async def jobs_train(job: TrainingAgentJob) -> str:
    running_now = DB.check_train_test_job(job.user)
    if running_now is not None:
        return f"Currently running {running_now}. Stop/Kill it first."
    agent_exists = DB.check_agent(job.name)
    if job.isNew:
        if agent_exists:
            return f"Agent {job.name} already exists, choose another name"
        DB.new_agent(job)
    elif not agent_exists:
        return f"Agent {job.name} doesn't exist anymore"
    if job.episodes:
        job.description = f"Training {job.name} for {job.user}"
        job.type = JobType.TRAIN
        DB.new_job(job)
    return "ok"


@app.post('/jobs/test')
async def jobs_test(job: TestAgentJob) -> str:
    running_now = DB.check_train_test_job(job.user)
    if running_now is not None:
        return f"Currently running {running_now}. Stop/Kill it first."
    if (job.name not in EXTRA_AGENTS) and not DB.check_agent(job.name):
        return f"Agent {job.name} doesn't exist"
    job.description = f"Testing {job.name} for {job.user}"
    job.type = JobType.TEST
    DB.new_job(job)
    return "ok"


@app.post('/watch/new_agent')
async def watch_new_agent(job: WatchAgentJob) -> str:
    previous_user = job.previous
    if previous_user:
        DB.cancel_job(previous_user, JobCancelType.KILL)
        DB.games.delete_many({'user': previous_user})
    DB.new_watch_job(job)
    return "ok"


@app.post('/watch/new_game')
async def watch_new_game(job: GameWatchNew):
    DB.new_watch_game(job)


@app.post('/watch/new_moves')
async def watch_new_moves(req: NewMovesRequest) -> NewMovesResponse:
    return DB.new_watch_moves(req)


@app.post('/jobs/description')
async def jobs_description(job_request: SimpleUserRequest) -> JobUpdateResponse:
    user = job_request.userName
    job = DB.check_train_test_job(user)
    if job is None:
        return JobUpdateResponse(status=f"No running jobs for {user}")
    return JobUpdateResponse(status=f"ok", job=job)


@app.post('/jobs/cancel')
async def jobs_cancel(cancel_request: JobCancelRequest) -> str:
    description = cancel_request.description
    cancel_type = cancel_request.type
    count = DB.cancel_job(description, cancel_type)
    if not count:
        return "Job doesn't exist anymore"
    return f'{cancel_type.value} "{description}": processing request'


@app.post('/logs/update')
async def jobs_description(logs_request: SimpleUserRequest) -> LogsUpdateResponse:
    user = logs_request.userName
    ACTIVE_USERS[user] = 0
    new_logs = DB.update_logs(user)
    if new_logs is None and user != "Login":
        return LogsUpdateResponse(status=f'User {user} does not exist')
    return LogsUpdateResponse(status="ok", logs=new_logs)


@app.put('/logs/clear')
async def jobs_description(clear_request: SimpleUserRequest):
    user = clear_request.userName
    DB.clear_logs(user)


@app.post('/agents/list')
async def agents_list(agent_list_request: ItemListRequest) -> AgentListResponse:
    return DB.agent_list(agent_list_request)


@app.post('/games/list')
async def games_list(game_list_request: ItemListRequest) -> GameListResponse:
    return DB.game_list(game_list_request)


@app.post('/agents/just_names')
async def just_agent_names(agent_list_request: ItemListRequest) -> JustNamesResponse:
    return DB.just_names(agent_list_request, ItemType.AGENTS)


@app.delete('/item/delete')
async def item_delete(delete_item_request: ItemDeleteRequest):
    delete_item_total(delete_item_request)


@app.get('/games/{name}')
async def full_game(name: str) -> FullGameResponse:
    return DB.full_game(name)


if __name__ == '__main__':

    uvicorn.run(app, host="0.0.0.0", port=5000)
