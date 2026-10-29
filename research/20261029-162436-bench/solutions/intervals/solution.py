from __future__ import annotations
from typing import List

def merge_intervals(intervals: List[List[int]]) -> List[List[int]]:
    """
    Merge all overlapping or touching intervals.

    Parameters
    ----------
    intervals : List[List[int]]
        A list of intervals, each represented as a two-element list [start, end].
        Intervals may be unsorted and may overlap or touch.

    Returns
    -------
    List[List[int]]
        A new list of merged intervals sorted by start value.
        Intervals that only touch (e.g., [1, 2] and [2, 3]) are merged into a single interval.
    """
    if not intervals:
        return []

    # Sort intervals by start value
    sorted_intervals = sorted(intervals, key=lambda x: x[0])

    merged: List[List[int]] = []
    current_start, current_end = sorted_intervals[0]

    for start, end in sorted_intervals[1:]:
        # If the current interval overlaps or touches the next one, merge them
        if start <= current_end:
            current_end = max(current_end, end)
        else:
            merged.append([current_start, current_end])
            current_start, current_end = start, end

    # Append the last interval
    merged.append([current_start, current_end])

    return merged