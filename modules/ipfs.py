
import ipfsapi
from config import IPFSConfig


class RelayIpfs:
    """
    Relay IPFS is a IPFS node that spreads the artists' papers. Since IPFS node in the browser doesn't spread the file
    itself, this helps the clients(artists) uploaded files to be spread out more rapidly.
    """
    def __init__(self):
        self.api = ipfsapi.connect(IPFSConfig.node_address, IPFSConfig.port)

    def get_connection(self):
        return self.api
