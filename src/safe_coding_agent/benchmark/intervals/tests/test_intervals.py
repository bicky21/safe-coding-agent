import pytest

from solution import merge_intervals


@pytest.mark.parametrize("intervals, expected", [
    ([], []),
    ([[1, 3], [2, 6], [8, 10], [15, 18]], [[1, 6], [8, 10], [15, 18]]),
    ([[1, 4], [4, 5]], [[1, 5]]),
    ([[5, 7], [1, 2], [2, 3]], [[1, 3], [5, 7]]),
    ([[1, 10], [2, 3], [4, 5]], [[1, 10]]),
])
def test_merge_intervals(intervals, expected):
    assert merge_intervals(intervals) == expected
