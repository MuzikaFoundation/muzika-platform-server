
"""
# Config.py

 Global constants for server configuration.
"""
import os


class WebServerConfig:
    """
    Global constants for Web backend server.
    """
    host = 'localhost'
    port = 7001
    timezone = 'UTC'
    issuer = 'http://muzika.network'


class IPFSConfig:
    """
    Global constants for IPFS configuration.

    The server's IPFS must support websocket address. For supporting websocket address Edit IPFS config
    (the file path may be ~/.ipfs/config).
    reference : https://github.com/ipfs/js-ipfs/tree/master/examples/circuit-relaying
    """
    node_address = 'localhost'
    port = 5001


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


class SignMessageConfig:
    """
    Global constants for sign message
    """
    unsigned_message_expired_time = 60          # 1 minute
    signed_message_expired_time = 24 * 60 * 60  # 1 day


class CacheConfig:
    """
    Global constants for redis
    """
    cache_type = 'redis' if os.environ.get('ENV') in ['production', 'stage'] else 'local'
    host = 'localhost'
    port = 6379         # ignored if local cache
    key_prefix = 'muzika-redis-cache'
