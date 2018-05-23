
from Crypto.Cipher import PKCS1_OAEP, AES
from Crypto.PublicKey import RSA

from modules.block.block import AES_KEY_LENGTH, IV_SIZE
from modules.block.block_request import BlockRequest

RSA_KEY_LENGTH = 2048


class BlockKey(object):
    def __init__(self, block_hash=None):
        self.private_key = RSA.generate(RSA_KEY_LENGTH)
        self.block_hash = block_hash

    def generate_request(self):
        return BlockRequest(block_hash=self.block_hash, public_key=self.private_key.publickey())

    def decrypt(self, block):
        decrypted_block = block.clone()

        # if the block is not encrypted, no need to decrypt. Raise error
        if decrypted_block.encrypted_key is None:
            raise ValueError("Not encrypted block.")

        # if this block key is not for the parameter block (different hash value), return with nothing
        if self.block_hash != decrypted_block.block_hash:
            return None

        # decrypt encrypted key by RSA private key
        cipher = PKCS1_OAEP.new(self.private_key)
        try:
            aes_key = cipher.decrypt(decrypted_block.encrypted_key)
        except ValueError as e:
            # if failed to decrypt
            return None

        # if the length of AES key is invalid
        if len(aes_key) != int(AES_KEY_LENGTH / 8):
            return None

        iv = decrypted_block.data[:IV_SIZE]
        cipher = AES.new(aes_key, AES.MODE_CBC, iv)
        try:
            plain_data = cipher.decrypt(decrypted_block.data[IV_SIZE:])
        except ValueError as e:
            # if failed to decrypt
            print(e)
            return None

        decrypted_block.data = plain_data
        decrypted_block.unpad()
        decrypted_block.update_file_hash()

        # if the hash of the decrypted block is invalid
        if decrypted_block.block_hash != self.block_hash:
            return None

        # success to decrypt
        return decrypted_block
