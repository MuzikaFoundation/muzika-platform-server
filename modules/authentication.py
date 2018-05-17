
"""
 Muzika
"""

from sqlalchemy import text

__all__ = [
    'generate_random_sign_message',
]


SIGN_MESSAGE_LENGTH = 16
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


def register_sign_message_by_id(connection, user_id):
    insert_message_sql_str = """
        INSERT INTO `sign_messages`
        SET
          `user_id` = :user_id,
          `message` = :message
    """

    connection.execute(text(insert_message_sql_str), user_id=user_id, message=generate_random_sign_message())


def register_sign_message_by_address(connection, address):
    insert_message_sql_str = """
        INSERT INTO `sign_messages`
        SET 
          `user_id` = (SELECT `user_id` FROM `users` WHERE `address` = :address),
          `message` = :message
    """

    connection.execute(text(insert_message_sql_str), address=address, message=generate_random_sign_message())
