from sqlalchemy import text
from web3.utils.threads import Timeout

from config import MuzikaContractConfig
from modules import database as db
from modules.web3 import get_web3
from modules.contracts.paper_contract import MuzikaPaperContract


def update_contracts():
    web3 = get_web3()

    # query for deleting music contracts and their IPFS files list if not mined
    delete_query_statement = """
        UPDATE `{}` `mc`
        INNER JOIN `{}` `mb`
          ON (`mb`.`post_id` = `mc`.`post_id`)
        SET
          `mb`.`status` = :set_status,
          `mc`.`status` = :set_status
        WHERE
          `mc`.`status` = :delete_status AND `mc`.`created_at` < NOW() - :expired_time
    """.format(db.table.board('music'), db.table.MUSIC_CONTRACTS)

    transaction_query_statement = """
        SELECT `mc`.*, `u`.`address`
        FROM
          `{}` `mc`
        LEFT JOIN `{}` `mb`
          ON (`mb`.`post_id` = `mc`.`post_id`)
        LEFT JOIN `{}` `u`
          ON (`u`.`user_id` = `mb`.`user_id`)
        WHERE
          `mc`.`status` = :track_status
    """.format(db.table.MUSIC_CONTRACTS, db.table.board('music'), db.table.USERS)

    with db.engine_rdwr.connect() as connection:
        # DELETE contracts that are not mined over specific time
        connection.execute(text(delete_query_statement),
                           set_status='deleted',
                           delete_status='untracked',
                           expired_time=MuzikaContractConfig.mining_expired_seconds)

        # QUERY not mined contracts
        contracts = db.to_relation_model_list(
            connection.execute(text(transaction_query_statement), track_status='untracked')
        )

        for contract in contracts:
            try:
                tx = web3.eth.waitForTransactionReceipt(transaction_hash=contract['tx_hash'], timeout=1)
            except Timeout:
                # if failed to get contract (not mined or fake transaction), check next contract
                continue

            # get contract
            if tx:
                contract_address = tx['contractAddress']
                tx_contract = MuzikaPaperContract(web3, contract_address=contract_address)
                seller_address = tx_contract.get_seller()

                # Check seller.
                # If the contract is derived from music post and the author of it is different from the real
                # contract owner, set status to tracked and delete post
                if contract['address'] and seller_address != contract['address']:
                    db.Statement(db.table.board('music'))\
                        .set(status='deleted')\
                        .where(post_id=contract['post_id'])\
                        .update(connection)

                db.Statement(db.table.MUSIC_CONTRACTS)\
                    .set(contract_address=contract_address, seller_address=seller_address, status='tracked')\
                    .where(contract_id=contract['contract_id'])\
                    .update(connection)