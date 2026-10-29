import re

# Regular expression to match the duration string.
# It allows optional whitespace between parts and is case-insensitive.
# The order of units is enforced by the order of optional groups.
_DUR_PATTERN = re.compile(
    r"""
    ^\s*                                   # Optional leading whitespace
    (?:(?P<days>\d+)\s*d\s*)?              # Optional days
    (?:(?P<hours>\d+)\s*h\s*)?             # Optional hours
    (?:(?P<minutes>\d+)\s*m\s*)?           # Optional minutes
    (?:(?P<seconds>\d+)\s*s\s*)?           # Optional seconds
    \s*$                                   # Optional trailing whitespace
    """,
    re.IGNORECASE | re.VERBOSE
)

def parse_duration(s: str) -> int:
    """
    Convert a duration string into total seconds.

    Parameters
    ----------
    s : str
        Duration string, e.g. '1h30m', '2d 4h', '45s', etc.
        Units are d (days), h (hours), m (minutes), s (seconds).
        Units are case-insensitive and may appear at most once
        in the order d, h, m, s. Spaces between parts are allowed.

    Returns
    -------
    int
        Total number of seconds represented by the duration.

    Raises
    ------
    ValueError
        If the string is empty, does not contain any unit,
        contains a unit without a preceding number, contains
        repeated units, or has units out of order.
    """
    if not isinstance(s, str):
        raise ValueError("Input must be a string")

    match = _DUR_PATTERN.fullmatch(s)
    if not match:
        raise ValueError(f"Invalid duration format: {s!r}")

    # Ensure that at least one unit is present
    if not any(match.group(g) for g in ('days', 'hours', 'minutes', 'seconds')):
        raise ValueError(f"Duration string must contain at least one unit: {s!r}")

    # Extract groups; if a group is missing, default to 0
    days = int(match.group('days')) if match.group('days') else 0
    hours = int(match.group('hours')) if match.group('hours') else 0
    minutes = int(match.group('minutes')) if match.group('minutes') else 0
    seconds = int(match.group('seconds')) if match.group('seconds') else 0

    # Compute total seconds
    total_seconds = (
        days * 86400 +
        hours * 3600 +
        minutes * 60 +
        seconds
    )

    return total_seconds