
from web3 import Web3

from config import Web3ProviderConfig


def get_default_provider():
    """
    :return: default HTTPProvider (endpoint url from config.py)
    """
    return Web3.HTTPProvider(
        Web3ProviderConfig.endpoint_url,
        request_kwargs={
            'timeout': Web3ProviderConfig.timeout
        }
    )


def get_web3(provider=None):
    """
    Returns web3 instance for backend interacting with block chain network. If not setting provider parameter, bring
    configuration from config.py.
    """
    return Web3(provider) if provider else Web3(get_default_provider())

