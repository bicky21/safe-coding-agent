import pytest

from solution import spiral_ccw


@pytest.mark.parametrize("n, expected", [
    (0, []),
    (1, [[1]]),
    (2, [[1, 4], [2, 3]]),
    (3, [[1, 8, 7], [2, 9, 6], [3, 4, 5]]),
    (4, [[1, 12, 11, 10], [2, 13, 16, 9], [3, 14, 15, 8], [4, 5, 6, 7]]),
])
def test_spiral_ccw(n, expected):
    assert spiral_ccw(n) == expected
