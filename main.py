from fastapi import FastAPI, Request
import uvicorn
from base.utils import *

app = FastAPI()


@app.get('/')
async def root():
    return {'message': 'Robot-2048 backend, made with FastAPI, go to /docs to see all available endpoints'}


@app.post('/user')
async def manage_users(request: Request):
    to_do = await request.json()
    name, pwd, action = to_do['name'], to_do['pwd'], to_do['action']
    user = DB.find_user(name)
    content = None
    match action:
        case 'submit':
            user = DB.find_user(name)
            if user is None:
                return {
                    'status': f"User {name} doesn't exist. Create with 'New' button"
                }
            if user['pwd'] != pwd:
                return {
                    'status': f'Wrong password!'
                }
            else:
                user['logs'] = DB.adjust_logs(user)
                content = {
                    'profile': user,
                    'max_logs': DB.max_logs
                }
        case 'new':
            user = DB.find_user(name)
            if user:
                return {
                    'status': f'User {name} already exists'
                }
            else:
                status = 'admin' if name == 'Loki' else 'guest'
                user = DB.new_user(name, pwd, status)
                content = {
                    'profile': user,
                    'max_logs': DB.max_logs
                }
        case 'delete':
            delete_user_total(user)
    return {
        'status': 'ok',
        'content': content
    }


@app.post('/update')
async def update(request: Request):
    to_do = await request.json()
    name = to_do['name']
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
    kind = to_do['kind']
    idx = to_do['idx']
    action = to_do['action']
    content = None
    match action:
        case 'download':
            file_list = S3.list_files(kind=kind)
            if idx not in file_list:
                return {
                    'status': f'No item for download named: {idx}'
                }
            url = S3.client.generate_presigned_url('get_object', Params={
                'Bucket': S3.space_name, 'Key': full_s3_key(idx, kind)}, ExpiresIn=60)
            content = url
        case 'delete':
            count = delete_item_total(idx, 'Jobs')
            if not count:
                return {
                    'status': f'No item to delete named: {idx}'
                }
    return {
        'status': 'ok',
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
    idx = to_do['name']
    kind = to_do['kind']
    if idx in S3.list_files(kind):
        url = S3.client.generate_presigned_url('get_object', Params={
            'Bucket': S3.space_name, 'Key': full_s3_key(idx, kind)}, ExpiresIn=300)
        return {
            'status': 'ok',
            'content': url
        }
    else:
        return {
            'status': f'Item with name {idx} is not in Storage'
        }


@app.post('/slow')
async def slow_job(request: Request):
    to_do = await request.json()
    mode = to_do['mode']
    agent_idx = to_do['agent']['idx']
    new = to_do['new']
    if mode == 'train' and new and agent_idx in DB.all_items('Agents'):
        return {'status': f'Agent {agent_idx} already exists, choose another name'}
    name = to_do['name']
    user = DB.find_user(name)
    DB.add_array_item(name, to_do, 'Jobs')
    return {
        'status': 'ok',
        'content': len(user['Jobs'])
    }


if __name__ == '__main__':

    uvicorn.run(app, host="0.0.0.0", port=5000)
