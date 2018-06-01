
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
        {
            'APIServer': 'http://52.78.36.21:7002',
            'ID': '/ip4/52.78.36.21/tcp/4001/ipfs/QmZtphDfarH8XcjTM6ZVW6kGp3krqsCnYVJWmtao7N6nYf'
        },
        {
            'APIServer': 'http://52.78.36.21:7002',
            'ID': '/ip4/52.78.36.21/tcp/4004/ws/ipfs/QmZtphDfarH8XcjTM6ZVW6kGp3krqsCnYVJWmtao7N6nYf'
        },
    ]

    return helper.response_ok(seed_list)
