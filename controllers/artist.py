
from flask import Blueprint, request
from modules.ipfs import RelayIpfs
from modules.web3 import get_web3
from modules.response import helper
from modules.response import error_constants as ER

blueprint = Blueprint('artist', __name__, url_prefix='/api')


@blueprint.route('/paper', methods=['PUT'])
def _upload_paper():
    """
    Uploads a paper file from client.

    json form:
    {
        "hash": file hash string,
        "address" : artist wallet address string (public-key hash)
    }

    Server downloads the paper file by its IPFS process from the client IPFS node and it creates a muzika contract
    for creating a paper in the block chain network.

    Server must have an IPFS node and it pins the object file for spreading the paper file.
    """
    json_form = request.get_json(force=True, silent=True)
    file_hash = json_form.get('hash')
    wallet_address = json_form.get('address')

    # check request json
    if not isinstance(file_hash, str):
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    # TODO : check artist

    # pin the file for spreading out the paper
    relay_ipfs = RelayIpfs()
    api = relay_ipfs.get_connection()
    # TODO : process if failed to pin (timeout problem)
    api.pin_add(file_hash)

    # TODO : create a contract for generating paper in block chain network
    web3 = get_web3()

    return helper.response_ok({'status': 'success'})

