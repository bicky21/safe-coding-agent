"""
Utility module for parsing duration strings into seconds.

The main function `parse_duration` accepts a string representation of a duration
(e.g. "1h30m", "2d 3h", "45s") and returns the total number of seconds as an
integer. The string may contain the units days (d), hours (h), minutes (m),
and seconds (s) in that order, each appearing at most once. Spaces between
components are allowed. Any deviation from the expected format raises a
ValueError.
"""

import re
from typing import Dict

__all__ = ["parse_duration"]


def parse_duration(s: str) -> int:
    """
    Convert a duration string into total seconds.

    Parameters
    ----------
    s : str
        Duration string containing optional whitespace and units in the
        order d, h, m, s. Units are case-insensitive. Each unit may appear
        at most once.

    Returns
    -------
    int
        Total number of seconds represented by the duration.

    Raises
    ------
    ValueError
        If the input string is empty, contains invalid characters,
        has units out of order, repeats a unit, or has a number without a
        unit (or vice versa).
    """
    if not isinstance(s, str):
        raise ValueError("Input must be a string")

    # Remove all whitespace for easier processing
    cleaned = "".join(s.split())
    if not cleaned:
        raise ValueError("Empty duration string")

    # Regular expression to capture a number followed by a unit
    pattern = re.compile(r"(?i)(\d+)([dhms])")
    matches = list(pattern.finditer(cleaned))

    if not matches:
        raise ValueError("No valid duration components found")

    # Ensure that the entire cleaned string is consumed by the matches
    concatenated = "".join(m.group(0) for m in matches)
    if concatenated != cleaned:
        raise ValueError("Invalid format or unknown characters in duration")

    # Order enforcement: d -> h -> m -> s
    order = {"d": 0, "h": 1, "m": 2, "s": 3}
    seen_units = set()
    last_index = -1

    total_seconds = 0
    unit_to_seconds: Dict[str, int] = {"d": 86400, "h": 3600, "m": 60, "s": 1}

    for match in matches:
        number_str, unit = match.group(1), match.group(2).lower()

        # Check for repeated units
        if unit in seen_units:
            raise ValueError(f"Repeated unit '{unit}' in duration")
        seen_units.add(unit)

        # Enforce order
        current_index = order[unit]
        if current_index <= last_index:
            raise ValueError(f"Unit '{unit}' out of order in duration")
        last_index = current_index

        # Convert number to integer and validate
        try:
            value = int(number_str)
        except ValueError:
            raise ValueError(f"Invalid number '{number_str}' in duration")

        if value < 0:
            raise ValueError(f"Negative value '{value}' not allowed in duration")

        total_seconds += value * unit_to_seconds[unit]

    return total_seconds