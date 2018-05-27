from Crypto.PublicKey import RSA
from flask import Blueprint, request, make_response
from sqlalchemy import text

from modules import database as db
from modules.aws import MuzikaS3Bucket
from modules.block.block import Block
from modules.block.block_request import BlockRequest
from modules.contracts.paper_contract import MuzikaPaperContract
from modules.ipfs import RelayIpfs
from modules.login import jwt_check
from modules.muzika_contract import MuzikaContractHandler
from modules.response import error_constants as ER
from modules.response import helper
from modules.web3 import get_web3

blueprint = Blueprint('paper', __name__, url_prefix='/api')


@blueprint.route('/paper', methods=['POST'])
@jwt_check
def _upload_paper_contract():
    """
    Uploads a paper contract.

    json form:
    {
        "tx_hash": tx-hash value,
        "name": paper name,
        "file_id": file id (optional),
    }

    The background process checks the transaction is mined, and if then, save the contract address. It must checks
    the contract file IPFS hash, seller address (seller's user id) and if invalid, remove the requested paper from
    the database for paper contract integrity. Also, when the transaction is not mined for over 10 minutes, ignore
    it too.
    """
    user_id = request.user['user_id']

    json_form = request.get_json(force=True, silent=True)
    tx_hash = json_form.get('tx_hash')
    file_id = json_form.get('file_id')
    name = json_form.get('name')

    statement = db.Statement(db.table.PAPERS).set(user_id=user_id, tx_hash=tx_hash, name=name)

    # When the transaction is mined, so the created contract would have file hash value. If the server and storage
    # (s3 bucket) have the file hash, the background process gets file id from database and update the file id. If
    # not, remove the paper contract in the database.
    if file_id:
        statement.set(file_id=file_id)

    with db.engine_rdwr.connect() as connection:
        statement.insert(connection)
        return helper.response_ok({'status': 'success'})


"""
 TODO: Approve user to add a new paper contract to the network.
"""
# @blueprint.route('/paper', methods=['POST'])
@jwt_check
def _upload_paper():
    """
    Uploads a paper file from client.

    json form:
    {
        "hash": file hash string,
        "price": uint256,
        "encrypted": true | false,
    }

    Server downloads the paper file by its IPFS process from the client IPFS node and it creates a muzika contract
    for creating a paper in the block chain network.

    Server must have an IPFS node and it pins the object file for spreading the paper file.
    """
    json_form = request.get_json(force=True, silent=True)
    file_hash = json_form.get('hash')
    wallet_address = request.user['address']
    price = json_form.get('price')
    encrypted = json_form.get('encrypted', False)

    # check request json
    if not isinstance(file_hash, str) or not isinstance(price, int) or not isinstance(encrypted, bool):
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    # pin the file for spreading out the paper
    relay_ipfs = RelayIpfs()
    api = relay_ipfs.get_connection()
    # TODO : process if failed to pin (timeout problem)
    api.pin_add(file_hash)

    # create a paper contract
    web3 = get_web3()
    contract_handler = MuzikaContractHandler()
    paper_contract = contract_handler.get_contract(web3, 'MuzikaPaperContract')

    tx_hash = paper_contract.constructor(web3.toChecksumAddress(wallet_address), price, file_hash, '').transact()

    return helper.response_ok({'status': 'success'})


@blueprint.route('/paper/<contract_address>', methods=['GET'])
def _get_paper_contract(contract_address):
    """
    Gets the paper contract information.
    """
    paper_contract_statement = """
        SELECT `p`.*, '!user', `u`.* FROM `papers` `p`
        LEFT JOIN `users` `u`
          ON (`u`.`user_id` = `p`.`user_id`)
        WHERE `contract_address` = :contract_address
        LIMIT 1
    """

    with db.engine_rdonly.connect() as connection:
        paper_contract = connection.execute(text(paper_contract_statement),
                                            contract_address=contract_address).fetchone()

        if not paper_contract:
            return helper.response_err(ER.NOT_EXIST, ER.NOT_EXIST_MSG)

        return helper.response_ok(db.to_relation_model(paper_contract))


@blueprint.route('/paper/<contract_address>/download', methods=['POST'])
@jwt_check
def _get_paper_file(contract_address):
    """
    Downloads a paper from a contract.

    json form:
    {
        "public_key": public key for encryption
    }
    """
    json_form = request.get_json(force=True, silent=True)
    public_key = json_form.get('public_key')

    # not support downloading without encryption
    if not isinstance(public_key, str):
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    # parse public key
    try:
        public_key = RSA.import_key(public_key)
    except ValueError:
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    user_address = request.user['address']

    web3 = get_web3()
    contract = MuzikaPaperContract(web3, contract_address=contract_address)

    if not contract.purchased(user_address):
        # if the user hasn't purchased this paper
        return helper.response_err(ER.AUTHENTICATION_FAILED, ER.AUTHENTICATION_FAILED_MSG)

    paper_statement = db.Statement(db.table.PAPERS).where(contract_address=contract_address).limit(1)

    with db.engine_rdonly.connect() as connection:
        paper = db.to_relation_model(paper_statement.select(connection).fetchone())

        # if not supporting this paper contract
        if not paper:
            return helper.response_err(ER.NOT_EXIST, ER.NOT_EXIST_MSG)

        file_id = paper['file_id']

        # if not having file
        if not file_id:
            # TODO:
            return helper.response_err(ER.NOT_EXIST, ER.NOT_EXIST_MSG)
        else:
            # get ipfs file hash
            file_hash = paper['ipfs_file_hash']

            # download from bucket
            bucket = MuzikaS3Bucket()
            s3_response = bucket.get(connection, file_id)
            file_blob = s3_response['Body'].read()

            block = Block(data=file_blob, hash=file_hash)
            block_request = BlockRequest(block_hash=file_hash, public_key=public_key)
            encrypted_block = block_request.encrypt(block)

            response = make_response(encrypted_block.data)
            return response
