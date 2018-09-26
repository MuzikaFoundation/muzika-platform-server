
import ecdsa
from ecdsa.util import string_to_number
from ecdsa.numbertheory import square_root_mod_prime
from ecdsa import ellipticcurve


def uncompress_public_key(public_key):
    """
    Uncompress the compressed public key.

    :param public_key: compressed public key
    :return: uncompressed public key
    """
    is_even = public_key.startswith(b'\x02')
    x = string_to_number(public_key[1:])

    curve = ecdsa.NIST256p.curve
    order = ecdsa.NIST256p.order
    p = curve.p()
    alpha = (pow(x, 3, p) + (curve.a() * x) + curve.b()) % p

    beta = square_root_mod_prime(alpha, p)

    if is_even == bool(beta & 1):
        y = p - beta
    else:
        y = beta

    point = ellipticcurve.Point(curve, x, y, order)
    from ecdsa.util import number_to_string
    return b''.join([number_to_string(point.x(), order), number_to_string(point.y(), order)])
