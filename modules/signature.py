
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

    The signature objects have either "message" or "messageHash" and "signature". It calculates the wallet address from
    the message hash and signature and check validation by comparing it with original address.
    """
    try:
        purpose = sig_obj.get('purpose')
        message = sig_obj.get('message')
        message_hash = HexBytes(sig_obj.get('messageHash')) or \
                       defunct_hash_message(text='{}\nsignature : {}'.format(purpose, message))
        signature = sig_obj.get('signature')
        return web3.eth.account.recoverHash(message_hash=message_hash, signature=signature) == address
    except TypeError:
        return False
    except ValueError:
        return False

