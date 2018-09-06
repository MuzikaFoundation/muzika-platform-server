
import requests
from flask import Blueprint

from modules.response import helper
from modules.cache import MuzikaCache

blueprint = Blueprint('price', __name__, url_prefix='/api')


@blueprint.route('/price/eth')
def _get_eth_price():
    """
    Returns the ethereum price
    """
    cache = MuzikaCache()
    eth_price = cache().get('/price/eth')

    if not eth_price:
        eth_price = requests.get('https://api.etherscan.io/api?module=stats&action=ethprice').json()
        cache().set('/price/eth', eth_price, 1)
    return helper.response_ok(eth_price['result'])
