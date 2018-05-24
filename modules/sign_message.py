
"""
 Muzika
"""

from sqlalchemy import text

__all__ = [
    'generate_random_sign_message',
    'construct_sign_message',
]


SIGN_MESSAGE_LENGTH = 20
SIGN_MESSAGE_CHAR = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'
SIGN_MESSAGE_CHAR_LENGTH = len(SIGN_MESSAGE_CHAR)


def generate_random_sign_message():
    """
    Generate a random message for authentication.
    """
    from random import randrange
    sign_message = ''
    for i in range(SIGN_MESSAGE_LENGTH):
        # generate a random character and append to sign message
        ch = SIGN_MESSAGE_CHAR[randrange(0, SIGN_MESSAGE_CHAR_LENGTH)]
        sign_message += ch

    return sign_message


def validate_message(message):
    """
    Validate the message format.
    """
    # if the message length is invalid
    if len(message) != SIGN_MESSAGE_LENGTH:
        return False

    for ch in message:
        if ch not in SIGN_MESSAGE_CHAR:
            return False

    return True


def register_sign_message_by_id(connection, user_id, message=None):
    insert_message_sql_str = """
        INSERT INTO `sign_messages`
        SET
          `user_id` = :user_id,
          `message` = :message
    """
    message = message or generate_random_sign_message()
    message_id = connection.execute(text(insert_message_sql_str), user_id=user_id, message=message).lastrowid
    return message_id, message


def register_sign_message_by_address(connection, address, message=None):
    insert_message_sql_str = """
        INSERT INTO `sign_messages`
        SET 
          `user_id` = (SELECT `user_id` FROM `users` WHERE `address` = :address),
          `message` = :message
    """
    message = message or generate_random_sign_message()
    message_id = connection.execute(text(insert_message_sql_str), address=address, message=message).lastrowid
    return message_id, message


def get_message_for_user(user_id, cache=None):
    """
    Return a random sign message for the user.

    If it has in the database with not expired, return it and
    if not, it generates a new random sign message for the user.
    """
    import datetime
    import arrow
    from config import WebServerConfig, SignMessageConfig
    from modules.cache import MuzikaCache

    cache = cache or MuzikaCache()
    msg_url = '/db/sign-message/{}'.format(user_id)
    user_message_info = cache().get(msg_url)
    current_time = arrow.now(WebServerConfig.timezone).datetime

    # if expired message, ignore the message
    if user_message_info and user_message_info['expired_at'] < current_time:
        user_message_info = None

    if user_message_info is None:
        # if message is not in cache, make a new message
        timeout = SignMessageConfig.unsigned_message_expired_time
        expired_time = current_time + datetime.timedelta(seconds=timeout)
        message = generate_random_sign_message()

        # generate message
        cache().set(msg_url, {
            'sign_message': message,
            'expired_at': expired_time
        }, timeout=SignMessageConfig.unsigned_message_expired_time)

        # return generated message
        return message

    else:
        # if not expired message exists, return it
        return user_message_info['sign_message']


def expire_sign_message(user_id, cache=None):
    from modules.cache import MuzikaCache

    cache = cache or MuzikaCache()
    msg_url = '/db/sign-message/{}'.format(user_id)
    cache().delete(msg_url)


def construct_sign_message(purpose, message, version=1):
    signed_message_header = b'Ethereum Signed Message:\n'
    mz_message = '{}\nSignature : {}'.format(purpose, message).encode('ascii')
    msg_len = len(mz_message)

    if version == 1:
        # Metamask format
        mz_len_bytes = '{}'.format(msg_len).encode('ascii')
    elif version == 2:
        # Trezor format
        if msg_len < 253:
            mz_len_bytes = bytes([msg_len & 0xFF])
        elif msg_len < 65536:
            mz_len_bytes = bytes([
                253,
                msg_len & 0xFF,
                (msg_len >> 8) & 0xFF,
            ])
        else:
            mz_len_bytes = bytes([
                254,
                msg_len & 0xFF,
                (msg_len >> 8) & 0xFF,
                (msg_len >> 16) & 0xFF,
                (msg_len >> 24) & 0xFF,
            ])
    else:
        # unsupported signature version
        return None

    entire_message = b''.join([
        bytes([len(signed_message_header)]),  # length of signed message
        signed_message_header,
        mz_len_bytes,
        mz_message,
    ])

    return entire_message