import re

TX_HASH_REGEXP = re.compile('^0x([A-Fa-f0-9]{64})$')
ETH_ADDRESS_REGEXP = re.compile('^0x([A-Fa-f0-9]{40})$')


def txhash_validation(txhash):
    return bool(TX_HASH_REGEXP.match(txhash))


def eth_address_validation(address):
    return bool(ETH_ADDRESS_REGEXP.match(address))
