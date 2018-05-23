
def check_address_format(address):
    if len(address) != 42 or address[:2] != '0x':
        return False

    for ch in address[2:]:
        if ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890":
            return False

    return True
