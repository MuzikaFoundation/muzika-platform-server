
"""
# Config.py

 Global constants for server configuration.
"""


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
