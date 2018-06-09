
import os
from celery import Celery
from modules.ipfs import RelayIpfs

if os.environ.get('ENV') in ['production', 'stage']:
    # In production or stage level, use redis as broker.
    from config import CacheConfig
    celery_broker = 'redis://{}:{}/0'.format(CacheConfig.host, CacheConfig.port)
    app = Celery('tasks', backend=celery_broker, broker=celery_broker)
else:
    # In local, use sqlite for convenient. It has to be used only in local environment.
    app = Celery('tasks', backend='db+sqlite:///celery.sqlite', broker='sqla+sqlite:///celery.sqlite')
