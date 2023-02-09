from base.start import *

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
                DB.insert_user(name, pwd, status)
                profile = {'status': status, 'Agents': [], 'Games': []}
                content = {
                    'msg': f'Welcome {name}!',
                    'profile': profile
                }
        case 'delete':
            for agent in user['Agents']:
                S3.delete(agent, 'Agents')
                S3.delete(agent, 'stop')
            for game in user['Games']:
                S3.delete(game, 'Games')
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
    action = to_do['action']
    kind = to_do['kind']
    name = to_do['name']
    if name not in S3.list_files(folder=kind):
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
                S3.delete(name, kind)
                content = {
                    'msg': f'{name} successfully deleted'
                }
                return {'status': 'ok', 'content': content}
            except Exception as ex:
                return {'status': f'Looks like S3 storage failed: {str(ex)}'}
        case _:
            return {'status': 'ok', 'content': None}


if __name__ == '__main__':

    uvicorn.run(app, host="0.0.0.0", port=5000)
