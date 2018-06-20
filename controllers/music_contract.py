from Crypto.PublicKey import RSA
from flask import Blueprint, request
from sqlalchemy import text

from modules import database as db
from modules.contracts.paper_contract import MuzikaPaperContract
from modules.login import jwt_check
from modules.response.error import ERR
from modules.response import helper
from modules.web3 import get_web3
from modules.utils import txhash_validation

blueprint = Blueprint('music_contract', __name__, url_prefix='/api')


@blueprint.route('/music/<contract_address>/key', methods=['POST'])
@jwt_check
def _get_paper_file(contract_address):
    """
    Get aes key for decrypt a paper from a contract.

    json form:
    {
        "public_key": public key for encryption
    }
    """
    json_form = request.get_json(force=True, silent=True)
    public_key = json_form.get('public_key')

    # not support downloading without encryption
    if not isinstance(public_key, str):
        return helper.response_err(ERR.INVALID_REQUEST_BODY)

    # parse public key
    try:
        public_key = RSA.import_key(public_key)
    except ValueError:
        return helper.response_err(ERR.INVALID_REQUEST_BODY)

    user_address = request.user['address']

    web3 = get_web3()
    contract_address = web3.toChecksumAddress(contract_address)
    contract = MuzikaPaperContract(web3, contract_address=contract_address)

    if not contract.purchased(user_address, {'from': user_address}):
        # if the user hasn't purchased this paper
        return helper.response_err(ERR.AUTHENTICATION_FAILED)

    key_query_statement = """
        SELECT 
          `if`.`ipfs_hash`, `if`.`encrypted`, `fp`.`aes_key` 
        FROM `music_contracts` `mc`
        INNER JOIN `ipfs_files` `if`
          ON (`mc`.`ipfs_file_id` = `if`.`file_id`)
        LEFT JOIN `ipfs_files_private` `fp`
          ON (`if`.`file_id` = `fp`.`file_id`)
        WHERE
          `contract_address` = :contract_address AND `mc`.`status` = :contract_status
        LIMIT 1
    """

    with db.engine_rdonly.connect() as connection:
        key_query = connection.execute(text(key_query_statement),
                                       contract_address=contract_address,
                                       contract_status='success').fetchone()

        # if the contract is not registered in the server or does not have IPFS file
        if not key_query:
            return helper.response_err(ERR.NOT_EXIST)

        ipfs_hash = key_query['ipfs_hash']
        encrypted = key_query['encrypted']
        aes_key = key_query['aes_key']

        if not encrypted:
            # if the file is not encrypted, response with null key
            return helper.response_ok({'key': None})
        else:
            # if the file is encrypted, response with AES key encrypted by user's public key.
            from Crypto.Cipher import PKCS1_OAEP
            cipher = PKCS1_OAEP.new(public_key)
            encrypted_aes_key = cipher.encrypt(aes_key)
            return helper.response_ok({'key': encrypted_aes_key})


@blueprint.route('/music/purchase', methods=['POST'])
@jwt_check
def _post_music_purchase():
    """
    Receive txHash from client. This hash is about music purchase.
    For simplify and security, only accept txHash (any of other extra information is not received)
    That is, no contract address and price are given. (After mined, automatically saved the information)
    See works/update_payments.py
    """
    json_form = request.get_json(force=True, silent=True)
    tx_hash = json_form.get('tx_hash')
    requester = request.user['address']

    if not txhash_validation(tx_hash):
        return helper.response_err(ERR.INVALID_TX_HASH)

    with db.engine_rdonly.connect() as connection:
        payment_id = db.statement(db.table.MUSIC_PAYMENTS).set(
            # Set to lowercase
            tx_hash=tx_hash.lower(),
            requester=requester
        ).insert(connection).lastrowid

    return helper.response_ok({'payment_id': payment_id, 'tx_hash': tx_hash})
