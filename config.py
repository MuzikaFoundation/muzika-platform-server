
"""
# Config.py

 Global constants for server configuration.
"""
import os
import json


class WebServerConfig:
    """
    Global constants for Web backend server.
    """
    host = 'localhost'
    port = 7001


class IPFSConfig:
    """
    Global constants for IPFS configuration.

    The server's IPFS must support websocket address. For supporting websocket address Edit IPFS config
    (the file path may be ~/.ipfs/config).
    reference : https://github.com/ipfs/js-ipfs/tree/master/examples/circuit-relaying
    """
    node_address = '127.0.0.1'
    port = 4004


class Web3ProviderConfig:
    """
    Global constants for web3 provider for interacting with ethereum block chain.
    """
    endpoint_url = \
        'http://localhost:8545' if os.environ.get('ENV') != 'production' \
        else 'https://api.myetherapi.com/eth'

    timeout = 5


class MuzikaContractConfig:
    """
    Global constants for Muzika contracts.
    """
    build_path = './muzika-contract/build/contracts'
