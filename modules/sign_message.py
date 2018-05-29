"""
 Muzika
"""
from cytoolz import (
    compose,
)
from eth_account.internal.signing import (
    signature_wrapper,
)
from eth_utils import (
    keccak,
    to_bytes,
)
from hexbytes import (
    HexBytes,
)

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


def register_sign_message_by_id(connection, user_id, platform_type, message=None):
    message = message or generate_random_sign_message()
    message_id = db.statement(db.table.SIGN_MESSAGES).set(user_id=user_id,
                                                          platform_type=platform_type,
                                                          message=message).insert(connection).lastrowid
    return message_id, message


def get_message_for_user(address, cache=None, always_new=False):
    """
    Return a random sign message for the user.

    If it has in the database with not expired, return it and
    if not, it generates a new random sign message for the user.
    """
    from config import SignMessageConfig
    from modules.cache import MuzikaCache

    cache = cache or MuzikaCache()
    address = address.lower()
    msg_url = '/db/sign-message/{}'.format(address)
    user_message_info = cache().get(msg_url)

    if user_message_info is None or always_new is True:
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


def expire_sign_message(address, cache=None):
    from modules.cache import MuzikaCache

    cache = cache or MuzikaCache()
    msg_url = '/db/sign-message/{}'.format(address)
    cache().delete(msg_url)


# Trezor format
def trezor_signature_wrapper(message, version=b'E'):
    preamble = b'\x19Ethereum Signed Message:\n'
    msg_len = len(message)

    if msg_len < 253:
        size = bytes([msg_len & 0xFF])
    elif msg_len < 65536:
        size = bytes([
            253,
            msg_len & 0xFF,
            (msg_len >> 8) & 0xFF,
        ])
    else:
        size = bytes([
            254,
            msg_len & 0xFF,
            (msg_len >> 8) & 0xFF,
            (msg_len >> 16) & 0xFF,
            (msg_len >> 24) & 0xFF,
        ])

    return preamble + size + message


# Custom Implementation of eth_account.messages.defunct_hash_message
# Support Trezor sign-message wrapper
def construct_sign_message(purpose, message, version=1):
    mz_message = '{}\nSignature: {}'.format(purpose, message)
    message_bytes = to_bytes(text=mz_message)
    recovery_hasher = compose(HexBytes, keccak, trezor_signature_wrapper if version == 2 else signature_wrapper)
    return recovery_hasher(message_bytes)
