from Crypto.PublicKey import RSA
from flask import Blueprint, request, make_response

from modules.block.block import Block
from modules.block.block_request import BlockRequest
from modules.ipfs import RelayIpfs
from modules.login import jwt_check
from modules.response import error_constants as ER
from modules.response import helper
import base64

blueprint = Blueprint('paper_test', __name__, url_prefix='/api/test')

"""
 This APIs are only for development. The production environment should not support these APIs.
"""


@blueprint.route('/paper/download', methods=['POST'])
def _get_paper_file():
    """
    Tests to download a paper. It does not check contract. The requester has a private key and a public key, call with
    only public key, and the server responses the data with the encrypted data with the private key.

    json form:
    {
        "public_key": public key for encryption
    }
    """
    json_form = request.get_json(force=True, silent=True)
    public_key = json_form.get('public_key')
    test_data = b'Paper test download!' * 1000

    # not support downloading without encryption
    if not isinstance(public_key, str):
        return ''

    # parse public key
    try:
        public_key = RSA.import_key(public_key)
    except ValueError:
        # if invalid PEM format, return nothing
        return ''

    # download from bucket
    ipfs = RelayIpfs().get_connection()
    hash = ipfs.add_bytes(test_data, opts={'only-hash': True})
    print(hash)

    block = Block(data=test_data, hash=hash)
    block_request = BlockRequest(block_hash=hash, public_key=public_key)
    encrypted_block = block_request.encrypt(block)

    response = make_response(encrypted_block.encrypted_key + encrypted_block.data)
    response.headers['content-length'] = len(encrypted_block.encrypted_key + encrypted_block.data)
    response.headers['content-type'] = 'text/plain'
    return response
