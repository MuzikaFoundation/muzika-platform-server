from flask import Blueprint, request
from sqlalchemy import text

from modules import database as db
from modules.login import jwt_check
from modules.response import error_constants as ER
from modules.response import helper
from modules.web3 import get_web3
from modules.sign_message import generate_random_sign_message, get_message_for_user
from modules.ethereum_address import check_address_format

blueprint = Blueprint('user', __name__, url_prefix='/api')


@blueprint.route('/me', methods=['GET'])
@jwt_check
def _get_me():
    return helper.response_ok(request.user)


@blueprint.route('/user/<address>', methods=['GET'])
def _get_user(address):
    """
    Returns an user information by wallet address.

    If user(address) does not exist, give a random message for signing
    """

    # if invalid address format, don't generate message
    if not check_address_format(address):
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    with db.engine_rdonly.connect() as connection:
        user = db.statement(db.table.USERS).where(address=address).select(connection).fetchone()
        return helper.response_ok(db.to_relation_model(user))


@blueprint.route('/user/<address>/sign-message', methods=['GET'])
def _get_user_sign_message(address):
    """
    Returns an user information by wallet address.

    If user(address) does not exist, give a random message for signing
    """

    # if invalid address format, don't generate message
    if not check_address_format(address):
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    return helper.response_ok(get_message_for_user(address))


@blueprint.route('/user', methods=['PUT'])
@jwt_check
def _modify_user():
    """
    Modify user's information.
    """
    json_form = request.get_json(force=True, silent=True)
    user_name = json_form.get('name')
    address = request.user['address']

    if not isinstance(user_name, str):
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    with db.engine_rdwr.connect() as connection:
        result = db.statement(db.table.USERS)\
            .where(address=address)\
            .set(name=user_name)\
            .update(connection)

        if result.row_count:
            return helper.response_ok({'status': 'success'})
        else:
            return helper.response_err(ER.ALREADY_EXIST, ER.ALREADY_EXIST_MSG)


@blueprint.route('/register', methods=['POST'])
@blueprint.route('/login', methods=['POST'])
def _login():
    from modules.login import generate_jwt_token

    json_form = request.get_json(force=True, silent=True)
    address = json_form.get('address')
    signature = json_form.get('signature')
    sign_message_id = json_form.get('message_id')
    sign_message = json_form.get('message')     # only for unregistered user
    signature_version = json_form.get('signature_version')

    user_name = json_form.get('user_name')

    web3 = get_web3()

    with db.engine_rdwr.connect() as connection:
        jwt_token = generate_jwt_token(
            connection,
            web3, address, signature,
            signature_version=signature_version,
            sign_message=sign_message,   # only for unregistered user
            default_user_name=user_name
        )

        if jwt_token:
            return helper.response_ok(jwt_token)
        else:
            return helper.response_err(ER.AUTHENTICATION_FAILED, ER.AUTHENTICATION_FAILED_MSG)


