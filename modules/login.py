
"""
 Login process functions in Muzika-Backend

 Muzika backend server generates a random message and give it to user who wants to sign in. The user signs the message
 by the user's wallet and send it back to the server. It checks validation of the signing message and if validated give
 a JWT token to the user.
"""

import hashlib

import jwt
from sqlalchemy import text

from config import WebServerConfig
from modules.secret import load_secret_json

jwt_json = load_secret_json('jwt')

JWT_SECRET_KEY = jwt_json['jwt_secret_key']


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
    from config import WebServerConfig
    from modules.sign_message import (
        generate_random_sign_message, register_sign_message_by_id, validate_message, expire_sign_message
    )
    from modules.signature import validate_signature
    from modules.cache import MuzikaCache

    # if first sign in, get message not by sign message id since db doesn't have it
    signature_version = kwargs.get('signature_version')
    sign_message = kwargs.get('sign_message')
    default_user_name = kwargs.get('default_user_name', None)

    # allocate later if cache is used
    cache = None

    user_id_query_str = """
        SELECT * FROM `users`
        WHERE `address` = :address
    """

    user_insert_query_str = """
        INSERT INTO `users`
        SET
          `address` = :address,
          `name` = :user_name
    """

    sign_update_query_str = """
        UPDATE `sign_messages`
        SET `user_id` = :user_id, `private_key` = :private_key
        WHERE `message_id` = :message_id
    """

    try:
        """
        Get sign message and its private key. The private key is used for the hash value in JWT token.
        
        If the user is registered in database, get random-generated sign message from database (get by message_id),
        and if unregistered, get any message.
        """

        # get user id by address
        user_id_query = connection.execute(text(user_id_query_str), address=address).fetchone()
        if user_id_query:
            user_id = user_id_query['user_id']
        else:
            user_id = None

        # if registered user, get sign message from cache. (ignore unregistered sign message)
        if user_id:
            from modules.sign_message import get_message_for_user
            cache = MuzikaCache()
            sign_message = get_message_for_user(user_id, cache=cache)
        else:
            # if invalid message format
            if not validate_message(sign_message):
                return None
        private_key = generate_random_sign_message()

    except TypeError:
        # if sign message does not exist
        return None

    tz = arrow.now(WebServerConfig.timezone).datetime

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

    # if user(wallet) is not registered yet, register it with empty name
    if not user_id:
        if default_user_name is not None:
            user_id = connection.execute(text(user_insert_query_str), address=address, user_name=default_user_name).lastrowid
        else:
            return None

    # create a new sign message
    sign_message_id, _ = register_sign_message_by_id(connection, user_id, sign_message)

    # after checking validation, authenticated, so update sign message
    connection.execute(text(sign_update_query_str),
                       user_id=user_id, private_key=private_key, message_id=sign_message_id)

    # JWT payload
    payload = {
        'hash': hashlib.md5("{}-{}-{}-{}".format(user_id, sign_message_id, address, private_key)
                            .encode('utf-8')).hexdigest(),
        'jti': '{}-{}'.format(address, sign_message_id),
        'iss': WebServerConfig.issuer,
        'aud': WebServerConfig.issuer,
        'iat': tz - datetime.timedelta(seconds=60),
        'exp': tz + datetime.timedelta(days=30)
    }

    if not cache:
        cache = MuzikaCache()

    # if validated, expire the message, so never use the sign message anymore.
    expire_sign_message(user_id, cache)

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
        from modules.response import error_constants as ER

        # get JWT token from request header "Authorization"
        token = request.headers.get('Authorization', None)
        token = token.split(' ')[-1] if token is not None else None

        # decode token
        try:
            decoded_token = jwt.decode(token, JWT_SECRET_KEY, verify=True, audience=WebServerConfig.issuer)
        except jwt.exceptions.InvalidSignatureError:
            return helper.response_err(ER.INVALID_SIGNATURE, ER.INVALID_SIGNATURE_MSG)
        address, sign_message_id = decoded_token['jti'].split('-')

        # get sign message for calculating hash
        request.connection = db.engine_rdonly.connect()
        sign_message_query_str = """
            SELECT * FROM `sign_messages` `sm`
            INNER JOIN `users` `u`
            ON (`u`.`user_id` = `sm`.`user_id`)
            WHERE `message_id` = :sign_message_id
        """
        sign_message_query = request.connection.execute(text(sign_message_query_str),
                                                        sign_message_id=sign_message_id).fetchone()
        user_id = sign_message_query['user_id']
        private_key = sign_message_query['private_key']
        sign_user_address = sign_message_query['address']

        # get hash from decoded JWT
        decoded_hash = decoded_token['hash']

        # calculate hash from db
        real_hash = hashlib.md5("{}-{}-{}-{}".format(user_id, sign_message_id, sign_user_address, private_key)
                                .encode('utf-8')).hexdigest()

        # if decoded hash is not equal to calculated hash from db, it's invalid token
        if decoded_hash != real_hash:
            return helper.response_err(ER.INVALID_SIGNATURE, ER.INVALID_SIGNATURE_MSG)

        # authenticated and inject user information
        request.user = dict(sign_message_query)

        return func(*args, **kwargs)

    return decorated_func
