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
                content = {
                    'msg': f'Welcome back {name}!',
                    'profile': user
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
                    'msg': f'Welcome {name}!',
                    'profile': user
                }
        case 'delete':
            delete_user_total(user)
    return {
        'status': 'ok',
        'content': content
    }


@app.post('/file')
async def manage_files(request: Request):
    to_do = await request.json()
    kind = to_do['kind']
    name = to_do['name']
    action = to_do['action']
    file_list = S3.list_files(kind=kind)
    if name not in file_list:
        return {
            'status': f'No file with supplied name: {name}'
        }
    content = None
    match action:
        case 'download':
            url = S3.client.generate_presigned_url('get_object', Params={
                'Bucket': S3.space_name, 'Key': full_s3_key(name, kind)}, ExpiresIn=60)
            content = url
        case 'delete':
            delete_item_total(name, kind)
    return {
        'status': 'ok',
        'content': content
    }


@app.post('/all_items')
async def manage_files(request: Request):
    to_do = await request.json()
    return {
        'status': 'ok',
        'content': DB.all_items(item=to_do['kind'])
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
        case 'user_list':
            content = DB.all_items('name')
        case 'status_list':
            status_list = DB.all_items('status')
            content = {
                'list': status_list,
                'status': user['status']
            }
        case 'delete':
            delete_user_total(user)
        case 'status':
            new_status = to_do['status']
            if new_status == user['status']:
                return {
                    'status': f'Status of {to_do["name"]} is already set as {new_status}'
                }
            match new_status:
                case 'admin':
                    fields = {
                        'status': 'admin',
                        'Agents': DB.all_items('Agents'),
                        'Games': DB.all_items('Games'),
                        'jobs': DB.all_items('jobs')
                    }
                    DB.update_user(to_do["name"], {'status': 'admin'})
                case 'guest':
                    fields = {
                        'status': 'guest'
                    }
            DB.update_user(to_do["name"], fields)
    return {
        'status': 'ok',
        'content': content
    }


@app.post('/replay')
async def manage_files(request: Request):
    to_do = await request.json()
    game = S3.load(to_do['name'], 'Games')
    if game:
        return {
            'status': 'ok',
            'content': game
        }
    else:
        return {
            'status': f'Game with name {to_do["name"]} is not in Storage'
        }


@app.post('/slow')
async def slow_job(request: Request):
    to_do = await request.json()
    match to_do['job']:
        case _:
            func = to_do['job']
            params = to_do['params']
    try:
        res = RQ.enqueue(func, params)
        DB.add_item(to_do['user'], to_do['description'], 'jobs')
        DB.add_job(to_do['description'], res.id)
        return {
            'status': 'ok',
            'content': res.id
        }
    except Exception as ex:
        return {'status': f'Unable to place job in Queue: {str(ex)}'}


@app.post('/check_slow')
async def check_slow_job(request: Request):
    to_do = await request.json()
    idx = to_do['idx']
    try:
        job = Job(idx, REDIS.conn)
        return {
            'status': 'ok',
            'content': job.get_status()
        }
    except Exception as ex:
        return {
            'status': f'Unable to get job status: {str(ex)}'
        }


if __name__ == '__main__':

    uvicorn.run(app, host="0.0.0.0", port=5000)
