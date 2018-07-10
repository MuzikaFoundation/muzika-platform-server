"""
 Login process functions in Muzika-Backend

 Muzika backend server generates a random message and give it to user who wants to sign in. The user signs the message
 by the user's wallet and send it back to the server. It checks validation of the signing message and if validated give
 a JWT token to the user.
"""

import hashlib

import jwt
from sqlalchemy import text

from config import AppConfig
from modules import database as db
from modules.secret import load_secret_json

jwt_json = load_secret_json('jwt')
s3_policy = load_secret_json('aws')['s3']

JWT_SECRET_KEY = jwt_json['jwt_secret_key']


PLATFORM_TYPES = ['electron', 'app', 'web']


def generate_jwt_token(connection, web3, address, signature, **kwargs):
    """
    Validate the user signature and if authenticated, generate a new JWT token for the user.

    :param connection: database connection.
    :param web3: web3(ethereum) instance.
    :param address: the wallet address of the user.
    :param signature_version: signature creation type (Trezur, Metamask signature creation type)
    :param signature: message signed by user's wallet.
    :param default_user_name: if not-None-type-value and user_id not exists at the address, this function creates user
    :return: return JWT token if authenticated and generated, nor None if not authenticated.
    """
    import arrow
    import datetime
    from config import AppConfig
    from modules.sign_message import (
        generate_random_sign_message, register_sign_message_by_id, expire_sign_message
    )
    from modules.signature import validate_signature
    from modules.sign_message import get_message_for_user

    # if first sign in, get message not by sign message id since db doesn't have it
    signature_version = kwargs.get('signature_version')
    default_user_name = kwargs.get('default_user_name', None)
    platform_type = kwargs.get('platform_type')
    checksum_address = web3.toChecksumAddress(address)

    if platform_type not in PLATFORM_TYPES:
        return None

    """
    Get sign message and its private key. The private key is used for the hash value in JWT token.
    
    get random-generated sign message from database (get by message_id),
    """

    sign_message = get_message_for_user(address, always_new=False)

    tz = arrow.now(AppConfig.timezone).datetime

    """
    Validate the signature. If fail to validate, never generate JWT token.
    
    If succeed to validate,
    
      1. Create an user if the address is not registered in database
      2. Generate a new JWT token 
    """
    # if validation failed, don't generate JWT token
    if not validate_signature(web3, address, sig_obj={'purpose': 'Login to Muzika!',
                                                      'message': sign_message,
                                                      'signature': signature,
                                                      'signature_version': signature_version}):
        return None

    # get user id by address
    user_id = db.statement(db.table.USERS).where(address=checksum_address).select(connection).fetchone()
    user_id = user_id['user_id'] if user_id is not None else None

    # if user(wallet) is not registered yet, register it with empty name
    if not user_id:
        if default_user_name is not None:
            user_id = db.statement(db.table.USERS).set(address=checksum_address,
                                                       name=default_user_name).insert(connection).lastrowid
        else:
            return None

    # create a new sign message
    sign_message_id, _ = register_sign_message_by_id(connection, user_id, platform_type, sign_message)

    private_key = generate_random_sign_message()

    # after checking validation, authenticated, so update sign message
    db.statement(db.table.SIGN_MESSAGES) \
        .set(private_key=private_key) \
        .where(message_id=sign_message_id, user_id=user_id).update(connection)

    # JWT payload
    payload = {
        'hash': hashlib.md5("{}-{}-{}-{}".format(user_id, sign_message_id, checksum_address, private_key)
                            .encode('utf-8')).hexdigest(),
        'jti': '{}-{}'.format(address, sign_message_id),
        'iss': AppConfig.issuer,
        'aud': AppConfig.issuer,
        'iat': tz - datetime.timedelta(seconds=60),
        'exp': tz + datetime.timedelta(days=30)
    }

    # if validated, expire the message, so never use the sign message anymore.
    expire_sign_message(address)

    # return JWT token
    return jwt.encode(payload=payload, key=JWT_SECRET_KEY, algorithm='HS256',
                      headers={'jti': payload['jti']}).decode('utf-8')


def jwt_check(func):
    """
    Validate user login before API called.

    Usage:
    >>> @blueprint.route('..', methods=[..])
    >>> @jwt_check
    >>> def _function(..):
    >>> ....

    Decorate API function only when the API needs authentication.

    If success to authenticate, it injects user information to the request instance.

    >>> request.user
    {
      "user_id": ...,
      "address": ...,
      "name": ...,
      ...
    }
    """
    from functools import wraps

    @wraps(func)
    def decorated_func(*args, **kwargs):
        from modules import database as db
        from flask import request

        from modules.response import helper
        from modules.response.error import ERR

        # get JWT token from request header "Authorization"
        token = request.headers.get('Authorization', None)
        token = token.split(' ')[-1] if token is not None else None

        # decode token
        try:
            decoded_token = jwt.decode(token, JWT_SECRET_KEY, verify=True, audience=AppConfig.issuer)
        except jwt.exceptions.InvalidTokenError:
            return helper.response_err(ERR.COMMON.INVALID_SIGNATURE)
        address, sign_message_id = decoded_token['jti'].split('-')

        # get sign message for calculating hash
        request.connection = db.engine_rdonly.connect()
        s3_base_url = 'https://s3.{region}.amazonaws.com'.format(region=s3_policy['profile']['region'])
        sign_message_query_str = """
            SELECT 
              `u`.*, 
              CONCAT(:s3_base_url, '/', `f`.`bucket`, '/', `f`.`object_key`) AS `profile_image`, 
              '!sign_message', 
              `sm`.* 
            FROM 
              `users` `u`
            LEFT JOIN `files` `f`
              ON (`f`.`file_id` = `u`.`profile_file_id` AND `f`.`type` = :file_type)
            INNER JOIN `sign_messages` `sm` ON (`u`.`user_id` = `sm`.`user_id`)
            WHERE `message_id` = :sign_message_id AND `address` = :address
            LIMIT 1
        """
        user_row = request.connection.execute(text(sign_message_query_str),
                                              file_type='profile',
                                              address=address,
                                              s3_base_url=s3_base_url,
                                              sign_message_id=sign_message_id).fetchone()
        if user_row is not None:
            user_row = db.to_relation_model(user_row)
            user_id = user_row['user_id']
            sign_message = user_row['sign_message']

            del user_row['sign_message']

            # get hash from decoded JWT
            decoded_hash = decoded_token['hash']

            # calculate hash from db
            real_hash = hashlib.md5("{}-{}-{}-{}".format(user_id,
                                                         sign_message_id,
                                                         user_row['address'],
                                                         sign_message['private_key'])
                                    .encode('utf-8')).hexdigest()

            # if decoded hash is not equal to calculated hash from db, it's invalid token
            if decoded_hash != real_hash:
                return helper.response_err(ERR.COMMON.INVALID_SIGNATURE)

            # authenticated and inject user information
            request.user = user_row

        return func(*args, **kwargs)

    return decorated_func
