"""
Solution for merging overlapping or touching intervals.

The function `merge_intervals` takes a list of intervals, where each interval is
represented as a two-element list `[start, end]`. It merges all intervals that
overlap or touch (i.e., where the end of one interval is greater than or equal
to the start of the next) and returns a new list of merged intervals sorted
by their start values.

Example:
    >>> merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]])
    [[1, 6], [8, 10], [15, 18]]
"""

from __future__ import annotations

from typing import List


def merge_intervals(intervals: List[List[int]]) -> List[List[int]]:
    """
    Merge all overlapping or touching intervals.

    Parameters
    ----------
    intervals : List[List[int]]
        A list of intervals, each represented as a list of two integers
        `[start, end]`. The list may be unsorted and may contain duplicate
        or nested intervals.

    Returns
    -------
    List[List[int]]
        A new list of merged intervals sorted by start value. Each interval
        is represented as a list `[start, end]`.

    Notes
    -----
    - Intervals that only touch (e.g., `[1, 2]` and `[2, 3]`) are merged.
    - If the input list is empty, an empty list is returned.
    - The function does not modify the input list.
    """
    if not intervals:
        return []

    # Sort intervals by start value. If starts are equal, sort by end.
    sorted_intervals = sorted(intervals, key=lambda x: (x[0], x[1]))

    merged: List[List[int]] = []
    current_start, current_end = sorted_intervals[0]

    for start, end in sorted_intervals[1:]:
        # If the current interval overlaps or touches the next one,
        # extend the current interval's end if necessary.
        if start <= current_end:
            current_end = max(current_end, end)
        else:
            # No overlap; append the current interval and start a new one.
            merged.append([current_start, current_end])
            current_start, current_end = start, end

    # Append the last interval.
    merged.append([current_start, current_end])

    return merged