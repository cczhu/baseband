# Licensed under the GPLv3 - see LICENSE
from __future__ import division, unicode_literals, print_function

import numpy as np

__all__ = ['bcd_decode', 'bcd_encode', 'CRC']


def bcd_decode(value):
    try:
        # Far faster than my routine for scalars
        return int('{:x}'.format(value))
    except ValueError:  # Might be an array (older python versions)
        if not isinstance(value, np.ndarray):
            raise ValueError("invalid BCD encoded value {0}={1}."
                             .format(value, hex(value)))
    except TypeError:  # Might still be an array (newer python versions)
        if not isinstance(value, np.ndarray):
            raise

    bcd = value
    factor = 1
    result = np.zeros_like(value)
    while np.any(bcd > 0):
        bcd, digit = divmod(bcd, 0x10)
        if np.any(digit > 9):
            if not np.isscalar(digit):
                value = value[digit > 9][0]
            raise ValueError("invalid BCD encoded value {0}={1}."
                             .format(value, hex(value)))
        result += digit * factor
        factor *= 10

    return result


def bcd_encode(value):
    try:
        # Far faster than my routine for scalars
        return int('{:d}'.format(value), base=16)
    except Exception:  # Maybe an array?
        if not isinstance(value, np.ndarray):
            raise

    result = np.zeros_like(value)
    result = 0
    factor = 1
    while np.any(value > 0):
        value, digit = divmod(value, 10)
        result += digit*factor
        factor *= 16
    return result


class CRC(object):
    """Cyclic Redundancy Check for a bitstream.

    See https://en.wikipedia.org/wiki/Cyclic_redundancy_check

    Once initialised, the instance can be used as a function that calculates
    the CRC, or one can use the `check` method to check that the CRC at the
    end of a stream is correct.

    Parameters
    ----------
    polynomial : int
        Binary encoded CRC divisor. For instance, that used by Mark 4 headers
        is 0x180f, or x^12 + x^11 + x^3 + x^2 + x + 1.
    """
    def __init__(self, polynomial):
        self.polynomial = polynomial
        self.pol_bin = np.array(
            [int(bit) for bit in '{:b}'.format(polynomial)], dtype=np.int8)

    def __len__(self):
        return self.pol_bin.size - 1

    def __call__(self, stream):
        """Calculate CRC for the given stream.

        Parameters
        ----------
        stream : array of bool or unsigned int
            The dimension is treated as the index into the bits.  For a single
            stream, the array should thus be of type `bool`. Integers represent
            multiple streams. E.g., for a 64-track Mark 4 header, the stream
            would be an array of ``np.uint64`` words.

        Returns
        -------
        crc : array
            The crc will have the same dtype as the input stream.
        """
        stream = np.hstack((stream, np.zeros((len(self),), stream.dtype)))
        return self._crc(stream)

    def check(self, stream):
        """Check that the CRC at the end of the stream is correct.

        Parameters
        ----------
        stream : array of bool or unsigned int
            The dimension is treated as the index into the bits.  For a single
            stream, the array should thus be of type `bool`. Integers represent
            multiple streams. E.g., for a 64-track Mark 4 header, the stream
            would be an array of ``np.uint64`` words.

        Returns
        -------
        ok : bool
             `True` if the calculated CRC is all zero (which should be the
             case if the CRC at the end of the stream is correct).
        """
        return np.all(self._crc(stream.copy()) == 0)

    def _crc(self, stream):
        """Internal function to calculate the CRC.

        Note that the stream is changed in-place.
        """
        pol_bin = (-self.pol_bin).astype(stream.dtype)
        for i in range(0, len(stream) - len(self)):
            stream[i:i+pol_bin.size] ^= (pol_bin & stream[i])
        return stream[-len(self):]


# PY2
def gcd(a, b):
    """Calculate the Greatest Common Divisor of a and b.

    Unless b==0, the result will have the same sign as b (so that when
    b is divided by it, the result comes out positive).
    """
    # Transliterated from Python 2.7's fractions.gcd.  Can just use math.gcd
    # once we dropy Python 2 support.
    while b:
        a, b = b, a % b
    return a


def lcm(a, b):
    """Calculate the least common multiple of a and b."""
    return abs(a * b) // gcd(a, b)
