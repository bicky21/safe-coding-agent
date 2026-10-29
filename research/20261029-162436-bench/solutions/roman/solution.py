"""
Roman numeral to integer conversion.

This module provides a single function `roman_to_int` that converts a Roman numeral
string into its integer representation. The implementation follows the standard
rules for Roman numerals, including subtractive notation (e.g., IV = 4, IX = 9,
XL = 40, XC = 90, CD = 400, CM = 900).

The function is tolerant of an empty string, returning 0 in that case. It
expects the input to be a string containing only the characters I, V, X, L,
C, D, and M in uppercase. If the input contains any other characters, a
`ValueError` is raised.

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

    Raises
    ------
    ValueError
        If the input string contains characters other than the standard Roman
        numeral symbols (I, V, X, L, C, D, M).

    Notes
    -----
    The function implements the classic subtractive notation:
        - IV = 4
        - IX = 9
        - XL = 40
        - XC = 90
        - CD = 400
        - CM = 900

    An empty string is considered to represent the value 0.
    """
    if not s:
        return 0

    # Mapping of single Roman numeral characters to their integer values.
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
    prev_value = 0

    # Process the string from right to left to simplify subtractive logic.
    for char in reversed(s):
        if char not in roman_map:
            raise ValueError(f"Invalid Roman numeral character: {char!r}")

        value = roman_map[char]
        if value < prev_value:
            # Subtractive case: subtract this value.
            total -= value
        else:
            # Additive case: add this value.
            total += value
            prev_value = value

    return total