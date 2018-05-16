
from flask import Blueprint, request
from modules.ipfs import RelayIpfs
from modules.web3 import get_web3
from modules.muzika_contract import MuzikaContractHandler
from modules.signature import validate_signature
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
        "address": artist wallet address string (public-key hash),
        "price": uint256,
        "encrypted": true | false,
        "signature": signature object for validation
    }

    Server downloads the paper file by its IPFS process from the client IPFS node and it creates a muzika contract
    for creating a paper in the block chain network.

    Server must have an IPFS node and it pins the object file for spreading the paper file.
    """
    json_form = request.get_json(force=True, silent=True)
    file_hash = json_form.get('hash')
    wallet_address = json_form.get('address')
    price = json_form.get('price')
    encrypted = json_form.get('encrypted', False)
    sig_obj = json_form.get('signature')

    # check signature validation
    web3 = get_web3()
    if not validate_signature(web3, wallet_address, sig_obj):
        return helper.response_err(ER.INVALID_SIGNATURE, ER.INVALID_SIGNATURE_MSG)

    # check request json
    if not isinstance(file_hash, str) or not isinstance(price, int) or not isinstance(encrypted, bool):
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    # TODO : check artist

    # pin the file for spreading out the paper
    relay_ipfs = RelayIpfs()
    api = relay_ipfs.get_connection()
    # TODO : process if failed to pin (timeout problem)
    api.pin_add(file_hash)

    # create a paper contract
    contract_handler = MuzikaContractHandler()
    paper_contract = contract_handler.get_contract(web3, 'MuzikaPaperContract')

    heartbeat_timeout = 7 * 24 * 3600
    tx_hash = paper_contract.constructor(wallet_address, file_hash, price, heartbeat_timeout).transact()

    return helper.response_ok({'status': 'success'})

