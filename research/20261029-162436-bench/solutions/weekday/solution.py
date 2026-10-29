"""
Solution for nth_weekday problem.

Provides a function `nth_weekday` that returns the day of the month for the
n-th occurrence of a given weekday in a specified month and year.

The function uses the `calendar` module to determine month lengths and
weekday positions. It validates inputs and raises `ValueError` for
invalid arguments or when the requested occurrence does not exist.
"""

import calendar
from typing import Final

# Constants for weekday indices
MONDAY: Final[int] = 0
TUESDAY: Final[int] = 1
WEDNESDAY: Final[int] = 2
THURSDAY: Final[int] = 3
FRIDAY: Final[int] = 4
SATURDAY: Final[int] = 5
SUNDAY: Final[int] = 6


def nth_weekday(year: int, month: int, weekday: int, n: int) -> int:
    """
    Return the day of the month for the n-th occurrence of a given weekday.

    Parameters
    ----------
    year : int
        The year (e.g., 2023).
    month : int
        The month (1-12).
    weekday : int
        The weekday index (0=Monday, 6=Sunday).
    n : int
        The occurrence number:
            * n > 0 : the n-th occurrence from the start of the month.
            * n < 0 : the |n|-th occurrence from the end of the month.
            * n == 0 : invalid, raises ValueError.

    Returns
    -------
    int
        The day of the month (1-31) corresponding to the requested
        occurrence.

    Raises
    ------
    ValueError
        If `n` is 0, if `weekday` is not in 0..6, or if the requested
        occurrence does not exist in the specified month.
    """
    # Validate weekday
    if not 0 <= weekday <= 6:
        raise ValueError(f"weekday must be in 0..6, got {weekday}")

    # Validate n
    if n == 0:
        raise ValueError("n must not be zero")

    # Get first weekday of the month and number of days in month
    first_weekday, month_days = calendar.monthrange(year, month)

    # Compute the first occurrence of the desired weekday
    offset_first = (weekday - first_weekday) % 7
    first_occurrence_day = 1 + offset_first

    if n > 0:
        # n-th occurrence from the start
        day = first_occurrence_day + (n - 1) * 7
        if day > month_days:
            raise ValueError(
                f"{n}-th occurrence of weekday {weekday} does not exist "
                f"in {year}-{month:02d}"
            )
        return day

    # n < 0: occurrence from the end
    # Compute the weekday of the last day of the month
    last_weekday = (first_weekday + month_days - 1) % 7
    offset_last = (last_weekday - weekday) % 7
    last_occurrence_day = month_days - offset_last

    day = last_occurrence_day + (n + 1) * 7  # n is negative
    if day < 1:
        raise ValueError(
            f"{n}-th occurrence of weekday {weekday} does not exist "
            f"in {year}-{month:02d}"
        )
    return day