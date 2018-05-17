from flask import Blueprint, request
from sqlalchemy import text

from modules import database as db
from modules.login import jwt_check
from modules.response import error_constants as ER
from modules.response import helper
from modules.signature import validate_signature
from modules.web3 import get_web3

blueprint = Blueprint('user', __name__, url_prefix='/api')


@blueprint.route('/user/<address>', methods=['GET'])
def _get_user(address):
    """
    Returns an user information by wallet address
    """
    with db.engine_rdonly.connect() as connection:
        query = "SELECT * FROM `users` WHERE `address` = :address"
        user = connection.execute(text(query), address=address).fetchone()
        return helper.response_ok(dict(user))


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

    user_update_query_str = """
        UPDATE `users`
        SET
          `name` = :user_name
        WHERE `address` = :address
    """

    with db.engine_rdwr.connect() as connection:
        if connection.execute(text(user_update_query_str), user_name=user_name, address=address).row_count:
            return helper.response_ok({'status': 'success'})
        else:
            return helper.response_err(ER.ALREADY_EXIST, ER.ALREADY_EXIST_MSG)


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


