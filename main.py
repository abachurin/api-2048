import threading
import time

from fastapi import FastAPI, Request
import uvicorn
from threading import Thread
from base.utils import *

ACTIVE_USERS = {}


def set_inactive():
    while True:
        to_delete = []
        for name in ACTIVE_USERS:
            ACTIVE_USERS[name] += 1
            if ACTIVE_USERS[name] == 2:
                to_delete.append(name)
        for name in to_delete:
            ACTIVE_USERS.pop(name, None)
        time.sleep(8)


threading.Thread(target=set_inactive, daemon=True).start()

app = FastAPI()


@app.get('/')
async def root():
    return {'message': 'Robot-2048 backend, made with FastAPI, go to /docs to see all available endpoints'}


@app.post('/user')
async def user(request: Request):
    to_do = await request.json()
    name, pwd, action = to_do['name'], to_do['pwd'], to_do['action']
    user = DB.find_user(name)
    status = 'ok'
    content = None
    match action:
        case 'submit':
            user = DB.find_user(name)
            if user is None:
                status = f"User {name} doesn't exist. Create with 'New' button"
            elif user['pwd'] != pwd:
                status = f'Wrong password for {name}!'
            elif name in ACTIVE_USERS:
                status = f'{name} is already logged in'
            else:
                user['logs'] = DB.adjust_logs(user)
                content = {
                    'profile': user,
                    'max_logs': DB.max_logs
                }
        case 'new':
            user = DB.find_user(name)
            if user:
                status = f'User {name} already exists'
            else:
                s = 'admin' if name == 'Loki' else 'guest'
                user = DB.new_user(name, pwd, s)
                content = {
                    'profile': user,
                    'max_logs': DB.max_logs
                }
        case 'delete':
            delete_user_total(user)
    return {
        'status': status,
        'content': content
    }


@app.post('/update')
async def update(request: Request):
    to_do = await request.json()
    name = to_do['name']
    ACTIVE_USERS[name] = 0
    log_break = to_do['log_break']
    user = DB.find_user(name)
    if user is None:
        return {
            'status': f"Looks like user {name} doesn't exist anymore"
        }
    logs = user['logs']
    new_logs = user['logs'][log_break:] if len(logs) > log_break else []
    if to_do['clear_logs']:
        DB.update_user(name, {'logs': new_logs})
    else:
        DB.adjust_logs(user)
    user.pop('logs')
    return {
        'status': 'ok',
        'content': {
            'profile': user,
            'new_logs': new_logs
        }
    }


@app.post('/file')
async def file(request: Request):
    to_do = await request.json()
    idx = to_do['idx']
    action = to_do['action']
    content = None
    status = 'ok'
    match action:
        case 'weights':
            key = full_key(idx)
            file_list = S3.list_files()
            if key not in file_list:
                status = f'No weights for agent {idx} in storage'
            else:
                content = S3.client.generate_presigned_url('get_object', Params={
                    'Bucket': S3.space_name, 'Key': key}, ExpiresIn=60)
        case 'delete':
            kind = to_do['kind']
            count = delete_item_total(idx, kind)
            if not count:
                status = f'No item to delete named: {idx}'
    return {
        'status': status,
        'content': content
    }


@app.post('/all_items')
async def all_items(request: Request):
    to_do = await request.json()
    kind = to_do['kind']
    if kind == 'all':
        content = {v: DB.all_items(kind=to_do[v]) for v in DB.ARRAYS}
    else:
        content = DB.all_items(kind=kind)
    return {
        'status': 'ok',
        'content': content
    }


@app.post('/admin')
async def admin(request: Request):
    to_do = await request.json()
    job = to_do['job']
    user = DB.find_user(to_do['name'])
    if not user:
        return {
            'status': f'User {to_do["name"]} does not exist'
        }
    content = None
    match job:
        case 'user_description':
            status_list = ['guest', 'admin']
            description = {kind: [v['idx'] for v in user[kind]] for kind in DB.ARRAYS}
            description['time'] = user.get('time', time_now())
            content = {
                'list': status_list,
                'status': user['status'],
                'description': description
            }
        case 'status':
            new_status = to_do['status']
            if new_status == user['status']:
                return {
                    'status': f'Status of {to_do["name"]} is already set as {new_status}'
                }
            DB.update_user(to_do['name'], {'status': new_status})
    return {
        'status': 'ok',
        'content': content
    }


@app.post('/replay')
async def replay(request: Request):
    to_do = await request.json()
    idx = to_do['idx']
    status = 'ok'
    content = DB.get_game(idx)
    if content is None:
        status = f'Item with name {idx} is not in Storage'
    return {
        'status': status,
        'content': content
    }


@app.post('/slow')
async def slow(request: Request):
    to_do = await request.json()
    mode = to_do['mode']
    agent_idx = to_do['agent']
    name = to_do['name']
    match mode:
        case 'train':
            if to_do['is_new'] and (agent_idx in DB.all_items('Agents')):
                return {
                    'status': f'Agent {agent_idx} already exists, choose another name'
                }
            DB.replace_agent(name, to_do)
        case 'watch':
            if (agent_idx not in EXTRA_AGENTS) and \
                    (agent_idx not in DB.all_items('Agents')) or \
                    (full_key(agent_idx) not in S3.list_files()):
                return {
                    'status': f'Agent {agent_idx} does not exist or weights were not saved yet'
                }
            DB.delete_watch_user(to_do['current'])
            DB.new_user(name, None, 'tmp')
    DB.add_array_item(name, to_do, 'Jobs')
    return {
        'status': 'ok',
        'content': None
    }


@app.post('/job_status')
async def job_status(request: Request):
    to_do = await request.json()
    idx = to_do['idx']
    status = to_do['status']
    DB.set_job_status(idx, status)
    return {
        'status': 'ok',
        'content': None
    }


@app.post('/watch')
async def watch(request: Request):
    to_do = await request.json()
    idx = to_do['idx']
    mode = to_do['mode']
    status = 'ok'
    content = None
    match mode:
        case 'check_agent_load':
            content = DB.check_job_status(idx)
            if content in (1, 2):
                status = 'not loaded yet'
        case 'get_moves':
            job = DB.get_item(idx, 'Jobs')
            if job is None:
                status = f'Looks like <{idx}> process terminated'
            else:
                i = to_do['break']
                content = {
                    'moves': job['moves'][i:],
                    'tiles': job['tiles'][i:],
                }
        case 'once_again':
            count = DB.rerun_watch_job(idx, to_do['row'])
            if not count:
                status = f'<{idx}> process expired. Use "Watch Agent" button again'
    return {
        'status': status,
        'content': content
    }


if __name__ == '__main__':

    uvicorn.run(app, host="0.0.0.0", port=5000)
