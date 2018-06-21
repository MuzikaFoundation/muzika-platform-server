from flask import Blueprint, request
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from modules import database as db
from modules.ethereum_address import check_address_format
from modules.login import jwt_check, PLATFORM_TYPES
from modules.response.error import ERR
from modules.response import helper
from modules.secret import load_secret_json
from modules.sign_message import get_message_for_user
from modules.web3 import get_web3

blueprint = Blueprint('user', __name__, url_prefix='/api')


s3_policy = load_secret_json('aws')['s3']


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

    s3_base_url = 'https://s3.{region}.amazonaws.com'.format(region=s3_policy['profile']['region'])

    user_query_stmt = """
        SELECT `u`.*, CONCAT(:s3_base_url, '/', `f`.`bucket`, '/', `f`.`object_key`) AS `profile_image` FROM `{}` `u`
        LEFT JOIN `{}` `f`
          ON (`f`.`file_id` = `u`.`profile_file_id` AND `f`.`type` = :file_type)
        WHERE `u`.`address` = :address
        LIMIT 1
    """.format(db.table.USERS, db.table.FILES)

    # if invalid address format, don't generate message
    if not check_address_format(address):
        return helper.response_err(ERR.INVALID_REQUEST_BODY)

    web3 = get_web3()
    web3.toChecksumAddress(address)

    with db.engine_rdonly.connect() as connection:
        user = connection.execute(
            text(user_query_stmt),
            s3_base_url=s3_base_url,
            address=address,
            file_type='profile'
        ).fetchone()

        if user is None:
            return helper.response_err(ERR.NOT_EXIST)

        return helper.response_ok(db.to_relation_model(user))


@blueprint.route('/user/<address>/sign-message', methods=['GET'])
def _get_user_sign_message(address):
    """
    Returns an user information by wallet address.

    If user(address) does not exist, give a random message for signing
    """

    # if invalid address format, don't generate message
    if not check_address_format(address):
        return helper.response_err(ERR.INVALID_REQUEST_BODY)

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
        return helper.response_err(ERR.INVALID_REQUEST_BODY)

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
            return helper.response_err(ERR.AUTHENTICATION_FAILED)


def _change_user_info(column_name, max_len, min_len=0):
    json_form = request.get_json(force=True, silent=True)
    user_id = request.user['user_id']
    value = json_form.get(column_name)

    if len(value) > max_len or len(value) < min_len:
        return helper.response_err(ERR.TOO_LONG_PARAMETER)

    with db.engine_rdwr.connect() as connection:
        try:
            db.statement(db.table.USERS).set(**{column_name:value}).where(user_id=user_id).update(connection)
        except IntegrityError:
            return helper.response_err(ERR.ALREADY_EXIST)
        return helper.response_ok({'status': 'success'})


@blueprint.route('/user', methods=['PUT'])
@jwt_check
def _put_user_info():
    """
    Modify user's info. Never change user_id, address.
    """
    json_form = request.get_json(force=True, silent=True)
    user_id = request.user['user_id']
    profile_file_id = json_form.get('profile_file_id')

    # only these columns can be changed
    changable_columns = ['name', 'youtube_url', 'facebook_url', 'soundcloud_url', 'spotify_url']
    change_value = {}

    if isinstance(profile_file_id, int):
        change_value.update({'profile_file_id': profile_file_id})

    for column in changable_columns:
        if column in json_form:
            change_value.update({column: json_form.get(column)})

        if column == 'name' and len(change_value['name']) < 1:
            return helper.response_err(ERR.TOO_SHORT_PARAMETER)

    with db.engine_rdwr.connect() as connection:
        try:
            db.statement(db.table.USERS).set(**change_value).where(user_id=user_id).update(connection)
        except IntegrityError:
            return helper.response_err(ERR.ALREADY_EXIST)
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


@blueprint.route('/user/profile', methods=['PUT'])
@jwt_check
def _change_user_profile():
    json_form = request.get_json(force=True, silent=True)
    user_id = request.user['user_id']
    profile_file_id = request.user.get('profile_file_id')

    if not isinstance(profile_file_id, int):
        return helper.response_err(ERR.INVALID_REQUEST_BODY)

    with db.engine_rdwr.connect() as connection:
        db.statement(db.table.USERS).set(profile_file_id=profile_file_id).where(user_id=user_id).update(connection)

    return helper.response_ok({'status': 'success'})