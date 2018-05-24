
"""
 Signature.py

 is a module for validating the json bodies of the requests. The requests for POST, PUT, or DELETE methods should be
 validated to check the requests are sent from the trusted users.

 All HTTP POST, PUT or DELETE requests for muzika backends should have signature objects for validation. Signature
 objects is a JSON object like below.

 {
   "message": original-message
   "messageHash": message hash
   "signature": signature
 }
"""

from eth_account.messages import defunct_hash_message
from hexbytes.main import HexBytes


__all__ = [
    'validate_signature'
]


def validate_signature(web3, address, sig_obj):
    """
    Validate the signature by signature object.

    It calculates the wallet address from the message hash and signature
    and check validation by comparing it with original address.
    """
    from modules.sign_message import construct_sign_message

    try:
        purpose = sig_obj.get('purpose')
        message = sig_obj.get('message')
        version = sig_obj.get('signature_version', 1)
        signature = HexBytes(sig_obj.get('signature'))

        muzika_message = construct_sign_message(purpose, message, version)
        message_hash = defunct_hash_message(web3.sha3(muzika_message))

        # recover address from hash and signature
        recover_address = web3.eth.account.recoverHash(message_hash, signature=signature)

        # if equal to address, it's valid signature.
        return recover_address.lower() == address.lower()
    except TypeError:
        # if unsupported signature version or invalid variable format, fail to validate
        return False
    except ValueError:
        return False

