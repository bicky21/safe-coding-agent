"""
Roman numeral to integer conversion.

This module provides a single function `roman_to_int` that converts a Roman numeral
string into its integer representation. The implementation follows the standard
rules for Roman numerals, including subtractive notation (e.g., IV = 4, IX = 9,
XL = 40, XC = 90, CD = 400, CM = 900).

The function is tolerant of an empty string, returning 0 in that case. It
expects the input to be a string containing only the characters I, V, X, L,
C, D, and M in uppercase. No validation of malformed numerals is performed
beyond the basic conversion logic.

Example:
    >>> roman_to_int('MCMXCIV')
    1994
"""

from __future__ import annotations

__all__ = ["roman_to_int"]


def roman_to_int(s: str) -> int:
    """
    Convert a Roman numeral string to an integer.

    Parameters
    ----------
    s : str
        Roman numeral string (e.g., 'MCMXCIV').

    Returns
    -------
    int
        The integer value of the Roman numeral.

    Notes
    -----
    The function handles the standard Roman numeral symbols:
        I  -> 1
        V  -> 5
        X  -> 10
        L  -> 50
        C  -> 100
        D  -> 500
        M  -> 1000

    Subtractive pairs are recognized:
        IV -> 4, IX -> 9, XL -> 40, XC -> 90, CD -> 400, CM -> 900

    An empty string returns 0. The function does not perform extensive
    validation of malformed numerals; it simply applies the conversion
    algorithm.
    """
    if not s:
        return 0

    # Mapping of single Roman numerals to their integer values.
    roman_map = {
        "I": 1,
        "V": 5,
        "X": 10,
        "L": 50,
        "C": 100,
        "D": 500,
        "M": 1000,
    }

    total = 0
    i = 0
    n = len(s)

    while i < n:
        # Current numeral value
        curr_val = roman_map.get(s[i], 0)

        # Look ahead to the next numeral if it exists
        if i + 1 < n:
            next_val = roman_map.get(s[i + 1], 0)
            if curr_val < next_val:
                # Subtractive pair detected
                total += next_val - curr_val
                i += 2
                continue

        # Regular addition
        total += curr_val
        i += 1

    return total