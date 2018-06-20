from flask import Blueprint, request
from sqlalchemy.exc import IntegrityError

from modules import database as db
from modules.ethereum_address import check_address_format
from modules.login import jwt_check, PLATFORM_TYPES
from modules.response import error_constants as ER
from modules.response import helper
from modules.sign_message import get_message_for_user
from modules.web3 import get_web3

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

    web3 = get_web3()
    web3.toChecksumAddress(address)

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

    return helper.response_ok(get_message_for_user(address, always_new=True))


@blueprint.route('/register', methods=['POST'])
@blueprint.route('/login', methods=['POST'])
def _login():
    from modules.login import generate_jwt_token

    json_form = request.get_json(force=True, silent=True)
    address = json_form.get('address')
    signature = json_form.get('signature')
    signature_version = json_form.get('signature_version', 1)
    user_name = json_form.get('user_name', '')

    platform_type = json_form.get('platform_type')
    if platform_type not in PLATFORM_TYPES:
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    web3 = get_web3()

    with db.engine_rdwr.connect() as connection:
        jwt_token = generate_jwt_token(
            connection,
            web3, address, signature,
            platform_type=platform_type,
            signature_version=signature_version,
            default_user_name=user_name
        )

        if jwt_token:
            return helper.response_ok(jwt_token)
        else:
            return helper.response_err(ER.AUTHENTICATION_FAILED, ER.AUTHENTICATION_FAILED_MSG)


def _change_user_info(column_name, max_len, min_len=0):
    json_form = request.get_json(force=True, silent=True)
    user_id = request.user['user_id']
    value = json_form.get(column_name)

    if len(value) > max_len or len(value) < min_len:
        return helper.response_err(ER.TOO_LONG_PARAMETER, ER.TOO_LONG_PARAMETER_MSG)

    with db.engine_rdwr.connect() as connection:
        try:
            db.statement(db.table.USERS).set(**{column_name:value}).where(user_id=user_id).update(connection)
        except IntegrityError:
            return helper.response_err(ER.ALREADY_EXIST, ER.ALREADY_EXIST_MSG)
        return helper.response_ok({'status': 'success'})


@blueprint.route('/user', methods=['PUT'])
@jwt_check
def _put_user_info():
    """
    Modify user's info. Never change user_id, address.
    """
    json_form = request.get_json(force=True, silent=True)
    user_id = request.user['user_id']

    # only these columns can be changed
    changable_columns = ['name', 'youtube_url', 'facebook_url', 'soundcloud_url', 'spotify_url']
    change_value = {}

    for column in changable_columns:
        if column in json_form:
            change_value.update({column: json_form.get(column)})

        if column == 'name' and len(change_value['name']) < 1:
            return helper.response_err(ER.TOO_SHORT_PARAMETER, ER.TOO_SHORT_PARAMETER_MSG)

    with db.engine_rdwr.connect() as connection:
        try:
            db.statement(db.table.USERS).set(**change_value).where(user_id=user_id).update(connection)
        except IntegrityError:
            return helper.response_err(ER.ALREADY_EXIST, ER.ALREADY_EXIST_MSG)
        return helper.response_ok({'status': 'success'})


@blueprint.route('/user/name', methods=['PUT'])
@jwt_check
def _change_user_name():
    return _change_user_info('name', 50, 1)


@blueprint.route('/user/youtube', methods=['PUT'])
@jwt_check
def _change_user_youtube_url():
    return _change_user_info('youtube_url', 255)


@blueprint.route('/user/facebook', methods=['PUT'])
@jwt_check
def _change_user_facebook_url():
    return _change_user_info('facebook_url', 255)


@blueprint.route('/user/soundcloud', methods=['PUT'])
@jwt_check
def _change_user_soundcloud_url():
    return _change_user_info('soundcloud_url', 255)


@blueprint.route('/user/spotify', methods=['PUT'])
@jwt_check
def _change_user_spotify_url():
    return _change_user_info('spotify_url', 255)