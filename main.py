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
async def manage_users(request: Request):
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
                user_status = 'admin' if name == 'Loki' else 'guest'
                user = DB.new_user(name, pwd, user_status)
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
async def manage_files(request: Request):
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
async def get_all_items(request: Request):
    to_do = await request.json()
    kind = to_do['kind']
    if kind == 'all':
        content = {v: DB.all_items(kind=to_do[v]) for v in DB.FIELDS}
    else:
        content = DB.all_items(kind=kind)
    return {
        'status': 'ok',
        'content': content
    }


@app.post('/admin')
async def manage_users(request: Request):
    to_do = await request.json()
    job = to_do['job']
    if 'name' in to_do:
        user = DB.find_user(to_do['name'])
        if not user:
            return {
                'status': f'User {to_do["name"]} does not exist'
            }
    content = None
    match job:
        case 'status_list':
            status_list = DB.all_items('status')
            content = {
                'list': status_list,
                'status': user['status']
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


@app.post('/watch')
async def replay(request: Request):
    to_do = await request.json()
    status = 'ok'
    content = None
    idx = to_do['idx']
    key = full_key(idx)
    file_list = S3.list_files()
    if key not in file_list:
        status = f'No weights for agent {idx} in storage'
    else:
        agent = DB.get_agent(idx, 'Agents')
        if agent is None:
            status = f'Looks like Agent {idx} was deleted'
        else:
            content = {
                'url': S3.client.generate_presigned_url('get_object', Params={
                    'Bucket': S3.space_name, 'Key': key}, ExpiresIn=60),
                'signature': agent['weight_signature']
            }
    return {
        'status': status,
        'content': content
    }


@app.post('/slow')
async def slow_job(request: Request):
    to_do = await request.json()
    mode = to_do['mode']
    agent_idx = to_do['agent']
    new = to_do['is_new']
    name = to_do['name']
    if mode == 'train':
        if new and (agent_idx in DB.all_items('Agents')):
            return {
                'status': f'Agent {agent_idx} already exists, choose another name'
            }
        DB.replace_agent(name, to_do)
    user = DB.find_user(name)
    DB.add_array_item(name, to_do, 'Jobs')
    return {
        'status': 'ok',
        'content': len(user['Jobs'])
    }


@app.post('/job_status')
async def slow_job(request: Request):
    to_do = await request.json()
    idx = to_do['idx']
    status = to_do['status']
    DB.set_job_status(idx, status)
    return {
        'status': 'ok',
        'content': None
    }


if __name__ == '__main__':

    uvicorn.run(app, host="0.0.0.0", port=5000)
