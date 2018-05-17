
"""
 Login process functions in Muzika-Backend

 Muzika backend server generates a random message and give it to user who wants to sign in. The user signs the message
 by the user's wallet and send it back to the server. It checks validation of the signing message and if validated give
 a JWT token to the user.
"""

import datetime
import hashlib
import json
import os

import arrow
import jwt
from sqlalchemy import text

with open(os.path.join(os.path.dirname(__file__), '../secret/jwt.json')) as jwt_file:
    jwt_json = json.loads(jwt_file.read())

JWT_SECRET_KEY = jwt_json['JWT_SECRET_KEY']


def generate_jwt_token(connection, web3, address, signature, sign_message_id):
    """
    Validate the user signature and if authenticated, generate a new JWT token for the user.

    :param connection: database connection.
    :param web3: web3(ethereum) instance.
    :param address: the wallet address of the user.
    :param signature: message signed by user's wallet.
    :param sign_message_id: sign message ID.
    :return: return JWT token if authenticated and generated, nor None if not authenticated.
    """
    from config import SignMessageConfig
    from modules.authentication import generate_random_sign_message
    from modules.signature import validate_signature

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

    sign_message_query_str = """
        SELECT `message` FROM `sign_messages`
        WHERE `message_id` = :sign_message_id AND NOW() - `created_at` <= :expired LIMIT 1
    """

    sign_update_query_str = """
        UPDATE `sign_messages`
        SET `user_id` = :user_id, `private_key` = :private_key
        WHERE `message_id` = :message_id
    """

    try:
        # get sign message and its private key
        # the private key is used for the hash value in JWT token
        sign_message_query = connection.execute(text(sign_message_query_str),
                                                sign_message_id=sign_message_id,
                                                expired=SignMessageConfig.expired_time).fetchone()
        sign_message = sign_message_query['message']
        private_key = generate_random_sign_message()

        # get user id by address
        user_id_query = connection.execute(text(user_id_query_str), address=address).fetchone()
        if user_id_query:
            user_id = user_id_query['user_id']
        else:
            # if user(wallet) is not registered, register it with empty name
            user_id = connection.execute(text(user_insert_query_str), address=address, name='').lastrowid
    except TypeError:
        # if sign message does not exist
        return None

    tz = arrow.now('Asia/Seoul').datetime

    # if validation failed, don't generate JWT token
    if not validate_signature(web3, address, sig_obj={'message': sign_message, 'signature': signature}):
        return None

    # after checking validation, authenticated, so update sign message
    connection.execute(text(sign_update_query_str),
                       user_id=user_id, private_key=private_key, message_id=sign_message_id)

    # JWT payload
    payload = {
        'hash': hashlib.md5("{}-{}-{}-{}".format(user_id, sign_message_id, address, private_key)
                            .encode('utf-8')).hexdigest(),
        'jti': '{}-{}'.format(address, sign_message_id),
        'iss': 'http://mapianist.com',
        'aud': 'http://mapianist.com',
        'iat': tz - datetime.timedelta(seconds=60),
        'exp': tz + datetime.timedelta(days=30)
    }

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
        decoded_token = jwt.decode(token, JWT_SECRET_KEY, verify=True, audience='http://mapianist.com')
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

        # calculate hash from database
        real_hash = hashlib.md5("{}-{}-{}-{}".format(user_id, sign_message_id, sign_user_address, private_key))

        # if decoded hash is not equal to calculated hash from database, it's invalid token
        if decoded_hash != real_hash:
            return helper.response_err(ER.INVALID_SIGNATURE, ER.INVALID_SIGNATURE_MSG)

        # authenticated and inject user information
        request.user = dict(sign_message_query)

        return func(*args, **kwargs)

    return decorated_func
