from sqlalchemy import text
from web3.utils.threads import Timeout

from config import MuzikaContractConfig
from modules import database as db
from modules.web3 import get_web3


def update_contracts():
    web3 = get_web3()

    # query for deleting music contracts and their IPFS files list if not mined
    delete_query_statement = """
        UPDATE `{}` `mb`
        INNER JOIN `{}` `mc`
          ON (`mb`.`contract_id` = `mc`.`contract_id`)
        SET
          `mb`.`status` = :set_status,
          `mc`.`status` = :set_status
        WHERE
          `mc`.`status` = :delete_status AND `mc`.`created_at` < NOW() - :expired_time
    """.format(db.table.board('music'), db.table.MUSIC_CONTRACTS)

    with db.engine_rdwr.connect() as connection:
        # DELETE contracts that are not mined over specific time
        connection.execute(text(delete_query_statement),
                           set_status='deleted',
                           delete_status='untracked',
                           expired_time=MuzikaContractConfig.mining_expired_seconds)

        # UPDATE contracts if they are mined
        contracts = db.to_relation_model_list(
            db.Statement(db.table.MUSIC_CONTRACTS).where(contract_address=None).select(connection)
        )

        for contract in contracts:
            try:
                tx = web3.eth.waitForTransactionReceipt(transaction_hash=contract['tx_hash'], timeout=1)
            except Timeout:
                continue

            # if mined, update it
            if tx:
                db.Statement(db.table.MUSIC_CONTRACTS)\
                    .set(contract_address=tx['contractAddress'], status='tracked')\
                    .where(contract_id=contract['contract_id'])\
                    .update(connection)
