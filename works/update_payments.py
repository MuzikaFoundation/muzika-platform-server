from sqlalchemy import text
from web3.utils.threads import Timeout

from config import MuzikaContractConfig
from modules import database as db
from modules.web3 import get_web3


def update_payments():
    """
    All of transaction for purchase of music is not reliable,
    which can have price, buyer or contract address.
    Therefore we have to wait for transaction to be mined with txHash and get receipt
    of the txHash, then all of information (price, buyer etc.) are obtained by the receipt.
    Then, save the information to our database

    Status
        pending  : Ready for mined transaction given hash.
        success  : The transaction is valid and accepted in the blockchain.
        failed   : The transaction is failed because of out of gas, not enough muzika or any other reason.
        invalid  : The transaction is invalid (e.g. this transaction is not for purchase of music)
        disabled : The transaction is not found in the blockchain (That is, timeout of waiting for transaction)
    """
    web3 = get_web3()
    purchase_event_name = web3.sha3(b'Purchase(address,uint256)')

    # query for updating status of timeout transaction
    update_query_statement = """
        UPDATE `{}` SET `status` = 'disabled'
        WHERE
            `status` = 'pending'
        AND `created_at` < NOW() - INTERVAL 3 HOUR
    """.format(db.table.MUSIC_PAYMENTS)

    # query for deleting timeout transaction
    delete_query_statement = """
        DELETE FROM `{}`
        WHERE
            `status` = 'disabled'
        AND `created_at` < NOW() - INTERVAL 6 HOUR
    """.format(db.table.MUSIC_PAYMENTS)

    with db.engine_rdwr.connect() as connection:

        # get list of payment history that is not mined (wait)
        payments = db.to_relation_model_list(
            db.Statement(db.table.MUSIC_PAYMENTS).where(status='pending').select(connection)
        )

        def invalid_payment(__payment):
            # this transaction is not valid
            db.Statement(db.table.MUSIC_PAYMENTS)\
                .set(status='invalid')\
                .where(payment_id=__payment['payment_id'])\
                .update(connection)

        for payment in payments:
            try:
                receipt = web3.eth.waitForTransactionReceipt(transaction_hash=payment['tx_hash'], timeout=1)
            except Timeout:
                continue

            if not receipt:
                continue

            if receipt.status == 0:
                # this transaction is failed
                db.Statement(db.table.MUSIC_PAYMENTS)\
                    .set(status='failed')\
                    .where(payment_id=payment['payment_id'])\
                    .update(connection)

                continue

            """
            Because we use approval function to purchase music, value of `to` in
            transaction is MuzikaCoin contract's address

                MuzikaCoin.address == tx['to']
                
            Contract address is equal to event.address
            """

            purchase_events = [event for event in receipt.logs if event.topics[0] == purchase_event_name]

            if len(purchase_events) == 0:
                # Purchase event is not emitted
                invalid_payment(payment)
                continue

            event = purchase_events[-1]
            contract_address = event.address
            contract_exists = db.Statement(db.table.MUSIC_CONTRACTS).columns('"_"')\
                .where(contract_address=contract_address, status='success')\
                .limit(1).select(connection).fetchone()

            if contract_exists is None:
                # Contract is not exists in our database. It is not a contract for muzika platform
                invalid_payment(payment)
                continue

            """
            Contract is valid for our platform. Use it!
            """

            # price is equal to event.data (type is str)
            price = event.data

            # buyer is equal to event.topics[1]
            # structure of event is `Purchase(address,uint256)`
            # type is HexBytes
            buyer = web3.toChecksumAddress('0x' + event.topics[1].hex()[-40:])

            db.Statement(db.table.MUSIC_PAYMENTS)\
                .set(buyer_address=buyer,
                     contract_address=contract_address,
                     price=price,
                     status='success')\
                .where(payment_id=payment['payment_id'])\
                .update(connection)

        # execute update query
        connection.execute(text(update_query_statement))

        # execute delete query (timeout is doubled)
        connection.execute(text(delete_query_statement))
