
"""
 Block is data format for sending and receiving between the muzika nodes.
"""

from Crypto import Random
from Crypto.Hash import keccak

# AES key length (bit)
AES_KEY_LENGTH = 256

# initializer vector size for CBC(Cipher Block Chain) mode
IV_SIZE = 16

# total garbage padding size must be a multiple of IV_SIZE since the total data size must be the multiple of IV_SIZE.
TOTAL_GARBAGE_PADDING_SIZE = 256


class Block(object):
    front_garbage_size = False
    encrypted_key = None

    def __init__(self, data, padded=False, hash=None, front_garbage_size=None, encrypted_key=None):
        if isinstance(data, list) or isinstance(data, bytes):
            data = bytearray(data)
        if not isinstance(data, bytearray):
            raise TypeError("data must be bytearray type")
        self.data = data
        self.padded = padded
        if hash:
            self.block_hash = hash
        else:
            self.update_file_hash()
        self.front_garbage_size = front_garbage_size
        self.encrypted_key = encrypted_key

    def pad(self):
        """
        Pad the data with the multiple of IV length.

        Since the data size must be the multiple of IV length in CBC (Cipher Block Chain) mode, pad the data if not.
        After padding the data, add garbage padding front and end of the data to protect from known plaintext attack.
        """
        if self.padded:
            return

        # calculate padding size and padding byte value
        original_data_size = len(self.data)
        size_with_padding = int(original_data_size / IV_SIZE) * IV_SIZE + IV_SIZE
        added_size = size_with_padding - original_data_size

        # concatenate padding
        self.data += bytearray([added_size] * added_size)

        # garbage padding
        self.front_garbage_size = Random.get_random_bytes(1)[0]
        self.data = bytearray([self.front_garbage_size]) + \
                    bytearray(Random.get_random_bytes(self.front_garbage_size)) + \
                    self.data + \
                    bytearray(Random.get_random_bytes(TOTAL_GARBAGE_PADDING_SIZE - self.front_garbage_size - 1))

        # set padded to true
        self.padded = True

    def unpad(self):
        """
        remove padding, so make pure data.
        """
        if not self.padded:
            return

        # remove garbage padding
        self.front_garbage_size = self.data[0]
        back_garbage_padding_size = TOTAL_GARBAGE_PADDING_SIZE - 1 - self.front_garbage_size
        if back_garbage_padding_size:
            self.data = self.data[1 + self.front_garbage_size:-back_garbage_padding_size]
        else:
            self.data = self.data[1 + self.front_garbage_size:]

        # get padding value
        padding_value = self.data[-1]

        # remove padding
        self.data = self.data[:-padding_value]
        self.padded = False

    def update_file_hash(self):
        """
        Calculate keccak-256 hash of data. If the data padded, it cannot calculate it.
        """
        if self.padded:
            raise ValueError("The data must not be padded for getting hash.")

        keccak_hash = keccak.new(digest_bits=256)
        keccak_hash.update(self.data)
        self.block_hash = keccak_hash.hexdigest()

    def clone(self):
        block = Block(
            data=bytearray(),
            padded=self.padded,
            hash=self.block_hash,
            front_garbage_size=self.front_garbage_size,
            encrypted_key=self.encrypted_key
        )
        block.data[:] = self.data
        return block
