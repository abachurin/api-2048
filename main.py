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
    if name in RQ:
        for fail in RQ[name]['fail'].get_job_ids():
            job = Job.fetch(fail, connection=REDIS.conn)
            print(job.latest_result())
            DB.add_log(name, job.latest_result())
            RQ[name]['fail'].remove(fail, delete_job=True)
        if len(RQ[name]['q'].jobs) == 0:
            RQ[name]['worker'].ter
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
    kind = to_do['kind']
    if kind == 'all':
        content = {v: DB.all_items(item=to_do[v]) for v in DB.FIELDS}
    else:
        content = DB.all_items(item=kind)
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
    mode = to_do['mode']
    agent_idx = to_do['agent']['idx']
    new = to_do['new']
    if mode == 'train' and new and agent_idx in DB.all_items('Agents'):
        return {'status': f'Agent {agent_idx} already exists, choose another name'}
    idx = to_do['idx']
    name = to_do['name']
    to_do['func'] = SLOW_TASKS[mode]
    try:
        if name not in RQ:
            RQ[name] = {
                'q': Queue(ame=name, connection=REDIS.conn),
                'fail': FailedJobRegistry(name=name, connection=REDIS.conn),
                'worker': Worker(queues=[name], name=name, connection=REDIS.conn)
            }
            RQ[name]['worker'].work()
        job = RQ[name]['q'].enqueue(slow_task, to_do, job_id=idx, timeout=-1)
        DB.add_array_item(name, idx, 'Jobs')
        return {
            'status': 'ok',
            'content': job.id
        }
    except Exception as ex:
        return {
            'status': f'Unable to place job in Queue: {str(ex)}'
        }


if __name__ == '__main__':

    uvicorn.run(app, host="0.0.0.0", port=5000)
