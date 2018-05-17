from flask import Blueprint, request
from sqlalchemy import text

from modules import database as db
from modules.response import error_constants as ER
from modules.response import helper
from modules.signature import validate_signature
from modules.web3 import get_web3

blueprint = Blueprint('user', __name__, url_prefix='/api')


@blueprint.route('/user', methods=['POST'])
def _register_user():
    """
    Sign up by wallet address.

    It registers a wallet address to the muzika backend database. It does not save wallet address private key.

    json form:
    {
        "signature": signature object,
        "address": wallet address,
        "nickname": nickname of the wallet address
    }
    """
    json_form = request.get_json(force=True, silent=True)
    signature = json_form.get('signature')
    wallet_address = json_form.get('address')
    nickname = json_form.get('nickname')

    # check signature validation
    web3 = get_web3()
    if not validate_signature(web3, wallet_address, signature):
        return helper.response_err(ER.INVALID_SIGNATURE, ER.INVALID_SIGNATURE_MSG)

    # TODO : save wallet address to the database
    raise NotImplementedError


@blueprint.route('/user/<address>', methods=['GET'])
def _get_user(address):
    """
    Returns an user information by wallet address
    """

    with db.engine_rdonly.connect() as connection:
        query = "SELECT * FROM `users` WHERE `address` = :address"
        user = connection.execute(text(query), address=address).fetchone()
        return helper.response_ok(dict(user))


@blueprint.route('/login', methods=['POST'])
def _login():
    from modules.login import generate_jwt_token

    json_form = request.get_json(force=True, silent=True)
    address = json_form('address')
    signature = json_form('signature')
    sign_message_id = json_form('message_id')

    web3 = get_web3()

    with db.engine_rdwr.connect() as connection:
        jwt_token = generate_jwt_token(connection, web3, address, signature, sign_message_id)

        if jwt_token:
            return helper.response_ok({
                'address': address,
                'token': jwt_token
            })
        else:
            return helper.response_err(ER.AUTHENTICATION_FAILED, ER.AUTHENTICATION_FAILED_MSG)


