"""
Solution for nth_weekday problem.

The function nth_weekday returns the day of the month for the nth occurrence
of a given weekday in a specified month and year. Positive n counts from the
beginning of the month, negative n counts from the end. n=0 or a non-existent
occurrence raises ValueError.
"""

import calendar
from typing import Final

__all__: Final = ["nth_weekday"]


def nth_weekday(year: int, month: int, weekday: int, n: int) -> int:
    """
    Return the day of the month for the nth occurrence of a weekday.

    Parameters
    ----------
    year : int
        The year (e.g., 2023).
    month : int
        The month (1-12).
    weekday : int
        The weekday (0=Monday, 6=Sunday).
    n : int
        The occurrence number. Positive values count from the start of the
        month, negative values count from the end. n=0 is invalid.

    Returns
    -------
    int
        The day of the month (1-31) corresponding to the nth occurrence.

    Raises
    ------
    ValueError
        If n is 0 or the requested occurrence does not exist in the month.
    """
    if n == 0:
        raise ValueError("n must not be zero")

    # Validate weekday range
    if not 0 <= weekday <= 6:
        raise ValueError("weekday must be in 0..6")

    # Get first weekday of the month and number of days in month
    first_weekday, month_days = calendar.monthrange(year, month)

    if n > 0:
        # Day of the first occurrence of the desired weekday
        first_occurrence_day = 1 + (weekday - first_weekday) % 7
        # Compute nth occurrence
        day = first_occurrence_day + (n - 1) * 7
        if day > month_days:
            raise ValueError("The requested occurrence does not exist")
        return day
    else:
        # Compute last weekday of the month
        last_weekday_of_month = (first_weekday + month_days - 1) % 7
        # Day of the last occurrence of the desired weekday
        last_occurrence_day = month_days - (last_weekday_of_month - weekday) % 7
        # Compute nth from the end
        day = last_occurrence_day + (n + 1) * 7
        if day < 1:
            raise ValueError("The requested occurrence does not exist")
        return day