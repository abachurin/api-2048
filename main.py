from fastapi import FastAPI, HTTPException, Request
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
    match action:
        case 'submit':
            user = DB.find_user(name)
            if user is None:
                return {'status': f"User {name} doesn't exist. Create with 'New' button"}
            if user['pwd'] != pwd:
                return {'status': f'Wrong password!'}
            else:
                status = user['status']
                if status == 'guest':
                    agents = user['Agents']
                    games = user['Games']
                else:
                    agents = DB.all_items('Agents')
                    games = DB.all_items('Games')
                profile = {'status': status, 'Agents': agents, 'Games': games}
                content = {
                    'msg': f'Welcome back {name}!',
                    'profile': profile
                }
        case 'new':
            user = DB.find_user(name)
            if user:
                return {'status': f'User {name} already exists'}
            else:
                status = 'admin' if name == 'Loki' else 'guest'
                DB.new_user(name, pwd, status)
                profile = {'status': status, 'Agents': ['config.json'], 'Games': ['config.json']}
                content = {
                    'msg': f'Welcome {name}!',
                    'profile': profile
                }
        case 'delete':
            for agent in user['Agents']:
                delete_item(agent, 'Agents')
                S3.delete(agent, 'stop')
            for game in user['Games']:
                delete_item(game, 'Games')
            DB.delete_user(name)
            content = {
                'msg': f'{name} successfully deleted'
            }
        case _:
            content = None
    return {'status': 'ok', 'content': content}


@app.post('/file')
async def manage_files(request: Request):
    to_do = await request.json()
    kind = to_do['kind']
    name = to_do['name']
    action = to_do['action']
    try:
        file_list = S3.list_files(folder=kind)
    except Exception as ex:
        return {'status': f'Looks like S3 Storage is inaccessible: {str(ex)}'}
    if name not in file_list:
        return {'status': f'No file with supplied name: {name}'}
    match action:
        case 'download':
            try:
                url = S3.client.generate_presigned_url('get_object', Params={
                    'Bucket': S3.space_name, 'Key': full_s3_key(name, kind)}, ExpiresIn=60)
                content = {
                    'url': url
                }
                return {'status': 'ok', 'content': content}
            except Exception as ex:
                return {'status': f'Looks like S3 storage failed: {str(ex)}'}
        case 'delete':
            try:
                delete_item(name, kind)
                content = {
                    'msg': f'{name} successfully deleted'
                }
                return {'status': 'ok', 'content': content}
            except Exception as ex:
                return {'status': f'Looks like S3 storage failed: {str(ex)}'}
        case _:
            return {'status': 'ok', 'content': None}


@app.post('/all_items')
async def manage_files(request: Request):
    to_do = await request.json()
    return {'status': 'ok', 'content': {'list': DB.all_items(kind=to_do['kind'])}}


@app.post('/replay')
async def manage_files(request: Request):
    to_do = await request.json()
    game = S3.load(to_do['name'], 'Games')
    return {'status': 'ok', 'content': {'list': DB.all_items(kind=to_do['kind'])}}


@app.post('/slow')
async def slow_job(request: Request):
    to_do = await request.json()
    match to_do['job']:
        case _:
            func = to_do['job']
            params = to_do['params']
    try:
        res = Q.enqueue(func, params)
        return {'status': 'ok', 'msg': res.id}
    except Exception as ex:
        return {'status': f'Unable to place job in Queue: {str(ex)}'}


@app.post('/check_slow')
async def check_slow_job(request: Request):
    to_do = await request.json()
    idx = to_do['idx']
    try:
        job = Job(idx, REDIS.conn)
        return {'status': 'ok', 'msg': job.get_status()}
    except Exception as ex:
        return {'status': f'Unable to get job status: {str(ex)}'}


if __name__ == '__main__':

    uvicorn.run(app, host="0.0.0.0", port=5000)
