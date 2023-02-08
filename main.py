from base.start import *

app = FastAPI()


@app.get('/')
async def root():
    return {'message': 'Robot-2048 backend, made with FastAPI, go to /docs to see all available endpoints'}


@app.post('/users/new')
async def new_user(user: User):
    if DB.find_user(user.name):
        return {'status': False, 'message': f'{user.name} already exists'}
    else:
        DB.insert_user(user)
        return {'status': True, 'message': f'{user.name} successfully added'}


@app.get('/users/list')
async def new_user():
    return {'user_list': DB.user_list()}


@app.post('/users/delete')
async def delete_user(username: str):
    user = DB.find_user(username)
    if user:
        for agent in user['agents']:
            S3.delete(f'{agent}.pkl', 'agents')
            S3.delete(f'best_of_{agent}.pkl', 'games')
            S3.delete(f'best_of_trial_{agent}.pkl', 'games')
            S3.delete(f'stop_{agent}.json', 'stop')
        DB.delete_user(username)
        return {'status': False, 'message': f'{user.name} successfully deleted'}
    else:
        return {'status': True, 'message': f'{user.name} does not exist'}


if __name__ == '__main__':

    uvicorn.run(app, host="0.0.0.0", port=5000)
