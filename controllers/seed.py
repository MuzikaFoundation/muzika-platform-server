
from flask import Blueprint

from modules.response import helper

blueprint = Blueprint('seed', __name__, url_prefix='/api')


@blueprint.route('/seed/ipfs')
def _get_ipfs_node():
    """
    Returns an IPFS node that uploads contract files to IPFS.
    """
    # TODO: seed the IPFS node by DNS?
    seed_list = [
        '/ip4/52.78.36.21/tcp/4004/ws/ipfs/QmSMbmF2oZhVuu77vV7iWKiuBuEH6npAJYamq7Kgor5Eow'
    ]

    return helper.response_ok(seed_list)
