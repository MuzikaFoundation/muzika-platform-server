from sqlalchemy import text
from web3.utils.threads import Timeout

from config import MuzikaContractConfig
from modules import database as db
from modules.web3 import get_web3


def update_contracts():
    web3 = get_web3()

    delete_query_statement = """
        DELETE FROM `{}`
        WHERE `contract_address` IS NULL AND `created_at` < NOW() - :expired_time
    """.format(db.table.PAPERS)

    with db.engine_rdwr.connect() as connection:
        # DELETE contracts that are not mined over specific time
        connection.execute(text(delete_query_statement), expired_time=MuzikaContractConfig.register_expired_seconds)

        # UPDATE contracts if they are mined
        contracts = db.to_relation_model_list(
            db.Statement(db.table.PAPERS).where(contract_address=None).select(connection)
        )

        for contract in contracts:
            try:
                tx = web3.eth.waitForTransactionReceipt(transaction_hash=contract['tx_hash'], timeout=1)
            except Timeout:
                continue

            # if mined, update it
            if tx:
                db.Statement(db.table.PAPERS)\
                    .set(contract_address=tx['contractAddress'])\
                    .where(paper_id=contract['paper_id'])\
                    .update(connection)
