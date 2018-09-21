from modules.response.helper import deprecated


@deprecated
def check_address_format(address):
    """
    Deprecated since muzika supports ethereum and ontology protocol. This only
    checks the address is ethereum account format, so use `check_eth_address_format`
    if checking ethereum account or use `check_ont_address_format` to check ontology
    account format.
    :param address: account address to check.
    :return: True if valid format or false.
    """
    if len(address) != 42 or address[:2] != '0x':
        return False

    for ch in address[2:]:
        if ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890":
            return False

    return True


def check_eth_address_format(address):
    """
    Checks the address is ethereum account address format (hex string) or not.
    :param address: account address to check.
    :return: True if valid format or false.
    """
    if len(address) != 42 or address[:2] != '0x':
        return False

    for ch in address[2:]:
        if ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890":
            return False

    return True


def check_ont_address_format(address):
    """
    Checks the address is ontology account address format (base58) or not.
    :param address: account address to check.
    :return: True if valid format or false.
    """
    if len(address) != 34:
        return False

    for ch in address:
        if ch not in '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz':
            return False

    return True
