from sqlalchemy import text
from web3.utils.threads import Timeout

from config import MuzikaContractConfig
from modules import database as db
from modules.muzika_contract import MuzikaContractHandler
from modules.web3 import get_web3
from modules.contracts.paper_contract import MuzikaPaperContract


def update_contracts():
    web3 = get_web3()

    complete_delete_query_statement = """
        DELETE FROM `{}`
        WHERE `status` NOT IN :delete_status AND `created_at` < NOW() - INTERVAL 6 HOUR
    """.format(db.table.MUSIC_CONTRACTS)

    # query for deleting music contracts and their IPFS files list if not mined
    delete_query_statement = """
        UPDATE `{}` `mc`
        LEFT JOIN `{}` `mb`
          ON (`mb`.`post_id` = `mc`.`post_id`)
        SET
          `mb`.`status` = :set_board_status,
          `mc`.`status` = :set_contract_status
        WHERE
          `mc`.`status` = :delete_status AND `mc`.`created_at` < NOW() - INTERVAL 3 HOUR
        """.format(db.table.MUSIC_CONTRACTS, db.table.board('music'))

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
        # DELETE contracts completely that are not mined over specific time
        connection.execute(text(complete_delete_query_statement),
                           delete_status=['success'])

        # DELETE contracts that are not mined over specific time
        connection.execute(text(delete_query_statement),
                           set_board_status='deleted',
                           set_contract_status='disabled',
                           delete_status='pending')

        # QUERY not mined contracts
        contracts = db.to_relation_model_list(
            connection.execute(text(transaction_query_statement), track_status='pending')
        )

        # get original bytecode of the paper contract
        contract_handler = MuzikaContractHandler()
        payment_interface_contract = contract_handler.get_interface('Dispatcher')
        payment_contract = contract_handler.get_interface('MuzikaPaperContract')
        contract_bytecode = payment_contract['bytecode'][:-68]
        contract_bytecode = contract_bytecode.replace(
            '__LibPaperPaymentInterface______________',
            payment_interface_contract['networks'][web3.version.network]['address'][2:]
        )

        for contract in contracts:
            contract_status = 'success'
            board_status = 'posted'

            try:
                tx_receipt = web3.eth.waitForTransactionReceipt(transaction_hash=contract['tx_hash'], timeout=1)
            except Timeout:
                # if failed to get contract (not mined or fake transaction), check next contract
                continue

            if tx_receipt:
                # TODO : validate the contract

                try:
                    contract_address = tx_receipt['contractAddress']
                    tx_contract = MuzikaPaperContract(web3, contract_address=contract_address)
                    seller_address = tx_contract.get_seller()

                    tx = web3.eth.getTransaction(contract['tx_hash'])

                    # if tx data is invalid, set contract status to invalid and board status to deleted
                    if tx.input[:len(contract_bytecode)] != contract_bytecode:
                        contract_status = 'invalid'
                        board_status = 'deleted'

                    # Check seller.
                    # If the contract is derived from music post but the author of it is different from the real
                    # contract owner, set status to success but delete post
                    if contract['address'] and seller_address != contract['address']:
                        board_status = 'deleted'
                except ValueError as e:
                    # if ValueError occurs (may be wrong transaction), set invalid contracvt and delete post
                    contract_status = 'invalid'
                    board_status = 'deleted'

                if board_status == 'deleted':
                    db.Statement(db.table.board('music'))\
                        .set(status='deleted')\
                        .where(post_id=contract['post_id'])\
                        .update(connection)

                if contract_status == 'success':
                    db.Statement(db.table.MUSIC_CONTRACTS)\
                        .set(contract_address=contract_address, seller_address=seller_address, status='success')\
                        .where(contract_id=contract['contract_id'])\
                        .update(connection)
                else:
                    db.Statement(db.table.MUSIC_CONTRACTS)\
                        .set(status=contract_status)\
                        .where(contract_id=contract['contract_id'])\
                        .update(connection)