
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


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """
    Registers periodical tasks.
    """
    from config import MuzikaContractConfig
    sender.add_periodic_task(MuzikaContractConfig.update_period, update_contracts.s(), name='update_contracts')
    sender.add_periodic_task(MuzikaContractConfig.update_period, update_payments.s(), name='update_payments')


@app.task(bind=True, max_retries=3)
def update_contract_files(self, ipfs_file_id, contract_id):
    from modules.ipfs import track_object, translate_contract
    with db.engine_rdwr.connect() as connection:
        track_object(connection, ipfs_file_id=ipfs_file_id)
        translate_contract(connection, contract_id)


@app.task(bind=True)
def update_contracts(self):
    from works.update_contracts import update_contracts
    update_contracts()


@app.task(bind=True)
def update_payments(self):
    from works.update_payments import update_payments
    update_payments()