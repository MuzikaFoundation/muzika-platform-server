
"""
 Muzika
"""

from sqlalchemy import text
from modules import database as db

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
    message = message or generate_random_sign_message()
    message_id = db.statement(db.table.SIGN_MESSAGES).set(user_id=user_id, message=message).insert(connection).lastrowid
    return message_id, message


def register_sign_message_by_address(connection, address, message=None):
    user_row = db.statement(db.table.SIGN_MESSAGES).columns('user_id').where(address=address).fetchone()
    if user_row is not None:
        return register_sign_message_by_id(connection, user_row['user_id'], message)
    else:
        return None, None


def get_message_for_user(address, cache=None):
    """
    Return a random sign message for the user.

    If it has in the database with not expired, return it and
    if not, it generates a new random sign message for the user.
    """
    from config import SignMessageConfig
    from modules.cache import MuzikaCache

    cache = cache or MuzikaCache()
    msg_url = '/db/sign-message/{}'.format(address)
    user_message_info = cache().get(msg_url)

    if user_message_info is None:
        # if message is not in cache, make a new message
        message = generate_random_sign_message()

        # generate message
        cache().set(msg_url, {
            'sign_message': message
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