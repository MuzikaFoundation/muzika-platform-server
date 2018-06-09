
import os
from celery import Celery
from modules import database as db

if os.environ.get('ENV') in ['production', 'stage']:
    # In production or stage level, use redis as broker.
    from config import CacheConfig
    celery_broker = 'redis://{}:{}/0'.format(CacheConfig.host, CacheConfig.port)
    app = Celery('tasks', backend=celery_broker, broker=celery_broker)
else:
    # In local, use sqlite for convenient. It has to be used only in local environment.
    app = Celery('tasks', backend='db+sqlite:///celery.sqlite', broker='sqla+sqlite:///celery.sqlite')


@app.task(bind=True, max_retries=3)
def ipfs_objects_update(self, ipfs_file_id):
    from modules.ipfs import track_object
    with db.engine_rdwr.connect() as connection:
        track_object(connection, ipfs_file_id=ipfs_file_id)