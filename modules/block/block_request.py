
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto import Random
from Crypto.PublicKey import RSA
from modules.block.block import AES_KEY_LENGTH, IV_SIZE


def generate_aes_key():
    """
    Generate 256-bit secret AES key. The key must be exposed to other.
    :return: 256-bit random AES key
    """
    return Random.get_random_bytes(int(AES_KEY_LENGTH / 8))


def generate_iv():
    """
    Generate initializer vector
    :return: randomly generated initializer vector
    """
    return Random.get_random_bytes(IV_SIZE)


class BlockRequest(object):
    def __init__(self, block_hash, public_key, **kwargs):
        passphrase = kwargs.get('passphrase')

        self.block_hash = block_hash
        if isinstance(public_key, bytes) or isinstance(public_key, str):
            self.public_key = RSA.import_key(extern_key=public_key, passphrase=passphrase)
        else:
            self.public_key = public_key

    def encrypt(self, block):
        encrypted_block = block.clone()

        if encrypted_block.encrypted_key:
            raise ValueError("already encrypted.")

        encrypted_block.pad()
        aes_key = generate_aes_key()
        iv = generate_iv()

        # encrypt data by generated AES key
        cipher = AES.new(aes_key, AES.MODE_CBC, iv)
        encrypted_block.data = cipher.encrypt(encrypted_block.data)
        encrypted_block.data = iv + encrypted_block.data

        # encrypt the key by RSA
        cipher = PKCS1_OAEP.new(self.public_key)
        encrypted_block.encrypted_key = cipher.encrypt(aes_key)

        return encrypted_block